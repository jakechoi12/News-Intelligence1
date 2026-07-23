# News Intelligence — 인수인계 매뉴얼

> 작성일: 2026-07-23
> 목적: 담당자 변경에 대비해 이 프로젝트의 구조, 동작 원리, 자동화 방식, 필요한 외부 API/Webhook을 코드 기준으로 정리한 문서입니다.
> Live: https://jakechoi12.github.io/News-Intelligence1/
> Repo: https://github.com/jakechoi12/News-Intelligence1

---

## 1. 이 프로젝트는 무엇인가

무역·물류·경제 뉴스를 자동으로 수집 → AI로 분석(카테고리/감성/키워드) → 정적 JSON으로 저장 → GitHub Pages에 대시보드로 표시하는 **서버리스 뉴스 인텔리전스 도구**입니다. 별도의 백엔드 서버(상시 구동되는 API 서버)가 없습니다 — 모든 게 GitHub Actions가 하루 한 번 실행하는 배치 스크립트 + 정적 파일 호스팅으로 돌아갑니다.

핵심 특징:
- **DB 없음**: 모든 데이터는 `frontend/data/*.json` 파일이며, 이 자체가 Git에 커밋되어 저장/버전관리됩니다.
- **서버 없음**: 프론트엔드는 GitHub Pages가 정적 호스팅. 뒤에서 상시 떠 있는 서버 프로세스가 없습니다.
- **스케줄러는 GitHub Actions cron**: 별도 서버의 cron이 아니라 `.github/workflows/daily_collection.yml`이 트리거입니다.

---

## 2. 전체 아키텍처

```
                    ┌───────────────────────────────────────────┐
                    │   GitHub Actions (평일 09:00 KST 자동 실행)  │
                    │   .github/workflows/daily_collection.yml   │
                    └───────────────────┬─────────────────────────┘
                                        │
        ┌───────────────────────────────┼───────────────────────────────┐
        │                               │                               │
        ▼                               ▼                               ▼
┌──────────────────┐        ┌──────────────────────┐        ┌────────────────────┐
│  1. 뉴스 수집       │  →     │  2. AI 분석/집계        │  →     │  3. JSON 파일 생성     │
│  backend/         │        │  backend/analyzer.py │        │  backend/           │
│  collectors/*.py  │        │  (Gemini API)        │        │  data_manager.py    │
└──────────────────┘        └──────────────────────┘        └─────────┬──────────┘
                                                                        │
                    ┌───────────────────────────────────────────────────┘
                    ▼
        ┌───────────────────────────┐        ┌──────────────────────────┐
        │ 4. git commit & push       │  →     │ 5. Teams 알림 발송         │
        │ frontend/data/*.json       │        │ backend/notify_teams.py  │
        └─────────────┬───────────────┘        └──────────────────────────┘
                      │
                      ▼
        ┌───────────────────────────┐
        │ 6. GitHub Pages 배포        │
        │ frontend/ → 정적 호스팅      │
        └─────────────┬───────────────┘
                      ▼
        ┌───────────────────────────┐
        │ 사용자 브라우저               │
        │ frontend/js/app.js가       │
        │ /data/*.json fetch 후 렌더  │
        └───────────────────────────┘
```

---

## 3. 워크플로 상세 (`.github/workflows/daily_collection.yml`)

**트리거**
```yaml
schedule:
  - cron: '0 0 * * 1-5'   # UTC 00:00 = KST 09:00, 평일(월~금)만
workflow_dispatch:         # Actions 탭에서 수동 실행 가능
```

**Job 1: `collect`** (ubuntu-latest)
| 순서 | 스텝 | 내용 |
|---|---|---|
| 1 | Checkout | 저장소 체크아웃 (`fetch-depth: 0`) |
| 2 | Setup Python | 3.11 |
| 3 | Install dependencies | `pip install -r requirements.txt` |
| 4 | **Run news collection** | `python backend/run_collection.py` — 아래 §4 전체가 여기서 실행됨 |
| 5 | Commit and push | `frontend/data/` 변경분만 커밋. **푸시 충돌 시 자동 복구 로직 있음**(원격 최신으로 reset 후 방금 만든 데이터만 다시 체크아웃해서 재커밋) |
| 6 | Send Teams notification | `python backend/notify_teams.py`. `continue-on-error: true`라서 **Teams 알림이 실패해도 워크플로 전체는 성공 처리됨** |

