"""
Google News Collector with Enhanced Logging

Collects logistics-related news from Google News RSS feeds.
Extended queries based on requirement.md specifications.
"""

import feedparser
import time
from typing import List, Dict, Any
from urllib.parse import quote_plus
from .base import BaseCollector

# Extended Google News search queries - requirement.md 기반
GOOGLE_NEWS_QUERIES = [
    # ===== 공급망 위기 및 disruption =====
    'supply chain disruption',
    'port strike',
    'shipping delay',
    'freight congestion',
    'logistics crisis',
    'supply chain crisis',
    'port closure',
    'shipping crisis',
    
    # ===== 물류 뉴스 일반 =====
    'logistics news',
    'freight rates',
    'container shipping',
    'air cargo news',
    'ocean freight',
    'trucking industry news',
    
    # ===== 운임 및 비용 =====
    'ocean freight rates',
    'air freight rates',
    'shipping costs increase',
    'freight rate surge',
    'container rates',
    'SCFI index',
    'BDI index',
    
    # ===== 주요 항로 및 요충지 =====
    'Suez Canal shipping',
    'Panama Canal transit',
    'Red Sea shipping crisis',
    'Strait of Malacca shipping',
    'Cape of Good Hope route',
    'Bab el-Mandeb strait',
    'Strait of Hormuz shipping',
    'Taiwan strait shipping',
    'South China Sea shipping',
    'Bosphorus strait shipping',
    'Gibraltar strait shipping',
    
    # ===== 정책 및 규제 =====
    'shipping regulations',
    'trade policy',
    'customs regulations',
    'import tariffs',
    'export restrictions',
    'IMO regulations shipping',
    'EU ETS shipping',
    'carbon neutral shipping',
    
    # ===== 지정학적 리스크 =====
    'geopolitical risk supply chain',
    'Ukraine war logistics',
    'Taiwan strait shipping risk',
    'Middle East shipping disruption',
    'sanctions shipping impact',
    'trade war logistics',
    'Houthi attack shipping',
    'Red Sea attack',
    
    # ===== 최신 트렌드 =====
    'nearshoring supply chain',
    'reshoring manufacturing',
    'EV battery supply chain',
    'semiconductor logistics',
    'green shipping',
    'autonomous shipping',
    'digital freight',
    
    # ===== 기후/환경 =====
    'weather shipping disruption',
    'drought Panama Canal',
    'hurricane port closure',
    'typhoon shipping delay',
    'climate change shipping',
    
    # ===== 노동 이슈 =====
    'dockworkers strike',
    'truckers strike',
    'warehouse workers strike',
    'labor shortage logistics',
    'port workers union',
    
    # ===== 주요 선사 (글로벌) =====
    'Maersk shipping news',
    'MSC Mediterranean shipping',
    'CMA CGM news',
    'COSCO shipping news',
    'Evergreen Marine news',
    'Hapag-Lloyd news',
    'ONE Ocean Network Express',
    'Yang Ming shipping',
    'ZIM shipping',
    'HMM Hyundai shipping',
    
    # ===== 주요 항만 (아시아) =====
    'Port of Shanghai',
    'Port of Singapore',
    'Port of Busan',
    'Port of Ningbo',
    'Port of Shenzhen',
    'Port of Hong Kong',
    'Port of Kaohsiung',
    'Port of Tokyo',
    
    # ===== 주요 항만 (유럽) =====
    'Port of Rotterdam',
    'Port of Antwerp',
    'Port of Hamburg',
    'Port of Valencia',
    'Port of Piraeus',
    
    # ===== 주요 항만 (미주) =====
    'Port of Los Angeles',
    'Port of Long Beach',
    'Port of New York',
    'Port of Savannah',
    'Port of Houston',
    
    # ===== 주요 공항 (화물) =====
    'Hong Kong airport cargo',
    'Memphis airport cargo',
    'Incheon airport cargo',
    'Shanghai Pudong cargo',
    'Dubai airport cargo',
    'Louisville airport cargo',
    'Anchorage airport cargo',
    
    # ===== 주요 제조업체/물류기업 =====
    'Amazon logistics',
    'FedEx shipping',
    'UPS freight',
    'DHL logistics',
    'Flexport news',
    'XPO Logistics',
    'CH Robinson',
    
    # ===== 무역 및 통관 =====
    'global trade news',
    'customs clearance',
    'trade disruption',
    'export logistics',
    'import delays',
    'tariff impact',
]


