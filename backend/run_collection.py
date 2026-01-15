"""
Main Collection Script

Orchestrates the entire news collection and analysis process:
1. Collect news from all sources (RSS, Google News, Naver News)
2. Deduplicate articles
3. Analyze with AI (Gemini)
4. Generate JSON files for frontend

Usage:
    python backend/run_collection.py
    
Environment Variables:
    GEMINI_API_KEY - Google Gemini API key
    NAVER_CLIENT_ID - Naver API client ID
    NAVER_CLIENT_SECRET - Naver API client secret
    ECOS_API_KEY - 한국은행 ECOS API key (optional)
"""

import os
import sys
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.collectors.rss_collector import RSSCollector
from backend.collectors.google_news_collector import GoogleNewsCollector
from backend.collectors.naver_news_collector import NaverNewsCollector
from backend.collectors.gdelt_collector import GDELTCollector
from backend.analyzer import GeminiAnalyzer
from backend.data_manager import DataManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-7s | %(name)-25s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("main")


def load_env():
    """Load environment variables from .env file if exists"""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        logger.info("✅ Loaded .env file")
    except ImportError:
        logger.debug("python-dotenv not installed, using system env vars")


def collect_news() -> List[Dict[str, Any]]:
    """
    Collect news from all sources.
    
    Returns:
        List of all collected articles
    """
    all_articles = []
    seen_urls = set()
    
    logger.info("=" * 70)
    logger.info("🚀 STARTING NEWS COLLECTION")
    logger.info("=" * 70)
    
    # 1. RSS Feeds
    logger.info("\n📰 [1/3] Collecting from RSS Feeds...")
    try:
        rss_collector = RSSCollector(feed_type='all')
        rss_articles = rss_collector.collect()
        
        for article in rss_articles:
            if article['url'] not in seen_urls:
                seen_urls.add(article['url'])
                all_articles.append(article)
        
        logger.info(f"   RSS: {len(rss_articles)} articles (unique: {len(rss_articles)})")
    except Exception as e:
        logger.error(f"   ❌ RSS collection failed: {e}")
    
    # 2. Google News
    logger.info("\n🔍 [2/3] Collecting from Google News...")
    try:
        google_collector = GoogleNewsCollector(max_per_query=3)  # Limit for speed
        google_articles = google_collector.collect()
        
        new_count = 0
        for article in google_articles:
            if article['url'] not in seen_urls:
                seen_urls.add(article['url'])
                all_articles.append(article)
                new_count += 1
        
        logger.info(f"   Google News: {len(google_articles)} articles (new: {new_count})")
    except Exception as e:
        logger.error(f"   ❌ Google News collection failed: {e}")
    
    # 3. Naver News
    logger.info("\n🇰🇷 [3/4] Collecting from Naver News...")
    try:
        naver_collector = NaverNewsCollector(max_per_query=3)  # Limit for speed
        naver_articles = naver_collector.collect()
        
        new_count = 0
        for article in naver_articles:
            # Normalize Naver URLs for deduplication
            url = article['url'].split('?')[0] if '?' in article['url'] else article['url']
            if url not in seen_urls:
                seen_urls.add(url)
                all_articles.append(article)
                new_count += 1
        
        logger.info(f"   Naver News: {len(naver_articles)} articles (new: {new_count})")
    except Exception as e:
        logger.error(f"   ❌ Naver News collection failed: {e}")
    
    # 4. GDELT (Crisis Events)
    logger.info("\n🌐 [4/4] Collecting from GDELT...")
    try:
        gdelt_collector = GDELTCollector(goldstein_threshold=-4.0, max_events=30)
        gdelt_articles = gdelt_collector.collect()
        
        new_count = 0
        for article in gdelt_articles:
            if article['url'] and article['url'] not in seen_urls:
                seen_urls.add(article['url'])
                all_articles.append(article)
                new_count += 1
        
        logger.info(f"   GDELT: {len(gdelt_articles)} events (new: {new_count})")
    except Exception as e:
        logger.error(f"   ❌ GDELT collection failed: {e}")
    
    logger.info("\n" + "=" * 70)
    logger.info(f"📊 COLLECTION SUMMARY")
    logger.info(f"   Total unique articles: {len(all_articles)}")
    
    # Count by type
    kr_count = sum(1 for a in all_articles if a.get('news_type') == 'KR')
    global_count = len(all_articles) - kr_count
    logger.info(f"   Korean news: {kr_count}")
    logger.info(f"   Global news: {global_count}")
    logger.info("=" * 70)
    
    return all_articles


