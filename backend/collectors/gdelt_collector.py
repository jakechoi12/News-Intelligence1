"""
GDELT Collector

Collects logistics-related crisis events from GDELT data.
Supports both local GDELT data files and direct API calls.
"""

import os
import sys
import re
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from pathlib import Path
from .base import BaseCollector
import logging

logger = logging.getLogger(__name__)

# Simple cache for fetched titles
_title_cache: Dict[str, str] = {}

# GDELT API endpoint for recent events
GDELT_GKG_URL = "https://api.gdeltproject.org/api/v2/doc/doc"


class GDELTCollector(BaseCollector):
    """
    Collects logistics-relevant crisis events from GDELT.
    
    Focuses on events with negative Goldstein scores that may
    indicate supply chain disruptions (conflicts, strikes, etc.)
    """
    
    # GDELT themes related to logistics/supply chain
    LOGISTICS_THEMES = [
        'SUPPLY_CHAIN', 'TRADE', 'PORTS', 'SHIPPING', 'CARGO',
        'SANCTIONS', 'EMBARGO', 'STRIKE', 'PROTEST', 'BLOCKADE',
        'MILITARY', 'CONFLICT', 'WAR', 'ATTACK', 'BOMB',
        'RED_SEA', 'SUEZ', 'PANAMA', 'STRAIT', 'CHOKEPOINT',
    ]
    
    def __init__(self, goldstein_threshold: float = -4.0, max_events: int = 50):
        """
        Initialize GDELT collector.
        
        Args:
            goldstein_threshold: Minimum Goldstein score for crisis detection
            max_events: Maximum events to collect
        """
        super().__init__(name='GDELTCollector')
        self.goldstein_threshold = goldstein_threshold
        self.max_events = max_events
    
    def collect(self) -> List[Dict[str, Any]]:
        """
        Collect crisis events from GDELT.
        
        Returns:
            List of event dictionaries formatted as news articles
        """
        articles = []
        
        self.log_start(len(self.LOGISTICS_THEMES))
        
        try:
            # First try local gdelt_backend if available
            articles = self._collect_from_backend()
            
            if not articles:
                # Fallback to GDELT API
                articles = self._collect_from_api()
            
            # Fetch actual titles from URLs
            if articles:
                self._fetch_titles_parallel(articles, max_workers=10)
            
            self.log_complete()
            
        except Exception as e:
            self.logger.error(f"GDELT collection error: {e}")
        
        return articles
    
    def _collect_from_backend(self) -> List[Dict[str, Any]]:
        """Try to collect from local gdelt_backend module."""
        try:
            # Import from same directory
            from . import gdelt_backend
            
            result = gdelt_backend.get_cached_alerts(
                goldstein_threshold=self.goldstein_threshold,
                max_alerts=self.max_events,
                sort_by='scale'
            )
            
            if 'error' in result:
                self.logger.warning(f"GDELT backend error: {result['error']}")
                return []
            
            alerts = result.get('alerts', [])
            articles = []
            
            for alert in alerts:
                try:
                    article = self._convert_alert_to_article(alert)
                    if article:
                        articles.append(article)
                except Exception as e:
                    self.logger.debug(f"Error converting alert: {e}")
            
            self.logger.info(f"Collected {len(articles)} events from GDELT backend")
            return articles
            
        except ImportError:
            self.logger.debug("gdelt_backend not available, will use API")
            return []
        except Exception as e:
            self.logger.debug(f"Error using gdelt_backend: {e}")
            return []
    
    def _collect_from_api(self) -> List[Dict[str, Any]]:
        """Collect from GDELT public API."""
        articles = []
        
        # Build search query
        query_terms = [
            "supply chain disruption",
            "shipping crisis",
            "port strike",
            "trade sanctions",
            "Red Sea attack",
        ]
        
        for query in query_terms[:3]:  # Limit queries
            try:
                params = {
                    'query': query,
                    'mode': 'artlist',
                    'maxrecords': min(10, self.max_events // 3),
                    'format': 'json',
                    'timespan': '7d',
                    'sort': 'hybridrel',
                }
                
                response = requests.get(GDELT_GKG_URL, params=params, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    for item in data.get('articles', [])[:10]:
                        article = {
                            'title': item.get('title', 'GDELT Event'),
                            'content_summary': item.get('seendate', ''),
                            'source_name': item.get('domain', 'GDELT'),
                            'url': item.get('url', ''),
                            'published_at_utc': self._parse_gdelt_date(item.get('seendate')),
                            'news_type': 'GLOBAL',
                            'country_tags': [],
                            'is_crisis': True,
                        }
                        articles.append(article)
                        self._stats['sources_success'] += 1
                        
            except Exception as e:
                self.logger.debug(f"GDELT API error for '{query}': {e}")
                self._stats['sources_failed'] += 1
        
        return articles
    
    def _parse_gdelt_date(self, date_str: str) -> Optional[str]:
        """Parse GDELT date format."""
        if not date_str:
            return None
        try:
            # GDELT format: YYYYMMDDHHMMSS
            if len(date_str) >= 8:
                dt = datetime.strptime(date_str[:8], '%Y%m%d')
                return dt.strftime('%Y-%m-%dT%H:%M:%SZ')
        except:
            pass
        return None
    
    def _convert_alert_to_article(self, alert: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Convert GDELT alert to article format."""
        source_url = alert.get('source_url') or alert.get('url') or ''
        
        # Build title
        actor1 = alert.get('actor1', '') or ''
        actor2 = alert.get('actor2', '') or ''
        category = alert.get('category', 'Crisis Event')
        location = alert.get('location', '')
        
        if actor1 and actor2:
            title = f"[GDELT] {actor1} - {actor2}: {category}"
        elif actor1:
            title = f"[GDELT] {actor1}: {category}"
        elif location:
            title = f"[GDELT] {location}: {category}"
        else:
            title = f"[GDELT] {category}"
        
        # Build summary
        goldstein = alert.get('goldstein_scale') or alert.get('scale') or 0
        
        summary_parts = []
        if location:
            summary_parts.append(f"Location: {location}.")
        summary_parts.append(f"Category: {category}.")
        if actor1:
            summary_parts.append(f"Involves: {actor1}.")
        
        summary = ' '.join(summary_parts) if summary_parts else f"GDELT event: {category}"
        
        # Parse date
        published_at = None
        date_str = alert.get('event_date') or alert.get('date')
        if date_str:
            try:
                if len(str(date_str)) == 8:
                    dt = datetime.strptime(str(date_str), '%Y%m%d')
                    published_at = dt.strftime('%Y-%m-%dT%H:%M:%SZ')
            except:
                pass
        
        # Country tags
        country_tags = []
        for field in ['actor1_country', 'actor2_country', 'country_code']:
            if alert.get(field) and alert[field] not in country_tags:
                country_tags.append(alert[field])
        
        return {
            'title': title,
            'content_summary': summary,
            'source_name': 'GDELT',
            'url': source_url,
            'published_at_utc': published_at,
            'news_type': 'GLOBAL',
            'country_tags': country_tags,
            'is_crisis': True,
            'goldstein_scale': goldstein,
            'avg_tone': alert.get('avg_tone'),
        }
    
    def _fetch_titles_parallel(self, articles: List[Dict[str, Any]], max_workers: int = 10):
        """Fetch actual titles from URLs in parallel."""
        needs_fetch = [
            (i, a) for i, a in enumerate(articles)
            if a.get('url') and a['url'].startswith('http') and '[GDELT]' in a.get('title', '')
        ]
        
        if not needs_fetch:
            return
        
        self.logger.info(f"Fetching titles for {len(needs_fetch)} GDELT articles...")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_idx = {
                executor.submit(self._fetch_title_from_url, a['url']): i
                for i, a in needs_fetch
            }
            
            fetched = 0
            for future in as_completed(future_to_idx, timeout=30):
                idx = future_to_idx[future]
                try:
                    title = future.result()
                    if title:
                        articles[idx]['title'] = title
                        fetched += 1
                except:
                    pass
        
        self.logger.info(f"Fetched {fetched} titles from URLs")
    
    def _fetch_title_from_url(self, url: str) -> Optional[str]:
        """Fetch title from URL."""
        global _title_cache
        
        if url in _title_cache:
            return _title_cache[url]
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; NewsBot/1.0)',
                'Accept': 'text/html',
            }
            
            response = requests.get(url, headers=headers, timeout=5)
            html = response.text[:10000]
            
            # Extract title
            match = re.search(r'<title[^>]*>([^<]+)</title>', html, re.IGNORECASE)
            if match:
                title = match.group(1).strip()
                title = re.sub(r'\s*[\|\-–—]\s*[^|\-–—]+$', '', title)
                if title and len(title) > 5:
                    _title_cache[url] = title
                    return title
            
            return None
            
        except:
            return None

