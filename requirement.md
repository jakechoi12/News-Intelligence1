# News Intelligence 요구정의서

> **최종 업데이트**: 2026-01-16
> **버전**: v2.6 (프로토타입 배포용)

---

## 1. 서비스 목적 (Why)

이 서비스는 내부 구성원들이 무역, 물류, 경제, 금융에 **영향을 주는 국내·글로벌 뉴스를 빠르게 이해**할 수 있도록 돕는 것을 목표로 한다.

* 특히 전 세계에서 발생하는 파업, 항만 혼잡, 운임 변동, 지정학 리스크 등 crisis 관련 내용과 부정적인 기사들은 (Alert)로 바로 확인할 수 있게 한다.
* 뉴스를 단순히 읽는 서비스"가 아니라 "기사를 바탕으로 인사이트를 주는 것이" 목적이다.

이외에도 **주가지수, 환율, 금리**를 함께 보여주고 경제 및 금융 인사이트를 주는 것을 목표로 한다.

---

## 2. 전체 구조 한눈에 보기 (How it works – 개념)

### 2.1 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                    GitHub Repository                             │
├────────────────┬───────────────────┬────────────────────────────┤
│   /frontend    │   /backend        │   /.github/workflows       │
│  (정적 파일)   │  (수집 스크립트)   │  (자동화)                  │
├────────────────┼───────────────────┼────────────────────────────┤
│ • HTML/CSS/JS  │ • 뉴스 수집기     │ • 매일 09시(KST) 수집      │
│ • GitHub Pages │ • AI 분석        │ • JSON 생성 → commit       │
│   호스팅       │ • JSON 생성       │ • 팀즈 알람 발송           │
└────────────────┴───────────────────┴────────────────────────────┘
                            ▼
              /frontend/data/news_data.json (정적 데이터)
              /frontend/data/economic_data.json
              /frontend/data/last_update.json
