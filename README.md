# News Intelligence

무역·물류·경제 뉴스 인텔리전스 대시보드

> 내부 구성원들이 무역, 물류, 경제, 금융에 영향을 주는 국내·글로벌 뉴스를 빠르게 파악할 수 있도록 돕는 서비스

🔗 **Live Demo**: https://jakechoi12.github.io/News-Intelligence1/

---

## 주요 기능

- **뉴스 수집**: RSS, Google News, Naver News, GDELT에서 자동 수집
- **AI 분석**: Gemini 2.0 Flash를 활용한 카테고리 분류, 감성 분석, 키워드 추출
- **경제 지표**: 주가지수, 환율, 금리 (한국은행 ECOS API)
- **자동화**: GitHub Actions로 평일 오전 9시(KST) 자동 실행
- **알림**: Microsoft Teams 웹훅으로 일일 리포트 발송

---

## 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│                  GitHub Repository                       │
├──────────────┬─────────────────┬────────────────────────┤
│  /frontend   │    /backend     │  /.github/workflows    │
│  정적 파일    │   수집 스크립트   │       자동화           │
├──────────────┼─────────────────┼────────────────────────┤
│ HTML/CSS/JS  │ 뉴스 수집기      │ 매일 09시(KST) 실행    │
│ GitHub Pages │ AI 분석         │ JSON 생성 → commit     │
│    호스팅    │ JSON 생성       │ Teams 알림 발송        │
└──────────────┴─────────────────┴────────────────────────┘
```

---

## 설치 및 실행

### 1. 환경 설정

```bash
# 저장소 클론
git clone https://github.com/jakechoi12/News-Intelligence1.git
cd News-Intelligence1

# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

### 2. 환경 변수 (.env)

```env
# 필수
GEMINI_API_KEY=your_gemini_api_key

# 선택
NAVER_CLIENT_ID=your_naver_client_id
NAVER_CLIENT_SECRET=your_naver_client_secret
BOK_API_KEY=your_bok_api_key
TEAMS_WEBHOOK_URL=your_teams_webhook_url
```

### 3. 로컬 실행

```bash
# 뉴스 수집 실행
python backend/run_collection.py

# 프론트엔드 서버 (테스트용)
cd frontend && python -m http.server 8080
```

---

## 프로젝트 구조

```
News-Intelligence/
├── backend/
│   ├── collectors/          # 뉴스 수집기
│   │   ├── rss_collector.py
│   │   ├── google_news_collector.py
│   │   ├── naver_news_collector.py
│   │   └── gdelt_collector.py
│   ├── analyzer.py          # AI 분석 (Gemini)
│   ├── data_manager.py      # JSON 생성
│   ├── bok_api.py           # 경제지표 API
│   ├── run_collection.py    # 메인 실행 스크립트
│   └── notify_teams.py      # Teams 알림
│
├── frontend/
│   ├── index.html           # 대시보드
│   ├── js/app.js            # 프론트엔드 로직
│   └── data/                # 생성된 JSON 데이터
│       ├── news_data.json
│       ├── headlines_data.json
│       ├── economic_data.json
│       ├── wordcloud_data.json
│       └── map_data.json
│
├── .github/workflows/
│   └── daily_collection.yml # GitHub Actions 워크플로우
│
├── requirements.txt
└── README.md
```

---

## 뉴스 카테고리

| 카테고리 | 설명                                    |
| -------- | --------------------------------------- |
| Crisis   | 파업, 항만 혼잡, 운하 차단 등 위기 상황 |
| Ocean    | 해운, 항만, 컨테이너                    |
| Air      | 항공 화물, 공항                         |
| Inland   | 육상 운송, 철도, 트럭                   |
| Economy  | 경제, 금융, 환율                        |
| ETC      | 기타                                    |

---

## GitHub Actions 설정

Repository Settings → Secrets에 환경 변수 추가:

- `GEMINI_API_KEY` (필수)
- `NAVER_CLIENT_ID`
- `NAVER_CLIENT_SECRET`
- `BOK_API_KEY`
- `TEAMS_WEBHOOK_URL`

### Teams 알림 401 오류 시

**A. Workflow 웹훅 사용 시**

1. **트리거 인증**: "트리거 실행 허용"을 **Anyone(누구나)**로 설정.
2. **URL 전체 복사**: "When a Teams webhook request is received" 트리거를 펼친 뒤 **HTTP POST URL**을 복사할 때,  
   **끝까지 전부** 복사해야 합니다. (`?api-version=...&sp=...&sv=1.0&sig=...` 등 쿼리 파라미터 포함)  
   `sig=` 가 빠진 URL이면 **401 "Shared Access scheme"** 오류가 납니다.
3. GitHub Secrets에 붙여넣을 때 URL이 잘리지 않았는지 확인.

**B. 대안: 구형 Incoming Webhook (권장)**

Workflow URL이 계속 401을 내면, **채널 커넥터**로 만든 Incoming Webhook을 쓰세요.

- Teams 채널 → **⋯** → **채널 관리** → **커넥터** → **Incoming Webhook** 검색 후 **추가**
- 생성된 URL(`https://...webhook.office.com/...`)을 `TEAMS_WEBHOOK_URL`에 그대로 사용 (인증 없이 POST 가능)

---

## 기술 스택

**Backend**: Python 3.10+, google-generativeai, feedparser, requests

**Frontend**: HTML/CSS/JS, Chart.js, Leaflet, WordCloud2.js

**Infra**: GitHub Pages, GitHub Actions

---

## License

This project is for internal use only.
