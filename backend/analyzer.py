"""
AI Analyzer using Google Gemini

Analyzes news articles for:
- Category classification (Crisis, Ocean, Air, Inland, Economy, ETC)
- Sentiment analysis (positive, negative, neutral)
- Country/region extraction
- Keyword extraction
"""

import os
import json
import logging
import time
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger("analyzer.Gemini")

# Category definitions
CATEGORIES = {
    'Crisis': '파업, 사고, 분쟁, 재해 등 위기 상황',
    'Ocean': '해운, 컨테이너, 항만, 선박 관련',
    'Air': '항공 화물, 공항, 항공사 관련',
    'Inland': '내륙 운송, 트럭, 철도, 창고 관련',
    'Economy': '경제, 운임, 수요, 무역, 금융 관련',
    'ETC': '기타 물류/공급망 뉴스',
}

# Crisis keywords for quick classification
CRISIS_KEYWORDS = [
    'strike', 'crisis', 'disruption', 'closure', 'disaster', 'attack',
    'war', 'conflict', 'shortage', 'congestion', 'delay', 'accident',
    '파업', '위기', '혼잡', '사고', '지연', '폐쇄', '분쟁', '공격', '재해',
]

# Negative sentiment keywords
NEGATIVE_KEYWORDS = [
    'decline', 'drop', 'fall', 'crash', 'loss', 'concern', 'risk', 'threat',
    'warning', 'trouble', 'problem', 'failure', 'worst', 'critical',
    '하락', '감소', '위험', '우려', '손실', '문제', '악화', '최악', '위기',
]