```

### 2.2 데이터 흐름

1. **GitHub Actions**가 정해진 시간(한국 시간 기준 평일 오전 9시)에 자동 실행
2. 백엔드 스크립트가 뉴스 및 경제지표 수집
3. 시간을 하나의 기준(UTC)으로 통일
4. **불필요한 기사 필터링** (결혼, 부동산 광고, 여권 순위 등) (v2.4)
5. 같은 뉴스는 한 번만 저장 (URL 기반 중복 제거)
6. 최근 72시간 이내 기사만 선별
7. AI가 뉴스 성격과 지표들을 분석 후 인사이트 정리 (Gemini 2.5 Flash 모델 사용)
8. 결과를 JSON 파일로 저장 → GitHub에 자동 커밋
9. 팀즈 채널에 알람 발송
10. 프론트엔드(GitHub Pages)는 JSON 파일을 fetch하여 표시

---

## 3. 뉴스 수집 방식 (Data Collection)

### 3.1 수집 주기 (언제 가져오나?)

* **한국 시간 기준 평일 오전 9시마다 자동 실행** (GitHub Actions cron: `0 0 * * 1-5` UTC)
* 수동 실행 가능 (workflow_dispatch)

---

### 3.2 수집 대상 (어디서 가져오나?)

#### 3.2.1 뉴스

**해외 물류/공급망 뉴스 (RSS)**

| 소스                          | RSS URL                                                 | 설명             |
| ----------------------------- | ------------------------------------------------------- | ---------------- |
| The Loadstar                  | https://theloadstar.com/feed/                           | 글로벌 물류 전문 |
| FreightWaves                  | https://www.freightwaves.com/feed                       | 화물 운송 뉴스   |
| Supply Chain Dive             | https://www.supplychaindive.com/feeds/news/             | SCM 전문 미디어  |
| Splash247                     | https://splash247.com/feed/                             | 해운 뉴스        |
| Air Cargo Week                | https://aircargoweek.com/feed/                          | 항공 화물        |
| Supply Chain 247              | https://www.supplychain247.com/rss/all/feeds            | SCM 종합         |
| Logistics Management          | https://www.logisticsmgmt.com/rss/news                  | 물류 관리 전문   |
| DC Velocity                   | https://www.dcvelocity.com/rss/news                     | 물류센터/유통    |
| American Shipper              | https://www.freightwaves.com/american-shipper/feed      | 미국 해운        |
| Supply Chain Brain            | https://www.supplychainbrain.com/rss/articles           | SCM 인사이트     |
| Material Handling & Logistics | https://www.mhlnews.com/rss                             | 물류 장비/자동화 |
| Global Trade Magazine         | https://www.globaltrademag.com/feed/                    | 글로벌 무역      |
| Transport Topics              | https://www.ttnews.com/rss/all                          | 미국 운송 뉴스   |
| Lloyd's List                  | https://lloydslist.maritimeintelligence.informa.com/rss | 해운 전문 (유료) |
| TradeWinds                    | https://www.tradewindsnews.com/rss                      | 해운 산업        |
| Journal of Commerce           | https://www.joc.com/rss/all                             | 해운/물류 (유료) |
| Seatrade Maritime             | https://www.seatrade-maritime.com/rss.xml               | 해운 산업        |
| Hellenic Shipping News        | https://www.hellenicshippingnews.com/feed/              | 해운 뉴스        |
| Port Technology               | https://www.porttechnology.org/feed/                    | 항만 기술        |
| Container News                | https://container-news.com/feed/                        | 컨테이너 전문    |

**해외 경제/금융 뉴스 (RSS)**

| 소스              | RSS URL                                                 | 설명                  |
| ----------------- | ------------------------------------------------------- | --------------------- |
| Reuters Business  | https://feeds.reuters.com/reuters/businessNews          | 글로벌 비즈니스       |
| Reuters Markets   | https://feeds.reuters.com/reuters/marketsNews           | 금융 시장             |
| CNBC World        | https://www.cnbc.com/id/100727362/device/rss/rss.html   | 글로벌 경제           |
| CNBC Finance      | https://www.cnbc.com/id/10000664/device/rss/rss.html    | 금융 뉴스             |
| MarketWatch       | https://feeds.marketwatch.com/marketwatch/topstories    | 시장 뉴스             |
| Financial Times   | https://www.ft.com/rss/home                             | 경제/금융 (부분 공개) |
| The Economist     | https://www.economist.com/finance-and-economics/rss.xml | 금융/경제 분석        |
| Business Insider  | https://www.businessinsider.com/rss                     | 비즈니스 뉴스         |
| Forbes            | https://www.forbes.com/business/feed/                   | 비즈니스/금융         |
| Bloomberg (Quint) | https://www.bloombergquint.com/feed                     | 블룸버그 파트너       |
| Yahoo Finance     | https://finance.yahoo.com/news/rssindex                 | 금융 뉴스             |
| Investing.com     | https://www.investing.com/rss/news.rss                  | 투자/시장             |
| Seeking Alpha     | https://seekingalpha.com/market_currents.xml            | 시장 분석             |

**해외 무역/관세 뉴스 (RSS)**

| 소스               | RSS URL                                           | 설명      |
| ------------------ | ------------------------------------------------- | --------- |
| Trade.gov          | https://www.trade.gov/rss/feed                    | 미국 무역 |
| WTO News           | https://www.wto.org/english/news_e/news_rss_e.xml | WTO 뉴스  |
| Customs Today      | https://customstoday.com/feed/                    | 관세 뉴스 |
| World Trade Online | https://insidetrade.com/rss/world-trade-online    | 무역 정책 |
| Export.gov         | https://www.export.gov/rss                        | 미국 수출 |

**국내 물류 뉴스 (RSS)**

| 소스             | RSS URL                                                 | 설명           |
| ---------------- | ------------------------------------------------------- | -------------- |
| 물류신문         | https://www.klnews.co.kr/rss/allArticle.xml             | 국내 물류 종합 |
| 해운신문         | https://www.maritimepress.co.kr/rss/allArticle.xml      | 해운 전문      |
| 카고뉴스         | https://www.cargonews.co.kr/rss/allArticle.xml          | 화물/물류      |
| 코리아쉬핑가제트 | https://www.ksg.co.kr/rss/allArticle.xml                | 해운/항만      |
| 현대해양         | https://www.hdhy.co.kr/rss/allArticle.xml               | 해양/조선      |
| 월간 해양한국    | https://www.monthlymaritimekorea.com/rss/allArticle.xml | 해양 산업      |
| 한국해사신문     | https://www.haesanews.com/rss/allArticle.xml            | 해사 뉴스      |
| 로지스틱스매거진 | https://www.logisticsmagazine.co.kr/rss/allArticle.xml  | 물류 매거진    |
| SCM인사이트      | https://www.scminsight.co.kr/rss/allArticle.xml         | SCM 전문       |

**국내 경제/금융 뉴스 (RSS)**

| 소스         | RSS URL                                | 설명      |
| ------------ | -------------------------------------- | --------- |
| 매일경제     | https://www.mk.co.kr/rss/30000001/     | 종합 경제 |
| 한국경제     | https://www.hankyung.com/feed/all-news | 경제 전문 |
| 아시아경제   | https://www.asiae.co.kr/rss/all.xml    | 경제 뉴스 |
| 이데일리     | https://www.edaily.co.kr/rss/all.xml   | 경제/금융 |
| 머니투데이   | https://news.mt.co.kr/rss/all.xml      | 금융/증권 |
| 파이낸셜뉴스 | https://www.fnnews.com/rss/all.xml     | 금융 전문 |
| 서울경제     | https://www.sedaily.com/rss/all.xml    | 경제/산업 |
| 헤럴드경제   | https://biz.heraldcorp.com/rss/all.xml | 비즈니스  |
| 뉴스핌       | https://www.newspim.com/rss/all.xml    | 금융/증권 |
| 이투데이     | https://www.etoday.co.kr/rss/all.xml   | 경제/금융 |

**국내 무역/산업 뉴스 (RSS)**

| 소스         | RSS URL                                          | 설명        |
| ------------ | ------------------------------------------------ | ----------- |
| 한국무역신문 | https://www.weeklytrade.co.kr/rss/allArticle.xml | 무역 전문   |
| 전자신문     | https://www.etnews.com/rss/all.xml               | IT/산업     |
| 산업일보     | https://www.kidd.co.kr/rss/allArticle.xml        | 산업 뉴스   |
| 철강금속신문 | https://www.snmnews.com/rss/allArticle.xml       | 철강/금속   |
| 오토타임즈   | https://www.autotimes.co.kr/rss/allArticle.xml   | 자동차      |
| 반도체뉴스   | https://www.snnews.co.kr/rss/allArticle.xml      | 반도체      |
| 전기신문     | https://www.electimes.com/rss/allArticle.xml     | 에너지/전력 |

**글로벌 이슈 데이터**

* GDELT (title은 url에서 크롤링해서 가져와야함)
* GDELT title 스크래핑 실패 기사는 기사 count와 화면에서 제외, but DB에는 저장

**검색 기반 뉴스**

**Google News 검색 쿼리:**

```python
GOOGLE_NEWS_QUERIES = [
    # ===== Supply chain disruptions =====
    'supply chain disruption',
    'port strike',
    'shipping delay',
    'freight congestion',
  
    # ===== Logistics news =====
    'logistics news',
    'freight rates',
    'container shipping',
    'air cargo',
  
    # ===== Crisis events =====
    'port closure',
    'shipping crisis',
    'supply chain crisis',
  
    # ===== Freight rates and costs =====
    'ocean freight rates',
    'air freight rates',
    'shipping costs increase',
    'logistics costs',
  
    # ===== Major shipping routes and chokepoints =====
    'Suez Canal shipping',
    'Panama Canal transit',
    'Red Sea shipping',
    'Strait of Malacca',
    'Cape of Good Hope route',
    'Bab el-Mandeb strait',
    'Strait of Hormuz shipping',
    'Bosphorus strait shipping',
    'Gibraltar strait shipping',
    'Northern Sea Route',
  
    # ===== Policy and regulations =====
    'shipping regulations',
    'trade policy',
    'customs regulations',
    'import tariffs',
    'export restrictions',
    'IMO regulations',
  
    # ===== Major carriers (Ocean) =====
    'Maersk shipping',
    'MSC Mediterranean',
    'CMA CGM',
    'COSCO shipping',
    'Evergreen Marine',
    'Hapag-Lloyd',
    'ONE Ocean Network Express',
    'Yang Ming shipping',
    'HMM Hyundai Merchant',
    'ZIM shipping',
    'PIL Pacific International Lines',
    'Wan Hai Lines',
  
    # ===== Major carriers (Air) =====
    'FedEx cargo',
    'UPS air freight',
    'DHL Express',
    'Cargolux',
    'Korean Air Cargo',
    'Cathay Pacific Cargo',
    'Emirates SkyCargo',
    'Qatar Airways Cargo',
    'Singapore Airlines Cargo',
    'Lufthansa Cargo',
  
    # ===== Major ports (Asia) =====
    'Port of Shanghai',
    'Port of Singapore',
    'Port of Busan',
    'Port of Ningbo',
    'Port of Shenzhen',
    'Port of Guangzhou',
    'Port of Hong Kong',
    'Port of Qingdao',
    'Port of Tianjin',
    'Port of Kaohsiung',
    'Port of Tanjung Pelepas',
    'Port of Laem Chabang',
    'Port of Ho Chi Minh',
    'Port of Mumbai',
    'Port of Colombo',
  
    # ===== Major ports (Europe) =====
    'Port of Rotterdam',
    'Port of Antwerp',
    'Port of Hamburg',
    'Port of Bremerhaven',
    'Port of Valencia',
    'Port of Barcelona',
    'Port of Piraeus',
    'Port of Felixstowe',
    'Port of Le Havre',
    'Port of Genoa',
  
    # ===== Major ports (Americas) =====
    'Port of Los Angeles',
    'Port of Long Beach',
    'Port of New York',
    'Port of Savannah',
    'Port of Houston',
    'Port of Seattle',
    'Port of Oakland',
    'Port of Vancouver',
    'Port of Santos',
    'Port of Colon Panama',
    'Port of Manzanillo',
  
    # ===== Major ports (Middle East/Africa) =====
    'Port of Jebel Ali',
    'Port of Salalah',
    'Port of Jeddah',
    'Port of Port Said',
    'Port of Durban',
    'Port of Tangier Med',
  
    # ===== Major airports (cargo) =====
    'Hong Kong airport cargo',
    'Memphis airport cargo',
    'Incheon airport cargo',
    'Shanghai Pudong cargo',
    'Anchorage airport cargo',
    'Dubai airport cargo',
    'Louisville airport UPS',
    'Singapore Changi cargo',
    'Tokyo Narita cargo',
    'Frankfurt airport cargo',
    'Paris CDG cargo',
    'Amsterdam Schiphol cargo',
    'London Heathrow cargo',
    'Los Angeles LAX cargo',
    'Miami airport cargo',
    'Taipei Taoyuan cargo',
    'Guangzhou Baiyun cargo',
  
    # ===== Trade and customs =====
    'global trade news',
    'customs clearance',
    'trade disruption',
    'export logistics',
    'import delays',
  
    # ===== Geopolitical risks =====
    'geopolitical risk supply chain',
    'Ukraine war logistics',
    'Taiwan strait shipping',
    'Middle East shipping disruption',
    'sanctions shipping',
    'Russia sanctions logistics',
    'China Taiwan conflict shipping',
    'South China Sea shipping',
    'Iran sanctions shipping',
    'North Korea shipping ban',
    'Houthi attacks shipping',
    'Yemen crisis shipping',
    'Israel Gaza shipping',
    'US China trade war',
    'EU sanctions Russia',
  
    # ===== Latest trends =====
    'nearshoring supply chain',
    'reshoring manufacturing',
    'EV battery supply chain',
    'semiconductor logistics',
    'green shipping',
    'decarbonization shipping',
    'alternative fuels shipping',
    'ammonia fuel shipping',
    'methanol fuel shipping',
    'LNG powered ships',
    'digital supply chain',
    'blockchain logistics',
    'AI logistics',
    'autonomous shipping',
    'drone delivery',
    'cold chain logistics',
    'pharmaceutical logistics',
  
    # ===== Major manufacturers (Semiconductor) =====
    'TSMC supply chain',
    'Samsung semiconductor',
    'Intel chip supply',
    'SK Hynix logistics',
    'Micron supply chain',
    'NVIDIA chip shortage',
    'AMD supply chain',
    'Qualcomm logistics',
    'ASML supply chain',
  
    # ===== Major manufacturers (Automotive) =====
    'Tesla supply chain',
    'Toyota logistics',
    'Volkswagen supply chain',
    'BYD supply chain',
    'Hyundai logistics',
    'Ford supply chain',
    'GM supply chain',
    'BMW logistics',
    'Mercedes supply chain',
  
    # ===== Major manufacturers (EV Battery) =====
    'CATL supply chain',
    'LG Energy Solution',
    'Samsung SDI logistics',
    'Panasonic battery supply',
    'SK On supply chain',
    'BYD battery logistics',
  
    # ===== Major manufacturers (Electronics) =====
    'Apple supply chain',
    'Foxconn logistics',
    'Samsung Electronics supply',
    'Huawei supply chain',
    'Sony logistics',
    'LG Electronics supply',
  
    # ===== Climate/Weather =====
    'weather shipping disruption',
    'drought Panama Canal',
    'hurricane port closure',
    'typhoon shipping delay',
    'flooding port disruption',
    'extreme weather logistics',
  
    # ===== Labor issues =====
    'dockworkers strike',
    'truckers strike',
    'warehouse workers strike',
    'labor shortage logistics',
    'port workers union',
    'ILA strike',
    'ILWU strike',
]
```

**Naver News 검색 쿼리:**

```python
NAVER_NEWS_QUERIES = [
    # ===== 기본 물류 =====
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
  
    # ===== 주요 공항 (글로벌 화물) =====
    '인천공항 화물',
    '김해공항 화물',
    '화물터미널',
    '홍콩공항 화물',
    '상하이푸동 화물',
    '싱가포르창이 화물',
    '두바이공항 화물',
    '앵커리지 화물',
    '멤피스공항 페덱스',
    '루이빌공항 UPS',
    '프랑크푸르트 화물',
    '파리CDG 화물',
    '암스테르담 화물',
    '나리타공항 화물',
    '타이베이 화물',
    '광저우바이윈 화물',
  
    # ===== 무역 및 통관 =====
    '무역 동향',
    '수출 물류',
    '수입 통관',
    '통관 지연',
    'FTA 활용',
    '원산지 증명',
    '수출입 통계',
    '무역수지',
  
    # ===== 최신 이슈 =====
    '반도체 물류',
    '배터리 공급망',
    '전기차 물류',
    '친환경 선박',
    '자율운항 선박',
    '암모니아 선박',
    '메탄올 선박',
    'LNG 추진선',
    '탈탄소 해운',
    '콜드체인',
    '의약품 물류',
  
    # ===== 지정학 (글로벌) =====
    '중국 수출 규제',
    '미중 무역',
    '러시아 제재 물류',
    '북한 해운',
    '우크라이나 전쟁 물류',
    '대만 해협 위기',
    '이란 제재',
    '후티 반군 공격',
    '예멘 사태 해운',
    '이스라엘 가자 물류',
    '중동 위기 해운',
    '남중국해 분쟁',
    '인도태평양 공급망',
    '미국 관세',
    '트럼프 관세',
    'EU 제재',
  
    # ===== 디지털 물류 =====
    '스마트 물류',
    '물류 자동화',
    'AI 물류',
    '물류 로봇',
    '디지털 포워딩',
    '블록체인 물류',
    '디지털 트윈 물류',
  
    # ===== 풀필먼트 =====
    '풀필먼트 센터',
    '당일배송',
    '새벽배송',
    '라스트마일',
    '쿠팡 물류',
    'CJ대한통운',
    '롯데글로벌로지스',
    '한진',
    '로젠',
  
    # ===== 주요 제조업체 =====
    '삼성전자 물류',
    'SK하이닉스 공급망',
    '현대차 물류',
    '기아 공급망',
    'LG에너지솔루션',
    '삼성SDI',
    'SK온',
    'CATL 배터리',
    'TSMC 공급망',
    '테슬라 물류',
    '애플 공급망',
]
```

#### 3.2.1.1 수집 개수 제한 (v2.3)

* **GDELT**: 최대 200건 (기존 50건)
* **Google News**: 쿼리당 최대 20건 (기존 5건)
* **Naver News**: 쿼리당 최대 20건 (기존 5건)
* **RSS Feeds**: 제한 없음 (모든 피드 수집)

#### 3.2.2 경제 지표 (한국은행 ECOS API)

**우선순위 순서**: 주가지수 > 환율 > 금리

| 탭                 | 지표                      | 한국은행 통계표 | 주요 항목                                          |
| ------------------ | ------------------------- | --------------- | -------------------------------------------------- |
| **주가지수** | 국제 주요국 주가지수      | 902Y002         | KOSPI, KOSDAQ, S&P500, Nasdaq, Nikkei, Shanghai 등 |
| **환율**     | 주요국 통화의 대원화 환율 | 731Y001         | USD, EUR, JPY, CNY, GBP 등                         |
| **금리**     | 기준금리                  | 722Y001         | 한국 기준금리                                      |
| **금리**     | 주요국 기준금리           | 902Y006         | 미국, EU, 일본, 중국 등                            |

---

## 4. 시간 처리 원칙 (Time Standardization)

### 4.1 왜 시간 통일이 필요한가?

* 뉴스는 한국, 미국, 유럽 등 **각기 다른 시간대**로 제공된다.
* 그대로 두면 "언제 나온 뉴스인지" 비교가 어려워진다.

### 4.2 처리 방식

* 뉴스가 어떤 나라 시간으로 오든 상관없이
* **모든 뉴스 시간을 UTC 기준으로 변환해서 저장**
* JSON에는 아래 두 시간만 저장한다:
  * `published_at_utc` : 뉴스가 실제로 발행된 시간
  * `collected_at_utc` : 우리 시스템이 가져온 시간

👉 화면에서는 필요하면 한국시간(KST) / 세계시간으로 변환해서 보여준다.

---

## 5. 중복 및 불필요한 뉴스 처리 (De-duplication & Filtering)

### 5.1 왜 중복 제거가 필요한가?

* 같은 뉴스가 여러 매체, 여러 경로로 반복 수집됨
* 그대로 두면 숫자와 통계가 왜곡됨

### 5.2 프로토타입 기준의 단순한 규칙

1. **URL이 같으면 같은 뉴스로 판단 → 1개만 저장**
2. 제목과 내용이 거의 같은 경우 → 하나의 뉴스로 묶어서 관리 (그룹 처리)

### 5.3 불필요한 기사 필터링 (v2.4 신규)

수집된 기사 중 물류/무역/경제와 무관한 기사를 자동으로 제거:

**필터링 대상:**

* 결혼/혼인 관련: `[화촉]`, `결혼`, `결혼식`, `wedding`
* 부동산 광고: `견본주택`, `분양`, `입주`, `리버블시티`, `자이`, `아파트.*광고`
* 여권/비자 랭킹: `여권.*순위`, `여권.*\d+위`, `비자.*면제`, `passport.*rank`
* 기타 광고/프로모션: `\[.*광고.*\]`, `\[.*프로모션.*\]`, `\[.*이벤트.*\]`
* 자격시험/교육 일정: `자격시험.*일정`, `특례교육.*일정`, `시험.*공고`
* 동정 기사: `[동정]`, `방문.*마치고.*귀국`, `출장.*귀국`
* 연예인 사건사고: `전신.*화상`, `휠체어.*귀국` (물류 무관)

**필터링 방식:**

* 제목과 요약에서 정규표현식 패턴 매칭
* 매칭되는 기사는 수집 결과에서 제외
* 필터링된 기사 수를 로그에 기록

---

## 6. AI 분석 기능 (Simple AI Processing)

### 6.1 사용 모델 및 성능 최적화 (v2.3)

* **Gemini 2.5 Flash** (Google AI)
* 환경변수: `GEMINI_API_KEY`

**성능 최적화 (v2.3)**

* **배치 처리**: 20개씩 묶어서 처리
* **병렬 처리**: 최대 5개 스레드로 동시 분석
* **시사점 생성**: 최대 3개 스레드로 병렬 처리
* **예상 처리 시간**: 기존 대비 60-70% 단축

### 6.2 뉴스 카테고리 분류

AI를 사용하여 뉴스를 아래 중 하나로 자동 분류한다.

| 카테고리 | 설명                                      | Alert 사용 |
| -------- | ----------------------------------------- | ---------- |
| Crisis   | 파업, 사고, 분쟁 등 (실제 진행 중인 사건) | ✅         |
| Ocean    | 해운, 조선, 해양연구, KRISO 등            |            |
| Air      | 항공                                      |            |
| Inland   | 내륙 운송                                 |            |
| Economy  | 경제, 운임, 수요                          |            |
| ETC      | 기타                                      |            |

**카테고리 분류 규칙 (v2.4):**

* 기술 개발, R&D 성공, 국산화 뉴스는 **Crisis가 아님**
* 예: "AI 기반 손상통제지원시스템 국산화 성공" → Ocean (기술 개발이므로)
* 해양/조선/해사 관련 연구소(KRISO, 해수부 등) 뉴스 → Ocean

### 6.3 뉴스 감성 분류

AI를 사용하여 뉴스를 아래 중 하나로 자동 분류한다.

| 감성 | Alert 사용 |
| ---- | ---------- |
| 긍정 |            |
| 부정 | ✅         |
| 중립 |            |

### 6.4 국가 정보 추출

* 뉴스 내용에서 **관련 국가 또는 지역**을 AI가 추출
* ISO 국가 코드 형식 (예: US, KR, CN)
* 지도 시각화에 사용

### 6.5 키워드 추출 (v2.4 개선)

* 각 뉴스에서 **중요 키워드 최대 10개** 추출 (기존 3~5개 → 10개)
* 워드클라우드 시각화에 사용
* Stop Words 자동 제외

### 6.6 경제 지표 인사이트 (선택)

* 지표 변동에 대한 간단한 해설 제공
* 물류/무역 관점에서의 시사점 분석

---

## 7. 데이터 저장 및 아카이브

### 7.1 기본 원칙 (정적 파일 기반)

* 모든 데이터는 JSON 파일로 저장한다.
* 뉴스 수집 범위는 **최근 24시간** 데이터이다.
* GitHub Actions가 수집 후 자동으로 repository에 커밋한다.

### 7.2 JSON 파일 구조

```
/frontend/data/
├── news_data.json          # 뉴스 데이터 (기사 목록)
├── headlines_data.json     # 헤드라인 데이터 (별도 파일, v2.6)
├── economic_data.json      # 경제 지표 데이터
├── map_data.json           # 지도 데이터 (국가별 crisis 카운트)
├── wordcloud_data.json     # 워드클라우드 키워드
├── last_update.json        # 마지막 업데이트 정보
└── archive/                # 아카이브 (v2.6)
    ├── daily/              # 14일 보관
    │   └── 2026-01-16/
    ├── weekly/             # 12주 보관 (매주 금요일)
    │   └── 2026-W03/
    └── monthly/            # 12개월 보관 (매월 첫 평일)
        └── 2026-01/
