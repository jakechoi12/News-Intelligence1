"""
RSS Feed Collector with Enhanced Logging

Collects news from logistics RSS feeds with detailed progress tracking.
"""

import feedparser
import time
from typing import List, Dict, Any
from datetime import datetime, timezone
from .base import BaseCollector

# RSS Feed configurations - requirement.md 기반
# Note: 아래 피드들은 SSL/파싱 오류로 제거됨:
#   - Splash247 (SSL 인증서 오류)
#   - Port Technology (XML 파싱 오류)
#   - Reuters Business (DNS 오류)
#   - 코리아쉬핑가제트 (HTML 반환)
#   - 이데일리 (XML 파싱 오류)
RSS_FEEDS = {
    'global': [
        # 물류/공급망 전문
        {'name': 'The Loadstar', 'url': 'https://theloadstar.com/feed/', 'type': 'GLOBAL'},
        {'name': 'FreightWaves', 'url': 'https://www.freightwaves.com/feed', 'type': 'GLOBAL'},
        {'name': 'Supply Chain Dive', 'url': 'https://www.supplychaindive.com/feeds/news/', 'type': 'GLOBAL'},
        {'name': 'Air Cargo Week', 'url': 'https://aircargoweek.com/feed/', 'type': 'GLOBAL'},
        {'name': 'Supply Chain 247', 'url': 'https://www.supplychain247.com/rss/all/feeds', 'type': 'GLOBAL'},
        {'name': 'Global Trade Magazine', 'url': 'https://www.globaltrademag.com/feed/', 'type': 'GLOBAL'},
        {'name': 'Hellenic Shipping News', 'url': 'https://www.hellenicshippingnews.com/feed/', 'type': 'GLOBAL'},
        {'name': 'Container News', 'url': 'https://container-news.com/feed/', 'type': 'GLOBAL'},
        
        # 경제/금융
        {'name': 'CNBC World', 'url': 'https://www.cnbc.com/id/100727362/device/rss/rss.html', 'type': 'GLOBAL'},
        {'name': 'MarketWatch', 'url': 'https://feeds.marketwatch.com/marketwatch/topstories', 'type': 'GLOBAL'},
        {'name': 'BBC Business', 'url': 'https://feeds.bbci.co.uk/news/business/rss.xml', 'type': 'GLOBAL'},
        {'name': 'Bloomberg Markets', 'url': 'https://feeds.bloomberg.com/markets/news.rss', 'type': 'GLOBAL'},
    ],
    'korean': [
        # 물류/해운 전문
        {'name': '물류신문', 'url': 'https://www.klnews.co.kr/rss/allArticle.xml', 'type': 'KR'},
        {'name': '해양한국', 'url': 'https://www.monthlymaritimekorea.com/rss/allArticle.xml', 'type': 'KR'},
        {'name': '한국해운신문', 'url': 'https://www.maritimepress.co.kr/rss/allArticle.xml', 'type': 'KR'},
        {'name': '카고뉴스', 'url': 'https://www.cargonews.co.kr/rss/allArticle.xml', 'type': 'KR'},
        
        # 경제/금융
        {'name': '연합인포맥스', 'url': 'https://news.einfomax.co.kr/rss/allArticle.xml', 'type': 'KR'},
        {'name': '머니투데이', 'url': 'https://rss.mt.co.kr/mt_news.xml', 'type': 'KR'},
    ]
}


class RSSCollector(BaseCollector):
    """
    Collects news from RSS feeds with detailed progress logging.
    """
    
    def __init__(self, feed_type: str = 'all', timeout: int = 15):
        """
        Initialize RSS collector.
        
        Args:
            feed_type: 'global', 'korean', or 'all' (default)
            timeout: Request timeout in seconds
        """
        super().__init__(name='RSSCollector')
        self.feed_type = feed_type
        self.timeout = timeout
        self.feeds = self._get_feeds()
    
    def _get_feeds(self) -> List[Dict[str, str]]:
        """Get feed configurations based on feed_type"""
        if self.feed_type == 'global':
            return RSS_FEEDS['global']
        elif self.feed_type == 'korean':
            return RSS_FEEDS['korean']
        else:
            return RSS_FEEDS['global'] + RSS_FEEDS['korean']
    
    def collect(self) -> List[Dict[str, Any]]:
        """
        Collect news from all configured RSS feeds.
        """
        all_articles = []
        seen_urls = set()
        
        self.log_start(len(self.feeds))
        
        for idx, feed_config in enumerate(self.feeds, 1):
            feed_name = feed_config['name']
            feed_url = feed_config['url']
            
            self.logger.info(f"[{idx}/{len(self.feeds)}] Processing: {feed_name}")
            self.log_source_start(feed_name, feed_url)
            
            try:
                start_time = time.time()
                articles = self._collect_from_feed(feed_config)
                elapsed = time.time() - start_time
                
                # Deduplicate
                new_articles = []
                for article in articles:
                    if article['url'] not in seen_urls:
                        seen_urls.add(article['url'])
                        new_articles.append(article)
                    else:
                        self._stats['duplicates_removed'] += 1
                
                if new_articles:
                    all_articles.extend(new_articles)
                    self.log_source_success(feed_name, len(new_articles))
                    self.logger.debug(f"   ⏱️ Time: {elapsed:.2f}s")
                else:
                    self.log_source_empty(feed_name)
                    
            except Exception as e:
                self.log_source_failed(feed_name, str(e))
            
            # Rate limiting
            time.sleep(0.5)
        
        self.log_complete()
        return all_articles
    
    def _collect_from_feed(self, feed_config: Dict[str, str]) -> List[Dict[str, Any]]:
        """Collect articles from a single RSS feed."""
        articles = []
        
        # Parse the feed
        feed = feedparser.parse(
            feed_config['url'],
            request_headers={'User-Agent': 'NewsIntelligence/1.0'}
        )
        
        if feed.bozo and not feed.entries:
            raise Exception(f"Feed parsing error: {feed.bozo_exception}")
        
        self.logger.debug(f"   📰 Found {len(feed.entries)} entries")
        
        for entry in feed.entries:
            try:
                article = self._parse_entry(entry, feed_config)
                if article:
                    articles.append(article)
            except Exception as e:
                self.logger.debug(f"   ⚠️ Entry parse error: {e}")
                continue
        
        return articles
    
    def _parse_entry(self, entry, feed_config: Dict[str, str]) -> Dict[str, Any]:
        """Parse a single RSS entry into article dictionary."""
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
        
        return {
            'title': title,
            'content_summary': summary,
            'source_name': feed_config['name'],
            'url': url,
            'published_at_utc': published_at,
            'news_type': feed_config['type'],
        }


def get_rss_feeds_info() -> Dict[str, List[Dict]]:
    """Get information about configured RSS feeds"""
    return RSS_FEEDS

