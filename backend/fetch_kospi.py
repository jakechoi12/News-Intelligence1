"""
KOSPI 값 조회 스크립트 (한국은행 ECOS API)
실행: 프로젝트 루트에서 python backend/fetch_kospi.py
"""
import os
import sys

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    if not os.getenv("ECOS_API_KEY"):
        print("ECOS_API_KEY가 .env에 없습니다. 한국은행 ECOS에서 발급한 키를 넣어주세요.")
        sys.exit(1)

    from backend.economic.collect_economic import collect_economic_data

    print("한국은행 ECOS API로 경제 지표 수집 중... (주가지수 포함)")
    data = collect_economic_data(days_back=90)
    if not data:
        print("수집된 데이터 없음.")
        sys.exit(1)

    items = data.get("stock_index", {}).get("items", {})
    # KOSPI 키 (이름에 KOSPI 포함된 항목도 찾기)
    kospi = items.get("KOSPI")
    if not kospi:
        for k, v in items.items():
            if "KOSPI" in (v.get("name") or "") or "한국" in (v.get("name") or ""):
                kospi = v
                print(f"  (매칭된 키: {k})")
                break
    if not kospi:
        print("수집된 주가지수 항목:", list(items.keys()))
        if items:
            first = list(items.values())[0]
            print("첫 번째 항목 예시:", first.get("name"), "| current:", first.get("current"))
        sys.exit(0)

    print("\n=== KOSPI ===")
    print("  이름:", kospi.get("name"))
    print("  현재가:", kospi.get("current"))
    print("  이전:", kospi.get("previous"))
    print("  변동:", kospi.get("change"), "(", kospi.get("change_percent"), "%)")
    print("  시계열 데이터 포인트 수:", len(kospi.get("data") or []))
    return 0

if __name__ == "__main__":
    sys.exit(main())
