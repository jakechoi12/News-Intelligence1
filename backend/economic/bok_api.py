import requests
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import logging
import threading
import time
from functools import wraps

load_dotenv()

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ECOS_API_KEY = os.getenv("ECOS_API_KEY")
if not ECOS_API_KEY:
    logger.error("ECOS_API_KEY is not set in .env file. Please set it in .env file.")
    raise ValueError("ECOS_API_KEY is required. Please set it in .env file.")

API_BASE_URL = "http://ecos.bok.or.kr/api"
API_TIMEOUT = 30  # 30초 타임아웃

# ============================================================
# RATE LIMITING & CACHING CONFIGURATION
# ============================================================
# BOK API 제한: 3분(180초)에 300회 → 안전하게 3분에 250회로 제한
# 즉, 약 0.72초에 1회 → 안전하게 0.8초 간격으로 설정
RATE_LIMIT_INTERVAL = 0.8  # 최소 요청 간격 (초)
CACHE_TTL_SECONDS = 300  # 캐시 유효 시간 (5분)
CACHE_TTL_ITEM_LIST = 3600  # 항목 목록 캐시 유효 시간 (1시간)

# Rate Limiter - 요청 간격 제어
class RateLimiter:
    """API 호출 간격을 제어하는 Rate Limiter"""
    def __init__(self, min_interval=RATE_LIMIT_INTERVAL):
        self.min_interval = min_interval
        self.last_request_time = 0
        self.lock = threading.Lock()
        self.request_count = 0
        self.window_start = time.time()
        self.window_size = 180  # 3분 윈도우
        self.max_requests = 250  # 3분당 최대 요청 수
    
    def wait_if_needed(self):
        """필요한 경우 대기하여 rate limit을 준수"""
        with self.lock:
            current_time = time.time()
            
            # 윈도우 리셋 체크
            if current_time - self.window_start >= self.window_size:
                self.request_count = 0
                self.window_start = current_time
                logger.debug("Rate limit window reset")
            
            # 윈도우 내 요청 수 체크
            if self.request_count >= self.max_requests:
                wait_time = self.window_size - (current_time - self.window_start)
                if wait_time > 0:
                    logger.warning(f"Rate limit reached ({self.request_count}/{self.max_requests}). Waiting {wait_time:.1f}s")
                    time.sleep(wait_time)
                    self.request_count = 0
                    self.window_start = time.time()
                    current_time = time.time()
            
            # 최소 간격 체크
            elapsed = current_time - self.last_request_time
            if elapsed < self.min_interval:
                sleep_time = self.min_interval - elapsed
                time.sleep(sleep_time)
            
            self.last_request_time = time.time()
            self.request_count += 1
            logger.debug(f"API request #{self.request_count} in current window")

# 전역 Rate Limiter 인스턴스
_rate_limiter = RateLimiter()

# 캐시 저장소
class CacheEntry:
    """캐시 항목"""
    def __init__(self, data, ttl=CACHE_TTL_SECONDS):
        self.data = data
        self.created_at = time.time()
        self.ttl = ttl
    
    def is_expired(self):
        return time.time() - self.created_at > self.ttl

class APICache:
    """API 응답 캐시"""
    def __init__(self):
        self.cache = {}
        self.lock = threading.Lock()
    
    def get(self, key):
        """캐시에서 데이터 조회"""
        with self.lock:
            if key in self.cache:
                entry = self.cache[key]
                if not entry.is_expired():
                    logger.debug(f"Cache HIT: {key[:50]}...")
                    return entry.data
                else:
                    # 만료된 항목 삭제
                    del self.cache[key]
                    logger.debug(f"Cache EXPIRED: {key[:50]}...")
            return None
    
    def set(self, key, data, ttl=CACHE_TTL_SECONDS):
        """캐시에 데이터 저장"""
        with self.lock:
            self.cache[key] = CacheEntry(data, ttl)
            logger.debug(f"Cache SET: {key[:50]}... (TTL: {ttl}s)")
    
    def clear(self):
        """캐시 전체 삭제"""
        with self.lock:
            count = len(self.cache)
            self.cache.clear()
            logger.info(f"Cache cleared: {count} entries removed")
    
    def cleanup_expired(self):
        """만료된 캐시 항목 정리"""
        with self.lock:
            expired_keys = [k for k, v in self.cache.items() if v.is_expired()]
            for key in expired_keys:
                del self.cache[key]
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    def get_stats(self):
        """캐시 통계 반환"""
        with self.lock:
            total = len(self.cache)
            expired = sum(1 for v in self.cache.values() if v.is_expired())
            return {"total": total, "active": total - expired, "expired": expired}

# 전역 캐시 인스턴스
_api_cache = APICache()

def get_cache_stats():
    """캐시 통계 조회 (외부 노출용)"""
    return _api_cache.get_stats()

def clear_api_cache():
    """캐시 초기화 (외부 노출용)"""
    _api_cache.clear()

def _generate_cache_key(*args, **kwargs):
    """캐시 키 생성"""
    key_parts = [str(arg) for arg in args]
    key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
    return ":".join(key_parts)

# BOK ECOS API StatisticSearch 엔드포인트 형식:
# /StatisticSearch/{KEY}/{언어}/{요청시작건수}/{요청종료건수}/{통계표코드}/{주기}/{시작일자}/{종료일자}/{항목코드}
# 참고: https://ecos.bok.or.kr/api/#/DevGuide/DevSpeciflcation

