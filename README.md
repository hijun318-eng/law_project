# 노동 법률 종합 AI 어시스턴트 ⚖️

> **Streamlit + LangChain + ChromaDB 기반 노동법률 RAG 시스템**

대한민국 노동 법률에 대한 질의응답, 권리 분석, 진정서 작성 등을 지원하는 AI 어시스턴트입니다. 법령·판례·행정해석(질의회시)을 벡터 DB에 임베딩하고 LangGraph 기반 멀티스텝 추론으로 정확한 법률 정보를 제공합니다.

---

## 주요 기능

| 페이지 | 기능 |
|--------|------|
| **🏠 홈** | 대시보드 및 서비스 개요 |
| **💬 QA** | 법률 질문에 대한 RAG 기반 답변 |
| **🔍 권리찾기** | 상황별 권리 진단 |
| **📄 진정서 작성** | 자동 진정서/탄원서 생성 |
| **📎 증거자료 관리** | 증거 자료 업로드 및 관리 |
| **🧮 계산기** | 임금·퇴직금·퇴직연금 계산 |
| **📝 문서 작성기** | 법률 문서 자동 작성 |
| **📑 계약서 검토** | 근로계약서 AI 검토 |
| **📰 최신 뉴스** | 노동법 관련 뉴스 제공 |

---

## 프로젝트 구조

```
law_project/
├── main.py                    # 애플리케이션 진입점 (streamlit run)
├── law_parser.py              # 법령 PDF → 조문 단위 파싱 모듈
├── final_reason.ipynb         # LangGraph RAG 파이프라인 (실험/분석용)
│
├── backend/                   # 백엔드 엔진
│   ├── config.py              # LLM / 임베딩 설정 (OpenAI / 로컬)
│   ├── database.py            # ChromaDB 연결 (laws / precedents / qna)
│   ├── graph.py               # LangGraph StateGraph 빌드 + compile (3가지 그래프 변형)
│   ├── rag_engine.py          # RAG 검색 엔진
│   ├── router_engine.py       # 질문 라우팅 엔진
│   ├── news_engine.py         # 뉴스 수집 엔진
│   ├── calculator_engine.py   # 금액 계산 엔진
│   ├── init_db.py             # DB 초기화
│   ├── ocr_contract/          # 근로계약서 OCR 분석
│   │
│   ├── nodes/                 # ★ LangGraph 노드 함수 모듈
│   │   ├── __init__.py        #   노드 일괄 export
│   │   ├── graph_state.py     #   GraphState (TypedDict) 정의
│   │   ├── retrieval.py       #   검색 노드 2개
│   │   │   ├─ retrieve_precedent_node()       # 판례 직접 검색
│   │   │   └─ retrieve_law_node()             # 법령 검색
│   │   └── generation.py      #   생성 노드 2개
│   │       ├─ generate_answer_node()  # LLM 답변 생성
│   │       └─ procedure_guide_node()  # 절차 안내 생성
│   │
│   ├── builders/              # 그래프 빌더
│   ├── retrievers/            # 벡터 DB 검색기
│   │   └── law_retriever.py   #   법령 검색기 (멀티쿼리 + 하이브리드 스코어링)
│   ├── tools/                 # 도구 모음
│   ├── services/              # 서비스 레이어
│   │   ├── answer_service.py  #   LLM 답변 서비스
│   │   └── procedure_service.py # 절차 안내 서비스
│   ├── prompts/               # 프롬프트 템플릿
│   ├── preprocess/            # 데이터 전처리
│   ├── constants/             # 상수 정의
│   └── utils/                 # 유틸리티
│
├── frontend/                  # Streamlit 프론트엔드
│   ├── app.py                 # 메인 라우터
│   ├── config.py              # 프론트엔드 설정
│   ├── theme.py               # 테마/CSS
│   ├── sidebar.py             # 사이드바
│   ├── menu.py                # 메뉴 구성
│   └── pages/                 # 페이지 컴포넌트
│       ├── home.py
│       ├── qa.py
│       ├── rights.py
│       ├── report.py
│       ├── evidence.py
│       ├── calculator.py
│       ├── docwriter.py
│       ├── contract.py
│       └── latestNews.py
│
├── crawler/                   # 데이터 수집
│   ├── faq_crawler/           # FAQ(질의회시) 크롤러
│   └── precedent_crawler/     # 판례 크롤러
│
├── data/                      # 데이터
│   ├── raw/                   # 원본 데이터 (PDF, MD)
│   ├── process/               # 가공 데이터 (JSON)
│   │   ├── 법률/              # 법령 JSON
│   │   ├── 판례/              # 판례 JSON
│   │   └── 질의회시집/         # 질의회시 JSON
│   └── cache/                 # 캐시
│
└── vector_db/                 # ChromaDB 벡터 저장소
    ├── laws/                  # 법령 벡터 DB
    ├── precedents/            # 판례 벡터 DB
    └── qna/                   # 질의회시 벡터 DB
```

---

## 기술 스택

| 분야 | 기술 |
|------|------|
| **프레임워크** | Python, Streamlit |
| **LLM** | OpenAI GPT |
| **RAG** | LangChain, LangGraph |
| **벡터 DB** | ChromaDB |
| **임베딩** | text-embedding-3-small |
| **PDF 처리** | PyMuPDF (fitz) |
| **데이터 수집** | 웹 크롤링 (BeautifulSoup 등) |

---

## LangGraph RAG 파이프라인

`backend/nodes/`에 정의된 4개 노드를 `backend/graph.py`에서 3가지 그래프 변형으로 조합합니다.