```

### 7.3 news_data.json 스키마

```json
{
  "articles": [
    {
      "id": "unique_id",
      "title": "뉴스 제목",
      "content_summary": "요약",
      "source_name": "출처",
      "url": "원문 링크",
      "published_at_utc": "2026-01-15T01:00:00Z",
      "collected_at_utc": "2026-01-15T01:00:00Z",
      "news_type": "KR | GLOBAL",
      "category": "Crisis | Ocean | Air | Inland | Economy | ETC",
      "sentiment": "positive | negative | neutral",
      "is_crisis": true,
      "country_tags": ["US", "KR"],
      "keywords": ["strike", "port", "delay"],
      "goldstein_scale": -5.0,
      "avg_tone": -3.2,
      "num_mentions": 100,
      "num_sources": 15
    }
  ],
  "total": 156,
  "kr_count": 45,
  "global_count": 111,
  "generated_at": "2026-01-15T01:00:00Z"
}
```

### 7.3.1 headlines_data.json 스키마 (v2.6 신규)

```json
{
  "headlines": [
    {
      "id": "article_id",
      "title": "뉴스 제목",
      "content_summary": "기사 요약 (LLM 시사점 생성용)",
      "source_name": "출처",
      "url": "원문 링크",
      "published_at_utc": "2026-01-15T01:00:00Z",
      "group_count": 5,
      "insights": {
        "trade": "아시아-유럽 항로 운송 비용 20% 상승 예상",
        "logistics": "희망봉 우회로 인한 리드타임 7-10일 증가",
        "scm": "안전재고 확대 및 복수 항로 확보 필요"
      }
    }
  ],
  "total": 6,
  "generated_at": "2026-01-15T01:00:00Z"
}
```

**시사점 생성 방식 (v2.6):**

* **LLM(Gemini)만 사용**: title + content_summary 기반으로 AI가 시사점 생성
* **Rule-based fallback 제거**: LLM 실패 시 빈 시사점 반환
* **UI 표시**: 시사점이 없으면 "시사점 분석 데이터가 없습니다" 표시

### 7.4 economic_data.json 스키마

```json
{
  "stock_index": {
    "items": {
      "KOSPI": {
        "name": "KOSPI",
        "current": 2650.32,
        "previous": 2640.15,
        "change": 10.17,
        "change_percent": 0.39,
        "data": [
          {"time": "20260101", "value": 2600.00},
          {"time": "20260102", "value": 2610.50}
        ]
      }
    },
    "last_updated": "2026-01-15T01:00:00Z"
  },
  "exchange_rate": {
    "items": {
      "USD": {
        "name": "미국 달러 (USD)",
        "current": 1432.50,
        "previous": 1428.20,
        "change": 4.30,
        "change_percent": 0.30,
        "data": []
      }
    }
  },
  "interest_rate": {
    "items": {
      "KR": {
        "name": "한국 기준금리",
        "current": 3.50,
        "previous": 3.50,
        "change": 0,
        "change_percent": 0,
        "data": []
      }
    }
  }
}
```

### 7.5 데이터 아카이브 (v2.6 신규)

**아카이브 정책:**

| 구분    | 보관 위치                      | 보관 기간 | 생성 조건    |
| ------- | ------------------------------ | --------- | ------------ |
| Daily   | `/archive/daily/YYYY-MM-DD/` | 14일      | 매 수집 시   |
| Weekly  | `/archive/weekly/YYYY-WXX/`  | 12주      | 매주 금요일  |
| Monthly | `/archive/monthly/YYYY-MM/`  | 12개월    | 매월 첫 평일 |

**아카이브 대상 파일:**

* news_data.json
* headlines_data.json
* economic_data.json
* map_data.json
* wordcloud_data.json
* last_update.json

**자동 정리:**

* 보관 기간이 지난 아카이브는 자동 삭제
* 예상 용량: 일 350KB → 월 ~7MB → 연 ~82MB (GitHub 1GB 한도 내)

### 7.6 last_update.json 스키마

```json
{
  "executed_at_utc": "2026-01-15T01:00:00Z",
  "executed_at_kst": "2026-01-15T10:00:00+09:00",
  "total_collected": 156,
  "new_articles": 45,
  "duplicates": 20,
  "kr_count": 45,
  "global_count": 111,
  "crisis_count": 12,
  "duration_seconds": 125.5,
  "success": true,
  "errors": []
}
```

---

## 8. 화면 제공 방식 (Frontend Concept)

### 8.0 디자인 원칙

* **테마**: 다크 테마 유지
* **언어**: 글로벌 뉴스 원문을 제외하면 한국어로 구성
* **스타일**: 토스(Toss) 앱의 그래프 스타일 참고
* **폰트**: Pretendard (한글), JetBrains Mono (숫자/코드)

### 8.1 대시보드 레이아웃 (v2.1 Updated)

**레이아웃 원칙**

- 단일 컬럼 레이아웃 (사이드바 제거)
- 정보 우선순위에 따른 상단-하단 배치
- 경제 지표는 상단 티커로 항상 표시

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Header                                                                  │
│  ┌─────────┐  📊 98 | 🇰🇷 13 | 🌍 85 | 🚨 15     Last updated: 2026-01-15 │
│  │ 📰 Logo │  Total   Korea   Global   Crisis                 10:00 KST │
│  └─────────┘                                                            │
├─────────────────────────────────────────────────────────────────────────┤
│  💹 경제지표 티커 (좌로 흐르는 마퀴)                                      │
│  KOSPI 2,650 ▲+0.39% | S&P500 5,890 ▲+0.25% | USD 1,432 ▲+0.30% | ...  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────────────────────────┬─────────────────────────────────────┐
│  │  💬 Trending Keywords          │  📰 Top Headlines                    │
│  │  (구름 모양 워드클라우드)       │  - 주요 뉴스 6개                     │
│  │                                │  - 클릭 시 원문 이동                 │
│  └────────────────────────────────┴─────────────────────────────────────┘
│                                                                          │
│  ┌────────────────────────────────┬─────────────────────────────────────┐
│  │  🗺️ Critical Map               │  📊 Economic Indicators              │
│  │  - 국가별 위험도 히트맵         │  - 구글 파이낸스 스타일              │
│  │  - Leaflet 기반                │  - 대표 지표 선택 → 메인 차트        │
│  │                                │  - 나머지 지표는 증감률로 표시       │
│  │                                │  - 기간 선택: 1M, 3M, 6M, 1Y        │
│  └────────────────────────────────┴─────────────────────────────────────┘
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐
│  │  📈 Distribution (가로 바 차트)                                       │
│  │  ┌───────────────────────────────────────────────────────────────┐ │
│  │  │ Category: [Crisis] [Ocean] [Air] [Inland] [Economy] [ETC]    │ │
│  │  │           ████████  ██████████████  ████  ██████  ████  ████ │ │
│  │  └───────────────────────────────────────────────────────────────┘ │
│  │  ┌───────────────────────────────────────────────────────────────┐ │
│  │  │ Country:  [US] [CN] [KR] [JP] [DE] [SG] [Others]             │ │
│  │  │           ██████████  ████████  ██████  ████  ████  ██  ████ │ │
│  │  └───────────────────────────────────────────────────────────────┘ │
│  └─────────────────────────────────────────────────────────────────────┘
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐
│  │  📋 News Articles                                                    │
│  │  ┌─────────────────────────────────────────────────────────────┐   │
│  │  │ [All] [Korea] [Global]                                      │   │
│  │  └─────────────────────────────────────────────────────────────┘   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │
│  │  │ 🔴 Crisis 뉴스 카드 (빨간색 테두리)                         │   │
│  │  └─────────────────────────────────────────────────────────────┘   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │
│  │  │ 🔵 Ocean 뉴스 카드 (파란색 테두리)                          │   │
│  │  └─────────────────────────────────────────────────────────────┘   │
│  │  [ < ] [ 1 ] [ 2 ] [ 3 ] [ > ]  페이지네이션                       │
│  └─────────────────────────────────────────────────────────────────────┘
│                                                                          │
│  Footer: © 2026 News Intelligence                                       │
└─────────────────────────────────────────────────────────────────────────┘
```

