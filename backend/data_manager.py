"""
Data Manager for JSON Generation

Generates JSON files for frontend consumption:
- news_data.json
- economic_data.json
- map_data.json
- wordcloud_data.json
- alerts_data.json
- last_update.json
"""

import os
import json
import logging
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from collections import Counter

logger = logging.getLogger("data.manager")


class DataManager:
    """
    Manages data storage and JSON file generation.
    """
    
    def __init__(self, output_dir: str = "frontend/data"):
        """
        Initialize data manager.
        
        Args:
            output_dir: Directory to output JSON files
        """
        self.output_dir = output_dir
        self._ensure_dir()
        
        self.stats = {
            'total_articles': 0,
            'kr_count': 0,
            'global_count': 0,
            'crisis_count': 0,
            'categories': Counter(),
        }
    
    def _ensure_dir(self):
        """Ensure output directory exists"""
        os.makedirs(self.output_dir, exist_ok=True)
        logger.info(f"📁 Output directory: {self.output_dir}")
    
    def generate_all(self, articles: List[Dict[str, Any]], 
                     economic_data: Dict[str, Any] = None,
                     start_time: datetime = None) -> Dict[str, str]:
        """
        Generate all JSON files.
        
        Args:
            articles: List of analyzed article dictionaries
            economic_data: Economic indicator data
            start_time: Collection start time
            
        Returns:
            Dictionary of generated file paths
        """
        logger.info(f"{'='*60}")
        logger.info(f"📝 Generating JSON files")
        logger.info(f"   Output: {self.output_dir}")
        logger.info(f"{'='*60}")
        
        files = {}
        
        # Process articles
        processed_articles = self._process_articles(articles)
        
        # Generate news data
        files['news'] = self._generate_news_data(processed_articles)
        
        # Generate map data
        files['map'] = self._generate_map_data(processed_articles)
        
        # Generate wordcloud data
        files['wordcloud'] = self._generate_wordcloud_data(processed_articles)
        
        # Generate alerts data
        files['alerts'] = self._generate_alerts_data(processed_articles)
        
        # Generate economic data (use mock if not provided)
        if economic_data:
            files['economic'] = self._generate_economic_data(economic_data)
        else:
            files['economic'] = self._generate_mock_economic_data()
        
        # Generate last update info
        files['last_update'] = self._generate_last_update(start_time)
        
        logger.info(f"{'='*60}")
        logger.info(f"✅ JSON generation complete")
        logger.info(f"   Files generated: {len(files)}")
        logger.info(f"{'='*60}")
        
        return files
    
    def _process_articles(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process and prepare articles for output"""
        processed = []
        
        for article in articles:
            # Generate unique ID
            article_id = self._generate_id(article.get('url', ''))
            
            # Format datetime
            pub_date = article.get('published_at_utc')
            if isinstance(pub_date, datetime):
                pub_date_str = pub_date.strftime('%Y-%m-%dT%H:%M:%SZ')
            else:
                pub_date_str = pub_date
            
            collected_at = datetime.now(timezone.utc)
            
            processed_article = {
                'id': article_id,
                'title': article.get('title', ''),
                'content_summary': article.get('content_summary', ''),
                'source_name': article.get('source_name', ''),
                'url': article.get('url', ''),
                'published_at_utc': pub_date_str,
                'collected_at_utc': collected_at.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'news_type': article.get('news_type', 'GLOBAL'),
                'category': article.get('category', 'ETC'),
                'sentiment': article.get('sentiment', 'neutral'),
                'is_crisis': article.get('is_crisis', False),
                'country_tags': article.get('country_tags', []),
                'keywords': article.get('keywords', []),
            }
            
            # Add GDELT-specific fields if present
            if 'goldstein_scale' in article:
                processed_article['goldstein_scale'] = article['goldstein_scale']
            if 'avg_tone' in article:
                processed_article['avg_tone'] = article['avg_tone']
            if 'num_mentions' in article:
                processed_article['num_mentions'] = article['num_mentions']
            if 'num_sources' in article:
                processed_article['num_sources'] = article['num_sources']
            
            processed.append(processed_article)
            
            # Update stats
            self.stats['total_articles'] += 1
            if processed_article['news_type'] == 'KR':
                self.stats['kr_count'] += 1
            else:
                self.stats['global_count'] += 1
            if processed_article['is_crisis']:
                self.stats['crisis_count'] += 1
            self.stats['categories'][processed_article['category']] += 1
        
        # Sort by published date (newest first)
        processed.sort(
            key=lambda x: x.get('published_at_utc') or '',
            reverse=True
        )
        
        return processed
    
    def _generate_id(self, url: str) -> str:
        """Generate unique ID from URL"""
        return hashlib.md5(url.encode()).hexdigest()[:12]
    
    def _generate_news_data(self, articles: List[Dict[str, Any]]) -> str:
        """Generate news_data.json"""
        data = {
            'articles': articles,
            'total': len(articles),
            'kr_count': self.stats['kr_count'],
            'global_count': self.stats['global_count'],
            'crisis_count': self.stats['crisis_count'],
            'categories': dict(self.stats['categories']),
            'generated_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        }
        
        filepath = os.path.join(self.output_dir, 'news_data.json')
        self._write_json(filepath, data)
        logger.info(f"   ✅ news_data.json: {len(articles)} articles")
        return filepath
    
    def _generate_map_data(self, articles: List[Dict[str, Any]]) -> str:
        """Generate map_data.json with country-based crisis counts"""
        country_stats = Counter()
        country_articles = {}
        
        # Count by country (only crisis/negative articles)
        for article in articles:
            if article.get('is_crisis') or article.get('sentiment') == 'negative':
                for country in article.get('country_tags', []):
                    country_stats[country] += 1
                    if country not in country_articles:
                        country_articles[country] = []
                    if len(country_articles[country]) < 3:  # Max 3 articles per country
                        country_articles[country].append({
                            'title': article['title'],
                            'url': article['url'],
                        })
        
        # Format for map
        map_data = {
            'countries': [
                {
                    'code': code,
                    'count': count,
                    'risk_level': 'high' if count >= 5 else 'medium' if count >= 2 else 'low',
                    'articles': country_articles.get(code, []),
                }
                for code, count in country_stats.most_common(30)
            ],
            'total_crisis_countries': len(country_stats),
            'generated_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        }
        
        filepath = os.path.join(self.output_dir, 'map_data.json')
        self._write_json(filepath, map_data)
        logger.info(f"   ✅ map_data.json: {len(country_stats)} countries")
        return filepath
    
    def _generate_wordcloud_data(self, articles: List[Dict[str, Any]]) -> str:
        """Generate wordcloud_data.json with keyword frequencies"""
        keyword_counts = Counter()
        
        for article in articles:
            for keyword in article.get('keywords', []):
                keyword_counts[keyword.lower()] += 1
        
        # Format for wordcloud
        wordcloud_data = {
            'keywords': [
                {'text': word, 'count': count, 'size': min(count * 10, 100)}
                for word, count in keyword_counts.most_common(50)
            ],
            'total_keywords': len(keyword_counts),
            'generated_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        }
        
        filepath = os.path.join(self.output_dir, 'wordcloud_data.json')
        self._write_json(filepath, wordcloud_data)
        logger.info(f"   ✅ wordcloud_data.json: {len(keyword_counts)} keywords")
        return filepath
    
    def _generate_alerts_data(self, articles: List[Dict[str, Any]]) -> str:
        """Generate alerts_data.json with critical alerts"""
        # Filter crisis articles
        crisis_articles = [
            a for a in articles 
            if a.get('is_crisis') or (a.get('category') == 'Crisis')
        ]
        
        # Sort by severity (Goldstein scale if available, then by recency)
        crisis_articles.sort(
            key=lambda x: (x.get('goldstein_scale', 0), x.get('published_at_utc', '')),
            reverse=False  # Lower Goldstein = more severe
        )
        
        # Take top 10 alerts
        top_alerts = crisis_articles[:10]
        
        alerts_data = {
            'alerts': [
                {
                    'id': a['id'],
                    'title': a['title'],
                    'summary': a['content_summary'][:200] + '...' if len(a.get('content_summary', '')) > 200 else a.get('content_summary', ''),
                    'source_name': a['source_name'],
                    'url': a['url'],
                    'published_at_utc': a['published_at_utc'],
                    'category': a['category'],
                    'country_tags': a.get('country_tags', []),
                    'goldstein_scale': a.get('goldstein_scale'),
                    'severity': 'critical' if a.get('goldstein_scale', 0) <= -5 else 'high' if a.get('goldstein_scale', 0) <= -2 else 'medium',
                }
                for a in top_alerts
            ],
            'total_crisis': len(crisis_articles),
            'generated_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        }
        
        filepath = os.path.join(self.output_dir, 'alerts_data.json')
        self._write_json(filepath, alerts_data)
        logger.info(f"   ✅ alerts_data.json: {len(top_alerts)} alerts")
        return filepath
    
    def _generate_economic_data(self, economic_data: Dict[str, Any]) -> str:
        """Generate economic_data.json"""
        # Add timestamp
        economic_data['generated_at'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        
        filepath = os.path.join(self.output_dir, 'economic_data.json')
        self._write_json(filepath, economic_data)
        logger.info(f"   ✅ economic_data.json")
        return filepath
    
    def _generate_mock_economic_data(self) -> str:
        """Generate mock economic_data.json for demo"""
        import random
        
        def generate_data(base, variance, days=30):
            data = []
            value = base
            for i in range(days, -1, -1):
                date = datetime.now(timezone.utc) - __import__('datetime').timedelta(days=i)
                value = value + (random.random() - 0.5) * variance
                data.append({
                    'time': date.strftime('%Y-%m-%d'),
                    'value': round(value, 2)
                })
            return data
        
        economic_data = {
            'stock_index': {
                'items': {
                    'KOSPI': {'name': 'KOSPI', 'current': 2650.32, 'previous': 2640.15, 'change': 10.17, 'change_percent': 0.39, 'data': generate_data(2600, 50)},
                    'KOSDAQ': {'name': 'KOSDAQ', 'current': 820.45, 'previous': 815.20, 'change': 5.25, 'change_percent': 0.64, 'data': generate_data(800, 20)},
                    'S&P500': {'name': 'S&P 500', 'current': 5890.12, 'previous': 5875.30, 'change': 14.82, 'change_percent': 0.25, 'data': generate_data(5800, 80)},
                    'NASDAQ': {'name': 'NASDAQ', 'current': 19250.50, 'previous': 19180.20, 'change': 70.30, 'change_percent': 0.37, 'data': generate_data(19000, 200)},
                }
            },
            'exchange_rate': {
                'items': {
                    'USD': {'name': 'USD/KRW', 'current': 1432.50, 'previous': 1428.20, 'change': 4.30, 'change_percent': 0.30, 'data': generate_data(1420, 15)},
                    'EUR': {'name': 'EUR/KRW', 'current': 1485.30, 'previous': 1480.50, 'change': 4.80, 'change_percent': 0.32, 'data': generate_data(1470, 20)},
                    'JPY': {'name': 'JPY/KRW', 'current': 9.25, 'previous': 9.20, 'change': 0.05, 'change_percent': 0.54, 'data': generate_data(9.1, 0.2)},
                    'CNY': {'name': 'CNY/KRW', 'current': 196.50, 'previous': 195.80, 'change': 0.70, 'change_percent': 0.36, 'data': generate_data(195, 3)},
                }
            },
            'interest_rate': {
                'items': {
                    'KR': {'name': '한국 기준금리', 'current': 3.00, 'previous': 3.00, 'change': 0, 'change_percent': 0, 'data': generate_data(3.0, 0.05)},
                    'US': {'name': '미국 기준금리', 'current': 4.50, 'previous': 4.50, 'change': 0, 'change_percent': 0, 'data': generate_data(4.5, 0.05)},
                    'EU': {'name': 'EU 기준금리', 'current': 3.00, 'previous': 3.00, 'change': 0, 'change_percent': 0, 'data': generate_data(3.0, 0.05)},
                    'JP': {'name': '일본 기준금리', 'current': 0.25, 'previous': 0.25, 'change': 0, 'change_percent': 0, 'data': generate_data(0.25, 0.02)},
                }
            },
            'generated_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        }
        
        filepath = os.path.join(self.output_dir, 'economic_data.json')
        self._write_json(filepath, economic_data)
        logger.info(f"   ✅ economic_data.json (mock data)")
        return filepath
    
    def _generate_last_update(self, start_time: datetime = None) -> str:
        """Generate last_update.json with collection metadata"""
        now_utc = datetime.now(timezone.utc)
        
        # Calculate duration
        duration = 0
        if start_time:
            duration = (now_utc - start_time.replace(tzinfo=timezone.utc)).total_seconds()
        
        update_data = {
            'executed_at_utc': now_utc.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'executed_at_kst': (now_utc.replace(tzinfo=timezone.utc)).astimezone(
                timezone(offset=__import__('datetime').timedelta(hours=9))
            ).strftime('%Y-%m-%dT%H:%M:%S+09:00'),
            'total_collected': self.stats['total_articles'],
            'kr_count': self.stats['kr_count'],
            'global_count': self.stats['global_count'],
            'crisis_count': self.stats['crisis_count'],
            'categories': dict(self.stats['categories']),
            'duration_seconds': round(duration, 2),
            'success': True,
            'errors': [],
        }
        
        filepath = os.path.join(self.output_dir, 'last_update.json')
        self._write_json(filepath, update_data)
        logger.info(f"   ✅ last_update.json")
        return filepath
    
    def _write_json(self, filepath: str, data: Dict[str, Any]):
        """Write data to JSON file"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