### GraphState (상태 구조)

```python
class GraphState(TypedDict):
    question: str                       # 사용자 질문
    precedent_docs_direct: list         # 판례 직접 검색 결과
    ref_articles_from_precedent: list   # 판례 llm_brief에서 추출한 참조조문 목록
    law_docs: list                      # 법령 검색 결과
    law_analysis: list                  # 법령 분석 결과 (law_name, article_no, score 등)
    law_source: str                     # 법령 검색 출처
    law_confidence: float               # 법령 검색 신뢰도
    precedent_docs: list                # 병합된 최종 판례 목록
    precedent_analysis: str             # 판례 분석 텍스트
    final_answer: str                   # 최종 LLM 답변
    used_precedents: list[str]          # 사용된 판례 사건번호 목록
    procedure_guide: str                # 절차 안내
```

### 6개 LangGraph 노드

| # | 노드 | 파일 | 역할 |
|---|------|------|------|
| 1 | `retrieve_precedent_node` | `retrieval.py` | ChromaDB(precedents)에서 질문과 유사한 판례 5건 직접 검색. llm_brief에서 참조조문(법령+조문) 추출 |
| 2 | `retrieve_law_node` | `retrieval.py` | `law_retriever`를 통해 법령 검색 (멀티쿼리 + 하이브리드 스코어링). 상위 5개 조문 반환 |
| 3 | `retrieve_precedent_by_law_node` | `retrieval.py` | 검색된 법령 조문(법령명+조문번호)을 쿼리로 판례 재검색. 조문-판례 간접 연결 |
| 4 | `merge_node` | `merge.py` | 법령 기반 판례 + 직접 검색 판례를 중복 제거 후 병합. 최대 5건, llm_brief 기반 분석 텍스트 생성 |
| 5 | `generate_answer_node` | `generation.py` | `answer_service`를 통해 법령 분석 + 판례 분석을 종합한 LLM 최종 답변 생성 |
| 6 | `procedure_guide_node` | `generation.py` | `procedure_service`를 통해 법적 절차(진정·소송 등) 안내 생성 |

### LangGraph 실행 흐름

```
사용자 질문
    │
    ▼
┌──────────────────────────────────────┐
│  1. retrieve_precedent_node          │  판례 DB 직접 검색 + 참조조문 추출
│     (precedent_db.similarity_search)  │
└──────────────┬───────────────────────┘
               ▼
┌──────────────────────────────────────┐
│  2. retrieve_law_node                │  법령 DB 검색 (멀티쿼리 + 스코어링)
│     (law_retriever.retrieve)          │
└──────────────┬───────────────────────┘
               ▼
┌──────────────────────────────────────┐
│  3. retrieve_precedent_by_law_node   │  법령 기반 판례 재검색
│     (조문 → 판례 간접 연결)           │
└──────────────┬───────────────────────┘
               ▼
┌──────────────────────────────────────┐
│  4. merge_node                       │  두 경로의 판례 중복 제거 + 병합
│     (법령기반 + 직접검색 → llm_brief)  │
└──────────────┬───────────────────────┘
               ▼
        ┌──────┴──────┐
        ▼              ▼
┌──────────────┐ ┌──────────────┐
│ 5. answer    │ │ 6. procedure │
│    generate  │ │    guide     │
│    _answer   │ │    _node     │
│    _node     │ │              │
└──────┬───────┘ └──────┬───────┘
       │                │
       ▼                ▼
    최종 답변        절차 안내
```

### 3가지 그래프 변형

`backend/graph.py`에서 3가지 버전의 compiled graph 제공:

| 그래프 | 경로 | 용도 |
|--------|------|------|
| `graph` | retrieve → law → law_precedent → merge → answer → procedure → END | 통합 QA (답변 + 절차) |
| `graph_answer` | retrieve → law → law_precedent → merge → answer → END | 답변만 필요한 경우 |
| `graph_procedure` | retrieve → law → law_precedent → merge → procedure → END | 절차 안내만 필요한 경우 |

---

## 설치 및 실행

### 1. 환경 설정

```bash
# 가상환경 생성
conda create -n law-assistant python=3.10
conda activate law-assistant

# 패키지 설치
pip install -r requirements.txt
```

### 2. 환경 변수 설정

`.env` 파일을 `law_project/` 디렉토리에 생성:

```env
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
NAVER_CLIENT_ID = xxxxxxxxxx
NAVER_CLIENT_SECRET = xxxxxx
```

### 3. 데이터 전처리

```bash
# 판례/질의회시 데이터 가공
python -m backend.preprocess.run_preprocess
```

### 4. 벡터 DB 생성 및 초기화

```bash
python -m backend.init_db
```

### 5. 애플리케이션 실행

```bash
streamlit run main.py
```

---

## 데이터 출처

| 데이터 | 출처 | 형식 |
|--------|------|------|
| **법령** | 국가법령정보센터 (law.go.kr) | PDF |
| **판례** | 대법원 종합법률정보 (glaw.scourt.go.kr) | Markdown |
| **질의회시** | 고용노동부 질의회시집 | Excel → JSON |

---

## 주의사항

> ⚠️ **본 서비스는 참고용이며 법적 효력이 없습니다.**
>
> - AI가 생성한 답변은 공식적인 법률 해석이 아닙니다.
> - 중요한 법적 결정은 반드시 전문 변호사와 상담하세요.
> - 법령 데이터는 최신 개정 사항이 반영되지 않을 수 있습니다.

---

## 라이선스

© 2025. All rights reserved.