**변경 사항 요약 (v2.1)**

- 헤더에 Daily Summary 통합 (Total, Korea, Global, Crisis)
- Critical Alerts 화면에서 제거 (추후 고도화)
- Economic Indicators: 구글 파이낸스 스타일 (대표 지표 + 증감률)
- Category/Country Distribution: 가로 바 차트로 변경
- 뉴스 카드: 카테고리별 색상 테두리 적용

### 8.2 Daily Summary (수집 요약)

* 최근 24시간 이내 수집된 뉴스 개수
* 한국 뉴스 / 글로벌 뉴스 개수
* 마지막 업데이트 시간(UTC + KST)

### 8.3 Distribution 차트 (가로 바 차트)

**Category Distribution**

* 가로 바 차트로 각 카테고리 비율 표시
* 색상 (굵은 범례와 함께):
  - **Crisis**: #ef4444 (빨강)
  - **Ocean**: #3b82f6 (파랑)
  - **Air**: #10b981 (초록)
  - **Inland**: #f59e0b (노랑/주황)
  - **Economy**: #8b5cf6 (보라)
  - **ETC**: #6b7280 (회색)

**Country Distribution**

* 가로 바 차트로 국가별 뉴스 비율 표시
* 상위 6개국 + Others로 표시
* 각 국가별 고유 색상 부여

