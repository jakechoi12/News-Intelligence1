"""
Quick Test Script - Limited queries for fast testing
"""

import os
import sys

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except:
        pass

import logging
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-7s | %(message)s',
    datefmt='%H:%M:%S',
)

logger = logging.getLogger("test")

def test_rss():
    """Test RSS collector with limited feeds"""
    logger.info("=" * 50)
    logger.info("TEST 1: RSS Collector (3 feeds only)")
    logger.info("=" * 50)
    
    from backend.collectors.rss_collector import RSSCollector
    
    # Create collector with limited feeds
    collector = RSSCollector(feed_type='global')
    collector.feeds = collector.feeds[:3]  # Only first 3 feeds
    
    articles = collector.collect()
    logger.info(f"Result: {len(articles)} articles collected")
    
    if articles:
        logger.info(f"Sample: {articles[0].get('title', '')[:50]}...")
    
    return articles

def test_google_news():
    """Test Google News with limited queries"""
    logger.info("=" * 50)
    logger.info("TEST 2: Google News (5 queries only)")
    logger.info("=" * 50)
    
    from backend.collectors.google_news_collector import GoogleNewsCollector
    
    # Limited queries for testing
    test_queries = [
        'supply chain disruption',
        'port strike',
        'shipping delay',
        'freight rates',
        'Red Sea shipping',
    ]
    
    collector = GoogleNewsCollector(queries=test_queries, max_per_query=3)
    articles = collector.collect()
    
    logger.info(f"Result: {len(articles)} articles collected")
    
    if articles:
        logger.info(f"Sample: {articles[0].get('title', '')[:50]}...")
    
    return articles

def test_naver_news():
    """Test Naver News with limited queries"""
    logger.info("=" * 50)
    logger.info("TEST 3: Naver News (5 queries only)")
    logger.info("=" * 50)
    
    naver_id = os.getenv('NAVER_CLIENT_ID')
    naver_secret = os.getenv('NAVER_CLIENT_SECRET')
    
    if not naver_id or not naver_secret:
        logger.warning("NAVER API credentials not set, skipping")
        return []
    
    from backend.collectors.naver_news_collector import NaverNewsCollector
    
    test_queries = [
        '물류 뉴스',
        '해운 운임',
        '부산항',
        '공급망',
        '수에즈운하',
    ]
    
    collector = NaverNewsCollector(queries=test_queries, max_per_query=3)
    articles = collector.collect()
    
    logger.info(f"Result: {len(articles)} articles collected")
    
    if articles:
        logger.info(f"Sample: {articles[0].get('title', '')[:50]}...")
    
    return articles

def test_analyzer():
    """Test AI analyzer"""
    logger.info("=" * 50)
    logger.info("TEST 4: AI Analyzer (rule-based)")
    logger.info("=" * 50)
    
    from backend.analyzer import GeminiAnalyzer
    
    # Test articles
    test_articles = [
        {
            'title': 'Port Strike Causes Major Shipping Delays in Los Angeles',
            'content_summary': 'Dockworkers strike at the Port of Los Angeles has caused significant delays...',
            'url': 'http://test1.com',
            'news_type': 'GLOBAL',
        },
        {
            'title': '부산항 컨테이너 물동량 증가',
            'content_summary': '부산항 컨테이너 처리량이 전년 대비 10% 증가했다...',
            'url': 'http://test2.com',
            'news_type': 'KR',
        },
    ]
    
    analyzer = GeminiAnalyzer()
    analyzed = analyzer.analyze_articles(test_articles)
    
    for a in analyzed:
        logger.info(f"  - {a['title'][:30]}... -> {a.get('category')}, {a.get('sentiment')}")
    
    return analyzed

def test_data_manager_with_real_data(articles):
    """Generate JSON with real collected articles"""
    logger.info("=" * 50)
    logger.info("TEST 5: Data Manager (with real data)")
    logger.info("=" * 50)
    
    from backend.data_manager import DataManager
    from backend.analyzer import GeminiAnalyzer
    from datetime import datetime, timezone
    
    if not articles:
        logger.warning("No articles to process!")
        return {}
    
    # Analyze articles
    logger.info(f"Analyzing {len(articles)} articles...")
    analyzer = GeminiAnalyzer()
    analyzed = analyzer.analyze_articles(articles)
    
    # Generate JSON (pass analyzer for headline insights)
    manager = DataManager(output_dir='frontend/data')
    files = manager.generate_all(analyzed, start_time=datetime.now(timezone.utc), analyzer=analyzer)
    
    logger.info(f"Generated {len(files)} files:")
    for name, path in files.items():
        logger.info(f"  - {name}: {path}")
    
    return files


def main():
    print("\n" + "=" * 50)
    print(" NEWS INTELLIGENCE - Quick Test")
    print("=" * 50 + "\n")
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except:
        pass
    
    all_articles = []
    
    # Test 1: RSS
    try:
        rss_articles = test_rss()
        all_articles.extend(rss_articles)
    except Exception as e:
        logger.error(f"RSS test failed: {e}")
    
    # Test 2: Google News
    try:
        google_articles = test_google_news()
        all_articles.extend(google_articles)
    except Exception as e:
        logger.error(f"Google News test failed: {e}")
    
    # Test 3: Naver News
    try:
        naver_articles = test_naver_news()
        all_articles.extend(naver_articles)
    except Exception as e:
        logger.error(f"Naver News test failed: {e}")
    
    # Test 4: Analyzer (skip - will analyze in step 5)
    # test_analyzer()
    
    # Test 5: Analyze and Generate JSON with real data
    try:
        test_data_manager_with_real_data(all_articles)
    except Exception as e:
        logger.error(f"Data Manager test failed: {e}")
    
    print("\n" + "=" * 50)
    print(f" TOTAL COLLECTED: {len(all_articles)} articles")
    print("=" * 50 + "\n")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