# Valid BOK Stat Codes and their primary Item Codes
# 확장된 BOK_MAPPING: 6개 카테고리별 여러 item_code 지원
# 주의: item_code는 실제 BOK API에서 반환하는 값을 확인 후 수정 필요
BOK_MAPPING = {
    "exchange": {
        "stat_code": "731Y001",  # 주요국 통화의 대원화 환율
        "name": "환율 및 금리 (KRW)",
        "default_cycle": "D",
        "items": {
            # Major Currencies
            "USD": {"code": "0000001", "name": "미국 달러 (USD)"},
            "EUR": {"code": "0000003", "name": "유로 (EUR)"},
            "JPY": {"code": "0000002", "name": "일본 엔화 (JPY) - 100엔"},
            "CNY": {"code": "0000053", "name": "중국 위안화 (CNY)"},
            "GBP": {"code": "0000012", "name": "영국 파운드 (GBP)"},
            "CHF": {"code": "0000014", "name": "스위스 프랑 (CHF)"},
            "CAD": {"code": "0000013", "name": "캐나다 달러 (CAD)"},
            "AUD": {"code": "0000017", "name": "호주 달러 (AUD)"},
            # Asia Pacific
            "HKD": {"code": "0000015", "name": "홍콩 달러 (HKD)"},
            "TWD": {"code": "0000031", "name": "대만 달러 (TWD)"},
            "SGD": {"code": "0000024", "name": "싱가포르 달러 (SGD)"},
            "THB": {"code": "0000028", "name": "태국 바트 (THB)"},
            "MYR": {"code": "0000025", "name": "말레이시아 링깃 (MYR)"},
            "IDR": {"code": "0000029", "name": "인도네시아 루피아 (IDR) - 100루피아"},
            "PHP": {"code": "0000034", "name": "필리핀 페소 (PHP)"},
            "VND": {"code": "0000035", "name": "베트남 동 (VND) - 100동"},
            "INR": {"code": "0000037", "name": "인도 루피 (INR)"},
            "PKR": {"code": "0000038", "name": "파키스탄 루피 (PKR)"},
            "BDT": {"code": "0000039", "name": "방글라데시 타카 (BDT)"},
            "NZD": {"code": "0000026", "name": "뉴질랜드 달러 (NZD)"},
            "MNT": {"code": "0000032", "name": "몽골 투그릭 (MNT)"},
            "KZT": {"code": "0000033", "name": "카자흐스탄 텡게 (KZT)"},
            "BND": {"code": "0000036", "name": "브루나이 달러 (BND)"},
            # Europe
            "SEK": {"code": "0000016", "name": "스웨덴 크로나 (SEK)"},
            "DKK": {"code": "0000018", "name": "덴마크 크로네 (DKK)"},
            "NOK": {"code": "0000019", "name": "노르웨이 크로네 (NOK)"},
            "RUB": {"code": "0000043", "name": "러시아 루블 (RUB)"},
            "HUF": {"code": "0000044", "name": "헝가리 포린트 (HUF)"},
            "PLN": {"code": "0000045", "name": "폴란드 즈워티 (PLN)"},
            "CZK": {"code": "0000046", "name": "체코 코루나 (CZK)"},
            # Americas
            "MXN": {"code": "0000040", "name": "멕시코 페소 (MXN)"},
            "BRL": {"code": "0000041", "name": "브라질 헤알 (BRL)"},
            "ARS": {"code": "0000042", "name": "아르헨티나 페소 (ARS)"},
            # Middle East
            "SAR": {"code": "0000020", "name": "사우디아라비아 리얄 (SAR)"},
            "AED": {"code": "0000023", "name": "아랍에미리트 디르함 (AED)"},
            "QAR": {"code": "0000047", "name": "카타르 리얄 (QAR)"},
            "KWD": {"code": "0000021", "name": "쿠웨이트 디나르 (KWD)"},
            "BHD": {"code": "0000022", "name": "바레인 디나르 (BHD)"},
            "JOD": {"code": "0000049", "name": "요르단 디나르 (JOD)"},
            "ILS": {"code": "0000048", "name": "이스라엘 셰켈 (ILS)"},
            "TRY": {"code": "0000050", "name": "튀르키예 리라 (TRY)"},
            # Africa
            "ZAR": {"code": "0000051", "name": "남아프리카공화국 랜드 (ZAR)"},
            "EGP": {"code": "0000052", "name": "이집트 파운드 (EGP)"}
        },
        "default_item": "USD"
    },
    "exchange-usd": {
        "stat_code": "731Y002",  # 주요국 통화의 대미달러 환율
        "name": "환율 및 금리 (USD)",
        "default_cycle": "D",
        "items": {
            # Corrected item codes based on actual BOK API item list
            "JPY": {"code": "0000002", "name": "일본엔/달러"},
            "EUR": {"code": "0000003", "name": "달러/유로"},
            "GBP": {"code": "0000012", "name": "달러/영국파운드"},
            "CAD": {"code": "0000013", "name": "캐나다달러/달러"},
            "CHF": {"code": "0000014", "name": "스위스프랑/달러"},
            "HKD": {"code": "0000015", "name": "홍콩달러/달러"},
            "SEK": {"code": "0000016", "name": "스웨덴크로나/달러"},
            "AUD": {"code": "0000017", "name": "달러/호주달러"},
            "DKK": {"code": "0000018", "name": "덴마크크로네/달러"},
            "NOK": {"code": "0000019", "name": "노르웨이크로네/달러"},
            "SGD": {"code": "0000024", "name": "싱가폴달러/달러"},
            "MYR": {"code": "0000025", "name": "말레이지아링기트/달러"},
            "NZD": {"code": "0000026", "name": "달러/뉴질랜드달러"},
            "THB": {"code": "0000028", "name": "태국바트/달러"},
            "IDR": {"code": "0000029", "name": "인도네시아루피아/달러"},
            "TWD": {"code": "0000031", "name": "대만달러/달러"},
            "MNT": {"code": "0000032", "name": "몽골투그릭/달러"},
            "KZT": {"code": "0000033", "name": "카자흐스탄텡게/달러"},
            "PHP": {"code": "0000034", "name": "필리핀페소/달러"},
            "VND": {"code": "0000035", "name": "베트남동/달러"},
            "BND": {"code": "0000036", "name": "브루나이달러/달러"},
            "INR": {"code": "0000037", "name": "인도루피/달러"},
            "PKR": {"code": "0000038", "name": "파키스탄루피/달러"},
            "BDT": {"code": "0000039", "name": "방글라데시타카/달러"},
            "MXN": {"code": "0000040", "name": "멕시코페소/달러"},
            "BRL": {"code": "0000041", "name": "브라질헤알/달러"},
            "ARS": {"code": "0000042", "name": "아르헨티나페소/달러"},
            "RUB": {"code": "0000043", "name": "러시아루블/달러"},
            "HUF": {"code": "0000044", "name": "헝가리포린트/달러"},
            "PLN": {"code": "0000045", "name": "폴란트즈워티/달러"},
            "CZK": {"code": "0000046", "name": "체코코루나/달러"},
            "QAR": {"code": "0000047", "name": "카타르리얄/달러"},
            "ILS": {"code": "0000048", "name": "이스라엘셰켈/달러"},
            "JOD": {"code": "0000049", "name": "요르단디나르/달러"},
            "TRY": {"code": "0000050", "name": "튀르키예리라/달러"},
            "ZAR": {"code": "0000051", "name": "남아프리카공화국랜드/달러"},
            "SAR": {"code": "0000020", "name": "사우디아라비아리알/달러"},
            "KWD": {"code": "0000021", "name": "쿠웨이트디나르/달러"},
            "BHD": {"code": "0000022", "name": "바레인디나르/달러"},
            "AED": {"code": "0000023", "name": "아랍연방토후국더히람/달러"},
            "EGP": {"code": "0000052", "name": "이집트파운드/달러"}
        },
        "default_item": "JPY"
    },
    "inflation": {
        "name": "물가",
        "default_cycle": "M",
        "item_code_mapping": {
            # 프론트엔드 itemCode → 실제 API item_code 매핑
            # NOTE: 901Y010(소비자물가지수 구성/세부) 기준
            # - 총지수: 00
            # - 신선식품: 10
            # - 공업제품: 212
            "CPI_TOTAL": "00",
            "CPI_FRESH": "10",
            "CPI_INDUSTRIAL": "212"
        },
        "statistics": [
            {
                "stat_code": "404Y014",
                "name": "물가 지표 1",
                "items": {}  # StatisticItemList로 동적 조회
            },
            {
                "stat_code": "404Y015",
                "name": "물가 지표 2",
                "items": {}
            },
            {
                "stat_code": "404Y016",
                "name": "물가 지표 3",
                "items": {}
            },
            {
                "stat_code": "404Y017",
                "name": "물가 지표 4",
                "items": {}
            },
            {
                "stat_code": "405Y006",
                "name": "물가 지표 5",
                "items": {}
            },
            {
                "stat_code": "405Y007",
                "name": "물가 지표 6",
                "items": {}
            },
            {
                "stat_code": "901Y009",
                "name": "소비자물가지수",
                "items": {}  # StatisticItemList로 동적 조회
            },
            {
                "stat_code": "901Y010",
                "name": "소비자물가지수 (추가)",
                "items": {}
            }
        ],
        "default_stat_code": "901Y010",
        "default_item": "CPI_TOTAL"
    },
    "gdp": {
        # 국민계정(연간) - 주요지표 (ECOS 200Y101)
        "stat_code": "200Y101",
        "name": "국민소득",
        "default_cycle": "A",
        "items": {
            # NOTE: 프론트에서 itemCode를 '10101'처럼 그대로 넘기기 때문에
            # key == code 형태로 등록합니다.
            # 실제 항목명은 get_statistic_item_list로 동적으로 가져오지만,
            # 초기값으로 실제 API 응답값을 사용합니다.
            "10101": {"code": "10101", "name": "국내총생산(명목, 원화표시)"},
            "1010101": {"code": "1010101", "name": "국내총생산(명목, 달러표시)"},
            "10102": {"code": "10102", "name": "국민총소득(명목, 원화표시)"},
            "1010201": {"code": "1010201", "name": "국민총소득(명목, 달러표시)"},
            "10106": {"code": "10106", "name": "1인당 국민총소득(명목, 원화표시)"},
            "1010601": {"code": "1010601", "name": "1인당 국민총소득(명목, 달러표시)"},
            "1010602": {"code": "1010602", "name": "1인당 가계총처분가능소득(명목, 원화표시)"},
            "1010603": {"code": "1010603", "name": "1인당 가계총처분가능소득(명목, 달러표시)"},
            "10107": {"code": "10107", "name": "1인당 국내총생산(명목, 원화표시)"},
            "1010701": {"code": "1010701", "name": "1인당 국내총생산(명목, 달러표시)"}
        },
        "default_item": "10101"
    },
    "money": {
        "stat_code": "102Y004",  # 본원통화 구성내역
        "name": "통화 및 금융",
        "default_cycle": "M",
        "items": {
            "BASE_MONEY": {"code": "BBKA00", "name": "본원통화"},
            "M2": {"code": "BBKA01", "name": "M2 (광의통화)"},
            "M1": {"code": "BBKA02", "name": "M1 (협의통화)"}
        },
        "default_item": "BASE_MONEY"
    },
    "sentiment": {
        "stat_code": "801Y001",  # 산업활동동향
        "name": "경기",
        "default_cycle": "M",
        "items": {
            "INDUSTRIAL_PRODUCTION": {"code": "J011", "name": "산업생산지수"},
            "BSI": {"code": "J012", "name": "기업경기실사지수 (BSI)"},
            "CCSI": {"code": "C000", "name": "소비자심리지수 (CCSI)"}
        },
        "default_item": "INDUSTRIAL_PRODUCTION"
    },
    "balance": {
        "stat_code": "301Y002",  # 경상수지
        "name": "국제 수지",
        "default_cycle": "M",
        "items": {
            "CURRENT_ACCOUNT": {"code": "000000", "name": "경상수지"},
            "TRADE_BALANCE": {"code": "000001", "name": "상품수지"},
            "SERVICE_BALANCE": {"code": "000002", "name": "서비스수지"}
        },
        "default_item": "CURRENT_ACCOUNT"
    },
    "interest": {
        "stat_code": "722Y001",  # 기준금리
        "name": "기준금리",
        "default_cycle": "D",
        "items": {
            "BASE_RATE": {"code": "0101000", "name": "기준금리"}
        },
        "default_item": "BASE_RATE"
    },
    "interest-international": {
        "stat_code": "902Y006",  # 주요국 기준금리
        "name": "주요국 기준금리",
        "default_cycle": "M",
        "items": {},  # 동적 조회 (get_statistic_item_list 사용)
        "default_item": None  # 첫 번째 국가 또는 한국
    },
    "cpi-international": {
        "stat_code": "902Y008",  # 국제 주요국 소비자물가지수
        "name": "국제 주요국 소비자물가지수",
        "default_cycle": "M",
        "items": {},  # 동적 조회 (get_statistic_item_list 사용)
        "default_item": None  # 첫 번째 국가 또는 한국
    },
    "export-international": {
        "stat_code": "902Y012",  # 국제 주요국 수출
        "name": "국제 주요국 수출",
        "default_cycle": "M",
        "items": {},  # 동적 조회 (get_statistic_item_list 사용)
        "default_item": None
    },
    "import-international": {
        "stat_code": "902Y013",  # 국제 주요국 수입
        "name": "국제 주요국 수입",
        "default_cycle": "M",
        "items": {},  # 동적 조회 (get_statistic_item_list 사용)
        "default_item": None
    },
    "gdp-growth-international": {
        "stat_code": "902Y015",  # 국제 주요국 경제성장률
        "name": "국제 주요국 경제성장률",
        "default_cycle": "Q",  # 분기별
        "items": {},  # 동적 조회 (get_statistic_item_list 사용)
        "default_item": None
    },
    "gdp-international": {
        "stat_code": "902Y016",  # 국제 주요국 국내총생산(GDP)
        "name": "국제 주요국 국내총생산(GDP)",
        "default_cycle": "A",  # 연간
        "items": {},  # 동적 조회 (get_statistic_item_list 사용)
        "default_item": None
    },
    "gni-international": {
        "stat_code": "902Y017",  # 국제 주요국 국민총소득(GNI)
        "name": "국제 주요국 국민총소득(GNI)",
        "default_cycle": "A",  # 연간
        "items": {},  # 동적 조회 (get_statistic_item_list 사용)
        "default_item": None
    },
    "gdp-per-capita-international": {
        "stat_code": "902Y018",  # 국제 주요국 1인당 GDP
        "name": "국제 주요국 1인당 GDP",
        "default_cycle": "A",  # 연간
        "items": {},  # 동적 조회 (get_statistic_item_list 사용)
        "default_item": None
    },
    "unemployment-international": {
        "stat_code": "902Y021",  # 국제 주요국 실업률(계절변동조정)
        "name": "국제 주요국 실업률(계절변동조정)",
        "default_cycle": "M",  # 월별
        "items": {},  # 동적 조회 (get_statistic_item_list 사용)
        "default_item": None
    },
    "stock-index-international": {
        "stat_code": "902Y002",  # 국제 주요국 주가지수
        "name": "국제 주요국 주가지수",
        "default_cycle": "M",  # 월별
        "items": {},  # 동적 조회 (get_statistic_item_list 사용)
        "default_item": None
    },
    "trade": {
        "stat_code": "301Y013",  # 수출입 통계
        "name": "수출입 통계",
        "default_cycle": "M",  # 월별
        "items": {
            # NOTE: 301Y013 통계표는 달러 단위만 제공 (백만달러)
            # 수출: 상품수출 (ITEM_CODE: 110000)
            # 수입: 상품수입 (ITEM_CODE: 120000)
            # KRW 단위는 현재 통계표에서 제공되지 않음 (USD만 사용)
            "EXPORT_USD": {"code": "110000", "name": "상품수출 (USD)"},
            "IMPORT_USD": {"code": "120000", "name": "상품수입 (USD)"},
            # KRW는 USD와 동일한 항목 코드 사용 (프론트엔드에서 환율 변환 필요할 수 있음)
            "EXPORT_KRW": {"code": "110000", "name": "상품수출 (KRW)"},
            "IMPORT_KRW": {"code": "120000", "name": "상품수입 (KRW)"}
        },
        "default_item": "EXPORT_USD"
    },
    "employment": {
        # WARNING: 901Y013은 실제로는 재정 통계(수입/지출)입니다.
        # 고용 통계의 정확한 통계표 코드는 ECOS API에서 추가 확인이 필요합니다.
        # 현재는 placeholder로 유지하며, 실제 사용 시 통계표 코드 및 item_code 확인 필요.
        "stat_code": "901Y013",  # ⚠️ 실제로는 재정 통계 - 고용 통계가 아님
        "name": "고용 통계",
        "default_cycle": "M",  # 월별
        "items": {
            # NOTE: 901Y013은 실제로 재정 통계이므로 아래 item_code는 잘못된 placeholder입니다.
            # 실제 고용 통계의 통계표 코드와 item_code를 찾아서 업데이트해야 합니다.
            # 한국은행 ECOS API에서 "고용", "실업", "취업", "경제활동인구" 등의 키워드로
            # 검색하여 정확한 통계표 코드를 확인한 후, 해당 통계표의 item_code를 조회해야 합니다.
            "UNEMPLOYMENT_RATE": {"code": "[item_code]", "name": "실업률 (%)"},
            "EMPLOYMENT_RATE": {"code": "[item_code]", "name": "고용률 (%)"},
            "EMPLOYED": {"code": "[item_code]", "name": "취업자 수 (만명)"}
        },
        "default_item": "UNEMPLOYMENT_RATE"
    },
    "ppi": {
        "stat_code": "404Y005",  # 생산자물가지수 (NOTE: 실제 코드 확인 필요, 404Y005는 INFO-200 에러 발생)
        "name": "생산자물가지수",
        "default_cycle": "M",  # 월별
        "items": {
            # NOTE: 실제 item_code는 get_statistic_item_list("404Y005") 또는 다른 통계표 코드로 확인 필요
            # 아래 코드는 placeholder이며, 실제 구현 시 API로 확인 후 업데이트 필요
            "PPI_TOTAL": {"code": "[item_code]", "name": "총지수"},
            "PPI_AGRICULTURE": {"code": "[item_code]", "name": "농림수산품"},
            "PPI_INDUSTRIAL": {"code": "[item_code]", "name": "공업제품"},
            "PPI_SERVICE": {"code": "[item_code]", "name": "서비스"}
        },
        "default_item": "PPI_TOTAL"
    }
}


