"""
경제 지표만 수집하여 frontend/data/economic_data.json 을 갱신합니다.
주가지수 해외(SP500, NASDAQ, Nikkei225, Shanghai)는 yfinance 실제 포인트 사용.

실행 (프로젝트 루트에서):
  python backend/refresh_economic.py

ECOS_API_KEY가 있으면 국내(KOSPI/KOSDAQ), 환율, 금리도 ECOS에서 수집.
없어도 yfinance로 해외 주가지수는 수집되어 JSON에 반영됩니다.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

def main():
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(ROOT, ".env"))
    except ImportError:
        pass

    from backend.economic.collect_economic import collect_economic_data
    from backend.data_manager import DataManager

    output_dir = os.path.join(ROOT, "frontend", "data")
    print("경제 지표 수집 중... (해외 주가는 yfinance 실제 포인트)")
    data = collect_economic_data(days_back=90)
    if not data:
        print("수집된 데이터 없음. economic_data.json은 갱신하지 않습니다.")
        sys.exit(1)

    stock_items = data.get("stock_index", {}).get("items", {})
    print("  주가지수 항목:", list(stock_items.keys()))
    for k, v in list(stock_items.items())[:6]:
        print(f"    {k}: current={v.get('current')}")

    dm = DataManager(output_dir=output_dir)
    dm._generate_economic_data(data)
    print("  저장 완료: frontend/data/economic_data.json")

if __name__ == "__main__":
    main()
