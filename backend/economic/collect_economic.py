"""
경제 지표 수집 (한국은행 ECOS API → 대시보드용 JSON 형식)

수집 항목: 환율, 주가지수(국제), 금리(국제)
반환 형식: data_manager._generate_economic_data() / 프론트엔드 economic_data.json 구조와 동일
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


def _normalize_time(t: str) -> str:
    """ECOS TIME 값을 YYYY-MM-DD 형식으로 변환 (일: YYYYMMDD, 월: YYYYMM → YYYY-MM-01)"""
    if not t or not isinstance(t, str):
        return ""
    t = t.strip().replace("-", "").replace(" ", "")
    if len(t) == 8:  # YYYYMMDD
        return f"{t[:4]}-{t[4:6]}-{t[6:8]}"
    if len(t) == 6:  # YYYYMM
        return f"{t[:4]}-{t[4:6]}-01"
    return t


def _bok_rows_to_series_and_stats(data_response: dict) -> Optional[Dict[str, Any]]:
    """
    StatisticSearch 응답에서 row 추출 → data 배열 + current/previous/change/change_percent.
    calculate_statistics와 동일 로직으로 통계 계산.
    """
    if "error" in data_response:
        return None
    if "StatisticSearch" not in data_response:
        return None
    rows = data_response.get("StatisticSearch", {}).get("row", []) or []
    if not rows:
        return {"data": [], "current": 0, "previous": 0, "change": 0, "change_percent": 0}

    values: List[float] = []
    data: List[Dict[str, Any]] = []

    for row in rows:
        if isinstance(row, dict):
            time_str = row.get("TIME", "")
            value_str = row.get("DATA_VALUE", "")
        else:
            continue
        if not value_str:
            continue
        try:
            value = float(value_str)
            if value <= 0:
                continue
        except (ValueError, TypeError):
            continue
        values.append(value)
        data.append({"time": _normalize_time(time_str), "value": round(value, 2)})

    # 시간순 정렬 (오래된 것 먼저)
    data.sort(key=lambda x: x["time"])

    if not values:
        return {"data": [], "current": 0, "previous": 0, "change": 0, "change_percent": 0}

    current = values[-1]
    previous = values[0] if len(values) > 1 else current
    change = current - previous
    change_percent = ((current - previous) / previous * 100) if previous != 0 else 0

    return {
        "data": data,
        "current": round(current, 2),
        "previous": round(previous, 2),
        "change": round(change, 2),
        "change_percent": round(change_percent, 2),
    }


def _collect_exchange_rates(start_date: str, end_date: str) -> Dict[str, Any]:
    """환율 (대원화 기준) 수집. USD, EUR, JPY, CNY."""
    from .bok_api import get_market_index, BOK_MAPPING

    mapping = BOK_MAPPING.get("exchange")
    if not mapping or not mapping.get("items"):
        return {}
    items = mapping["items"]
    # 프론트와 동일 키: USD, EUR, JPY, CNY
    wanted = ["USD", "EUR", "JPY", "CNY"]
    result: Dict[str, Any] = {}
    for key in wanted:
        if key not in items:
            continue
        info = items[key]
        name = info.get("name", key)
        res = get_market_index("exchange", start_date, end_date, item_code=key, cycle="D")
        out = _bok_rows_to_series_and_stats(res)
        if out is None:
            continue
        result[key] = {
            "name": f"{key}/KRW",
            "current": out["current"],
            "previous": out["previous"],
            "change": out["change"],
            "change_percent": out["change_percent"],
            "data": out["data"],
        }
    return result


def _collect_stock_indices(start_date: str, end_date: str) -> Dict[str, Any]:
    """국제 주가지수 수집 (902Y002). 항목은 API에서 동적 조회."""
    from .bok_api import get_market_index, get_category_info

    # 주기: ECOS 국제 주가지수는 보통 월별(M)
    cycle = "M"
    info = get_category_info("stock-index-international")
    if "error" in info:
        logger.warning("stock-index-international category info: %s", info["error"])
        return {}

    stat_items = info.get("items", {}) or {}
    if not stat_items:
        logger.warning("No items for stock-index-international")
        return {}

    # 최대 4개 항목 사용 (KOSPI, KOSDAQ, S&P500, NASDAQ 등에 대응 가능한 항목 우선)
    item_codes = list(stat_items.keys())[:8]
    result: Dict[str, Any] = {}
    display_names = {
        "KOSPI": "KOSPI",
        "KOSDAQ": "KOSDAQ",
        "S&P500": "S&P 500",
        "NASDAQ": "NASDAQ",
    }
    seen = 0
    for item_code in item_codes:
        if seen >= 4:
            break
        item_info = stat_items.get(item_code, {})
        name = (item_info.get("name") or item_code).strip()
        res = get_market_index(
            "stock-index-international",
            start_date,
            end_date,
            item_code=item_code,
            cycle=cycle,
        )
        if "error" in res:
            continue
        out = _bok_rows_to_series_and_stats(res)
        if out is None or not out.get("data"):
            continue
        # 키: 짧은 이름 (KOSPI, S&P500 등) 또는 첫 번째 단어/코드
        key = name.replace(" ", "")[:12] or item_code
        for canonical, label in display_names.items():
            if label in name or canonical in name:
                key = canonical
                break
        if key in result:
            key = f"{key}_{seen}"
        result[key] = {
            "name": name if len(name) < 20 else name[:17] + "...",
            "current": out["current"],
            "previous": out["previous"],
            "change": out["change"],
            "change_percent": out["change_percent"],
            "data": out["data"],
        }
        seen += 1
    return result


def _collect_interest_rates(start_date: str, end_date: str) -> Dict[str, Any]:
    """국제 금리 수집 (902Y006 등). 한국/미국/유로/일본 등."""
    from .bok_api import get_market_index, get_category_info

    cycle = "M"
    info = get_category_info("interest-international")
    if "error" in info:
        logger.warning("interest-international category info: %s", info["error"])
        return {}

    stat_items = info.get("items", {}) or {}
    if not stat_items:
        return {}

    # 이름에 한국/미국/유로/일본 포함된 항목 우선
    keywords = ["한국", "미국", "United States", "유로", "Euro", "일본", "Japan"]
    item_codes = list(stat_items.keys())
    ordered: List[str] = []
    for kw in keywords:
        for code in item_codes:
            if code in ordered:
                continue
            name = (stat_items.get(code) or {}).get("name") or ""
            if kw in name:
                ordered.append(code)
    for code in item_codes:
        if code not in ordered:
            ordered.append(code)

    result: Dict[str, Any] = {}
    key_map = {"한국": "KR", "미국": "US", "United States": "US", "유로": "EU", "Euro": "EU", "일본": "JP", "Japan": "JP"}
    for item_code in ordered[:6]:
        item_info = stat_items.get(item_code, {})
        name = (item_info.get("name") or item_code).strip()
        res = get_market_index(
            "interest-international",
            start_date,
            end_date,
            item_code=item_code,
            cycle=cycle,
        )
        if "error" in res:
            continue
        out = _bok_rows_to_series_and_stats(res)
        if out is None:
            continue
        key = "OTHER"
        for kw, k in key_map.items():
            if kw in name:
                key = k
                break
        if key == "OTHER":
            key = name[:4].replace(" ", "_") or item_code
        if key in result:
            key = f"{key}_{item_code}"
        result[key] = {
            "name": name if len(name) < 24 else name[:21] + "...",
            "current": out["current"],
            "previous": out["previous"],
            "change": out["change"],
            "change_percent": out["change_percent"],
            "data": out["data"],
        }
    return result


def collect_economic_data(days_back: int = 90) -> Optional[Dict[str, Any]]:
    """
    한국은행 ECOS API에서 환율·주가지수·금리 수집 후
    data_manager / 프론트엔드용 economic_data 형식으로 반환.

    Args:
        days_back: 과거 며칠치 수집 (기본 90일)

    Returns:
        {
          "stock_index": { "items": { ... } },
          "exchange_rate": { "items": { ... } },
          "interest_rate": { "items": { ... } }
        }
        실패 시 None (호출 측에서 mock 사용).
    """
    now = datetime.now(timezone.utc)
    end_dt = now
    start_dt = now - timedelta(days=days_back)
    end_date = end_dt.strftime("%Y%m%d")
    start_date = start_dt.strftime("%Y%m%d")

    try:
        exchange_items = _collect_exchange_rates(start_date, end_date)
        stock_items = _collect_stock_indices(start_date, end_date)
        interest_items = _collect_interest_rates(start_date, end_date)
    except Exception as e:
        logger.exception("Economic data collection failed: %s", e)
        return None

    # 최소한 환율이라도 있으면 성공으로 처리
    if not exchange_items and not stock_items and not interest_items:
        logger.warning("No economic data collected from BOK API")
        return None

    # 주가지수/금리가 없으면 빈 객체라도 넣어서 프론트 구조 유지
    return {
        "stock_index": {"items": stock_items},
        "exchange_rate": {"items": exchange_items},
        "interest_rate": {"items": interest_items},
    }
