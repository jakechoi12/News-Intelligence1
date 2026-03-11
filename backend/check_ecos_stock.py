"""
ECOS API에서 주가지수 관련 통계표 조회
실행: 프로젝트 루트에서 python backend/check_ecos_stock.py
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    if not os.getenv("ECOS_API_KEY"):
        print("ECOS_API_KEY 필요 (.env)")
        return 1

    from backend.economic.bok_api import search_statistical_codes, get_statistic_item_list

    print("=" * 60)
    print("1. ECOS 통계표 검색: '주가' 포함")
    print("=" * 60)
    r = search_statistical_codes(stat_name="주가", start_index=1, end_index=500)
    if "error" in r:
        print("오류:", r["error"])
    else:
        rows = r.get("row", [])
        for row in rows:
            print(f"  {row.get('STAT_CODE')} | {row.get('STAT_NAME')}")

    print("\n" + "=" * 60)
    print("2. ECOS 통계표 검색: '지수' 포함 (주가·증시 관련)")
    print("=" * 60)
    r2 = search_statistical_codes(stat_name="지수", start_index=1, end_index=500)
    if "error" in r2:
        print("오류:", r2["error"])
    else:
        rows2 = r2.get("row", [])
        # 주가/증시/주가지수 관련만 필터
        keywords = ["주가", "주가지수", "증시", "종합", "KOSPI", "코스피", "코스닥", "국제"]
        for row in rows2:
            name = (row.get("STAT_NAME") or "")
            if any(k in name for k in keywords):
                print(f"  {row.get('STAT_CODE')} | {name}")

    print("\n" + "=" * 60)
    print("3. 901Y057 (주가관련통계표) 항목 목록")
    print("=" * 60)
    items1 = get_statistic_item_list("901Y057", start_index=1, end_index=300)
    if "error" in items1:
        print("  오류:", items1["error"])
    else:
        for row in (items1.get("row") or [])[:30]:
            print(f"  {row.get('ITEM_CODE')} | {row.get('ITEM_NAME')} | {row.get('CYCLE')}")

    print("\n" + "=" * 60)
    print("4. 901Y058 (주가관련자료표) 항목 목록")
    print("=" * 60)
    items2 = get_statistic_item_list("901Y058", start_index=1, end_index=300)
    if "error" in items2:
        print("  오류:", items2["error"])
    else:
        for row in (items2.get("row") or [])[:30]:
            print(f"  {row.get('ITEM_CODE')} | {row.get('ITEM_NAME')} | {row.get('CYCLE')}")

    print("\n" + "=" * 60)
    print("5. 802Y001 통계표 항목 목록 (실제 주가지수용)")
    print("=" * 60)
    items_802 = get_statistic_item_list("802Y001", start_index=1, end_index=100)
    if "error" in items_802:
        print("  오류:", items_802["error"])
    else:
        for row in (items_802.get("row") or []):
            print(f"  {row.get('ITEM_CODE')} | {row.get('ITEM_NAME')} | {row.get('CYCLE')}")

    print("\n" + "=" * 60)
    print("6. 902Y002 (국제 주요국 주가지수) 항목 일부")
    print("=" * 60)
    items = get_statistic_item_list("902Y002", start_index=1, end_index=300)
    if "error" in items:
        print("오류:", items["error"])
    else:
        for row in (items.get("row") or [])[:15]:
            print(f"  {row.get('ITEM_CODE')} | {row.get('ITEM_NAME')} | cycle={row.get('CYCLE')}")

    return 0

if __name__ == "__main__":
    sys.exit(main())
