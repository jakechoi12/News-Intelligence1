"""
Data Manager for JSON Generation

Generates JSON files for frontend consumption:
- news_data.json
- headlines_data.json
- economic_data.json
- map_data.json
- wordcloud_data.json
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
                     start_time: datetime = None,
                     analyzer = None) -> Dict[str, str]:
        """
        Generate all JSON files.
        
        Args:
            articles: List of analyzed article dictionaries
            economic_data: Economic indicator data
            start_time: Collection start time
            analyzer: GeminiAnalyzer instance for generating insights
            
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
        
        # Generate headlines with insights
        headlines = self._generate_headlines(processed_articles, analyzer)
        
        # Generate news data (without headlines)
        files['news'] = self._generate_news_data(processed_articles)
        
        # Generate headlines data (separate file)
        files['headlines'] = self._generate_headlines_data(headlines)
        
        # Generate map data
        files['map'] = self._generate_map_data(processed_articles)
        
        # Generate wordcloud data
        files['wordcloud'] = self._generate_wordcloud_data(processed_articles)
        
        # Generate economic data (use mock if not provided)
        if economic_data:
            files['economic'] = self._generate_economic_data(economic_data)
        else:
            files['economic'] = self._generate_mock_economic_data()
        
        # Generate last update info
        files['last_update'] = self._generate_last_update(start_time)
        
        # Archive data
        self._archive_data()
        
        logger.info(f"{'='*60}")
        logger.info(f"✅ JSON generation complete")
        logger.info(f"   Files generated: {len(files)}")
        logger.info(f"{'='*60}")
        
        return files
    
    def _archive_data(self):
        """
        Archive data to daily/weekly/monthly folders.
        - daily/: Keep 14 days (weekdays only)
        - weekly/: Keep 12 weeks (every Friday)
        - monthly/: Keep 12 months (first weekday of month)
        """
        import shutil
        from datetime import timedelta
        
        today = datetime.now(timezone.utc)
        date_str = today.strftime('%Y-%m-%d')
        weekday = today.weekday()  # 0=Monday, 4=Friday
        day_of_month = today.day
        
        # Create archive directories
        daily_dir = os.path.join(self.output_dir, 'archive', 'daily', date_str)
        weekly_dir = os.path.join(self.output_dir, 'archive', 'weekly')
        monthly_dir = os.path.join(self.output_dir, 'archive', 'monthly')
        
        os.makedirs(daily_dir, exist_ok=True)
        os.makedirs(weekly_dir, exist_ok=True)
        os.makedirs(monthly_dir, exist_ok=True)
        
        # Files to archive
        files_to_archive = [
            'news_data.json',
            'headlines_data.json', 
            'economic_data.json',
            'map_data.json',
            'wordcloud_data.json',
            'last_update.json',
        ]
        
        # 1. Daily archive (always)
        for filename in files_to_archive:
            src = os.path.join(self.output_dir, filename)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(daily_dir, filename))
        logger.info(f"   📁 Daily archive: {date_str}")
        
        # 2. Weekly archive (every Friday)
        if weekday == 4:  # Friday
            week_str = today.strftime('%Y-W%W')
            week_dir = os.path.join(weekly_dir, week_str)
            os.makedirs(week_dir, exist_ok=True)
            for filename in files_to_archive:
                src = os.path.join(self.output_dir, filename)
                if os.path.exists(src):
                    shutil.copy2(src, os.path.join(week_dir, filename))
            logger.info(f"   📁 Weekly archive: {week_str}")
        
        # 3. Monthly archive (first weekday of month, days 1-3)
        if day_of_month <= 3 and weekday < 5:  # First 3 days, weekday only
            month_str = today.strftime('%Y-%m')
            month_dir = os.path.join(monthly_dir, month_str)
            if not os.path.exists(month_dir):  # Only if not already archived this month
                os.makedirs(month_dir, exist_ok=True)
                for filename in files_to_archive:
                    src = os.path.join(self.output_dir, filename)
                    if os.path.exists(src):
                        shutil.copy2(src, os.path.join(month_dir, filename))
                logger.info(f"   📁 Monthly archive: {month_str}")
        
        # 4. Cleanup old archives
        self._cleanup_old_archives()
    
    def _cleanup_old_archives(self):
        """Remove old archives beyond retention period"""
        import shutil
        from datetime import timedelta
        
        today = datetime.now(timezone.utc)
        
        # Daily: Keep 14 days
        daily_base = os.path.join(self.output_dir, 'archive', 'daily')
        if os.path.exists(daily_base):
            cutoff_daily = today - timedelta(days=14)
            for folder in os.listdir(daily_base):
                try:
                    folder_date = datetime.strptime(folder, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                    if folder_date < cutoff_daily:
                        shutil.rmtree(os.path.join(daily_base, folder))
                        logger.debug(f"   🗑️ Removed old daily: {folder}")
                except ValueError:
                    pass
        
        # Weekly: Keep 12 weeks
        weekly_base = os.path.join(self.output_dir, 'archive', 'weekly')
        if os.path.exists(weekly_base):
            folders = sorted(os.listdir(weekly_base), reverse=True)
            for folder in folders[12:]:  # Keep only latest 12
                shutil.rmtree(os.path.join(weekly_base, folder))
                logger.debug(f"   🗑️ Removed old weekly: {folder}")
        
        # Monthly: Keep 12 months
        monthly_base = os.path.join(self.output_dir, 'archive', 'monthly')
        if os.path.exists(monthly_base):
            folders = sorted(os.listdir(monthly_base), reverse=True)
            for folder in folders[12:]:  # Keep only latest 12
                shutil.rmtree(os.path.join(monthly_base, folder))
                logger.debug(f"   🗑️ Removed old monthly: {folder}")
    
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
    
    def _generate_headlines(self, articles: List[Dict[str, Any]], analyzer=None) -> List[Dict[str, Any]]:
        """
        Generate top headlines with insights.
        Groups similar articles to find most covered topics.
        """
        if not articles:
            return []
        
        logger.info("   📰 Generating headlines with similarity grouping...")
        
        # Group articles by similar titles (Jaccard similarity)
        def get_title_words(title: str) -> set:
            """Extract significant words from title"""
            import re
            # Remove special characters, split by space
            words = re.sub(r'[^\w\s]', ' ', title.lower()).split()
            # Filter out short words and common words
            stop_words = {'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'of', 'and', 'is', 'are', 
                         '이', '가', '을', '를', '의', '에', '에서', '로', '으로', '와', '과'}
            return {w for w in words if len(w) > 2 and w not in stop_words}
        
        def jaccard_similarity(set1: set, set2: set) -> float:
            """Calculate Jaccard similarity between two sets"""
            if not set1 or not set2:
                return 0.0
            intersection = len(set1 & set2)
            union = len(set1 | set2)
            return intersection / union if union > 0 else 0.0
        
        # Group similar articles
        article_groups = []  # List of (representative_article, group_count, articles_in_group)
        used_indices = set()
        
        for i, article in enumerate(articles):
            if i in used_indices:
                continue
            
            title_words_i = get_title_words(article.get('title', ''))
            group = [article]
            used_indices.add(i)
            
            # Find similar articles
            for j, other_article in enumerate(articles):
                if j in used_indices:
                    continue
                
                title_words_j = get_title_words(other_article.get('title', ''))
                similarity = jaccard_similarity(title_words_i, title_words_j)
                
                if similarity >= 0.4:  # 40% similarity threshold
                    group.append(other_article)
                    used_indices.add(j)
            
            article_groups.append((article, len(group), group))
        
        # Sort groups by size (most covered topics first)
        article_groups.sort(key=lambda x: x[1], reverse=True)
        
        # Step 3: Select headlines balancing KR/Global and coverage
        kr_headlines = []
        global_headlines = []
        
        for representative, group_count, group in article_groups:
            news_type = representative.get('news_type', 'GLOBAL')
            
            if news_type == 'KR' and len(kr_headlines) < 3:
                kr_headlines.append((representative, group_count))
            elif news_type == 'GLOBAL' and len(global_headlines) < 3:
                global_headlines.append((representative, group_count))
            
            if len(kr_headlines) >= 3 and len(global_headlines) >= 3:
                break
        
        # Combine and sort by group count
        selected = kr_headlines + global_headlines
        selected.sort(key=lambda x: x[1], reverse=True)
        
        # If not enough, fill with remaining top groups
        if len(selected) < 6:
            for representative, group_count, group in article_groups:
                if representative not in [s[0] for s in selected]:
                    selected.append((representative, group_count))
                    if len(selected) >= 6:
                        break
        
        top_articles = [article for article, _ in selected[:6]]
        
        logger.info(f"   📊 Selected {len(top_articles)} headlines (max group size: {selected[0][1] if selected else 0})")
        
        headlines = []
        for article, group_count in selected[:6]:
            headline = {
                'id': article['id'],
                'title': article['title'],
                'content_summary': article.get('content_summary', ''),  # For LLM insight generation
                'source_name': article['source_name'],
                'url': article['url'],
                'published_at_utc': article['published_at_utc'],
                'group_count': group_count,  # How many similar articles
                'insights': {}
            }
            headlines.append(headline)
        
        # Generate insights in parallel batch if analyzer is available
        if analyzer:
            from concurrent.futures import ThreadPoolExecutor, as_completed
            
            logger.info("   🔍 Generating insights in parallel...")
            
            def generate_insights_for_article(headline_item, article_item):
                try:
                    return analyzer.generate_insights(article_item)
                except Exception as e:
                    logger.debug(f"Failed to generate insights: {e}")
                    return {
                        'trade': '관련 시장 동향 모니터링 필요',
                        'logistics': '물류 일정 및 비용 영향 검토 필요',
                        'scm': '공급망 리스크 관리 점검 권장'
                    }
            
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = {executor.submit(generate_insights_for_article, h, a): (i, h) 
                          for i, (h, a) in enumerate(zip(headlines, top_articles))}
                
                for future in as_completed(futures):
                    idx, headline_item = futures[future]
                    try:
                        insights = future.result()
                        headlines[idx]['insights'] = insights
                    except Exception as e:
                        logger.debug(f"Insights generation error: {e}")
                        headlines[idx]['insights'] = {
                            'trade': '관련 시장 동향 모니터링 필요',
                            'logistics': '물류 일정 및 비용 영향 검토 필요',
                            'scm': '공급망 리스크 관리 점검 권장'
                        }
        else:
            # Default insights if no analyzer
            for headline in headlines:
                headline['insights'] = {
                    'trade': '관련 시장 동향 모니터링 필요',
                    'logistics': '물류 일정 및 비용 영향 검토 필요',
                    'scm': '공급망 리스크 관리 점검 권장'
                }
        
        logger.info(f"   ✅ Generated {len(headlines)} headlines with insights")
        return headlines
    
    def _generate_news_data(self, articles: List[Dict[str, Any]]) -> str:
        """Generate news_data.json (without headlines)"""
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
    
    def _generate_headlines_data(self, headlines: List[Dict[str, Any]]) -> str:
        """Generate headlines_data.json (separate file for headlines)"""
        data = {
            'headlines': headlines,
            'total': len(headlines),
            'generated_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        }
        
        filepath = os.path.join(self.output_dir, 'headlines_data.json')
        self._write_json(filepath, data)
        logger.info(f"   ✅ headlines_data.json: {len(headlines)} headlines")
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
        """Generate wordcloud_data.json with keyword frequencies (filtered)"""
        # 일반 단어 블랙리스트
        STOP_WORDS = {
            'freight', 'logistics', 'shipping', 'port', 'container', 'cargo', 
            'trade', 'import', 'export', 'supply chain', 'supplychain',
            '물류', '해운', '항만', '컨테이너', '수출', '수입', '무역', '화물', '운송', '공급망',
            'news', 'article', 'report', 'update', 'breaking', 'said', 'according',
            # 웹사이트/RSS 관련 불필요한 문구
            'appeared first', 'the post', 'first on', 'read more', 'click here',
            'on freightwaves', 'freightwaves', 'on air', 'cargo week', 'trade magazine',
            'source: bloomberg', 'journal of',
            # 일반적인 영어 구문
            'a new', 'of long', 'is expected', 'will be', 'has been', 'have been',
            'continued to', 'according to', 'more than', 'as well', 'such as',
            'this week', 'last year', 'last week', 'this year', 'next year',
            'from the', 'with the', 'from a', 'with a', 'that could', 'to be',
            'the new', 'the first', 'the us', 'the global', 'the maritime',
            'and the', 'as the', 'after the', 'across the', 'state of',
            'return to', 'service to', 'performance in', 'tonnes of',
            # 날짜/시간 관련 (한국어)
            '지난', '오늘', '내일', '올해', '작년', '이번', '다음', '밝혔다', '전했다',
            '등 다양한', '다양한 산업', '수 있도록', '수 있다는', '이에 따라', '참석한 가운데',
            '전년 대비', '포함)은', '이코노미', '클래스',
        }
        
        # 조사/관사 블랙리스트 (불필요한 키워드 필터링)
        PREPOSITIONS = {
            'in', 'on', 'at', 'to', 'for', 'of', 'the', 'a', 'an', 'and', 'or', 'but',
            'in the', 'to the', 'for the', 'of the', 'on the', 'at the', 'by the',
            'in 2024', 'in 2025', 'in 2026', 'for 2026', 'in december',
            'first on', 'the post', 'post appeared', 'on global',
            'port of', 'to', 'for', 'in', 'with the', 'from the', 'that the',
            # 날짜 패턴 (한국어)
            '지난 15일', '지난 14일', '지난 16일', '오는 15일', '오는 16일',
            '16일 밝혔다', '16일 오전', '지난해 12월',
            # 깨진 텍스트
            '…]', '…] the',
        }
        
        keyword_counts = Counter()
        
        for article in articles:
            # 키워드에서 일반 단어 제외
            filtered_keywords = [
                kw.lower() for kw in article.get('keywords', [])
                if kw.lower() not in STOP_WORDS and len(kw) > 2
            ]
            
            # 제목과 요약에서 구체적 키워드 추출 (앞뒤 단어 포함)
            title = article.get('title', '')
            summary = article.get('content_summary', '')
            text = f"{title} {summary}"
            
            # 2-3단어 구문 추출 (bigram/trigram) - 조사/관사 제외
            words = text.split()
            for i in range(len(words) - 1):
                # 2단어 구문
                bigram = f"{words[i]} {words[i+1]}".lower().strip('.,!?;:()[]{}"\'-')
                # 조사/관사가 포함된 경우 제외
                if bigram in PREPOSITIONS:
                    continue
                # 일반 단어가 포함되지 않은 경우만 추가
                if (bigram not in STOP_WORDS and 
                    bigram not in PREPOSITIONS and
                    len(bigram.split()) == 2 and 
                    len(bigram) > 4 and
                    not all(word in STOP_WORDS or word in PREPOSITIONS for word in bigram.split())):
                    keyword_counts[bigram] += 1
            
            # 3단어 구문도 추출 (중요한 구문)
            for i in range(len(words) - 2):
                trigram = f"{words[i]} {words[i+1]} {words[i+2]}".lower().strip('.,!?;:()[]{}"\'-')
                # 조사/관사가 포함된 경우 제외
                if any(phrase in trigram for phrase in PREPOSITIONS):
                    continue
                if (trigram not in STOP_WORDS and 
                    trigram not in PREPOSITIONS and
                    len(trigram.split()) == 3 and
                    len(trigram) > 6 and
                    not all(word in STOP_WORDS or word in PREPOSITIONS for word in trigram.split())):
                    keyword_counts[trigram] += 1
            
            # 기존 키워드 중 2단어 이상인 것만 추가
            for kw in filtered_keywords:
                if len(kw.split()) >= 2:  # 2단어 이상만
                    keyword_counts[kw] += 1
        
        # Format for wordcloud (더 많은 키워드 추출)
        wordcloud_data = {
            'keywords': [
                {'text': word, 'count': count, 'size': min(count * 10, 100)}
                for word, count in keyword_counts.most_common(100)  # 50 → 100
            ],
            'total_keywords': len(keyword_counts),
            'generated_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        }
        
        filepath = os.path.join(self.output_dir, 'wordcloud_data.json')
        self._write_json(filepath, wordcloud_data)
        logger.info(f"   ✅ wordcloud_data.json: {len(keyword_counts)} keywords")
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