**Job 2: `deploy`** (needs: collect)
- `frontend/` 디렉토리를 GitHub Pages 아티팩트로 업로드 후 배포 (`actions/deploy-pages@v4`)
- Pages 소스가 별도 브랜치가 아니라 **워크플로 자체가 매번 배포**하는 방식(Deploy from a branch가 아니라 "GitHub Actions" 소스로 Pages 설정되어 있어야 함 — Settings → Pages 확인)

**⚠️ 알아둘 것**: `collect` job이 "success"로 끝나도 실제 데이터가 제대로 채워졌는지는 보장 안 됩니다. `run_collection.py`, `analyzer.py` 내부에 예외 처리가 광범위하게 걸려 있어서 API 실패 시에도 조용히 넘어가고 exit code 0으로 끝나는 구조입니다. **"워크플로 성공 = 데이터 품질 정상"이 아님**을 다음 담당자에게 반드시 전달할 것.

---

## 4. 백엔드 파이프라인 상세 (`backend/run_collection.py`가 오케스트레이션)

### 4.1 수집 (`backend/collectors/`)

| 수집기 | 파일 | 방식 | 필요 인증 |
|---|---|---|---|
| RSS | `collectors/rss_collector.py` | 고정된 RSS 피드 목록(글로벌 12개 + 국내 6개, 코드에 하드코딩) 파싱 | 없음 |
| Google News | `collectors/google_news_collector.py` | `news.google.com/rss/search` 공개 검색 RSS, 쿼리 100개 이상을 반복 호출 (쿼리당 최대 20건) | 없음(공개 엔드포인트) |
| Naver News | `collectors/naver_news_collector.py` | 네이버 검색 API(`openapi.naver.com/v1/search/news.json`), 쿼리 130개 이상 반복 | **NAVER_CLIENT_ID + NAVER_CLIENT_SECRET 필요.** 없으면 `collect()`가 즉시 빈 리스트 반환(에러 아님, 그냥 스킵) |
| GDELT | `collectors/gdelt_collector.py` | 로컬 `gdelt_backend` 모듈을 먼저 시도 → **이 모듈은 `.gitignore`에 등록되어 저장소에 없음** → 항상 `ImportError`로 실패 → 공개 GDELT API(`api.gdeltproject.org`)로 자동 폴백. 즉 **실제 운영에서는 항상 공개 API 경로만 사용됨** | 없음 |

수집 후 `run_collection.py`에서:
1. URL 기준 중복 제거 (수집기 간 교차 중복도 여기서 한 번 더 제거, `run_collection.py:71-157`)
2. `filter_irrelevant_articles()` — 결혼/부동산 광고/여권 순위/스포츠 등 정규식 필터링 (`run_collection.py:160-214`)
3. `filter_recent_articles(hours=72)` — 최근 72시간 이내 기사만 남김 (`run_collection.py:217-253`)

### 4.2 AI 분석 (`backend/analyzer.py`, `GeminiAnalyzer` 클래스)

- 사용 모델: 코드상 `gemini-2.0-flash` (`analyzer.py:78`) — 참고로 README/requirement.md에는 "Gemini 2.5 Flash"라고 적혀 있어 **문서와 실제 코드가 불일치**함. 실제로 호출되는 모델명은 코드가 기준.
- `GEMINI_API_KEY`가 없거나 `google-generativeai` 임포트 실패 시 **규칙 기반(rule-based) 분석으로 자동 폴백** (`analyzer.py:69-83`, `235-369`) — 하드코딩된 키워드 매칭으로 카테고리/감성/국가/키워드를 뽑음. 완전히 멈추지는 않지만 품질이 크게 떨어짐.
- 배치 20개씩, 최대 5스레드 병렬 처리 (`analyzer.py:101-153`)
- 산출: `category`(Crisis/Ocean/Air/Inland/Economy/ETC), `sentiment`, `is_crisis`, `country_tags`, `keywords`