**범례 스타일**

* 굵은 글씨 (font-weight: 600)
* 색상 점 + 라벨 + 퍼센트
* 호버 시 해당 섹션 강조

### 8.4 Critical Alerts (v2.1 비활성화)

> ⚠️ **v2.1에서 비활성화**: 추후 고도화 시 재활성화 예정

* Crisis 카테고리 또는 부정 감성으로 분류된 기사들 요약
* 클릭 시 원문 이동
* 최대 5개 표시
* Goldstein Scale 기반 심각도 표시 (GDELT)

### 8.5 워드 클라우드 & 헤드라인

**8.5.1 워드 클라우드 (v2.3 개선)**

* 목적: 현재 물류 이슈의 **구체적인** 핵심 키워드를 한눈에 파악
* 데이터: 최근 24시간 이내 수집된 **전체 뉴스**의 키워드 (쿼리 무관)
* 빈도가 높을수록 크게 표시
* 클릭 시 해당 키워드 관련 뉴스 필터링

**일반 키워드 필터링 강화 (v2.3)**

다음과 같은 일반적인 업계 용어는 워드클라우드에서 제외:

```
freight, logistics, shipping, port, container, cargo, trade, 
import, export, supply chain, 물류, 해운, 항만, 컨테이너, 
수출, 수입, 무역, 화물, 운송, 공급망, news, article, report
```