class GoogleNewsCollector(BaseCollector):
    """
    Collects news from Google News using RSS search feeds.
    Enhanced with detailed logging and extended query list.
    """
    
    GOOGLE_NEWS_RSS_BASE = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
    
    def __init__(self, queries: List[str] = None, max_per_query: int = 5):
        """
        Initialize Google News collector.
        
        Args:
            queries: List of search queries (uses defaults if None)
            max_per_query: Maximum articles to collect per query
        """
        super().__init__(name='GoogleNews', news_type='GLOBAL')
        self.queries = queries or GOOGLE_NEWS_QUERIES
        self.max_per_query = max_per_query
    
    def collect(self) -> List[Dict[str, Any]]:
        """
        Collect news from Google News for all configured queries.
        """
        all_articles = []
        seen_urls = set()
        
        self.log_start(len(self.queries))
        self.logger.info(f"   Max per query: {self.max_per_query}")
        
        for idx, query in enumerate(self.queries, 1):
            if idx % 10 == 1:
                self.logger.info(f"[{idx}/{len(self.queries)}] Processing queries...")
            
            try:
                articles = self._search_news(query)
                
                # Deduplicate
                new_count = 0
                for article in articles:
                    if article['url'] not in seen_urls:
                        seen_urls.add(article['url'])
                        all_articles.append(article)
                        new_count += 1
                    else:
                        self._stats['duplicates_removed'] += 1
                
                if new_count > 0:
                    self._stats['total_collected'] += new_count
                    self._stats['success_sources'] += 1
                    self.logger.debug(f"   ✅ '{query}': {new_count} articles")
                
            except Exception as e:
                self._stats['failed_sources'] += 1
                self.logger.debug(f"   ❌ '{query}': {e}")
            
            # Rate limiting - Google News 요청 간격
            time.sleep(0.3)
        
        self.log_complete()
        return all_articles
    
    def _search_news(self, query: str) -> List[Dict[str, Any]]:
        """Search Google News for a specific query."""
        articles = []
        
        encoded_query = quote_plus(query)
        url = self.GOOGLE_NEWS_RSS_BASE.format(query=encoded_query)
        
        feed = feedparser.parse(url)
        
        if feed.bozo and not feed.entries:
            raise Exception(f"Feed error: {feed.bozo_exception}")
        
        for entry in feed.entries[:self.max_per_query]:
            try:
                article = self._parse_entry(entry, query)
                if article:
                    articles.append(article)
            except Exception as e:
                self.logger.debug(f"Parse error: {e}")
        
        return articles
    
    def _parse_entry(self, entry, query: str) -> Dict[str, Any]:
        """Parse a Google News RSS entry."""
        url = getattr(entry, 'link', None)
        if not url:
            return None
        
        title = getattr(entry, 'title', None)
        if not title:
            return None
        title = self.clean_text(title)
        
        # Get summary
        summary = ''
        if hasattr(entry, 'summary'):
            summary = self.clean_text(entry.summary)
        elif hasattr(entry, 'description'):
            summary = self.clean_text(entry.description)
        summary = self.truncate_summary(summary, 500)
        
        # Parse published date
        published_at = None
        if hasattr(entry, 'published'):
            published_at = self.parse_datetime(entry.published)
        elif hasattr(entry, 'updated'):
            published_at = self.parse_datetime(entry.updated)
        
        # Extract source name from title (Google News format: "Title - Source")
        source_name = 'Google News'
        if ' - ' in title:
            parts = title.rsplit(' - ', 1)
            if len(parts) == 2:
                title = parts[0].strip()
                source_name = parts[1].strip()
        
        return {
            'title': title,
            'content_summary': summary,
            'source_name': source_name,
            'url': url,
            'published_at_utc': published_at,
            'news_type': 'GLOBAL',
            '_search_query': query,  # 어떤 쿼리로 수집되었는지 추적용
        }