**⚠️ 헤드라인 "시사점(3줄 인사이트)" 기능은 코드에서 완전히 제거되었습니다 (2026-07-23).**
기존에는 `backend/data_manager.py`에 Gemini 할당량 문제로 통째로 주석 처리된 죽은 코드(LLM 호출 블록 전체)가 남아 있었고, `analyzer.py`에는 아무 데서도 호출되지 않는 `generate_insights()` / `_generate_insights_with_ai()` 메서드가 방치되어 있었습니다. 이 인수인계 작업 중 다음과 같이 정리했습니다:
- `backend/data_manager.py`의 주석 처리된 LLM 호출 블록 삭제. `_generate_headlines()`는 이제 `analyzer` 파라미터를 받지 않으며, 모든 헤드라인의 `insights` 필드는 `{}`로 명시적으로 고정 (`data_manager.py:_generate_headlines`)
- `backend/analyzer.py`에서 `generate_insights()`, `_generate_insights_with_ai()` 메서드 삭제 (호출부가 없어 완전한 데드 코드였음)
- `backend/run_collection.py`, `backend/test_collection.py`에서 더 이상 필요 없는 `analyzer` 전달 코드 제거

`headlines_data.json`의 모든 헤드라인은 여전히 `"insights": {}`로 나가고, 프론트엔드(`frontend/js/app.js:824-840`)는 이 경우 "시사점 분석 데이터가 없습니다" placeholder를 그대로 보여줍니다 — **동작(사용자 눈에 보이는 결과)은 이전과 동일하며, 이번 작업은 죽은 코드를 정리한 것**입니다.

**이 기능을 나중에 되살리고 싶다면**: 이 커밋 이전 git 히스토리(`git log -- backend/analyzer.py backend/data_manager.py`)에서 원래 구현(Gemini 프롬프트, JSON 파싱, 3-스레드 병렬 처리 로직)을 그대로 복원할 수 있습니다. 재도입 시 Gemini 호출량이 헤드라인 6개 × 매 실행마다 늘어나므로 할당량/과금부터 재확인할 것.

### 4.3 경제 지표 (`backend/economic/`)

| 파일 | 역할 |
|---|---|
| `bok_api.py` (1798줄) | 한국은행 ECOS API 저수준 클라이언트. Rate limiter(3분당 250회) + 5분 캐시 내장. **`ECOS_API_KEY`가 환경변수에 없으면 모듈 임포트 시점에 `ValueError`를 던짐** (`bok_api.py:16-19`) — 그래서 `run_collection.py`는 `ECOS_API_KEY`가 있을 때만 이 모듈 체인을 임포트하도록 방어 처리되어 있음 (`run_collection.py:295`) |
| `collect_economic.py` | 실제 수집 오케스트레이션. **국내 주가지수(KOSPI/KOSDAQ)는 ECOS 802Y001**, **해외 주가지수(S&P500/NASDAQ/Nikkei225/상하이)는 `yfinance` 라이브러리로 직접 조회**(ECOS 키 불필요, Yahoo Finance 공개 데이터). 환율/금리는 ECOS(731Y001, 722Y001, 902Y006 등) |
| `check_ecos_stock.py`, `fetch_kospi.py`, `refresh_economic.py` | 운영 파이프라인에는 포함 안 된 **수동 디버깅/단독 실행용 스크립트**. 로컬에서 `python backend/xxx.py`로 개별 테스트할 때 사용 |

`ECOS_API_KEY`가 없으면 → `economic_data.json`을 아예 새로 쓰지 않고 **기존 파일을 그대로 유지**함 (`data_manager.py:93-102`, "keep existing file so UI never shows empty/dummy"). 즉 경제지표가 며칠째 안 바뀌고 있다면 ECOS 키 문제일 가능성이 높음.

### 4.4 JSON 생성 & 아카이브 (`backend/data_manager.py`)

생성 파일 (`frontend/data/` 아래):
| 파일 | 내용 |
|---|---|
| `news_data.json` | 전체 기사 목록 |
| `headlines_data.json` | 상위 헤드라인 6개(한국 3 + 글로벌 3, 유사 기사 그룹핑으로 선정) + insights(현재 항상 빈 값, §4.2 참고) |
| `map_data.json` | 국가별 crisis/negative 기사 집계 (지도용) |
| `wordcloud_data.json` | 키워드 빈도 (2~3단어 구문 추출, 최대 100개) |
| `economic_data.json` | 주가지수/환율/금리 |
| `last_update.json` | 수집 메타데이터(총 건수, 소요시간 등) |