**구체적 키워드 추출 (v2.4 개선)**

* **2-3단어 구문(bigram/trigram) 추출**: 앞뒤 단어를 포함한 구체적 이슈 파악
  - 예: "Red Sea attacks", "부산항 체선", "운임 인상", "houthi 공격"
* **조사/관사 필터링**: `in 2025`, `in the`, `to the`, `port of`, `the post` 등 불필요한 조사/관사 제거
* **키워드 수 증가**: 워드클라우드 표시 키워드 50개 → 100개
* **필터링된 키워드**: 기존 키워드에서 일반 단어 제외 후 포함
* **우선순위**:
  1. 3단어 구문 (중요한 이슈)
  2. 2단어 구문 (구체적 사건/현상)
  3. 고유명사 (회사명, 항만명, 국가/지역명)
  4. 이슈 키워드 (사건/현상)

**8.5.2 주요 뉴스 헤드라인 (v2.6 개선)**

* 목적: 그날의 **진짜 중요한 뉴스**를 파악
* 선정 기준: **유사 기사 그룹핑 + 한국/글로벌 균형**
* **별도 JSON 파일**: `headlines_data.json`으로 분리 (v2.6)
* 동작 방식 (v2.6):
  1. 제목 유사도(Jaccard Similarity 40% 이상)로 기사 그룹핑
  2. 그룹 크기(같은 주제 기사 수) 순으로 정렬
  3. 한국/글로벌 각각 3개씩 선택 (가장 많이 다뤄진 주제 우선)
  4. 각 헤드라인에 **content_summary 포함** (시사점 생성용)
  5. 각 헤드라인에 대해 **LLM 시사점 생성** (병렬 처리, rule-based fallback 제거)
* 클릭 시 원문 이동

**헤드라인 선정 알고리즘 상세:**

```python
# 1. 제목 유사도로 기사 그룹핑
def jaccard_similarity(title1_words, title2_words):
    intersection = len(title1_words & title2_words)
    union = len(title1_words | title2_words)
    return intersection / union

# 유사도 40% 이상이면 같은 그룹으로 묶음
article_groups = group_by_similarity(articles, threshold=0.4)

# 2. 그룹 크기 순으로 정렬 (많이 다뤄진 주제 우선)
article_groups.sort(key=lambda x: x.group_count, reverse=True)

# 3. 한국/글로벌 균형 유지하며 선택
kr_headlines = [g for g in groups if g.news_type == 'KR'][:3]
global_headlines = [g for g in groups if g.news_type == 'GLOBAL'][:3]

# 4. 시사점 생성 (병렬 처리)
```

**왜 유사 기사 그룹핑인가?**

* 여러 매체에서 같은 이슈를 다루면 → **오늘의 주요 뉴스**
* 단순 최신순보다 **중요도 기반** 선정이 더 의미 있음
* `group_count`로 몇 개 매체에서 다뤘는지 표시 가능

**왜 한국/글로벌 혼합인가?**

* 한국 기사만 나오면 글로벌 트렌드를 놓칠 수 있음
* 글로벌 기사만 나오면 국내 영향도를 파악하기 어려움
* 균형 있는 뉴스 섭취를 위해 3:3 혼합

**헤드라인 툴팁 (v2.4 개선)**

마우스 오버 시 AI가 분석한 **무역/물류/SCM 종합 시사점** 표시:

```
┌─────────────────────────────────────────────────────┐
│ 💡 Red Sea attacks continue to disrupt shipping     │
├─────────────────────────────────────────────────────┤
│ • 아시아-유럽 운임 20% 상승 대비 원가 재산정 필요   │
│ • 수에즈 우회 시 14일 추가 소요, 선적 일정 조정 권장│
│ • 유럽향 부품 안전재고 3주 이상으로 상향 검토       │
└─────────────────────────────────────────────────────┘
```

* **틀 없이 종합 분석**: 무역/물류/SCM 관점을 자연스럽게 종합하여 3줄로 요약
* 각 줄은 30~50자 내외의 한국어 문장
* 구체적인 수치, 지역, 기업명, 영향 범위 포함
* AI(Gemini)가 **title + content_summary** 기반으로 자동 생성 (v2.6)
* **LLM 전용**: Rule-based fallback 완전 제거 (v2.6)
* LLM 실패 시 빈 시사점 반환 → UI에서 "시사점 분석 데이터가 없습니다" 표시

**8.5.3 지도 (Crisis Heatmap)**

* 목적: 어느 국가/지역에서 물류 리스크가 발생하는지 직관적 파악
* 데이터: Crisis 뉴스 + 부정 감성 뉴스
* 국가별 위험도 계산:
  * Crisis 뉴스 1건 = 1점
  * 누적 계산
* 색상 표현:
  * 1~2건: 연한 빨강
  * 3~5건: 중간 빨강
  * 6건 이상: 진한 빨강
* 마우스 오버: 국가명, 건수, 뉴스 목록

