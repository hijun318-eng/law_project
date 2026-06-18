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
│   ├── builders/              # 벡터 DB 빌더
│   │   ├── law_builder.py        # 법령 DB 빌드
│   │   ├── precedent_builder.py  # 판례 DB 빌드
│   │   └── qna_builder.py        # 질의회시 DB 빌드
│   ├── retrievers/            # 벡터 DB 검색기
│   │   └── law_retriever.py   #   법령 검색기 (2-Path Retrieval: 판례 참조조문 정확매칭 + 질의 유사도 검색)
│   ├── tools/                 # 도구 모음
│   ├── services/              # 서비스 레이어
│   │   ├── answer_service.py            #   LLM 답변 서비스
│   │   ├── precedent_summary_service.py #   판례 SAC 이중 요약 생성
│   │   └── procedure_service.py         #   절차 안내 서비스
│   ├── prompts/               # 프롬프트 템플릿 (5종)
│   │   ├── answer_prompt.md
│   │   ├── procedure_prompt.md
│   │   ├── news_prompt.md
│   │   ├── calculator_prompt.md
│   │   └── precedent_summary_prompt.md
│   ├── preprocess/            # 데이터 전처리
│   ├── constants/             # 상수 정의
│   └── utils/                 # 유틸리티
│       ├── law_normalizer.py  #   법령명·조문번호 정규화
│       ├── prompt_loader.py   #   프롬프트 파일 로드
│       └── __init__.py
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
│       ├── rights/             # (__init__.py + data.py)
│       ├── report/             # (__init__.py + data.py)
│       ├── evidence/           # (__init__.py + data.py)
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
    precedent_docs_direct: list         # 판례 직접 검색 결과 (리랭킹 후 상위 5건)
    ref_articles_from_precedent: list   # 판례 llm_brief에서 추출한 참조조문 목록
    law_docs: list                      # 법령 검색 결과 (raw documents)
    law_analysis: list                  # 법령 분석 결과 (law_name, article_no, score 등)
    law_source: str                     # 법령 검색 출처 (hybrid/precedent_based/query_based/unknown)
    law_context: str                    # 법령 컨텍스트 (LLM 주입용)
    law_confidence: float               # 법령 검색 신뢰도 (0.0~1.0)
    precedent_docs: list                # 병합된 최종 판례 목록
    precedent_analysis: str             # 판례 분석 텍스트
    precedent_context_docs: list        # 판례 컨텍스트 문서 (LLM 주입용, 상위 3건)
    final_answer: str                   # 최종 LLM 답변
    used_precedents: list[str]          # 사용된 판례 사건번호 목록
    procedure_guide: str                # 절차 안내
```

### 4개 LangGraph 노드

| # | 노드 | 파일 | 역할 |
|---|------|------|------|
| 1 | `retrieve_precedent_node` | `retrieval.py` | ChromaDB(precedents)에서 질문과 유사한 판례 30건 검색 → CrossEncoder 리랭킹 → 상위 5건 선정. llm_brief에서 정규식으로 참조조문(법령명+조문번호) 추출 |
| 2 | `retrieve_law_node` | `retrieval.py` | `law_retriever`를 통해 2-Path Retrieval (Path 1: 판례 참조조문 정확매칭 / Path 2: 질의 유사도 검색). 점수 합산 후 상위 7개 조문 반환 |
| 3 | `generate_answer_node` | `generation.py` | `answer_service`를 통해 법령 분석 + 판례 분석을 종합한 LLM 최종 답변 생성 |
| 4 | `procedure_guide_node` | `generation.py` | `procedure_service`를 통해 법적 절차(진정·소송 등) 안내 생성 |

### LangGraph 실행 흐름

```
사용자 질문
    │
    ▼
┌──────────────────────────────────────┐
│  1. retrieve_precedent_node          │  판례 DB 직접 검색 + 리랭킹 + 참조조문 추출
│     (similarity_search k=30 →        │
│      CrossEncoder rerank → top 5)    │
└──────────────┬───────────────────────┘
               ▼
┌──────────────────────────────────────┐
│  2. retrieve_law_node                │  법령 DB 2-Path 검색 + 점수 합산
│     (2-Path Retrieval:               │
│      precedent exact match +         │
│      query similarity search)        │
└──────────────┬───────────────────────┘
               ▼
         ┌──────┴──────┐
         ▼              ▼