아카이브 정책 (`data_manager.py:117-219`):
- `archive/daily/YYYY-MM-DD/` — 매 수집 시 생성, 14일 지나면 자동 삭제
- `archive/weekly/YYYY-WXX/` — 매주 금요일에만 생성, 12주 보관
- `archive/monthly/YYYY-MM/` — 매월 1~3일(평일) 중 첫 실행 시 생성, 12개월 보관

### 4.5 Teams 알림 (`backend/notify_teams.py`)

- `TEAMS_WEBHOOK_URL` 환경변수로 웹훅 URL을 받아 Adaptive Card 형식 메시지 전송
- `last_update.json` + `headlines_data.json`을 읽어서 총 수집 건수, 한국/글로벌 건수, 헤드라인 목록, 카테고리 분포를 카드로 구성
- 웹훅 URL이 없으면 조용히 스킵(워크플로 실패 아님)
- **401 에러 대응 로직 내장**: `logic.azure.com` 형태의 "Teams 워크플로" URL인데 `sig=` 파라미터가 없으면 경고 로그 출력 (§6.3 참고)

---

## 5. 프론트엔드 구조 (`frontend/`)

- 순수 정적 HTML/CSS/JS. 빌드 과정 없음(webpack/vite 등 X). `index.html` 하나에 인라인 `<style>`이 대부분 포함되어 있고, 로직은 `js/app.js`(약 1,290줄)에 분리.
- 외부 라이브러리는 전부 CDN 스크립트 태그로 로드: Chart.js(경제지표 차트), Leaflet(지도, OpenStreetMap 무료 타일), WordCloud2.js(워드클라우드). **프론트엔드 쪽에는 API 키가 전혀 필요 없음** — 전부 무료/공개 리소스.
- `app.js:init()` (라인 72)이 진입점. `frontend/data/*.json` 6개 파일을 `Promise.all`로 병렬 fetch한 뒤(`DATA_BASE_URL = './data'`, `app.js:67`) 각 섹션을 렌더링.
- 로컬 테스트: `cd frontend && python -m http.server 8080` (또는 저장소 루트의 `serve_local.py`).

---

## 6. 필요한 API / 인증정보 총정리

### 6.1 GitHub Secrets 목록 (Repository Settings → Secrets and variables → Actions)

