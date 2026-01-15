"""
News Collectors Package
"""

from .base import BaseCollector
from .rss_collector import RSSCollector, RSS_FEEDS
from .google_news_collector import GoogleNewsCollector, GOOGLE_NEWS_QUERIES
from .naver_news_collector import NaverNewsCollector, NAVER_NEWS_QUERIES

__all__ = [
    'BaseCollector',
    'RSSCollector',
    'RSS_FEEDS',
    'GoogleNewsCollector',
    'GOOGLE_NEWS_QUERIES',
    'NaverNewsCollector',
    'NAVER_NEWS_QUERIES',
]