┌──────────────────┐ ┌──────────────────┐
│ 3. generate_answer│ │ 4. procedure_   │
│    _node          │ │    guide_node    │
│    (LLM 답변 생성) │ │    (절차 안내)   │
└───────┬──────────┘ └───────┬──────────┘
        │                    │
        ▼                    ▼
     최종 답변            절차 안내
```

### 3가지 그래프 변형

`backend/graph.py`에서 3가지 버전의 compiled graph 제공:

| 그래프 | 경로 | 용도 |
|--------|------|------|
| `graph` | retrieve → law → answer → procedure → END | 통합 QA (답변 + 절차) |
| `graph_answer` | retrieve → law → answer → END | 답변만 필요한 경우 |
| `graph_procedure` | retrieve → law → procedure → END | 절차 안내만 필요한 경우 |

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

## 시스템 아키텍처

### 전체 처리 흐름

```
사용자 질문
    │
    ▼
┌─────────────────────┐
│  RouterEngine       │  LLM이 4개 모드 중 선택
│  (LawRouterEngine)  │  case_based_answer / procedure_guidance
└──────────┬──────────┘  allowance_calculator / latest_news
           │
           ▼ (case_based_answer 또는 procedure_guidance인 경우)
┌─────────────────────┐
│  LangGraph RAG      │  4개 노드 순차 실행 → 법령+판례 기반 답변 생성
│  (graph.py)         │
└──────────┬──────────┘
           │
           ▼ (SupervisorGraph로 진입 가능)
┌─────────────────────┐
│  SupervisorGraph    │  LLM이 복합 질문 분석 → 서브에이전트 순차 실행
│  (supervisor/graph) │  rag_router / calculator / news 중 선택 → 최대 3회
└──────────┬──────────┘
           │
           ▼
     ┌─────┴─────┐
     ▼           ▼