def validate_date_format(date_str):
    """
    날짜 형식 검증 (YYYYMMDD)
    """
    if not date_str or len(date_str) != 8:
        return False
    try:
        datetime.strptime(date_str, '%Y%m%d')
        return True
    except ValueError:
        return False


def format_date_for_cycle(date_str, cycle):
    """
    주기에 맞는 날짜 형식으로 변환합니다.
    
    한국은행 ECOS API는 주기에 따라 다른 날짜 형식을 요구합니다:
    - D (일): YYYYMMDD (예: 20251216)
    - M (월): YYYYMM (예: 202512)
    - Q (분기): YYYYQQ (예: 20251, 20252, 20253, 20254)
    - A (연): YYYY (예: 2025)
    
    Args:
        date_str: YYYYMMDD 형식의 날짜 문자열
        cycle: 주기 (D, M, Q, A, Y)
    
    Returns:
        str: 주기에 맞는 날짜 형식
    """
    if not date_str or len(date_str) != 8:
        return date_str
    
    year = date_str[:4]
    month = date_str[4:6]
    day = date_str[6:8]
    
    if cycle == 'D':
        # 일별: YYYYMMDD
        return date_str
    elif cycle == 'M':
        # 월별: YYYYMM
        return f"{year}{month}"
    elif cycle == 'Q':
        # 분기별: YYYYQn 형식 (예: 2024Q1, 2024Q2, 2024Q3, 2024Q4)
        month_int = int(month)
        quarter = ((month_int - 1) // 3) + 1
        return f"{year}Q{quarter}"
    elif cycle == 'A' or cycle == 'Y':
        # 연도별: YYYY
        return year
    else:
        # 기본값: YYYYMMDD
        return date_str


def get_bok_statistics(stat_code, item_code, cycle, start_date, end_date, start_index=1, end_index=None, use_cache=True):
    """
    한국은행 ECOS API에서 통계 데이터를 조회합니다.
    
    Args:
        stat_code: 통계표 코드 (예: "731Y001")
        item_code: 항목 코드 (예: "0000001")
        cycle: 주기 (D: 일, M: 월, Q: 분기, Y: 연, A: 연)
        start_date: 시작일자 (YYYYMMDD 형식으로 입력받지만, 주기에 따라 변환됨)
        end_date: 종료일자 (YYYYMMDD 형식으로 입력받지만, 주기에 따라 변환됨)
        start_index: 요청 시작 건수 (기본값: 1)
        end_index: 요청 종료 건수 (None이면 기간에 따라 자동 계산, 최대 1000)
        use_cache: 캐시 사용 여부 (기본값: True)
    
    Returns:
        dict: API 응답 데이터 또는 에러 정보
        
    참고: https://ecos.bok.or.kr/api/#/DevGuide/DevSpeciflcation
    """
    # 주기 검증
    valid_cycles = ['D', 'M', 'Q', 'Y', 'A']
    if cycle not in valid_cycles:
        return {"error": f"Invalid cycle: {cycle}. Valid values: {', '.join(valid_cycles)}"}
    
    # 입력 날짜 형식 검증 (YYYYMMDD)
    if not validate_date_format(start_date):
        return {"error": f"Invalid start_date format: {start_date}. Expected YYYYMMDD"}
    
    if not validate_date_format(end_date):
        return {"error": f"Invalid end_date format: {end_date}. Expected YYYYMMDD"}
    
    # 주기에 맞는 날짜 형식으로 변환
    formatted_start_date = format_date_for_cycle(start_date, cycle)
    formatted_end_date = format_date_for_cycle(end_date, cycle)
    
    # 날짜 범위 검증 (변환 전 날짜로 검증)
    try:
        start_dt = datetime.strptime(start_date, '%Y%m%d')
        end_dt = datetime.strptime(end_date, '%Y%m%d')
        if start_dt > end_dt:
            return {"error": f"start_date ({start_date}) must be before or equal to end_date ({end_date})"}
        
        # 최대 조회 기간 제한
        # - 일/월/분기 데이터는 과도한 요청을 막기 위해 5년 제한 유지
        # - 연도(A/Y) 데이터는 end_index(<=1000)로 이미 제한되므로 5년 제한을 적용하지 않음
        days_diff = (end_dt - start_dt).days
        if cycle not in ('A', 'Y') and days_diff > 1826:
            return {"error": f"Date range cannot exceed 5 years (current: {days_diff} days)"}
        
        # end_index가 None이면 기간에 따라 자동 계산
        if end_index is None:
            days = (end_dt - start_dt).days + 1
            
            if cycle == 'D':  # 일별 데이터
                end_index = min(days, 1000)  # 최대 1000건
            elif cycle == 'M':  # 월별 데이터
                months = (end_dt.year - start_dt.year) * 12 + (end_dt.month - start_dt.month) + 1
                end_index = min(months, 1000)
            elif cycle == 'Q':  # 분기별 데이터
                start_quarter = ((start_dt.month - 1) // 3) + 1
                end_quarter = ((end_dt.month - 1) // 3) + 1
                quarters = (end_dt.year - start_dt.year) * 4 + (end_quarter - start_quarter) + 1
                end_index = min(quarters, 1000)
            elif cycle == 'A' or cycle == 'Y':  # 연도별 데이터
                years = end_dt.year - start_dt.year + 1
                end_index = min(years, 1000)
            else:
                end_index = 100  # 기본값
            
            logger.info(f"Auto-calculated end_index: {end_index} for cycle={cycle}, period={days} days")
        else:
            # end_index가 명시적으로 제공된 경우
            if end_index > 1000:
                end_index = 1000
                logger.warning(f"end_index limited to 1000 (BOK API maximum)")
    except ValueError as e:
        return {"error": f"Date parsing error: {str(e)}"}
    
    # BOK ECOS API 엔드포인트 형식
    # /StatisticSearch/{KEY}/{언어}/{요청시작건수}/{요청종료건수}/{통계표코드}/{주기}/{시작일자}/{종료일자}/{항목코드}
    url = f"{API_BASE_URL}/StatisticSearch/{ECOS_API_KEY}/json/kr/{start_index}/{end_index}/{stat_code}/{cycle}/{formatted_start_date}/{formatted_end_date}/{item_code}"
    
    logger.info(f"BOK API Request: stat_code={stat_code}, item_code={item_code}, cycle={cycle}, period={formatted_start_date}~{formatted_end_date} (original: {start_date}~{end_date})")
    logger.debug(f"Request URL: {url}")
    
    # 캐시 키 생성 (API 키 제외)
    cache_key = _generate_cache_key("StatisticSearch", stat_code, item_code, cycle, formatted_start_date, formatted_end_date, start_index, end_index)
    
    # 캐시에서 먼저 조회
    if use_cache:
        cached_data = _api_cache.get(cache_key)
        if cached_data is not None:
            logger.info(f"Cache HIT for stat_code={stat_code}, item_code={item_code}")
            return cached_data
    
    try:
        # Rate Limiting 적용
        _rate_limiter.wait_if_needed()
        
        response = requests.get(url, timeout=API_TIMEOUT)
        response.raise_for_status()
        
        data = response.json()
        
        # BOK API 응답 구조 검증
        if 'RESULT' in data:
            result_code = data['RESULT'].get('CODE', '')
            result_message = data['RESULT'].get('MESSAGE', '')
            
            if result_code != 'INFO-000':
                error_msg = f"BOK API Error [{result_code}]: {result_message}"
                logger.error(error_msg)
                return {"error": error_msg, "result_code": result_code, "result_message": result_message}
        
        # StatisticSearch 데이터 확인
        if 'StatisticSearch' not in data:
            logger.warning("No 'StatisticSearch' key in response")
            return {"error": "Invalid API response format: missing 'StatisticSearch'", "response": data}
        
        stat_search = data['StatisticSearch']
        
        # 데이터 개수 확인
        total_count = stat_search.get('list_total_count', 0)
        if total_count == 0:
            logger.info(f"No data found for stat_code={stat_code}, item_code={item_code}, cycle={cycle}")
            return {
                "StatisticSearch": {
                    "list_total_count": 0,
                    "row": []
                }
            }
        
        logger.info(f"Successfully retrieved {total_count} records")
        
        # 성공적인 응답을 캐시에 저장
        if use_cache:
            _api_cache.set(cache_key, data, CACHE_TTL_SECONDS)
        
        return data
        
    except requests.exceptions.Timeout:
        error_msg = f"Request timeout after {API_TIMEOUT} seconds"
        logger.error(error_msg)
        return {"error": error_msg}
    
    except requests.exceptions.HTTPError as e:
        error_msg = f"HTTP Error {e.response.status_code}: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg, "status_code": e.response.status_code}
    
    except requests.exceptions.RequestException as e:
        error_msg = f"Request failed: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}
    
    except ValueError as e:
        error_msg = f"JSON parsing error: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}
    
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {"error": error_msg}


def get_market_index(category, start_date, end_date, item_code=None, cycle=None, stat_code=None):
    """
    카테고리별 시장 지수 데이터를 조회합니다.
    
    Args:
        category: 카테고리명 (exchange, inflation, gdp, money, sentiment, balance)
        start_date: 시작일자 (YYYYMMDD)
        end_date: 종료일자 (YYYYMMDD)
        item_code: 항목 코드 (선택적, 기본값은 카테고리의 default_item)
        cycle: 주기 (선택적, 기본값은 카테고리의 default_cycle)
        stat_code: 통계표 코드 (선택적, inflation의 경우 여러 통계표 지원)
    
    Returns:
        dict: API 응답 데이터 또는 에러 정보
    """
    logger.info(f"get_market_index called: category={category}, item_code={item_code}, cycle={cycle}, stat_code={stat_code}, start_date={start_date}, end_date={end_date}")
    
    mapping = BOK_MAPPING.get(category)
    if not mapping:
        error_msg = f"Unknown category: {category}. Available: {', '.join(BOK_MAPPING.keys())}"
        logger.error(error_msg)
        return {"error": error_msg}
    
    # International categories: 동적 국가 리스트 조회
    INTERNATIONAL_CATEGORIES = [
        "interest-international", "cpi-international", "export-international", 
        "import-international", "gdp-growth-international", "gdp-international",
        "gni-international", "gdp-per-capita-international", "unemployment-international",
        "stock-index-international"
    ]
    if category in INTERNATIONAL_CATEGORIES:
        stat_code = mapping.get('stat_code', '902Y006')
        requested_cycle = cycle if cycle else mapping.get('default_cycle', 'M')
        stat_items = mapping.get('items', {})
        
        # items가 비어있거나, 요청된 cycle의 items가 없으면 StatisticItemList로 조회
        # 요청된 cycle에 맞는 items가 있는지 확인
        has_requested_cycle_items = False
        if stat_items:
            for item_info in stat_items.values():
                if item_info.get('cycle') == requested_cycle:
                    has_requested_cycle_items = True
                    break
        
        if not stat_items or not has_requested_cycle_items:
            logger.info(f"Fetching country list for stat_code={stat_code}, cycle={requested_cycle}")
            item_list_result = get_statistic_item_list(stat_code, start_index=1, end_index=300)
            
            if 'error' in item_list_result:
                logger.warning(f"Failed to fetch item list: {item_list_result['error']}")
                if not stat_items:
                    stat_items = {}
            else:
                # 항목 목록을 items 형식으로 변환
                rows = item_list_result.get('row', [])
                if not stat_items:
                    stat_items = {}
                
                logger.info(f"Filtering items for cycle={requested_cycle}")
                
                # 요청된 cycle의 items만 추가/업데이트 (다른 cycle의 items는 유지)
                for row in rows:
                    # 대문자 필드명 사용 (실제 API 응답 형식)
                    item_code_val = row.get('ITEM_CODE', '')
                    item_name = row.get('ITEM_NAME', '')
                    row_cycle = row.get('CYCLE', '')
                    
                    # 요청된 주기와 일치하는 항목만 추가/업데이트
                    if item_code_val and row_cycle == requested_cycle:
                        # 키는 item_code만 사용 (주기별로 이미 필터링됨)
                        key = item_code_val
                        stat_items[key] = {
                            "code": item_code_val,
                            "name": item_name,
                            "cycle": row_cycle
                        }
                        logger.debug(f"Added/Updated item: code={item_code_val}, name={item_name}, cycle={row_cycle}")
                
                # 캐시에 저장
                mapping['items'] = stat_items
                logger.info(f"Cached {len(stat_items)} items for stat_code={stat_code}, cycle={requested_cycle}")
        
        # 요청된 cycle에 맞는 items만 필터링
        filtered_items = {k: v for k, v in stat_items.items() if v.get('cycle') == requested_cycle}
        if not filtered_items:
            logger.warning(f"No items found for cycle={requested_cycle}, using all items")
            filtered_items = stat_items
        stat_items = filtered_items
        
        # Determine item_code
        if item_code:
            # item_code가 제공된 경우 items에서 찾기
            item_info = None
            for key, info in stat_items.items():
                if info['code'] == item_code or key == item_code:
                    item_info = info
                    break
            
            if not item_info:
                available_items = [f"{k}({v['code']})" for k, v in stat_items.items()]
                error_msg = f"Unknown item_code '{item_code}' for stat_code '{stat_code}'. Available: {', '.join(available_items) if available_items else 'None'}"
                logger.error(error_msg)
                return {"error": error_msg}
            
            actual_item_code = item_info['code']
            logger.info(f"Using provided item_code: {item_code} -> {actual_item_code}")
        else:
            # Use default item or first item
            if stat_items:
                first_item = list(stat_items.values())[0]
                actual_item_code = first_item['code']
                logger.info(f"Using first item: {actual_item_code}")
            else:
                return {"error": f"No items available for stat_code '{stat_code}'"}
        
        # Determine cycle (요청된 주기 사용)
        cycle = requested_cycle
        logger.info(f"Using cycle: {cycle}")
        
        result = get_bok_statistics(
            stat_code=stat_code,
            item_code=actual_item_code,
            cycle=cycle,
            start_date=start_date,
            end_date=end_date
        )
        
        if 'error' in result:
            logger.error(f"get_bok_statistics returned error: {result['error']}")
        else:
            row_count = result.get('StatisticSearch', {}).get('list_total_count', 0)
            logger.info(f"get_bok_statistics returned {row_count} rows")
        
        return result
    
    # Inflation의 경우 여러 통계표 지원
    if category == "inflation":
        # statistics 배열에서 통계표 찾기
        statistics_list = mapping.get('statistics', [])
        
        if stat_code:
            # stat_code가 제공된 경우 해당 통계표 찾기
            target_stat = None
            for stat in statistics_list:
                if stat['stat_code'] == stat_code:
                    target_stat = stat
                    break
            
            if not target_stat:
                available_codes = [s['stat_code'] for s in statistics_list]
                error_msg = f"Unknown stat_code '{stat_code}' for inflation. Available: {', '.join(available_codes)}"
                logger.error(error_msg)
                return {"error": error_msg}
            
            actual_stat_code = stat_code
            stat_items = target_stat.get('items', {})
        else:
            # stat_code가 없으면 default_stat_code 사용
            default_stat_code = mapping.get('default_stat_code', '901Y009')
            target_stat = None
            for stat in statistics_list:
                if stat['stat_code'] == default_stat_code:
                    target_stat = stat
                    break
            
            if not target_stat:
                # 첫 번째 통계표 사용
                target_stat = statistics_list[0] if statistics_list else None
                if not target_stat:
                    return {"error": "No statistics available for inflation category"}
            
            actual_stat_code = target_stat['stat_code']
            stat_items = target_stat.get('items', {})
            
            # items가 비어있으면 StatisticItemList로 조회
            if not stat_items:
                logger.info(f"Fetching item list for stat_code={actual_stat_code}")
                item_list_result = get_statistic_item_list(actual_stat_code)
                
                if 'error' in item_list_result:
                    logger.warning(f"Failed to fetch item list: {item_list_result['error']}")
                    stat_items = {}
                else:
                    # 항목 목록을 items 형식으로 변환
                    rows = item_list_result.get('row', [])
                    stat_items = {}
                    
                    # 현재 요청된 cycle에 맞는 항목만 필터링
                    requested_cycle = cycle if cycle else mapping.get('default_cycle', 'M')
                    logger.info(f"Filtering items for cycle={requested_cycle}")
                    
                    for row in rows:
                        # 대문자 필드명 사용 (실제 API 응답 형식)
                        item_code_val = row.get('ITEM_CODE', '')
                        item_name = row.get('ITEM_NAME', '')
                        row_cycle = row.get('CYCLE', '')
                        
                        # 요청된 주기와 일치하는 항목만 추가
                        if item_code_val and row_cycle == requested_cycle:
                            # 키는 item_code만 사용 (주기별로 이미 필터링됨)
                            key = item_code_val
                            stat_items[key] = {
                                "code": item_code_val,
                                "name": item_name,
                                "cycle": row_cycle
                            }
                            logger.debug(f"Added item: code={item_code_val}, name={item_name}, cycle={row_cycle}")
                    
                    # 캐시에 저장
                    target_stat['items'] = stat_items
                    logger.info(f"Cached {len(stat_items)} items for stat_code={actual_stat_code}, cycle={requested_cycle}")
        
        # Determine item_code
        if item_code:
            # 프론트엔드 itemCode를 실제 API item_code로 변환
            item_code_mapping = mapping.get('item_code_mapping', {})
            actual_item_code_from_mapping = item_code_mapping.get(item_code, item_code)
            logger.info(f"Frontend itemCode '{item_code}' mapped to API item_code '{actual_item_code_from_mapping}'")
            
            # item_code가 제공된 경우 items에서 찾기
            item_info = None
            for key, info in stat_items.items():
                if info['code'] == actual_item_code_from_mapping or key == actual_item_code_from_mapping:
                    item_info = info
                    break
            
            if not item_info:
                available_items = [f"{k}({v['code']})" for k, v in stat_items.items()]
                error_msg = f"Unknown item_code '{item_code}' (mapped to '{actual_item_code_from_mapping}') for stat_code '{actual_stat_code}'. Available: {', '.join(available_items) if available_items else 'None'}"
                logger.error(error_msg)
                return {"error": error_msg}
            
            actual_item_code = item_info['code']
            logger.info(f"Using provided item_code: {item_code} -> {actual_item_code}")
        else:
            # Use default item
            default_item_key = mapping.get('default_item')
            if default_item_key and default_item_key in stat_items:
                actual_item_code = stat_items[default_item_key]['code']
                logger.info(f"Using default item: {default_item_key} -> {actual_item_code}")
            else:
                # Fallback to first item
                if stat_items:
                    first_item = list(stat_items.values())[0]
                    actual_item_code = first_item['code']
                    logger.info(f"Using first item: {actual_item_code}")
                else:
                    return {"error": f"No items available for stat_code '{actual_stat_code}'"}
        
        # Determine cycle
        if not cycle:
            cycle = mapping.get('default_cycle', 'M')
            logger.info(f"Using default cycle: {cycle}")
        
        result = get_bok_statistics(
            stat_code=actual_stat_code,
            item_code=actual_item_code,
            cycle=cycle,
            start_date=start_date,
            end_date=end_date
        )
        
        if 'error' in result:
            logger.error(f"get_bok_statistics returned error: {result['error']}")
        else:
            row_count = result.get('StatisticSearch', {}).get('list_total_count', 0)
            logger.info(f"get_bok_statistics returned {row_count} rows")
        
        return result
    
    else:
        # 기존 로직 (exchange, gdp 등)
        # GDP 카테고리의 경우 ECOS API에서 실제 항목명 조회
        if category == "gdp":
            stat_code = mapping.get('stat_code', '200Y101')
            requested_cycle = cycle if cycle else mapping.get('default_cycle', 'A')
            
            # items가 비어있거나 항목명이 없는 경우 ECOS API에서 조회
            items_need_update = False
            if not mapping.get('items') or not any(item.get('name') for item in mapping['items'].values()):
                items_need_update = True
            else:
                # 요청된 item_code의 항목명이 없는 경우도 업데이트 필요
                if item_code and item_code in mapping['items']:
                    if not mapping['items'][item_code].get('name'):
                        items_need_update = True
            
            if items_need_update:
                logger.info(f"Fetching item list for GDP stat_code={stat_code}, cycle={requested_cycle}")
                item_list_result = get_statistic_item_list(stat_code, start_index=1, end_index=300)
                
                if 'error' not in item_list_result:
                    rows = item_list_result.get('row', [])
                    if rows:
                        # 기존 items 딕셔너리 초기화 또는 업데이트
                        if not mapping.get('items'):
                            mapping['items'] = {}
                        
                        for row in rows:
                            item_code_val = row.get('ITEM_CODE', '')
                            item_name = row.get('ITEM_NAME', '')
                            row_cycle = row.get('CYCLE', '')
                            
                            # 요청된 주기와 일치하는 항목만 추가/업데이트
                            if item_code_val and row_cycle == requested_cycle:
                                # 키는 item_code 사용
                                key = item_code_val
                                if key not in mapping['items'] or not mapping['items'][key].get('name'):
                                    mapping['items'][key] = {
                                        "code": item_code_val,
                                        "name": item_name,
                                        "cycle": row_cycle
                                    }
                                    logger.debug(f"Updated GDP item: code={item_code_val}, name={item_name}, cycle={row_cycle}")
                        
                        logger.info(f"Cached {len(mapping['items'])} GDP items for stat_code={stat_code}, cycle={requested_cycle}")
        
        # Determine item_code
        if item_code:
            # If item_code is provided, find it in the items dict
            item_info = mapping['items'].get(item_code)
            if not item_info:
                error_msg = f"Unknown item_code '{item_code}' for category '{category}'. Available: {', '.join(mapping['items'].keys())}"
                logger.error(error_msg)
                return {"error": error_msg}
            actual_item_code = item_info['code']
            logger.info(f"Using provided item_code: {item_code} -> {actual_item_code}")
        else:
            # Use default item
            default_item_key = mapping.get('default_item')
            if default_item_key:
                actual_item_code = mapping['items'][default_item_key]['code']
                logger.info(f"Using default item: {default_item_key} -> {actual_item_code}")
            else:
                # Fallback to first item
                first_item = list(mapping['items'].values())[0]
                actual_item_code = first_item['code']
                logger.info(f"Using first item: {actual_item_code}")
        
        # Determine cycle
        if not cycle:
            cycle = mapping.get('default_cycle', 'D')
            logger.info(f"Using default cycle: {cycle}")

        def _shift_yyyymmdd_by_months(date_str, months_back):
            """
            YYYYMMDD 날짜를 months_back 개월만큼 과거로 이동합니다.
            (예: 분기 fallback 시 3개월 단위로 이동)
            """
            try:
                dt = datetime.strptime(date_str, '%Y%m%d')
            except Exception:
                return date_str

            total_month = dt.year * 12 + (dt.month - 1) - int(months_back)
            new_year = total_month // 12
            new_month = (total_month % 12) + 1

            # 해당 월의 마지막 일자 계산
            if new_month == 12:
                next_month = datetime(new_year + 1, 1, 1)
            else:
                next_month = datetime(new_year, new_month + 1, 1)
            last_day = (next_month - timedelta(days=1)).day
            new_day = min(dt.day, last_day)
            return datetime(new_year, new_month, new_day).strftime('%Y%m%d')
        
        # GDP/분기 데이터 및 Trade/월별 데이터는 최신 기간 미공개 시 INFO-200이 자주 발생하므로 end_date fallback 적용
        max_retry = 6  # 최대 6회까지 재시도
        current_end_date = end_date

        def _fetch_once(ed):
            return get_bok_statistics(
                stat_code=mapping['stat_code'],
                item_code=actual_item_code,
                cycle=cycle,
                start_date=start_date,
                end_date=ed
            )

        result = _fetch_once(current_end_date)

        def _is_empty_stat_result(res):
            try:
                if not isinstance(res, dict):
                    return False
                ss = res.get('StatisticSearch', {})
                rows = ss.get('row', [])
                total = ss.get('list_total_count', 0)
                return (total == 0) or (rows is None) or (isinstance(rows, list) and len(rows) == 0)
            except Exception:
                return False

        # GDP 분기별 또는 Trade 월별 fallback 로직
        should_fallback = False
        if category == 'gdp' and cycle == 'Q':
            should_fallback = True
            fallback_months = 3  # 분기는 3개월
        elif category == 'trade' and cycle == 'M':
            should_fallback = True
            fallback_months = 1  # 월별은 1개월

        if should_fallback and isinstance(result, dict):
            # 트리거:
            # 1) INFO-200 에러
            # 2) 정상 응답이지만 데이터가 0건(list_total_count=0)
            is_info200 = ('error' in result) and (result.get('result_code') == 'INFO-200' or 'INFO-200' in str(result.get('error', '')))
            is_empty = ('error' not in result) and _is_empty_stat_result(result)

            if is_info200 or is_empty:
                logger.warning(
                    f"{category.upper()} {cycle} fallback start: {'INFO-200' if is_info200 else 'EMPTY'} for end_date={current_end_date}. Retrying with earlier periods."
                )
                for i in range(max_retry):
                    # fallback_months 개월 전으로 이동
                    current_end_date = _shift_yyyymmdd_by_months(current_end_date, fallback_months)
                    try:
                        if validate_date_format(current_end_date):
                            if datetime.strptime(current_end_date, '%Y%m%d') < datetime.strptime(start_date, '%Y%m%d'):
                                logger.warning(f"{category.upper()} {cycle} fallback stopped: end_date moved before start_date")
                                break
                    except Exception:
                        pass

                    retry_result = _fetch_once(current_end_date)

                    # 성공: 에러가 없고, 데이터가 1건 이상
                    if isinstance(retry_result, dict) and ('error' not in retry_result) and (not _is_empty_stat_result(retry_result)):
                        logger.info(f"{category.upper()} {cycle} fallback success: end_date adjusted to {current_end_date} (attempt {i+1}/{max_retry})")
                        result = retry_result
                        break

                    # INFO-200이면 계속, 그 외 에러면 중단
                    if isinstance(retry_result, dict) and ('error' in retry_result):
                        if not (retry_result.get('result_code') == 'INFO-200' or 'INFO-200' in str(retry_result.get('error', ''))):
                            logger.warning(f"{category.upper()} {cycle} fallback stopped due to non-INFO-200 error: {retry_result.get('error')}")
                            result = retry_result
                            break

                    result = retry_result
        
        if 'error' in result:
            logger.error(f"get_bok_statistics returned error: {result['error']}")
        else:
            row_count = result.get('StatisticSearch', {}).get('list_total_count', 0)
            logger.info(f"get_bok_statistics returned {row_count} rows")
            
            # GDP 카테고리의 경우 항목명 정보 추가
            if category == "gdp" and item_code:
                item_info = mapping['items'].get(item_code)
                if item_info and item_info.get('name'):
                    # API 응답에 항목명 정보 추가
                    if 'item_info' not in result:
                        result['item_info'] = {}
                    result['item_info']['item_code'] = item_code
                    result['item_info']['item_name'] = item_info['name']
                    logger.info(f"Added item_name to response: {item_info['name']}")
        
        return result


def _parse_time_to_sort_key(time_str):
    """
    ECOS TIME 필드를 정렬 가능한 숫자 키로 변환합니다.
    - YYYYMMDD -> YYYYMMDD
    - YYYYMM   -> YYYYMM00
    - YYYYQn   -> YYYY*10 + n
    - YYYY     -> YYYY0000
    """
    if not time_str:
        return 0
    s = str(time_str).strip()
    try:
        # YYYYMMDD
        if len(s) == 8 and s.isdigit():
            return int(s)
        # YYYYMM
        if len(s) == 6 and s.isdigit():
            return int(s) * 100
        # YYYYQn
        if len(s) == 6 and ('Q' in s):
            # e.g., 2025Q4
            y = int(s[:4])
            q = int(s[-1])
            return y * 10 + q
        # YYYY
        if len(s) == 4 and s.isdigit():
            return int(s) * 10000
    except Exception:
        return 0
    return 0


def calculate_statistics_previous_period(data, currency_code=None):
    """
    직전 기간(이전 포인트) 대비 통계를 계산합니다.
    - current: 최신 값(마지막 포인트)
    - previous: 직전 값(마지막-1 포인트)
    - change: current - previous
    - changePercent: change / previous * 100
    """
    if "error" in data:
        return {"error": data["error"]}
    if "StatisticSearch" not in data:
        return {"error": "Invalid data format: missing 'StatisticSearch'"}

    rows = data.get('StatisticSearch', {}).get('row', []) or []
    if not rows:
        return {"error": "No data available"}

    parsed = []
    for row in rows:
        try:
            if isinstance(row, dict):
                t = row.get('TIME', '')
                v = row.get('DATA_VALUE', '')
            elif isinstance(row, list) and len(row) >= 2:
                t = str(row[0])
                v = str(row[1])
            else:
                continue

            if not t or v is None or v == '':
                continue
            value = float(v)
            if value <= 0:
                continue
            parsed.append((t, value))
        except Exception:
            continue

    if not parsed:
        return {"error": "No valid data values found"}

    parsed.sort(key=lambda x: _parse_time_to_sort_key(x[0]))
    values = [v for _, v in parsed]

    high = max(values)
    low = min(values)
    average = sum(values) / len(values)
    current = values[-1]
    previous = values[-2] if len(values) >= 2 else current

    change = current - previous
    change_percent = (change / previous * 100) if previous != 0 else 0

    return {
        "currency": currency_code or "UNKNOWN",
        "high": round(high, 2),
        "low": round(low, 2),
        "average": round(average, 2),
        "current": round(current, 2),
        "previous": round(previous, 2),
        "change": round(change, 2),
        "changePercent": round(change_percent, 2)
    }


def get_market_index_multi(category, start_date, end_date, item_codes=None, cycle=None):
    """
    한 카테고리의 여러 항목을 한 번에 조회합니다.
    """
    mapping = BOK_MAPPING.get(category)
    if not mapping:
        return {"error": f"Unknown category: {category}"}
    
    if not cycle:
        cycle = mapping.get('default_cycle', 'D')
    
    # International categories: 동적 국가 리스트 조회
    INTERNATIONAL_CATEGORIES = [
        "interest-international", "cpi-international", "export-international", 
        "import-international", "gdp-growth-international", "gdp-international",
        "gni-international", "gdp-per-capita-international", "unemployment-international",
        "stock-index-international"
    ]
    if category in INTERNATIONAL_CATEGORIES:
        stat_code = mapping.get('stat_code', '902Y006')
        requested_cycle = cycle if cycle else mapping.get('default_cycle', 'M')
        stat_items = mapping.get('items', {})
        
        # items가 비어있으면 StatisticItemList로 조회
        if not stat_items:
            logger.info(f"Fetching country list for stat_code={stat_code}, cycle={requested_cycle}")
            item_list_result = get_statistic_item_list(stat_code, start_index=1, end_index=300)
            
            if 'error' in item_list_result:
                logger.warning(f"Failed to fetch item list: {item_list_result['error']}")
                stat_items = {}
            else:
                rows = item_list_result.get('row', [])
                stat_items = {}
                
                for row in rows:
                    item_code_val = row.get('ITEM_CODE', '')
                    item_name = row.get('ITEM_NAME', '')
                    row_cycle = row.get('CYCLE', '')
                    
                    if item_code_val and row_cycle == requested_cycle:
                        key = item_code_val
                        stat_items[key] = {
                            "code": item_code_val,
                            "name": item_name,
                            "cycle": row_cycle
                        }
                
                mapping['items'] = stat_items
                logger.info(f"Cached {len(stat_items)} items for stat_code={stat_code}, cycle={requested_cycle}")
        
        # If item_codes not specified, fetch all items
        if not item_codes:
            item_codes = list(stat_items.keys())
        
        results = {}
        for item_key in item_codes:
            item_info = stat_items.get(item_key)
            if item_info:
                result = get_bok_statistics(
                    stat_code=stat_code,
                    item_code=item_info['code'],
                    cycle=requested_cycle,
                    start_date=start_date,
                    end_date=end_date
                )
                results[item_key] = {
                    "name": item_info['name'],
                    "data": result
                }
        
        return results
    
    # 기존 로직 (exchange, gdp 등)
    # If item_codes not specified, fetch all items
    if not item_codes:
        item_codes = list(mapping['items'].keys())
    
    results = {}
    for item_key in item_codes:
        item_info = mapping['items'].get(item_key)
        if item_info:
            result = get_bok_statistics(
                stat_code=mapping['stat_code'],
                item_code=item_info['code'],
                cycle=cycle,
                start_date=start_date,
                end_date=end_date
            )
            results[item_key] = {
                "name": item_info['name'],
                "data": result
            }
    
    return results


def calculate_statistics(data, currency_code=None):
    """
    환율 데이터에서 통계 정보를 계산합니다.
    
    Args:
        data: ECOS API 응답 데이터 (StatisticSearch 형식)
        currency_code: 통화 코드 (예: "USD") - 선택적
    
    Returns:
        dict: 통계 정보
        {
            "currency": 통화 코드,
            "high": 최고값,
            "low": 최저값,
            "average": 평균값,
            "current": 현재값 (최신),
            "previous": 이전값 (기간 시작일),
            "change": 변동액,
            "changePercent": 변동률
        }
    """
    if "error" in data:
        return {"error": data["error"]}
    
    if "StatisticSearch" not in data:
        return {"error": "Invalid data format: missing 'StatisticSearch'"}
    
    stat_search = data['StatisticSearch']
    rows = stat_search.get('row', [])
    
    if not rows or len(rows) == 0:
        return {"error": "No data available"}
    
    # 데이터 추출 및 정렬 (날짜순)
    values = []
    dates = []
    
    for row in rows:
        try:
            # ECOS API 응답 구조: row는 딕셔너리 형식
            # 프론트엔드에서 row.TIME, row.DATA_VALUE를 사용하므로 동일한 구조 가정
            if isinstance(row, dict):
                date_str = row.get('TIME', '')
                value_str = row.get('DATA_VALUE', '')
            elif isinstance(row, list) and len(row) >= 2:
                # 리스트 형식인 경우 (대체 형식)
                date_str = str(row[0]) if len(row) > 0 else ''
                value_str = str(row[1]) if len(row) > 1 else ''
            else:
                continue
            
            if not date_str or not value_str:
                continue
            
            # 값이 숫자인지 확인
            try:
                value = float(value_str)
                if value > 0:  # 유효한 값만 추가
                    values.append(value)
                    dates.append(date_str)
            except (ValueError, TypeError):
                continue
        except Exception as e:
            logger.warning(f"Error parsing row: {e}")
            continue
    
    if len(values) == 0:
        return {"error": "No valid data values found"}
    
    # 통계 계산
    high = max(values)
    low = min(values)
    average = sum(values) / len(values)
    current = values[-1]  # 최신값 (마지막)
    previous = values[0] if len(values) > 1 else current  # 첫 번째 값
    
    change = current - previous
    change_percent = ((current - previous) / previous * 100) if previous != 0 else 0
    
    result = {
        "currency": currency_code or "UNKNOWN",
        "high": round(high, 2),
        "low": round(low, 2),
        "average": round(average, 2),
        "current": round(current, 2),
        "previous": round(previous, 2),
        "change": round(change, 2),
        "changePercent": round(change_percent, 2)
    }
    
    return result


def get_category_info(category=None):
    """
    카테고리 정보를 반환합니다.
    """
    if category:
        mapping = BOK_MAPPING.get(category)
        if not mapping:
            return {"error": f"Unknown category: {category}"}
        
        # International categories: items가 비어있으면 동적으로 로드
        INTERNATIONAL_CATEGORIES = [
            "interest-international", "cpi-international", "export-international", 
            "import-international", "gdp-growth-international", "gdp-international",
            "gni-international", "gdp-per-capita-international", "unemployment-international",
            "stock-index-international"
        ]
        stat_items = mapping.get('items', {})
        if category in INTERNATIONAL_CATEGORIES and not stat_items:
            stat_code = mapping.get('stat_code')
            # Fallback stat_code mapping
            stat_code_fallback = {
                "interest-international": "902Y006",
                "cpi-international": "902Y008",
                "export-international": "902Y012",
                "import-international": "902Y013",
                "gdp-growth-international": "902Y015",
                "gdp-international": "902Y016",
                "gni-international": "902Y017",
                "gdp-per-capita-international": "902Y018",
                "unemployment-international": "902Y021",
                "stock-index-international": "902Y002"
            }
            stat_code = stat_code or stat_code_fallback.get(category)
            default_cycle = mapping.get('default_cycle', 'M')
            logger.info(f"Fetching items for {category} category (stat_code={stat_code}, cycle={default_cycle})")
            item_list_result = get_statistic_item_list(stat_code, start_index=1, end_index=300)
            
            if 'error' not in item_list_result:
                rows = item_list_result.get('row', [])
                stat_items = {}
                
                for row in rows:
                    item_code_val = row.get('ITEM_CODE', '')
                    item_name = row.get('ITEM_NAME', '')
                    row_cycle = row.get('CYCLE', '')
                    
                    if item_code_val and row_cycle == default_cycle:
                        key = item_code_val
                        stat_items[key] = {
                            "code": item_code_val,
                            "name": item_name,
                            "cycle": row_cycle
                        }
                
                # 캐시에 저장
                mapping['items'] = stat_items
                logger.info(f"Cached {len(stat_items)} items for {category} category")
        
        return {
            "category": category,
            "stat_code": mapping.get('stat_code') or mapping.get('default_stat_code'),
            "name": mapping['name'],
            "default_cycle": mapping.get('default_cycle', 'D'),
            "items": {k: {"code": v['code'], "name": v['name']} for k, v in stat_items.items()},
            "default_item": mapping.get('default_item')
        }
    else:
        return {
            "categories": {
                k: {
                    "stat_code": v.get('stat_code', v.get('default_stat_code', 'N/A')),  # inflation은 stat_code가 없을 수 있음
                    "name": v['name'],
                    "default_cycle": v.get('default_cycle', 'D'),
                    "item_count": len(v.get('items', {})) if 'items' in v else 0
                }
                for k, v in BOK_MAPPING.items()
            }
        }


def search_statistical_codes(stat_code=None, stat_name=None, start_index=1, end_index=100, use_cache=True):
    """
    통계표 코드를 검색합니다.
    
    NOTE:
    - ECOS의 `StatisticalCodeSearch`는 http -> https 리다이렉트(302) 후 404가 발생하는 환경이 있어,
      본 프로젝트에서는 `StatisticTableList`로 전체 통계표 목록을 조회한 뒤 로컬 필터링으로 검색을 제공합니다.
    
    Args:
        stat_code: 통계표 코드 (부분 검색 가능, 예: "901Y")
        stat_name: 통계표명 (부분 검색 가능, 예: "소비자물가지수")
        start_index: 요청 시작 건수 (기본값: 1)
        end_index: 요청 종료 건수 (기본값: 100, 최대 1000)
        use_cache: 캐시 사용 여부 (기본값: True)
    
    Returns:
        dict: 검색 결과 (StatisticalCodeSearch 형식) 또는 에러 정보
        
    참고: https://ecos.bok.or.kr/api/#/DevGuide/StatisticalCodeSearch
    """
    # end_index 제한 (최대 1000)
    if end_index > 1000:
        end_index = 1000
        logger.warning(f"end_index limited to 1000 (BOK API maximum)")
    
    # 캐시 키 생성 (검색 조건 포함)
    cache_key = _generate_cache_key("StatisticTableList", stat_code or "", stat_name or "", start_index, end_index)
    
    # 캐시에서 먼저 조회
    if use_cache:
        cached_data = _api_cache.get(cache_key)
        if cached_data is not None:
            logger.info(f"Cache HIT for StatisticTableList search")
            return cached_data
    
    # URL 구성
    # /StatisticTableList/{KEY}/{언어}/{요청시작건수}/{요청종료건수}/
    url = f"{API_BASE_URL}/StatisticTableList/{ECOS_API_KEY}/json/kr/{start_index}/{end_index}/"
    
    logger.info(f"BOK API StatisticTableList Request (for search): stat_code={stat_code}, stat_name={stat_name}, range={start_index}~{end_index}")
    logger.debug(f"Request URL: {url}")
    
    try:
        # Rate Limiting 적용
        _rate_limiter.wait_if_needed()
        
        # http에서 302로 https로 가면 404가 나는 케이스가 있어 리다이렉트를 따라가지 않음
        response = requests.get(url, timeout=API_TIMEOUT, allow_redirects=False)
        if response.status_code in (301, 302, 307, 308):
            logger.warning(f"Redirect blocked for StatisticTableList: {response.status_code} -> {response.headers.get('Location')}")
            return {"error": f"Redirect blocked: {response.status_code}", "status_code": response.status_code}
        response.raise_for_status()
        
        data = response.json()
        
        # BOK API 응답 구조 검증
        if 'RESULT' in data:
            result_code = data['RESULT'].get('CODE', '')
            result_message = data['RESULT'].get('MESSAGE', '')
            
            if result_code != 'INFO-000':
                error_msg = f"BOK API Error [{result_code}]: {result_message}"
                logger.error(error_msg)
                return {"error": error_msg, "result_code": result_code, "result_message": result_message}
        
        if 'StatisticTableList' not in data:
            logger.warning("No 'StatisticTableList' key in response")
            return {"error": "Invalid API response format: missing 'StatisticTableList'", "response": data}
        
        table_list = data['StatisticTableList']
        rows = table_list.get('row', []) or []
        
        # 로컬 필터링
        stat_code_kw = str(stat_code).strip() if stat_code else ""
        stat_name_kw = str(stat_name).strip() if stat_name else ""
        if stat_code_kw:
            rows = [r for r in rows if stat_code_kw in str(r.get('STAT_CODE', ''))]
        if stat_name_kw:
            rows = [r for r in rows if stat_name_kw in str(r.get('STAT_NAME', ''))]
        
        result = {
            "list_total_count": len(rows),
            "row": rows
        }
        
        logger.info(f"Successfully matched {result['list_total_count']} statistical codes")
        
        # 성공적인 응답을 캐시에 저장 (통계표 목록은 긴 TTL 사용)
        if use_cache:
            _api_cache.set(cache_key, result, CACHE_TTL_ITEM_LIST)
        
        return result
        
    except requests.exceptions.Timeout:
        error_msg = f"Request timeout after {API_TIMEOUT} seconds"
        logger.error(error_msg)
        return {"error": error_msg}
    
    except requests.exceptions.HTTPError as e:
        error_msg = f"HTTP Error {e.response.status_code}: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg, "status_code": e.response.status_code}
    
    except requests.exceptions.RequestException as e:
        error_msg = f"Request failed: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}
    
    except ValueError as e:
        error_msg = f"JSON parsing error: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}
    
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {"error": error_msg}


def get_statistic_item_list(stat_code, start_index=1, end_index=100, use_cache=True):
    """
    특정 통계표의 항목 목록을 조회합니다.
    
    한국은행 ECOS API의 StatisticItemList 기능을 사용하여
    특정 통계표 코드에 대한 모든 항목 코드와 항목명을 조회할 수 있습니다.
    
    Args:
        stat_code: 통계표 코드 (예: "901Y009")
        start_index: 요청 시작 건수 (기본값: 1)
        end_index: 요청 종료 건수 (기본값: 100, 최대 1000)
        use_cache: 캐시 사용 여부 (기본값: True)
    
    Returns:
        dict: 항목 목록 (StatisticItemList 형식) 또는 에러 정보
        
    참고: https://ecos.bok.or.kr/api/#/DevGuide/StatisticItemList
    """
    # end_index 제한 (최대 1000)
    if end_index > 1000:
        end_index = 1000
        logger.warning(f"end_index limited to 1000 (BOK API maximum)")
    
    # 캐시 키 생성
    cache_key = _generate_cache_key("StatisticItemList", stat_code, start_index, end_index)
    
    # 캐시에서 먼저 조회 (항목 목록은 자주 변경되지 않으므로 긴 TTL 사용)
    if use_cache:
        cached_data = _api_cache.get(cache_key)
        if cached_data is not None:
            logger.info(f"Cache HIT for StatisticItemList stat_code={stat_code}")
            return cached_data
    
    # URL 구성
    # /StatisticItemList/{KEY}/{언어}/{요청시작건수}/{요청종료건수}/{통계표코드}/
    url = f"{API_BASE_URL}/StatisticItemList/{ECOS_API_KEY}/json/kr/{start_index}/{end_index}/{stat_code}/"
    
    logger.info(f"BOK API StatisticItemList Request: stat_code={stat_code}, range={start_index}~{end_index}")
    logger.debug(f"Request URL: {url}")
    
    try:
        # Rate Limiting 적용
        _rate_limiter.wait_if_needed()
        
        response = requests.get(url, timeout=API_TIMEOUT)
        response.raise_for_status()
        
        data = response.json()
        
        # BOK API 응답 구조 검증
        if 'RESULT' in data:
            result_code = data['RESULT'].get('CODE', '')
            result_message = data['RESULT'].get('MESSAGE', '')
            
            if result_code != 'INFO-000':
                error_msg = f"BOK API Error [{result_code}]: {result_message}"
                logger.error(error_msg)
                return {"error": error_msg, "result_code": result_code, "result_message": result_message}
        
        # StatisticItemList 데이터 확인
        if 'StatisticItemList' not in data:
            logger.warning("No 'StatisticItemList' key in response")
            return {"error": "Invalid API response format: missing 'StatisticItemList'", "response": data}
        
        item_list = data['StatisticItemList']
        total_count = item_list.get('list_total_count', 0)
        
        logger.info(f"Successfully retrieved {total_count} items for stat_code={stat_code}")
        
        # 항목 목록은 자주 변경되지 않으므로 긴 TTL로 캐시
        if use_cache:
            _api_cache.set(cache_key, item_list, CACHE_TTL_ITEM_LIST)
        
        return item_list
        
    except requests.exceptions.Timeout:
        error_msg = f"Request timeout after {API_TIMEOUT} seconds"
        logger.error(error_msg)
        return {"error": error_msg}
    
    except requests.exceptions.HTTPError as e:
        error_msg = f"HTTP Error {e.response.status_code}: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg, "status_code": e.response.status_code}
    
    except requests.exceptions.RequestException as e:
        error_msg = f"Request failed: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}
    
    except ValueError as e:
        error_msg = f"JSON parsing error: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}
    
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {"error": error_msg}