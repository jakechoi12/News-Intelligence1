"""
Microsoft Teams Notification Script

Sends a notification to Teams channel when news collection is complete.
Includes collection summary and top headlines.

Usage:
    python backend/notify_teams.py
    
Environment Variables:
    TEAMS_WEBHOOK_URL - Teams Incoming Webhook URL
"""

import os
import sys
import json
import logging
import requests
from datetime import datetime, timezone, timedelta

# Load .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger("notify.teams")


def load_json_file(filename: str) -> dict:
    """Load JSON file from frontend/data directory"""
    try:
        paths = [
            f'frontend/data/{filename}',
            f'../frontend/data/{filename}',
            os.path.join(os.path.dirname(__file__), '..', 'frontend', 'data', filename),
        ]
        
        for path in paths:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        
        return {}
    except Exception as e:
        logger.error(f"Failed to load {filename}: {e}")
        return {}


def load_collection_stats() -> dict:
    """Load collection stats from last_update.json"""
    return load_json_file('last_update.json')


def load_news_data() -> dict:
    """Load news data for headlines"""
    return load_json_file('news_data.json')


def load_headlines_data() -> dict:
    """Load headlines data from headlines_data.json"""
    return load_json_file('headlines_data.json')


def truncate_text(text: str, max_length: int = 60) -> str:
    """Truncate text with ellipsis"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."


def send_teams_notification(webhook_url: str, stats: dict, headlines: dict) -> bool:
    """
    Send notification to Teams channel with summary and headlines.
    
    Args:
        webhook_url: Teams Webhook URL
        stats: Collection statistics
        headlines: Headlines data from headlines_data.json
        
    Returns:
        True if successful, False otherwise
    """
    # Format KST time
    kst_time = stats.get('executed_at_kst', '')
    if not kst_time:
        kst = timezone(timedelta(hours=9))
        kst_time = datetime.now(kst).strftime('%Y-%m-%d %H:%M:%S')
    
    total = stats.get('total_collected', 0)
    kr_count = stats.get('kr_count', 0)
    global_count = stats.get('global_count', 0)
    categories = stats.get('categories', {})
    
    # Get top headlines from headlines_data.json (up to 6)
    articles = headlines.get('headlines', [])[:6]
    
    # Build headline text
    headline_text = ""
    for i, article in enumerate(articles, 1):
        title = truncate_text(article.get('title', ''), 55)
        source = article.get('source_name', '')
        headline_text += f"\n{i}. [{source}] {title}"
    
    # Build category text
    category_text = ""
    if categories:
        filtered_categories = {k: v for k, v in categories.items() if k != 'Crisis'}
        category_text = " | ".join([f"{cat}: {cnt}" for cat, cnt in list(filtered_categories.items())[:5]])
    
    # Simple text message for Power Automate
    message = {
        "title": "📰 News Intelligence - Daily Report",
        "text": f"""**🕐 {kst_time} (KST)**

**📊 수집 현황**
- 총 수집: **{total}건**
- 🇰🇷 한국: {kr_count}건
- 🌍 글로벌: {global_count}건

**📋 Today's Headlines**{headline_text}

📁 {category_text}

[📱 대시보드 열기](https://jakechoi12.github.io/News-Intelligence/)"""
    }
    
    try:
        response = requests.post(
            webhook_url,
            json=message,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        # Teams webhook returns 200 or 202 for success
        if response.status_code in [200, 202]:
            logger.info("✅ Teams notification sent successfully!")
            return True
        else:
            logger.error(f"❌ Teams API error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Failed to send Teams notification: {e}")
        return False


def main():
    """Main entry point"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-7s | %(message)s',
    )
    
    logger.info("📤 Sending Teams notification...")
    
    # Get webhook URL
    webhook_url = os.getenv('TEAMS_WEBHOOK_URL')
    
    if not webhook_url:
        logger.warning("⚠️ TEAMS_WEBHOOK_URL not set. Skipping notification.")
        logger.info("   To enable, set the TEAMS_WEBHOOK_URL environment variable")
        return 0
    
    # Load data
    stats = load_collection_stats()
    headlines = load_headlines_data()
    
    if not stats:
        logger.warning("⚠️ No collection stats found. Using default values.")
        stats = {
            'total_collected': 0,
            'kr_count': 0,
            'global_count': 0,
            'categories': {},
        }
    
    logger.info(f"   📊 Stats: {stats.get('total_collected', 0)} articles")
    logger.info(f"   📰 Headlines: {len(headlines.get('headlines', []))} available")
    
    # Send notification
    success = send_teams_notification(webhook_url, stats, headlines)
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