def filter_recent_articles(articles: List[Dict[str, Any]], hours: int = 72) -> List[Dict[str, Any]]:
    """
    Filter articles to only include recent ones.
    
    Args:
        articles: List of articles
        hours: Maximum age in hours (default 72 for more coverage)
        
    Returns:
        Filtered list of articles
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    cutoff_naive = cutoff.replace(tzinfo=None)
    
    recent = []
    for article in articles:
        pub_date = article.get('published_at_utc')
        
        # If no date, include it
        if not pub_date:
            recent.append(article)
            continue
        
        # Parse if string
        if isinstance(pub_date, str):
            try:
                pub_date = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
                pub_date = pub_date.replace(tzinfo=None)
            except:
                recent.append(article)
                continue
        
        if pub_date >= cutoff_naive:
            recent.append(article)
    
    logger.info(f"📅 Filtered to {len(recent)} articles from last {hours} hours")
    return recent


def analyze_articles(articles: List[Dict[str, Any]]) -> tuple:
    """
    Analyze articles using AI.
    
    Args:
        articles: List of articles
        
    Returns:
        Tuple of (analyzed articles, analyzer instance)
    """
    logger.info("\n🤖 STARTING AI ANALYSIS")
    
    analyzer = GeminiAnalyzer()
    analyzed = analyzer.analyze_articles(articles)
    
    return analyzed, analyzer


def generate_output(articles: List[Dict[str, Any]], start_time: datetime, analyzer=None) -> Dict[str, str]:
    """
    Generate JSON output files.
    
    Args:
        articles: List of analyzed articles
        start_time: Collection start time
        analyzer: GeminiAnalyzer instance for generating insights
        
    Returns:
        Dictionary of generated file paths
    """
    logger.info("\n📝 GENERATING OUTPUT FILES")
    
    # Ensure output directory exists
    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend', 'data')
    
    manager = DataManager(output_dir=output_dir)
    
    # TODO: Add economic data collection here
    economic_data = None
    
    files = manager.generate_all(
        articles=articles,
        economic_data=economic_data,
        start_time=start_time,
        analyzer=analyzer
    )
    
    return files


def main():
    """Main entry point"""
    start_time = datetime.now(timezone.utc)
    
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " NEWS INTELLIGENCE - Daily Collection ".center(68) + "║")
    print("║" + f" Started: {start_time.strftime('%Y-%m-%d %H:%M:%S UTC')} ".center(68) + "║")
    print("╚" + "═" * 68 + "╝")
    print("\n")
    
    # Load environment variables
    load_env()
    
    # Check for API keys
    logger.info("🔑 Checking API keys...")
    gemini_key = os.getenv('GEMINI_API_KEY')
    naver_id = os.getenv('NAVER_CLIENT_ID')
    naver_secret = os.getenv('NAVER_CLIENT_SECRET')
    
    if gemini_key:
        logger.info("   ✅ GEMINI_API_KEY found")
    else:
        logger.warning("   ⚠️ GEMINI_API_KEY not set - using rule-based analysis")
    
    if naver_id and naver_secret:
        logger.info("   ✅ NAVER API credentials found")
    else:
        logger.warning("   ⚠️ NAVER API credentials not set - skipping Naver News")
    
    try:
        # Step 1: Collect news
        articles = collect_news()
        
        if not articles:
            logger.error("❌ No articles collected! Exiting.")
            sys.exit(1)
        
        # Step 2: Filter recent articles
        articles = filter_recent_articles(articles, hours=72)
        
        if not articles:
            logger.error("❌ No recent articles found! Exiting.")
            sys.exit(1)
        
        # Step 3: Analyze with AI
        articles, analyzer = analyze_articles(articles)
        
        # Step 4: Generate output (pass analyzer for headline insights)
        files = generate_output(articles, start_time, analyzer=analyzer)
        
        # Done!
        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()
        
        print("\n")
        print("╔" + "═" * 68 + "╗")
        print("║" + " ✅ COLLECTION COMPLETE ".center(68) + "║")
        print("╠" + "═" * 68 + "╣")
        print("║" + f" Total articles: {len(articles)} ".ljust(68) + "║")
        print("║" + f" Duration: {duration:.1f} seconds ".ljust(68) + "║")
        print("║" + f" Output: {len(files)} JSON files generated ".ljust(68) + "║")
        print("╚" + "═" * 68 + "╝")
        print("\n")
        
        # List generated files
        logger.info("Generated files:")
        for name, path in files.items():
            logger.info(f"   📄 {name}: {path}")
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("\n⚠️ Collection interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"\n❌ Collection failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())

