"""
Naver News Collector with Enhanced Logging

Collects Korean logistics news from Naver News API.
Extended queries based on requirement.md specifications.
"""

import os
import requests
import time
import re
from html import unescape
from typing import List, Dict, Any, Optional
from .base import BaseCollector

# Extended Naver News search queries - requirement.md 기반
NAVER_NEWS_QUERIES = [
    # ===== 기존 핵심 쿼리 =====
    '물류 파업',
    '항만 혼잡',
    '해운 운임',
    '물류 지연',
    '항공 화물',
    '공급망 위기',
    '컨테이너 부족',
    '물류 뉴스',
    '물류센터',
    '택배 파업',
    
    # ===== 운임 및 비용 =====
    '해상 운임',
    '항공 운임',
    '물류비 상승',
    '운송 비용',
    '유류할증료',
    '컨테이너 운임',
    'SCFI 운임지수',
    'BDI 지수',
    
    # ===== 주요 항로 및 요충지 =====
    '수에즈운하',
    '파나마운하',
    '홍해 항로',
    '말라카해협',
    '북극항로',
    '바브엘만데브 해협',
    '호르무즈 해협',
    '대만해협 물류',
    '남중국해 항로',
    '보스포루스 해협',
    '지브롤터 해협',
    '희망봉 우회',
    '아덴만 항로',
    
    # ===== 정책 및 규제 =====
    '해운 정책',
    '물류 규제',
    '통관 규제',
    '수출입 규제',
    '관세 정책',
    'IMO 규제',
    '탄소중립 해운',
    'EU ETS 해운',
    'EU CBAM',
    
    # ===== 주요 선사 (글로벌) =====
    '머스크',
    'MSC 해운',
    'CMA CGM',
    '코스코 해운',
    '에버그린 해운',
    '하파그로이드',
    'ONE 해운',
    '양밍해운',
    'ZIM 해운',
    '완하이 해운',
    
    # ===== 주요 선사 (한국) =====
    'HMM 실적',
    'SM상선',
    '고려해운',
    '흥아해운',
    '팬오션',
    '장금상선',
    '대한해운',
    '천경해운',
    '시노코르',
    '남성해운',
    
    # ===== 주요 항만 (아시아) =====
    '부산항',
    '인천항',
    '광양항',
    '평택항',
    '울산항',
    '싱가포르항',
    '상하이항',
    '닝보항',
    '선전항',
    '광저우항',
    '홍콩항',
    '칭다오항',
    '톈진항',
    '가오슝항',
    '도쿄항',
    '요코하마항',
    '호치민항',
    '하이퐁항',
    '방콕항',
    '자카르타항',
    '콜롬보항',
    '뭄바이항',
    
    # ===== 주요 항만 (유럽) =====
    '로테르담항',
    '앤트워프항',
    '함부르크항',
    '브레머하펜항',
    '발렌시아항',
    '바르셀로나항',
    '피레우스항',
    '르아브르항',
    '펠릭스토항',
    
    # ===== 주요 항만 (미주) =====
    'LA항',
    '롱비치항',
    '뉴욕항',
    '사바나항',
    '휴스턴항',
    '시애틀항',
    '밴쿠버항',
    '산토스항',
    '콜론항',
    '만사니요항',
    
    # ===== 주요 항만 (중동/아프리카) =====
    '두바이항',
    '제벨알리항',
    '살랄라항',
    '제다항',
    '포트사이드항',
    '탕헤르항',
    '더반항',
    
    # ===== 주요 공항 =====
    '인천공항 화물',
    '김해공항 화물',
    '화물터미널',
    '홍콩공항 화물',
    '창이공항 화물',
    '푸동공항 화물',
    '두바이공항 화물',
    '멤피스공항 화물',
    '루이빌공항 화물',
    '앵커리지공항 화물',
    
    # ===== 최신 이슈 =====
    '반도체 물류',
    '배터리 공급망',
    '전기차 물류',
    '친환경 선박',
    '자율운항 선박',
    
    # ===== 지정학 =====
    '중국 수출 규제',
    '미중 무역',
    '러시아 제재 물류',
    '북한 해운',
    '후티 반군 공격',
    '홍해 위기',
    
    # ===== 디지털 물류 =====
    '스마트 물류',
    '물류 자동화',
    'AI 물류',
    '물류 로봇',
    '디지털 포워딩',
    
    # ===== 풀필먼트 =====
    '풀필먼트 센터',
    '당일배송',
    '새벽배송',
    '라스트마일',
    '쿠팡 물류',
    'CJ대한통운',
    
    # ===== 무역 및 통관 =====
    '무역 동향',
    '수출 물류',
    '수입 통관',
    '통관 지연',
    'FTA 활용',
    '원산지 증명',
]