### 8.6 경제 지표 그래프 (구글 파이낸스 스타일)

**디자인 원칙 (구글 파이낸스 참고)**

* 대표 지표 선택 시 메인 라인 차트로 표시
* 나머지 지표는 증감률 리스트로 표시
* 기간 선택 가능: 1M (기본), 3M, 6M, 1Y
* X축/Y축 자동 스케일링 (기간에 따라 변경)
* 클린한 라인 차트 + 그라데이션 영역
* 컬러 시맨틱: 상승=초록, 하락=빨강

**탭 구조 (우선순위 순)**

| 탭       | 표시 항목                                          | 기본 선택 |
| -------- | -------------------------------------------------- | --------- |
| 주가지수 | KOSPI, KOSDAQ, S&P500, Nasdaq, Nikkei, Shanghai 등 | KOSPI     |
| 환율     | USD, EUR, JPY, CNY, GBP 등 대원화 환율             | USD       |
| 금리     | 한국, 미국, EU, 일본, 중국 기준금리                | 한국      |

**메인 컴포넌트 레이아웃**

```
┌─────────────────────────────────────────────────────────────────────┐
│ [주가지수] [환율] [금리]  ← 탭                                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  KOSPI                              [1M] [3M] [6M] [1Y]  ← 기간 선택 │
│  2,650.32  ▲ +10.17 (+0.39%)       ← 현재값 + 변동                  │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │         ╭─────────────────────────────╮                        │ │
│  │ 2,700 ─│                               ╲                       │ │
│  │        │                                ╲_____                 │ │
│  │ 2,650 ─│                                      ╲                │ │
│  │        │                                       ●               │ │
│  │ 2,600 ─│    ╱╲                                                 │ │
│  │        ╱    ╱  ╲                                               │ │
│  │ 2,550 ╱────╯                                                   │ │
│  │       ├────────┬─────────┬─────────┬─────────┬────────┤       │ │
│  │       1월1일   1월8일   1월15일   1월22일   1월29일           │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌─────────┬─────────┬─────────┬─────────┬─────────┐              │
│  │ KOSDAQ  │  S&P500 │ Nasdaq  │ Nikkei  │Shanghai │  ← 지표 리스트│
│  │ ▲+0.52% │ ▲+0.25% │ ▲+0.18% │ ▼-0.12% │ ▲+0.35% │              │
│  └─────────┴─────────┴─────────┴─────────┴─────────┘              │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

**기간별 X축 표시**

* 1M: 일별 (1일, 8일, 15일, 22일, 29일)
* 3M: 주별 (1월, 2월, 3월)
* 6M: 월별 (1월, 3월, 5월)
* 1Y: 분기별 (Q1, Q2, Q3, Q4)

**지표 리스트 (증감률 표시)**

* 선택되지 않은 지표들은 증감률만 간략히 표시
* 클릭 시 해당 지표가 메인 차트로 전환
* 상승: 초록색, 하락: 빨간색

### 8.7 뉴스 목록

**시간 표시 형식 (v2.2 개선)**

```
• 60분 이하: "X분 전" (예: 23분 전)
• 60분 초과 ~ 24시간: "X시간 Y분 전" (예: 2시간 35분 전)
• 24시간 초과: "X일 전" 또는 절대 시간 (예: 2026-01-15 10:30)
```

**뉴스 카드 스타일 (카테고리별 색상)**

각 카테고리에 따라 카드 좌측 테두리 또는 배경 악센트 색상 적용:

| 카테고리 | 테두리 색상 | Hex     |
| -------- | ----------- | ------- |
| Crisis   | 빨강        | #ef4444 |
| Ocean    | 파랑        | #3b82f6 |
| Air      | 초록        | #10b981 |
| Inland   | 주황        | #f59e0b |
| Economy  | 보라        | #8b5cf6 |
| ETC      | 회색        | #6b7280 |

**카드 레이아웃 예시**

```
┌────────────────────────────────────────────────────────────────────┐
│ │  🇰🇷 Korea   [Crisis]                          2026-01-15 10:23 │
│ █                                                                  │
│ █  부산항 체선 심화로 물류 지연 우려 확대                            │
│ █                                                                  │
│ │  부산항의 체선이 심화되면서 수출입 물류에 차질이 우려된다.        │
│ │  전문가들은 2주간 지속될 것으로...                               │
│ │                                                                  │
│ │  🏷️ strike, port, delay    🌍 KR, US                            │
└────────────────────────────────────────────────────────────────────┘
  ↑ 빨간색 테두리 (Crisis)
```

**각 뉴스 카드 표시 정보:**

* 대분류: 한국 뉴스 / 글로벌 뉴스 뱃지
* 소분류: 카테고리 라벨 (색상 배지)
  * 뉴스 제목 (클릭 시 원문 이동)
* 요약 (2줄 제한)
* 발행 시간 (상대적 시간 + 절대 시간)
* 관련 국가 태그
* 키워드 태그 (최대 10개, 화면에는 최대 3개 표시)
* 키워드 태그는 줄바꿈 지원 (flex-wrap)
  * GDELT 뉴스인 경우:
  * Goldstein Scale (심각도 바)
    * Avg Tone
    * Mentions / Sources

**필터링**

* [All] [Korea] [Global] 탭으로 필터링
* 카테고리 필터 (Distribution 차트 클릭 시 연동)

**정렬 및 페이지네이션**

* 정렬: 발행시간 기준 최신순
* 페이지네이션: 한 페이지에 최대 10개

---

## 9. API 제공 원칙 (Static JSON)

GitHub Pages는 정적 호스팅이므로 REST API 대신 JSON 파일을 직접 fetch

| 데이터        | 파일 경로                     |
| ------------- | ----------------------------- |
| 뉴스 목록     | `/data/news_data.json`      |
| 헤드라인      | `/data/headlines_data.json` |
| 경제 지표     | `/data/economic_data.json`  |
| 지도 데이터   | `/data/map_data.json`       |
| 워드클라우드  | `/data/wordcloud_data.json` |
| 업데이트 상태 | `/data/last_update.json`    |
| 아카이브      | `/data/archive/daily          |

프론트엔드 필터링:

* 한국/글로벌 탭: `news_type` 필드로 클라이언트 필터링
* 카테고리: `category` 필드로 클라이언트 필터링
* 페이지네이션: 클라이언트 사이드 처리

---

## 10. 배포 및 자동화 (Deployment & Automation)

### 10.1 GitHub Repository 구조

```
news-intelligence/
├── .github/
│   └── workflows/
│       └── daily_collection.yml
├── frontend/
│   ├── index.html
│   ├── css/
│   ├── js/
│   └── data/
│       ├── news_data.json
│       ├── economic_data.json
│       └── ...
├── backend/
│   ├── collectors/
│   ├── analyzer.py
│   ├── bok_backend.py
│   ├── gdelt_backend.py
│   ├── run_collection.py
│   └── notify_teams.py
├── requirements.txt
└── README.md
```

### 10.2 GitHub Pages 설정

* Source: `frontend/` 디렉토리
* Branch: `main`
* URL: `https://<org>.github.io/news-intelligence/`

### 10.3 GitHub Actions 워크플로우