┌─────────┐ ┌─────────┐
│ QA 답변  │ │ 절차 안내│  (또는 계산 결과 / 뉴스 검색 결과)
└─────────┘ └─────────┘
```

### 멀티에이전트 구성

| 에이전트 | 구현 위치 | 역할 |
|----------|----------|------|
| **Router** | `backend/router_engine.py` (129줄) | LLM 기반 4개 모드 분류. fallback: `case_based_answer` |
| **Supervisor** | `backend/supervisor/graph.py` (302줄) | LLM이 다음 실행 에이전트 결정. 중복 방지, 최대 3회 반복 |
| **RAG Router** | `backend/supervisor/graph.py` rag_router_node | LangGraph RAG 파이프라인 실행 (법령+판례 검색 → 답변 생성) |
| **Calculator** | `backend/calculator_engine.py` | LangGraph ReAct 기반 수당/퇴직금 계산 |
| **News** | `backend/news_engine.py` | ReAct 루프 기반 뉴스 검색 및 요약 |

### Tool Registry 및 MCP 인터페이스

- **ToolRegistry** (`backend/tools/registry.py`): 싱글턴 패턴으로 Tool 등록/조회/실행 관리
- **BaseTool** (`backend/tools/base.py`): 추상 기본 클래스 + `ToolResult` dataclass
- **MCP 스펙 변환**: `BaseTool.to_mcp_spec()` 메서드로 Tool → MCP 호환 스펙 변환 가능
  - 현재 MCP Server 프로세스는 미구현 상태 (to_mcp_spec() 인터페이스만 준비)
- **NewsSearchTool**: 네이버 뉴스 API 기반 뉴스 검색 도구 (BaseTool 상속)

### 외부 API 연동

| 연동 대상 |用途 | 설정 파일 |
|----------|-----|----------|
| OpenAI GPT (`gpt-5.4-nano`) | LLM 답변 생성, Router/Supervisor 판단 | `backend/config.py` |
| OpenAI Embedding (`text-embedding-3-small`) | 텍스트 임베딩 및 유사도 검색 | `backend/config.py` |
| 네이버 뉴스 API | 최신 노동법 뉴스 검색 | `.env` (NAVER_CLIENT_ID/SECRET) |
| ChromaDB (로컬) | 벡터 저장 및 검색 | `backend/database.py` |

### LLM 파라미터 정책

- **Temperature=0 고정**: 법률 도메인 특성상 답변의 일관성(Consistency)과 재현성(Reproducibility) 확보
- **Top-P 미설정 (기본값 사용)**: 동일한 이유로 별도 분기하지 않음
- **Use Case별 분기 대체 방식**: 생성 파라미터 대신 **Retrieval 기반 동적 컨텍스트 제어** 채택
  - 판례 검색 + 리랭킹 → 참조조문 추출 → 법령 정확 매칭 → 질의 유사도 검색 → 통합 점수 정렬
  - 이 다단계 Retrieval 파이프라인으로 LLM 입력 컨텍스트가 질의 복잡도에 따라 동적으로 구성됨

---

## 데이터 출처

| 데이터 | 출처 | 형식 |
|--------|------|------|
| **법령** | 국가법령정보센터 (law.go.kr) | PDF |
| **판례** | 대법원 종합법률정보 (glaw.scourt.go.kr) | Markdown |
| **질의회시** | 고용노동부 질의회시집 | Excel → JSON |

---

## 데이터 전처리 및 청킹 전략

### 데이터 수집 채널

| 데이터 | 출처 | 수집 방식 | 건수 |
|--------|------|----------|:---:|
| **법령** | 국가법령정보센터 (law.go.kr) | PDF 다운로드 후 조문 단위 파싱 | 8종 (근로기준법, 최저임금법 등 노동 핵심 법령) |
| **판례** | 대법원 종합법률정보 (casenote.kr) | 웹 크롤링 (BeautifulSoup) | 52건 (44개 리딩 케이스, A~F 카테고리) |
| **질의회시** | 고용노동부 질의회시집 | Excel → JSON 변환 | 1개 파일 (질의/회시 단위 분리) |

### 전처리 파이프라인

```
data/raw/ (원본: PDF, MD)
  → backend.preprocess.run_preprocess
    ├── preprocess_law.py   : PDF → 정규식 조문 파싱 → data/process/law/ (JSON)
    ├── preprocess_case.py  : MD → JSON 변환 → data/process/case/ (JSON)
    ├── preprocess_qna.py   : PDF → 질의 단위 파싱 → data/process/qna/ (JSON) ※ 현재 미실행 (run_preprocess.py에서 주석 처리)
    └── preprocess_sac.py   : 판례 LLM 이중 요약 → data/cache/sac/ (search + brief)
  → backend.init_db
    └── ChromaDB 저장 (vector_db/ 아래 3개 컬렉션)
```

### 청킹(Chunking) 전략

본 프로젝트는 데이터 유형별로 최적화된 3가지 청킹 전략을 사용합니다:

| 데이터 | 청킹 전략 | 설명 |
|--------|:---------:|------|
| **법령** | 구조 기반 청킹 (조문 단위) | `preprocess_law.py`에서 `제X조` 단위로 Document 분리. 장/절/조/항 메타데이터 포함. ChromaDB flat metadata 구조에 최적화 |
| **판례** | SAC (Summary-Augmented Chunking) | 1건의 판례를 **검색용(search, 구어체 요약)** 과 **LLM용(brief, 법률 내용)** 으로 분리 → Vocabulary Mismatch 해결. 카테고리별 요약 방식 차등 적용 |
| **질의회시** | 질문 단위 청킹 | 질문(question) 단위로 Document 분리 |

### SAC 구조 상세

SAC(Summary-Augmented Chunking)은 본 프로젝트의 핵심 청킹 전략으로, 검색 효율성과 답변 품질을 동시에 확보하기 위해 설계되었습니다.

```
[검색용 SAC - page_content (ChromaDB 임베딩 대상)]
  [핵심 쟁점]  카테고리 기반 쟁점 정리  → 사용자 구어체와 임베딩 공간 일치
  [판결 결론]  카테고리 기반 판결 요약

[LLM용 브리프 - metadata["llm_brief"] (LLM 컨텍스트 주입용)]
  [사건 개요]  발생한 분쟁을 법률 용어로 정리
  [판결 요지]  법원의 핵심 판단
  [핵심 법리]  판례에서 확립된 법적 원칙
  [참조 조문]  적용된 법령명과 조문번호