class NaverNewsCollector(BaseCollector):
    """
    Collects Korean news from Naver News Search API.
    Enhanced with detailed logging and extended query list.
    """
    
    NAVER_API_URL = "https://openapi.naver.com/v1/search/news.json"
    
    def __init__(self, queries: List[str] = None, max_per_query: int = 5):
        """
        Initialize Naver News collector.
        
        Args:
            queries: List of search queries (uses defaults if None)
            max_per_query: Maximum articles to collect per query
        """
        super().__init__(name='NaverNews', news_type='KR')
        self.queries = queries or NAVER_NEWS_QUERIES
        self.max_per_query = max_per_query
        
        # Get API credentials from environment
        self.client_id = os.getenv('NAVER_CLIENT_ID')
        self.client_secret = os.getenv('NAVER_CLIENT_SECRET')
        
        if not self.client_id or not self.client_secret:
            self.logger.warning("⚠️ Naver API credentials not found!")
            self.logger.warning("   Set NAVER_CLIENT_ID and NAVER_CLIENT_SECRET environment variables")
    
    def collect(self) -> List[Dict[str, Any]]:
        """
        Collect news from Naver News for all configured queries.
        """
        if not self.client_id or not self.client_secret:
            self.logger.error("❌ Naver API credentials not configured, skipping collection")
            return []
        
        all_articles = []
        seen_urls = set()
        
        self.log_start(len(self.queries))
        self.logger.info(f"   Max per query: {self.max_per_query}")
        
        for idx, query in enumerate(self.queries, 1):
            if idx % 10 == 1:
                self.logger.info(f"[{idx}/{len(self.queries)}] Processing queries...")
            
            try:
                articles = self._search_news(query)
                
                # Deduplicate
                new_count = 0
                for article in articles:
                    normalized_url = self._normalize_url(article['url'])
                    if normalized_url not in seen_urls:
                        seen_urls.add(normalized_url)
                        all_articles.append(article)
                        new_count += 1
                    else:
                        self._stats['duplicates_removed'] += 1
                
                if new_count > 0:
                    self._stats['total_collected'] += new_count
                    self._stats['success_sources'] += 1
                    self.logger.debug(f"   ✅ '{query}': {new_count} articles")
                
            except Exception as e:
                self._stats['failed_sources'] += 1
                self.logger.debug(f"   ❌ '{query}': {e}")
            
            # Rate limiting - Naver API 요청 제한 준수
            time.sleep(0.1)
        
        self.log_complete()
        return all_articles
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL for deduplication"""
        if '?' in url:
            return url.split('?')[0]
        return url
    
    def _search_news(self, query: str) -> List[Dict[str, Any]]:
        """Search Naver News for a specific query."""
        articles = []
        
        headers = {
            'X-Naver-Client-Id': self.client_id,
            'X-Naver-Client-Secret': self.client_secret,
        }
        
        params = {
            'query': query,
            'display': self.max_per_query,
            'start': 1,
            'sort': 'date',
        }
        
        response = requests.get(
            self.NAVER_API_URL,
            headers=headers,
            params=params,
            timeout=10
        )
        
        if response.status_code != 200:
            raise Exception(f"API error: {response.status_code}")
        
        data = response.json()
        items = data.get('items', [])
        
        for item in items:
            try:
                article = self._parse_item(item, query)
                if article:
                    articles.append(article)
            except Exception as e:
                self.logger.debug(f"Parse error: {e}")
        
        return articles
    
    def _parse_item(self, item: Dict, query: str) -> Optional[Dict[str, Any]]:
        """Parse a Naver News API item."""
        url = item.get('link') or item.get('originallink')
        if not url:
            return None
        
        title = item.get('title', '')
        title = self._clean_html(title)
        if not title:
            return None
        
        description = item.get('description', '')
        description = self._clean_html(description)
        description = self.truncate_summary(description, 500)
        
        # Parse published date
        published_at = None
        pub_date = item.get('pubDate')
        if pub_date:
            published_at = self.parse_datetime(pub_date)
        
        return {
            'title': title,
            'content_summary': description,
            'source_name': 'Naver News',
            'url': url,
            'published_at_utc': published_at,
            'news_type': 'KR',
            '_search_query': query,
        }
    
    def _clean_html(self, text: str) -> str:
        """Clean HTML tags and entities from text."""
        if not text:
            return ""
        
        text = unescape(text)
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