| Secret 이름 | 필수 여부 | 용도 | 없을 때 동작 | 발급처 |
|---|---|---|---|---|
| `GEMINI_API_KEY` | 사실상 필수 (없으면 분석 품질 급락) | 뉴스 카테고리/감성/키워드 AI 분석 | 규칙 기반 폴백으로 저하된 품질로 동작 (§4.2) | [Google AI Studio](https://aistudio.google.com/app/apikey) |
| `ECOS_API_KEY` | 권장 (없으면 국내 지표 없음) | 한국은행 경제지표(주가/환율/금리) | 해외 지수(yfinance)는 나오지만 국내(KOSPI 등)/환율/금리는 기존 파일 유지, 갱신 안 됨 | [한국은행 ECOS](https://ecos.bok.or.kr/api/) 회원가입 후 발급 |
| `NAVER_CLIENT_ID` | 선택 (없으면 국내 뉴스 수집원 하나 빠짐) | 네이버 뉴스 검색 API | Naver 수집 단계 자체가 스킵됨(에러 없음) | [Naver Developers](https://developers.naver.com/apps/#/register) 애플리케이션 등록 |
| `NAVER_CLIENT_SECRET` | 위와 세트 | 위와 동일 | 위와 동일 | 위와 동일 |
| `TEAMS_WEBHOOK_URL` | 선택 | 수집 완료 후 Teams 채널 알림 | 알림만 스킵, 워크플로는 정상 진행 | 아래 §6.3 참고 |

**Secret 값은 GitHub 어디서도(웹 UI, API, CLI 무엇으로도) 재조회가 불가능**합니다. 등록 여부와 마지막 수정일만 확인 가능. 값이 맞는지 검증하려면 재발급 후 덮어쓰기 → 수동 워크플로 실행 → 로그 확인이 유일한 방법입니다.

### 6.2 로컬 개발용 `.env` (저장소에는 없음, `.gitignore`에 의해 제외됨)

```env
GEMINI_API_KEY=xxx
ECOS_API_KEY=xxx
NAVER_CLIENT_ID=xxx
NAVER_CLIENT_SECRET=xxx
TEAMS_WEBHOOK_URL=xxx
```
`python-dotenv`가 `backend/run_collection.py`, `backend/notify_teams.py`, `backend/economic/bok_api.py` 등에서 자동으로 `.env`를 로드합니다.

### 6.3 Teams Webhook URL 발급 — 두 가지 방식과 주의점

README/코드 주석에 실제로 겪은 트러블슈팅이 남아 있음:

**A. Power Automate/Teams "워크플로" 웹훅 (신형)**
- Teams 채널 → 워크플로 추가 → "When a Teams webhook request is received"
- 트리거 인증을 반드시 **"Anyone(누구나)"**로 설정해야 GitHub Actions 같은 외부에서 호출 가능
- URL을 복사할 때 `?api-version=...&sp=...&sv=1.0&sig=...` **쿼리 파라미터까지 전부** 포함해야 함. `sig=`가 빠지면 `401 Shared Access scheme` 에러 발생 (`notify_teams.py:223-239`에 이 에러 자동 감지 및 안내 로그 있음)

**B. 구형 Incoming Webhook (권장, 더 단순함)**
- 채널 → `⋯` → 채널 관리 → 커넥터 → Incoming Webhook 검색 → 추가
- 생성된 `https://...webhook.office.com/...` URL을 그대로 `TEAMS_WEBHOOK_URL`에 사용. 인증 없이 POST 가능해서 훨씬 안정적.

### 6.4 프론트엔드에 필요한 키

**없음.** Leaflet은 OpenStreetMap 무료 타일 사용, Chart.js/WordCloud2.js는 순수 클라이언트 라이브러리. 지도 API 키, 분석 툴 키 등 일체 불필요.

---

## 7. 알려진 이슈 / 제한사항 (다음 담당자가 바로 알아야 할 것들)

1. **헤드라인 3줄 시사점(insights)은 코드에서 완전히 제거된 기능임.** §4.2 참고. 죽어있던 코드(주석 처리된 LLM 호출 블록 + 아무 데서도 안 불리던 `generate_insights()`)를 2026-07-23에 정리했음. `headlines_data.json`은 여전히 `insights: {}`를 반환하며 UI 동작은 정리 전과 동일. GEMINI_API_KEY를 아무리 잘 설정해도 이 기능은 살아나지 않음 — 되살리려면 git 히스토리에서 이전 구현을 복원해야 함.
2. **워크플로 "success" ≠ 데이터 정상.** 대부분의 실패가 조용히 삼켜지고 기본값으로 대체되는 구조라, Actions 탭의 초록 체크만으로는 안심할 수 없음. 실제 산출물(JSON)을 주기적으로 열어봐야 함.
3. **RSS 피드 일부가 코드 주석으로 이미 제거됨** (`rss_collector.py:14-19`): Splash247(SSL 오류), Port Technology(XML 파싱 오류), Reuters Business(DNS 오류), 코리아쉬핑가제트(HTML 반환), 이데일리(XML 파싱 오류). 이런 피드가 시간이 지나 복구됐는지 등은 아무도 재확인하지 않고 있음.
4. **GDELT는 로컬 backend 모듈(`gdelt_backend.py`) 없이 항상 공개 API 폴백 경로만 탐** — `.gitignore`에 등록되어 있어 저장소엔 없는 파일. 코드가 이를 "먼저 시도"하는 것처럼 보이지만 실제로는 항상 실패 → API로 넘어가는 구조라 약간의 데드코드성 지연이 있음(무해하지만 알아둘 것).
5. **README/requirement.md와 실제 코드의 모델 버전 불일치**: 문서는 "Gemini 2.5 Flash", 실제 코드(`analyzer.py:78`)는 `gemini-2.0-flash`.
6. **`push` 실패 시 강제 reset 로직이 워크플로에 내장**되어 있음 (`daily_collection.yml:54-73`): 동시에 다른 커밋이 들어오면 `git reset --hard origin/main` 후 방금 만든 데이터 파일만 재적용. 데이터 파일 외 다른 변경(코드 수정 등)과 동시에 이 워크플로가 돌면 충돌 가능성 있으니, 코드를 고칠 땐 가능하면 평일 09:00 KST 실행 시간대를 피하는 게 안전.

---

## 8. 로컬에서 직접 돌려보는 방법

```bash
git clone https://github.com/jakechoi12/News-Intelligence1.git
cd News-Intelligence1
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt

# .env 파일 생성 후 §6.2의 키들 입력

# 전체 파이프라인 실행 (수집 → 분석 → JSON 생성)
python backend/run_collection.py

# 경제지표만 갱신하고 싶을 때
python backend/refresh_economic.py

# Teams 알림만 테스트
python backend/notify_teams.py

# 프론트엔드 로컬 확인
cd frontend && python -m http.server 8080
# 또는 저장소 루트에서: python serve_local.py
```

수동으로 GitHub Actions를 돌리고 싶으면: 저장소 → Actions 탭 → "Daily News Collection" → **Run workflow** 버튼.

---

## 9. 파일 맵 (빠른 참조)

```
News-Intelligence1/
├── .github/workflows/daily_collection.yml   # 자동화 스케줄/배포 정의 (§3)
├── backend/
│   ├── run_collection.py       # 메인 오케스트레이터 — 여기서부터 읽으면 전체 흐름 파악 가능
│   ├── analyzer.py             # Gemini AI 분석 + 규칙기반 폴백 (§4.2)
│   ├── data_manager.py         # JSON 생성/아카이브, 헤드라인 선정 로직 (§4.4)
│   ├── notify_teams.py         # Teams 알림 (§4.5, §6.3)
│   ├── collectors/
│   │   ├── base.py             # 공통 베이스 클래스(로깅, 날짜 파싱 등)
│   │   ├── rss_collector.py    # RSS 피드 목록 + 파싱
│   │   ├── google_news_collector.py  # Google News 검색 쿼리 100+
│   │   ├── naver_news_collector.py   # 네이버 검색 API, 쿼리 130+
│   │   └── gdelt_collector.py        # GDELT 공개 API
│   ├── economic/
│   │   ├── bok_api.py          # ECOS API 클라이언트 (rate limit/cache 내장)
│   │   └── collect_economic.py # 경제지표 수집 오케스트레이션 (ECOS + yfinance)
│   ├── check_ecos_stock.py     # (디버깅용, 운영 파이프라인 아님)
│   ├── fetch_kospi.py          # (디버깅용)
│   ├── refresh_economic.py     # (경제지표만 단독 갱신용 유틸)
│   └── test_collection.py      # 로컬 테스트 스크립트
├── frontend/
│   ├── index.html              # 대시보드 마크업 + 인라인 CSS
│   ├── js/app.js               # 전체 프론트엔드 로직 (fetch, 렌더링, 필터, 차트)
│   └── data/                   # 자동 생성되는 JSON 산출물 + archive/
├── requirements.txt
├── README.md                   # 기존 사용자 대상 설명
├── requirement.md              # 원 요구정의서(기획 문서, v2.6)
└── HANDOVER.md                 # 이 문서
```

---

## 10. 다음 담당자를 위한 체크리스트

- [ ] GitHub 저장소 Owner/Collaborator 권한 이전 (Settings → Collaborators)
- [ ] GitHub Secrets 5종 재확인 또는 새 계정 키로 교체 (§6.1) — 특히 `GEMINI_API_KEY`, `ECOS_API_KEY`는 개인 계정으로 발급된 것일 가능성이 높으므로 퇴사 시 만료/삭제될 수 있음. **가장 먼저 확인할 항목.**
- [ ] `TEAMS_WEBHOOK_URL`이 특정 개인 소유 채널에 걸려있지 않은지 확인 (팀 공용 채널 커넥터로 재설정 권장)
- [ ] GitHub Pages 설정이 "GitHub Actions" 소스로 되어 있는지 확인 (Settings → Pages)
- [ ] Actions 탭에서 최근 실행 로그 몇 개를 열어 실제로 각 API가 정상 호출되고 있는지 확인 (성공 표시만 믿지 말 것, §7-2)
- [ ] 헤드라인 인사이트 기능을 계속 죽여둘지, 되살릴지 팀과 논의 (§7-1, 재활성화 시 Gemini 비용 증가 고려)