```

이 구조를 통해 "찾을 때는 구어체로, 답변 생성할 때는 법률 내용으로" 각각 최적화된 텍스트를 사용합니다.

### 데이터 중복 및 결측치 처리

- **판례 중복 제거**: 검색 결과에서 사건번호(`source_file` stem) 기준 `set()` 기반 중복 제거
- **법령 중복 제거**: `law_name + article_no` 기준 중복 제거 (참조조문 경로 + 질의 경로 동일 조문 병합)
- **결측치 필터링**: `article_no`가 없는 문서는 질의 기반 검색에서 제외
- **KoNLPy/형태소 분석**: RAG 아키텍처에서는 전통적 형태소 분석이 필수가 아니므로 OpenAI `text-embedding-3-small` 임베딩 API로 대체

---

## 테스트 및 평가 현황

### 단위/통합 테스트
- ❌ **테스트 코드 미구현**: pytest/unittest 기반 테스트 파일 없음
- ❌ **Ground Truth 데이터셋 미구축**: RAG 성능 평가용 정답 데이터셋 없음

### 정량적 평가 지표
| 평가 항목 | 적용 여부 | 비고 |
|----------|:--------:|------|
| BLEU/ROUGE | ❌ 미산출 | 번역/요약 평가지표 미적용 |
| LM-Eval (lm-evaluation-harness) | ❌ 미사용 | sLLM 벤치마크 테스트 미수행 |
| LLM-as-a-Judge (Context Relevance) | ❌ 미평가 | 검색 컨텍스트와 질문의 관련성 평가 없음 |
| LLM-as-a-Judge (Groundedness) | ❌ 미평가 | 답변의 검색 결과 근거 충실성 평가 없음 |
| LLM-as-a-Judge (Answer Relevance) | ❌ 미평가 | 답변의 질문 대응 적절성 평가 없음 |

### 회고 및 한계점 분석

프로젝트 파이프라인은 다음과 같은 7단계 진화 과정을 거쳤으며, 각 단계의 실패와 학습 내용이 `참고문서/`에 상세히 기록되어 있습니다:

1. **단순 Vector Search** → Vocabulary Mismatch 문제 발견
2. **메타데이터+프롬프트 보완** → 제한적 성과
3. **LLM 의존성 최소화 원칙 도출** → 검색 단계는 결정론적 방식 채택
4. **BM25+Vector 하이브리드** → 재현율 향상, 근본 문제 미해결
5. **질의회시 경유 파이프라인** → 기대 이하 성과
6. **SAC 구조 도입** → 검색 품질 혁신적 개선
7. **카테고리 기반 SAC 세분화** → 정밀도 추가 향상

**주요 한계점**:
1. 사용자 언어와 법률 언어 간 Semantic Gap (SAC으로 개선했으나 완전 해결 못함)
2. 복합 쟁점 입력 시 핵심 쟁점 분류 실패 가능성
3. 동일 조문도 판례마다 다른 해석 — LLM의 미묘한 차이 구분 한계
4. 44개 리딩 케이스+핵심 법령으로 제한된 데이터 커버리지

### 적용하지 않은 기술과 사유

| 기술 | 미적용 사유 |
|------|-----------|
| **KoNLPy 형태소 분석** | RAG 아키텍처 채택으로 OpenAI `text-embedding-3-small` 임베딩 API가 형태소 분석을 대체. 전통적 NLP 파이프라인(형태소 분석→BoW/TF-IDF→ML)을 따르지 않음 |
| **PEFT 파인튜닝 (LoRA/QLoRA)** | OpenAI API 기반 시스템으로 자체 모델 파인튜닝 불필요. 필요 시 LoRA 코드 추가 가능 |
| **Graph DB (Neo4j 등)** | 법령-판례 참조 관계를 정규식+메타데이터 매칭으로 대체 처리. Graph DB 없이도 2-Path Retrieval로 유사한 효과 달성 |
| **MCP Server 프로세스** | `to_mcp_spec()` 메서드로 Tool→MCP 스펙 변환 인터페이스는 준비 완료. 실제 MCP Server(stdio/SSE) 구축은 미완료 |
| **qna_db 파이프라인 미연결** | 질의회시 DB(`vector_db/qna/`)는 구축 완료. RAG 파이프라인 3번째 검색 경로로 추가 예정 |

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