```yaml
name: Daily News Collection

on:
  schedule:
    - cron: '0 0 * * 1-5'  # UTC 00:00 = KST 09:00 (평일)
  workflow_dispatch:      # 수동 실행 가능

jobs:
  collect:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
  
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
    
      - name: Install dependencies
        run: pip install -r requirements.txt
  
      - name: Run collection
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          ECOS_API_KEY: ${{ secrets.ECOS_API_KEY }}
          NAVER_CLIENT_ID: ${{ secrets.NAVER_CLIENT_ID }}
          NAVER_CLIENT_SECRET: ${{ secrets.NAVER_CLIENT_SECRET }}
        run: python backend/run_collection.py
  
      - name: Commit data files
        run: |
          git config user.name github-actions
          git config user.email github-actions@github.com
          git add frontend/data/
          git commit -m "📊 Daily news update $(date +%Y-%m-%d)" || exit 0
          git push
    
      - name: Send Teams notification
        env:
          TEAMS_WEBHOOK_URL: ${{ secrets.TEAMS_WEBHOOK_URL }}
        run: python backend/notify_teams.py
```

### 10.4 필요한 GitHub Secrets

| Secret Name             | 설명                        |
| ----------------------- | --------------------------- |
| `GEMINI_API_KEY`      | Google Gemini API 키        |
| `ECOS_API_KEY`        | 한국은행 ECOS API 키        |
| `NAVER_CLIENT_ID`     | 네이버 개발자 Client ID     |
| `NAVER_CLIENT_SECRET` | 네이버 개발자 Client Secret |
| `TEAMS_WEBHOOK_URL`   | Microsoft Teams Webhook URL |

---

## 11. 팀즈 알람 연동 (Teams Notification)

### 11.1 알람 발송 시점

* 매일 오전 9시 수집 완료 후 자동 발송
* 수집 실패 시에도 에러 알람 발송
* 대시보드 링크: `https://rosy-jihye-noh.github.io/News-Intelligence/`

### 11.2 알람 메시지 디자인

**성공 시:**

```json
{
  "@type": "MessageCard",
  "@context": "http://schema.org/extensions",
  "themeColor": "0076D7",
  "summary": "📰 News Intelligence Daily Report",
  "sections": [
    {
      "activityTitle": "📰 News Intelligence - 2026.01.15",
      "activitySubtitle": "오전 9시 정기 수집 완료",
      "facts": [
        { "name": "📊 총 수집", "value": "156건" },
        { "name": "🇰🇷 국내 뉴스", "value": "45건" },
        { "name": "🌍 글로벌 뉴스", "value": "111건" },
        { "name": "🚨 Crisis Alert", "value": "12건" },
        { "name": "⏱️ 소요 시간", "value": "2분 5초" }
      ],
      "markdown": true
    },
    {
      "activityTitle": "🔥 주요 Crisis 뉴스 (Top 3)",
      "text": "1. Port strike threatens US East Coast shipping\n2. Red Sea attacks disrupt container routes\n3. 부산항 체선 심화로 물류 지연 우려"
    },
    {
      "activityTitle": "📈 경제 지표 요약",
      "text": "• KOSPI: 2,650.32 (▲+0.39%)\n• USD/KRW: 1,432.50 (▲+0.30%)\n• 기준금리: 3.50% (변동없음)"
    }
  ],
  "potentialAction": [
    {
      "@type": "OpenUri",
      "name": "📊 대시보드 열기",
      "targets": [
        { "os": "default", "uri": "https://<org>.github.io/news-intelligence/" }
      ]
    }
  ]
}
```

**실패 시:**

```json
{
  "@type": "MessageCard",
  "themeColor": "FF0000",
  "summary": "⚠️ News Intelligence 수집 실패",
  "sections": [
    {
      "activityTitle": "⚠️ 수집 실패 알림 - 2026.01.15",
      "facts": [
        { "name": "❌ 상태", "value": "실패" },
        { "name": "🔍 에러", "value": "API timeout error" }
      ]
    }
  ]
}
```

---

## 12. 작업 계획

### 12.1 Phase 1: 프로젝트 구조 재정리

- [ ] 새 GitHub Repository 생성
- [ ] 디렉토리 구조 설정 (frontend/, backend/, .github/)
- [ ] 기존 코드 마이그레이션
- [ ] requirements.txt 정리

### 12.2 Phase 2: 백엔드 수집 스크립트

- [ ] JSON 생성 스크립트 개발 (`run_collection.py`)
- [ ] 검색 쿼리 업데이트 (Google News, Naver News)
- [ ] 경제 지표 수집 로직 통합
- [ ] AI 분석 로직 확인/개선

### 12.3 Phase 3: 프론트엔드 개선

- [ ] HTML 구조 재정비
- [ ] JSON fetch 로직 구현
- [ ] 경제 지표 섹션 추가
- [ ] 미니 차트 컴포넌트 개발
- [ ] 반응형 레이아웃 개선

### 12.4 Phase 4: 자동화 설정

- [ ] GitHub Actions 워크플로우 작성
- [ ] GitHub Secrets 설정
- [ ] GitHub Pages 활성화

### 12.5 Phase 5: 팀즈 알람

- [ ] Teams Webhook 알림 스크립트 개발
- [ ] 메시지 템플릿 구현
- [ ] 테스트

### 12.6 Phase 6: 테스트 및 배포

- [ ] 전체 플로우 테스트
- [ ] 버그 수정
- [ ] 문서화 (README.md)
- [ ] 최종 배포

---

## 13. 환경 변수 목록

| 변수명                  | 설명                        | 필수 |
| ----------------------- | --------------------------- | ---- |
| `GEMINI_API_KEY`      | Google Gemini API 키        | ✅   |
| `ECOS_API_KEY`        | 한국은행 ECOS API 키        | ✅   |
| `NAVER_CLIENT_ID`     | 네이버 개발자 Client ID     | ✅   |
| `NAVER_CLIENT_SECRET` | 네이버 개발자 Client Secret | ✅   |
| `TEAMS_WEBHOOK_URL`   | Microsoft Teams Webhook URL | ✅   |

---

## 부록 A: 컬러 팔레트 (다크 테마)

```css
:root {
  /* Background */
  --bg-primary: #0f0f0f;
  --bg-secondary: #1a1a1a;
  --bg-tertiary: #252525;
  
  /* Text */
  --text-primary: #ffffff;
  --text-secondary: #a0a0a0;
  --text-muted: #666666;
  
  /* Accent */
  --accent-blue: #3b82f6;
  --accent-green: #10b981;
  --accent-red: #ef4444;
  --accent-yellow: #f59e0b;
  --accent-purple: #8b5cf6;
  
  /* Severity (Crisis) */
  --severity-low: #f87171;
  --severity-medium: #dc2626;
  --severity-high: #991b1b;
  
  /* Chart */
  --chart-up: #10b981;
  --chart-down: #ef4444;
  --chart-neutral: #6b7280;
}
```

---

## 부록 B: 참고 문서

* [한국은행 ECOS API](https://ecos.bok.or.kr/api/)
* [GDELT Project](https://www.gdeltproject.org/)
* [Google Gemini API](https://ai.google.dev/)
* [Naver Developers](https://developers.naver.com/)
* [Chart.js](https://www.chartjs.org/)
* [Leaflet.js](https://leafletjs.com/)
