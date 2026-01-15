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
    
    def analyze_articles(self, articles: List[Dict[str, Any]], batch_size: int = 10) -> List[Dict[str, Any]]:
        """
        Analyze multiple articles.
        
        Args:
            articles: List of article dictionaries
            batch_size: Number of articles to analyze in each AI batch
            
        Returns:
            List of analyzed article dictionaries
        """
        logger.info(f"{'='*60}")
        logger.info(f"🤖 Starting AI Analysis")
        logger.info(f"   Total articles: {len(articles)}")
        logger.info(f"{'='*60}")
        
        analyzed = []
        
        for idx, article in enumerate(articles, 1):
            if idx % 50 == 0:
                logger.info(f"   Analyzing... {idx}/{len(articles)}")
            
            try:
                analyzed_article = self._analyze_single(article)
                analyzed.append(analyzed_article)
                self.stats['total_analyzed'] += 1
            except Exception as e:
                logger.warning(f"   ⚠️ Analysis error for article {idx}: {e}")
                # Keep original article with default values
                article['category'] = 'ETC'
                article['sentiment'] = 'neutral'
                article['is_crisis'] = False
                article['country_tags'] = []
                article['keywords'] = []
                analyzed.append(article)
                self.stats['errors'] += 1
        
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
- Crisis: Strikes, accidents, conflicts, disasters
- Ocean: Maritime shipping, containers, ports
- Air: Air cargo, airports, airlines
- Inland: Trucking, rail, warehousing
- Economy: Economic indicators, freight rates, trade
- ETC: Other logistics news"""

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
        
        # Crisis indicators
        if any(kw in text_lower for kw in CRISIS_KEYWORDS):
            return 'Crisis'
        
        # Ocean/Maritime
        ocean_keywords = ['ship', 'port', 'container', 'maritime', 'vessel', 'cargo ship',
                         '선박', '항만', '컨테이너', '해운', '선사']
        if any(kw in text_lower for kw in ocean_keywords):
            return 'Ocean'
        
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
        
        positive_keywords = ['growth', 'increase', 'rise', 'recovery', 'improve', 'success',
                            '성장', '증가', '상승', '회복', '개선', '호조']
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
        
        return found[:5]  # Limit to 5 keywords
    
    def generate_insights(self, article: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate trade/logistics/SCM insights for a headline article.
        
        Args:
            article: Article dictionary with title and content_summary
            
        Returns:
            Dictionary with 'trade', 'logistics', 'scm' insights
        """
        title = article.get('title', '')
        summary = article.get('content_summary', '')
        
        if self.model:
            try:
                return self._generate_insights_with_ai(title, summary)
            except Exception as e:
                logger.debug(f"AI insights generation failed: {e}")
        
        # Rule-based fallback
        return self._generate_insights_with_rules(title, summary)
    
    def _generate_insights_with_ai(self, title: str, summary: str) -> Dict[str, str]:
        """Generate insights using Gemini AI - specific to each article"""
        prompt = f"""당신은 무역, 물류, SCM 전문 분석가입니다. 아래 뉴스 기사를 읽고, 이 **특정 기사**에 대한 구체적인 시사점을 분석해주세요.

📰 기사 제목: {title}
📝 기사 요약: {summary}

분석 요청:
이 기사가 무역/물류/SCM 담당자에게 주는 **구체적이고 실행 가능한** 시사점을 작성하세요.
- 일반적인 조언이 아닌, **이 기사의 내용에 직접 연관된** 시사점이어야 합니다.
- 기사에서 언급된 **특정 지역, 기업, 품목, 수치** 등을 활용하세요.
- 각 시사점은 20~40자 내외의 한국어 한 문장으로 작성하세요.

아래 JSON 형식으로만 응답 (마크다운, 설명 없이):
{{
    "trade": "무역 관점: 이 기사로 인한 수출입/관세/무역정책 영향",
    "logistics": "물류 관점: 이 기사로 인한 운송/배송/창고 운영 영향",
    "scm": "SCM 관점: 이 기사로 인한 재고/조달/공급망 전략 영향"
}}

예시 (참고용):
- 기사: "홍해 후티 공격으로 MSC 선박 운항 중단" 
  → trade: "아시아-유럽 운임 20% 이상 상승 대비 원가 재산정 필요"
  → logistics: "수에즈 우회 시 14일 추가 소요, 선적 일정 조정 권장"
  → scm: "유럽향 부품 안전재고 3주 이상으로 상향 검토"

- 기사: "부산항 체선 2주째 지속"
  → trade: "부산항 경유 수출 건 납기 지연 불가피, 고객사 사전 통보 필요"
  → logistics: "광양항 또는 인천항 대체 선적 검토 권장"
  → scm: "국내 출고분 선제 확보 및 재고 위치 재배치 고려"""

        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()
            
            # Clean up response
            if text.startswith('```'):
                text = text.split('\n', 1)[1]
                text = text.rsplit('```', 1)[0]
            
            result = json.loads(text)
            time.sleep(0.1)  # Rate limiting
            
            return {
                'trade': result.get('trade', ''),
                'logistics': result.get('logistics', ''),
                'scm': result.get('scm', ''),
            }
            
        except Exception as e:
            logger.debug(f"AI insights parsing error: {e}")
            return self._generate_insights_with_rules(title, summary)
    
    def _generate_insights_with_rules(self, title: str, summary: str) -> Dict[str, str]:
        """
        Generate insights using rule-based approach.
        Used as fallback when AI is unavailable.
        Extracts key entities from the article to provide semi-customized insights.
        """
        text = f"{title} {summary}"
        text_lower = text.lower()
        
        # Extract key entities for context-aware insights
        location = self._extract_location_from_text(text)
        company = self._extract_company_from_text(text)
        
        # Build context-aware prefix
        context = ""
        if location:
            context = f"{location} 관련 "
        elif company:
            context = f"{company} 관련 "
        
        # Determine the main topic and generate specific insights
        # Strike/Labor issues
        if any(kw in text_lower for kw in ['strike', 'labor', '파업', '노동', '노조']):
            return {
                'trade': f"{context}파업 장기화 시 수출입 통관 지연 및 추가 비용 발생 예상",
                'logistics': f"{context}대체 항만/터미널 확보 및 긴급 운송 루트 검토 필요",
                'scm': f"{context}파업 기간 감안한 안전재고 확보 및 납기 재조정 권장",
            }
        
        # Port/Congestion issues
        elif any(kw in text_lower for kw in ['congestion', '혼잡', '체선', 'port', '항만', '항구']):
            return {
                'trade': f"{context}체선 비용 및 지연 손해 발생 가능, 계약 조건 점검 필요",
                'logistics': f"{context}입출항 일정 재조정 및 대체 항만 활용 검토",
                'scm': f"{context}리드타임 연장 감안한 발주 시점 앞당김 고려",
            }
        
        # Freight rates/Cost
        elif any(kw in text_lower for kw in ['rate', 'freight', '운임', '요금', 'cost', '비용']):
            return {
                'trade': f"{context}운임 변동분 반영한 수출입 원가 및 마진 재검토 필요",
                'logistics': f"{context}장기 계약 또는 스팟 운임 비교 분석 후 최적안 선택",
                'scm': f"{context}물류비 상승 대비 재고 정책 및 배송 빈도 최적화 검토",
            }
        
        # Geopolitical/Crisis/Attack
        elif any(kw in text_lower for kw in ['attack', 'war', 'crisis', '공격', '전쟁', '위기', '분쟁', 'houthi', '후티']):
            return {
                'trade': f"{context}해당 지역 경유 물동량 영향 및 우회 비용 산정 필요",
                'logistics': f"{context}대체 항로(희망봉 등) 활용 시 리드타임 증가 대비",
                'scm': f"{context}복수 소싱 및 지역 분산 전략으로 리스크 헷지 권장",
            }
        
        # Delay/Disruption
        elif any(kw in text_lower for kw in ['delay', 'disruption', '지연', '차질', '중단']):
            return {
                'trade': f"{context}납기 지연에 따른 고객 커뮤니케이션 및 페널티 검토",
                'logistics': f"{context}긴급 배송(항공 전환 등) 옵션 비용 대비 효과 분석",
                'scm': f"{context}버퍼 재고 확대 및 대체 공급처 활성화 검토",
            }
        
        # Supply chain/Shortage
        elif any(kw in text_lower for kw in ['supply chain', 'shortage', '공급망', '부족', '품귀']):
            return {
                'trade': f"{context}공급 불안정에 따른 수입선 다변화 검토 필요",
                'logistics': f"{context}핵심 품목 우선 확보 및 물류 채널 다각화 추진",
                'scm': f"{context}안전재고 수준 상향 및 대체 부품 승인 절차 가속화",
            }
        
        # Canal/Route specific (Suez, Panama, etc.)
        elif any(kw in text_lower for kw in ['suez', 'panama', 'canal', '수에즈', '파나마', '운하']):
            return {
                'trade': f"{context}운하 통과 지연/제한 시 운송 비용 상승 대비 필요",
                'logistics': f"{context}우회 항로 전환 시 추가 소요 일수 및 비용 산정",
                'scm': f"{context}장기화 대비 선제적 재고 확보 및 생산 일정 조정 권장",
            }
        
        # Default - try to be somewhat relevant
        else:
            return {
                'trade': f"{context}시장 동향 변화에 따른 수출입 전략 재검토 필요",
                'logistics': f"{context}운영 효율화 및 비용 최적화 기회 탐색 권장",
                'scm': f"{context}공급망 리스크 모니터링 강화 및 대응 체계 점검",
            }
    
    def _extract_location_from_text(self, text: str) -> str:
        """Extract primary location/port from text"""
        locations = {
            '부산': '부산항', '인천': '인천항', '광양': '광양항', '평택': '평택항',
            'busan': '부산항', 'shanghai': '상하이항', 'singapore': '싱가포르항',
            'rotterdam': '로테르담항', 'los angeles': 'LA항', 'long beach': '롱비치항',
            'red sea': '홍해', '홍해': '홍해', 'suez': '수에즈운하', '수에즈': '수에즈운하',
            'panama': '파나마운하', '파나마': '파나마운하',
            '중국': '중국', 'china': '중국', '미국': '미국', 'us': '미국',
            '유럽': '유럽', 'europe': '유럽', '일본': '일본', 'japan': '일본',
        }
        
        text_lower = text.lower()
        for keyword, location in locations.items():
            if keyword in text_lower:
                return location
        return ""
    
    def _extract_company_from_text(self, text: str) -> str:
        """Extract primary company/carrier from text"""
        companies = {
            'maersk': 'Maersk', 'msc': 'MSC', 'cosco': 'COSCO', 'cma cgm': 'CMA CGM',
            'evergreen': 'Evergreen', 'hmm': 'HMM', 'one': 'ONE', 'hapag': 'Hapag-Lloyd',
            '머스크': 'Maersk', '에버그린': 'Evergreen',
            'fedex': 'FedEx', 'ups': 'UPS', 'dhl': 'DHL',
            'tesla': 'Tesla', 'apple': 'Apple', 'samsung': '삼성', '삼성': '삼성',
            'tsmc': 'TSMC', 'nvidia': 'NVIDIA',
        }
        
        text_lower = text.lower()
        for keyword, company in companies.items():
            if keyword in text_lower:
                return company
        return ""