class GeminiAnalyzer:
    """
    Analyzes news articles using Google Gemini AI.
    Falls back to rule-based analysis if API is unavailable.
    """
    
    def __init__(self, api_key: str = None):
        """
        Initialize Gemini analyzer.
        
        Args:
            api_key: Gemini API key (uses env var if not provided)
        """
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        self.model = None
        self._init_gemini()
        
        self.stats = {
            'total_analyzed': 0,
            'ai_analyzed': 0,
            'rule_analyzed': 0,
            'errors': 0,
        }
    
    def _init_gemini(self):
        """Initialize Gemini model"""
        if not self.api_key:
            logger.warning("⚠️ GEMINI_API_KEY not set. Using rule-based analysis only.")
            return
        
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-2.0-flash')
            logger.info("✅ Gemini model initialized successfully")
        except ImportError:
            logger.warning("⚠️ google-generativeai not installed. Using rule-based analysis.")
        except Exception as e:
            logger.warning(f"⚠️ Failed to initialize Gemini: {e}")
    
    def analyze_articles(self, articles: List[Dict[str, Any]], batch_size: int = 20) -> List[Dict[str, Any]]:
        """
        Analyze multiple articles with parallel processing.
        
        Args:
            articles: List of article dictionaries
            batch_size: Number of articles to process in parallel
            
        Returns:
            List of analyzed article dictionaries
        """
        logger.info(f"{'='*60}")
        logger.info(f"🤖 Starting AI Analysis (Parallel Processing)")
        logger.info(f"   Total articles: {len(articles)}")
        logger.info(f"{'='*60}")
        
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        def analyze_batch(batch_articles, start_idx):
            """Analyze a batch of articles"""
            batch_results = []
            for idx, article in enumerate(batch_articles):
                try:
                    analyzed_article = self._analyze_single(article)
                    batch_results.append((start_idx + idx, analyzed_article))
                except Exception as e:
                    logger.debug(f"Analysis error for article {start_idx + idx}: {e}")
                    # Keep original article with default values
                    article['category'] = 'ETC'
                    article['sentiment'] = 'neutral'
                    article['is_crisis'] = False
                    article['country_tags'] = []
                    article['keywords'] = []
                    batch_results.append((start_idx + idx, article))
            return batch_results
        
        # Process articles in parallel batches
        analyzed = [None] * len(articles)
        total_processed = 0
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for i in range(0, len(articles), batch_size):
                batch = articles[i:i+batch_size]
                future = executor.submit(analyze_batch, batch, i)
                futures.append(future)
            
            for future in as_completed(futures):
                batch_results = future.result()
                for idx, result in batch_results:
                    analyzed[idx] = result
                    self.stats['total_analyzed'] += 1
                    total_processed += 1
                    
                    if total_processed % 50 == 0:
                        logger.info(f"   Analyzing... {total_processed}/{len(articles)}")
        
        # Filter out None values (shouldn't happen, but safety check)
        analyzed = [a for a in analyzed if a is not None]
        
        logger.info(f"{'='*60}")
        logger.info(f"✅ Analysis complete")
        logger.info(f"   Total: {self.stats['total_analyzed']}")
        logger.info(f"   AI analyzed: {self.stats['ai_analyzed']}")
        logger.info(f"   Rule-based: {self.stats['rule_analyzed']}")
        logger.info(f"   Errors: {self.stats['errors']}")
        logger.info(f"{'='*60}")
        
        return analyzed
    
    def _analyze_single(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a single article"""
        title = article.get('title', '')
        summary = article.get('content_summary', '')
        text = f"{title} {summary}".lower()
        
        # Try AI analysis first, fall back to rules
        if self.model:
            try:
                result = self._analyze_with_ai(article)
                if result:
                    self.stats['ai_analyzed'] += 1
                    return result
            except Exception as e:
                logger.debug(f"AI analysis failed, using rules: {e}")
        
        # Rule-based analysis
        self.stats['rule_analyzed'] += 1
        return self._analyze_with_rules(article, text)
    
    def _analyze_with_ai(self, article: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Analyze article using Gemini AI"""
        title = article.get('title', '')
        summary = article.get('content_summary', '')
        
        prompt = f"""Analyze this logistics/supply chain news article and provide a JSON response:

Title: {title}
Summary: {summary}

Respond with ONLY a JSON object (no markdown, no explanation):
{{
    "category": "one of: Crisis, Ocean, Air, Inland, Economy, ETC",
    "sentiment": "one of: positive, negative, neutral",
    "is_crisis": true or false,
    "country_tags": ["ISO country codes mentioned, e.g., US, KR, CN"],
    "keywords": ["3-5 key terms from the article"]
}}

Categories:
- Crisis: Strikes, accidents, conflicts, disasters (actual ongoing incidents)
- Ocean: Maritime shipping, containers, ports, shipbuilding, marine research, KRISO
- Air: Air cargo, airports, airlines
- Inland: Trucking, rail, warehousing
- Economy: Economic indicators, freight rates, trade
- ETC: Other logistics news

IMPORTANT: Technology development, R&D success, system innovation news should NOT be classified as Crisis.
For example, "AI-based damage control system development success" is Ocean, not Crisis."""

        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()
            
            # Clean up response
            if text.startswith('```'):
                text = text.split('\n', 1)[1]
                text = text.rsplit('```', 1)[0]
            
            result = json.loads(text)
            
            # Merge with original article
            article['category'] = result.get('category', 'ETC')
            article['sentiment'] = result.get('sentiment', 'neutral')
            article['is_crisis'] = result.get('is_crisis', False)
            article['country_tags'] = result.get('country_tags', [])
            article['keywords'] = result.get('keywords', [])
            
            # Rate limiting for Gemini API
            time.sleep(0.1)
            
            return article
            
        except json.JSONDecodeError:
            logger.debug("Failed to parse AI response as JSON")
            return None
        except Exception as e:
            logger.debug(f"AI analysis error: {e}")
            return None
    
    def _analyze_with_rules(self, article: Dict[str, Any], text: str) -> Dict[str, Any]:
        """Analyze article using rule-based approach"""
        
        # Category classification
        category = self._classify_category(text)
        article['category'] = category
        
        # Sentiment analysis
        sentiment = self._classify_sentiment(text)
        article['sentiment'] = sentiment
        
        # Crisis detection
        is_crisis = category == 'Crisis' or any(kw in text for kw in CRISIS_KEYWORDS)
        article['is_crisis'] = is_crisis
        
        # Country extraction (simple)
        article['country_tags'] = self._extract_countries(text)
        
        # Keyword extraction (simple)
        article['keywords'] = self._extract_keywords(text)
        
        return article
    
    def _classify_category(self, text: str) -> str:
        """Rule-based category classification"""
        text_lower = text.lower()
        
        # Technology/Development keywords (not Crisis)
        tech_positive_keywords = ['국산화', '성공', '개발', '기술', '시스템', 'development', 
                                  'technology', 'innovation', 'research', '연구', '혁신']
        has_tech_positive = any(kw in text_lower for kw in tech_positive_keywords)
        
        # Ocean/Maritime (check before Crisis to prioritize domain)
        ocean_keywords = ['ship', 'port', 'container', 'maritime', 'vessel', 'cargo ship',
                         '선박', '항만', '컨테이너', '해운', '선사', 'kriso', '해양', 
                         '손상통제', '조선', '해사', '해수부']
        if any(kw in text_lower for kw in ocean_keywords):
            # If it's a tech/development news in ocean domain, it's Ocean, not Crisis
            if has_tech_positive:
                return 'Ocean'
            # Check if it's actually a crisis in ocean domain
            if any(kw in text_lower for kw in CRISIS_KEYWORDS):
                return 'Crisis'
            return 'Ocean'
        
        # Crisis indicators (only if not tech/development news)
        if not has_tech_positive and any(kw in text_lower for kw in CRISIS_KEYWORDS):
            return 'Crisis'
        
        # Air
        air_keywords = ['air cargo', 'airport', 'airline', 'flight', 'aviation',
                       '항공', '공항', '화물기']
        if any(kw in text_lower for kw in air_keywords):
            return 'Air'
        
        # Inland
        inland_keywords = ['truck', 'rail', 'warehouse', 'distribution', 'last mile',
                          '트럭', '철도', '창고', '물류센터', '배송']
        if any(kw in text_lower for kw in inland_keywords):
            return 'Inland'
        
        # Economy
        economy_keywords = ['rate', 'price', 'cost', 'trade', 'economy', 'tariff', 'gdp',
                           '운임', '요금', '무역', '경제', '관세']
        if any(kw in text_lower for kw in economy_keywords):
            return 'Economy'
        
        return 'ETC'
    
    def _classify_sentiment(self, text: str) -> str:
        """Rule-based sentiment classification"""
        text_lower = text.lower()
        
        negative_count = sum(1 for kw in NEGATIVE_KEYWORDS if kw in text_lower)
        
        positive_keywords = [
            'growth', 'increase', 'rise', 'recovery', 'improve', 'success', 'award',
            'achievement', 'record', 'best', 'leading', 'innovation', 'partnership',
            '성장', '증가', '상승', '회복', '개선', '호조', '우수', '인증', '수상',
            '상생', '협력', '달성', '성공', '최고', '선정', '혁신', '도입', '체결'
        ]
        positive_count = sum(1 for kw in positive_keywords if kw in text_lower)
        
        if negative_count > positive_count:
            return 'negative'
        elif positive_count > negative_count:
            return 'positive'
        return 'neutral'
    
    def _extract_countries(self, text: str) -> List[str]:
        """Extract country codes from text"""
        text_upper = text.upper()
        
        country_mapping = {
            'UNITED STATES': 'US', 'USA': 'US', 'AMERICA': 'US', '미국': 'US',
            'CHINA': 'CN', 'CHINESE': 'CN', '중국': 'CN',
            'KOREA': 'KR', 'KOREAN': 'KR', '한국': 'KR',
            'JAPAN': 'JP', 'JAPANESE': 'JP', '일본': 'JP',
            'GERMANY': 'DE', 'GERMAN': 'DE', '독일': 'DE',
            'SINGAPORE': 'SG', '싱가포르': 'SG',
            'TAIWAN': 'TW', '대만': 'TW',
            'VIETNAM': 'VN', '베트남': 'VN',
            'INDIA': 'IN', '인도': 'IN',
            'NETHERLANDS': 'NL', 'DUTCH': 'NL', '네덜란드': 'NL',
            'UK': 'GB', 'BRITAIN': 'GB', 'BRITISH': 'GB', '영국': 'GB',
            'FRANCE': 'FR', 'FRENCH': 'FR', '프랑스': 'FR',
            'RUSSIA': 'RU', 'RUSSIAN': 'RU', '러시아': 'RU',
            'UKRAINE': 'UA', '우크라이나': 'UA',
            'IRAN': 'IR', '이란': 'IR',
            'SAUDI': 'SA', '사우디': 'SA',
            'UAE': 'AE', '아랍에미리트': 'AE',
            'YEMEN': 'YE', '예멘': 'YE',
        }
        
        found = set()
        for keyword, code in country_mapping.items():
            if keyword in text_upper:
                found.add(code)
        
        return list(found)[:5]  # Limit to 5 countries
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text (simple approach)"""
        # Common logistics keywords to look for
        keywords_to_check = [
            'strike', 'port', 'shipping', 'freight', 'container', 'delay',
            'disruption', 'supply chain', 'logistics', 'cargo', 'tariff',
            'trade', 'export', 'import', 'crisis', 'congestion',
            '파업', '항만', '해운', '물류', '컨테이너', '지연', '위기',
        ]
        
        text_lower = text.lower()
        found = [kw for kw in keywords_to_check if kw in text_lower]

        return found[:10]  # Limit to 10 keywords

