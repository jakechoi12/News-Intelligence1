"""
Base Collector Abstract Class with Enhanced Logging
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import logging
import sys

# Configure logging to show detailed progress
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-7s | %(name)-25s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)


class BaseCollector(ABC):
    """
    Abstract base class for all news collectors.
    Enhanced with detailed logging for tracking collection progress.
    """
    
    def __init__(self, name: str, news_type: str = 'GLOBAL'):
        """
        Initialize collector.
        
        Args:
            name: Collector name for logging
            news_type: 'KR' for Korean news, 'GLOBAL' for international
        """
        self.name = name
        self.news_type = news_type
        self.logger = logging.getLogger(f"collector.{name}")
        self._stats = {
            'total_collected': 0,
            'success_sources': 0,
            'failed_sources': 0,
            'duplicates_removed': 0,
        }
    
    @abstractmethod
    def collect(self) -> List[Dict[str, Any]]:
        """
        Collect news articles from the source.
        
        Returns:
            List of news article dictionaries
        """
        pass
    
    def log_start(self, source_count: int = 0):
        """Log collection start"""
        self.logger.info(f"{'='*60}")
        self.logger.info(f"🚀 Starting collection: {self.name}")
        if source_count:
            self.logger.info(f"   Sources to process: {source_count}")
        self.logger.info(f"{'='*60}")
    
    def log_source_start(self, source_name: str, source_url: str = None):
        """Log individual source collection start"""
        self.logger.info(f"📡 Fetching: {source_name}")
        if source_url:
            self.logger.debug(f"   URL: {source_url}")
    
    def log_source_success(self, source_name: str, count: int):
        """Log successful source collection"""
        self._stats['success_sources'] += 1
        self._stats['total_collected'] += count
        self.logger.info(f"   ✅ {source_name}: {count} articles collected")
    
    def log_source_failed(self, source_name: str, error: str):
        """Log failed source collection"""
        self._stats['failed_sources'] += 1
        self.logger.warning(f"   ❌ {source_name}: FAILED - {error}")
    
    def log_source_empty(self, source_name: str):
        """Log empty source"""
        self.logger.info(f"   ⚠️ {source_name}: No articles found")
    
    def log_complete(self) -> Dict[str, int]:
        """Log collection complete and return stats"""
        self.logger.info(f"{'='*60}")
        self.logger.info(f"✅ Collection complete: {self.name}")
        self.logger.info(f"   📊 Total articles: {self._stats['total_collected']}")
        self.logger.info(f"   ✅ Successful sources: {self._stats['success_sources']}")
        self.logger.info(f"   ❌ Failed sources: {self._stats['failed_sources']}")
        if self._stats['duplicates_removed']:
            self.logger.info(f"   🔄 Duplicates removed: {self._stats['duplicates_removed']}")
        self.logger.info(f"{'='*60}")
        return self._stats
    
    def parse_datetime(self, dt_str: str, formats: List[str] = None) -> Optional[datetime]:
        """
        Parse datetime string to UTC datetime object.
        """
        if not dt_str:
            return None
            
        if formats is None:
            formats = [
                '%a, %d %b %Y %H:%M:%S %z',  # RFC 822
                '%a, %d %b %Y %H:%M:%S GMT',  # RFC 822 GMT
                '%Y-%m-%dT%H:%M:%S%z',  # ISO 8601
                '%Y-%m-%dT%H:%M:%SZ',   # ISO 8601 UTC
                '%Y-%m-%d %H:%M:%S',    # Common format
                '%Y-%m-%d',             # Date only
            ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(dt_str.strip(), fmt)
                if dt.tzinfo is not None:
                    return dt.astimezone(timezone.utc).replace(tzinfo=None)
                return dt
            except (ValueError, AttributeError):
                continue
        
        self.logger.debug(f"Could not parse datetime: {dt_str}")
        return None
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text content."""
        if not text:
            return ""
        
        import re
        from html import unescape
        
        # Unescape HTML entities
        text = unescape(text)
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Strip leading/trailing whitespace
        text = text.strip()
        
        return text
    
    def truncate_summary(self, text: str, max_length: int = 500) -> str:
        """Truncate text to maximum length while preserving word boundaries."""
        if not text or len(text) <= max_length:
            return text
        
        truncated = text[:max_length]
        last_space = truncated.rfind(' ')
        
        if last_space > 0:
            truncated = truncated[:last_space]
        
        return truncated + '...'

