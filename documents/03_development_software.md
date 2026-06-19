# 개발된 소프트웨어: RAG 기반 LLM과 벡터 데이터베이스 연동 구현 코드

## 1. 시스템 개요

### 1-1. 프로젝트 개요

| 항목 | 내용 |
|------|------|
| **프로젝트명** | 노동 법률 종합 AI 어시스턴트 |
| **설계 목적** | RAG 기반 LLM-벡터 DB 연동, Multi-Agent 워크플로우 구현 및 코드 품질 평가 |
| **핵심 요구사항** | 법률 도메인 특화 검색 및 답변 생성, 복합 질의 처리 |

### 1-2. 기술 스택

| 분야 | 기술 |
|------|------|
| **언어/프레임워크** | Python, Streamlit (프론트엔드) |
| **LLM** | OpenAI GPT (gpt-5.4-nano) |
| **Embedding** | text-embedding-3-small |
| **Vector DB** | ChromaDB (2개 컬렉션: laws, precedents) |
| **RAG Orchestration** | LangChain, LangGraph |
| **Reranker** | Dongjin-kr/ko-reranker (CrossEncoder) |

### 1-3. 데이터 출처 및 전처리

| 데이터 | 출처 | 형식 | 전처리 방식 |
|--------|------|------|-------------|
| 법령 데이터 | 국가법령정보센터 | 텍스트/JSON | 조문 단위 청킹, 메타데이터 인덱싱 |
| 판례 데이터 | 대법원 종합법률정보 | 텍스트 | SAC 요약 (page_content + llm_brief), 카테고리 기반 차등 요약 |
| 질의회시 데이터 | 고용노동부 | Excel → JSON | 청킹 후 ChromaDB 저장 |

---

## 2. Hybrid RAG 시스템

### 2-1. RAG 파이프라인 구성

4개 노드가 순차적으로 실행되며, 각 노드는 LangGraph의 StateGraph로 연결된다(`backend/graph.py`).

```
        ┌────────────────────────────────────────────────────────────────────┐
        │                         RAG Pipeline                              │
        │                                                                    │
        │  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐         │
        │  │ retrieve_    │ →  │ retrieve_law │ →  │ generate_    │         │
        │  │ precedent    │    │              │    │ answer       │         │
        │  └──────────────┘    └──────────────┘    └──────┬───────┘         │
        │                                                  │                 │
        │                                                  ▼                 │
        │                                         ┌──────────────┐          │
        │                                         │ procedure_   │          │
        │                                         │ guide        │          │
        │                                         └──────────────┘          │
        └────────────────────────────────────────────────────────────────────┘
```

3가지 그래프 변형을 동일 빌더에서 파생하여 재사용성을 확보했다:

| 그래프 | 경로 | 용도 |
|--------|------|------|
| `graph` | 전체 4단계 | 통합 답변 + 절차 안내 |
| `graph_answer` | `retrieve_law → generate_answer → END` | 답변만 필요한 경우 |
| `graph_procedure` | `retrieve_law → procedure_guide → END` | 절차 안내만 필요한 경우 |

### 2-2. GraphState 구조

14개 필드로 구성된 GraphState(`backend/nodes/graph_state.py`)가 RAG 파이프라인 전반의 데이터 흐름을 제어한다.

| 필드 | 타입 | 생성 노드 | 소비 노드 |
|------|------|-----------|-----------|
| `question` | str | 입력 | 전체 노드 |
| `precedent_docs_direct` | list | retrieve_precedent | (디버깅/소스 표시) |
| `precedent_analysis` | str | retrieve_precedent | generate_answer |
| `precedent_docs` | list | retrieve_precedent | generate_answer (병합된 최종 판례) |
| `precedent_context_docs` | list | retrieve_precedent | generate_answer |
| `ref_articles_from_precedent` | list[str] | retrieve_precedent | retrieve_law |
| `law_docs` | list | retrieve_law | _format_sources |
| `law_analysis` | list[dict] | retrieve_law | generate_answer |
| `law_source` | str | retrieve_law | generate_answer (출처 신뢰도) |
| `law_context` | str | retrieve_law | generate_answer (LLM 주입용) |
| `law_confidence` | float | retrieve_law | (확장용) |
| `final_answer` | str | generate_answer | procedure_guide, 출력 |
| `used_precedents` | list[str] | generate_answer | procedure_guide |
| `procedure_guide` | str | procedure_guide | 출력 |

3개 그래프 변형은 `_build_base_graph()`로 공통 노드 등록부를 공유하고, 끝부분 엣지만 다르게 연결하는 방식으로 중복 코드 없이 3가지 시나리오를 처리한다.

### 2-3. 2-Path Retrieval 전략

법령 검색 단계에서는 판례 기반 검색과 질의 기반 검색을 병행하고, 각 경로에 서로 다른 가중치를 부여하여 재정렬하는 하이브리드 검색 방식을 적용하였다(`backend/retrievers/law_retriever.py`).

| 경로 | 점수 | 근거 |
|------|------|------|
| 판례 참조조문 → metadata 정확 매칭 | `PRECEDENT_SCORE = 1.0` | 판례가 실제로 인용한 조문이므로 법적 정합성이 가장 높음 |
| 사용자 질의 → Vector Search | `QUERY_SCORE = 0.6` | 판례 경로가 못 찾는 케이스를 보완하는 재현율 확보용 |
| 임베딩 유사도 가산 | `EMBEDDING_WEIGHT = 0.3` | metadata 유사도 score 기반 동일 경로 내 우선순위 세분화 |

최종적으로 `source` 필드를 다음 중 하나로 분류하여 답변 생성 단계에서 검색 결과의 출처를 추적할 수 있도록 하였다:

- `hybrid` — 두 경로 모두에서 검색된 결과
- `precedent_based` — 판례 참조조문 경로로만 검색
- `query_based` — 질의 유사도 경로로만 검색
- `unknown` — 출처 분류 불가

`confidence` 값은 전체 검색 결과 중 판례 기반 검색 결과의 비율로 계산된다. 현재는 검색 품질 분석 및 디버깅 지표로 활용하며, 향후 `confidence` 기반 검색 전략 분기에 활용할 수 있도록 설계하였다.

### 2-4. SAC (Summary-Augmented Chunking)

판례 데이터의 Semantic Gap(사용자 구어체 ↔ 법률 문어체) 문제를 해결하기 위해 각 청크에 이중 요약 구조를 적용했다.

```
┌─────────────────────────────────────────────────┐
│              판례 Document                        │
│                                                   │
│  ┌─────────────────────────────────────────────┐  │
│  │ page_content  (100-300자)                    │  │
│  │  → Vector Search 대상, 판례 핵심 사실 요약   │  │
│  └─────────────────────────────────────────────┘  │
│                                                   │
│  ┌─────────────────────────────────────────────┐  │
│  │ metadata[llm_brief]  (LLM용 상세 요약)       │  │
│  │  → 판례의 법리적 쟁점, 결론 포함              │  │
│  └─────────────────────────────────────────────┘  │
│                                                   │
│  카테고리 기반 차등 요약: 데이터 유형별 최적 요약  │
│  전략 적용                                        │
└─────────────────────────────────────────────────┘
```

검색은 `page_content`(짧은 요약) 대상으로 수행하고, LLM 답변 생성 시에는 `llm_brief`(상세 요약)를 컨텍스트로 제공하여 검색 효율과 답변 품질을 동시에 확보한다.

### 2-5. CrossEncoder 리랭킹

Vector Search 단독으로는 임베딩 유사도 상위 결과가 실제 법적 관련성과 다를 수 있기 때문에, CrossEncoder 리랭킹을 도입하여 (질문, 문서) 쌍을 직접 비교한다.

리랭킹 과정:

1. **Vector Search**: ChromaDB similarity_search로 k=30개 후보 추출
2. **사건번호 중복 제거**: 동일 사건번호를 가진 판례는 하나로 통합
3. **CrossEncoder 스코어링**: `Dongjin-kr/ko-reranker`로 각 (질문, llm_brief) 쌍의 관련도 점수 산출
4. **Top-5 선별**: 점수 기준 상위 5개 판례를 최종 컨텍스트로 사용

본 시스템은 판례 원문 전체가 아닌 사전에 생성한 SAC 기반 `llm_brief`를 대상으로 리랭킹을 수행한다. 이를 통해 판례의 핵심 쟁점 중심으로 관련도를 평가할 수 있으며, 긴 판례 원문을 비교하는 방식 대비 추론 비용을 줄이면서 검색 품질을 향상시켰다.

### 2-6. 설계 평가

**강점**

- **SAC 이중 요약**: 검색 효율과 LLM 답변 품질을 동시에 확보하는 혁신적 설계. 검색 단계(짧은 page_content)와 생성 단계(상세 llm_brief)를 분리하여 각 단계의 요구사항에 최적화함.
- **2-Path 하이브리드 검색**: 판례 참조조문(정밀도)과 질의 유사도(재현율)를 결합하여 법률 도메인의 특수성을 반영.
- **CrossEncoder 리랭킹**: Bi-encoder 단독 검색보다 정확한 관련도 평가. 사건번호 중복 제거로 다양성 확보.
- **3개 그래프 변형**: 동일 빌더에서 파생하여 시나리오별 최적 경로 제공, 코드 중복 최소화.

**한계 및 트레이드오프**

- **테스트 코드 미구현**: RAG 파이프라인의 각 노드별 단위 테스트 부재로 회귀 검증이 어려움.
- **BM25+Vector 혼합 미적용**: 현재는 Vector Search 단일 방식만 사용 중 — 하이브리드 검색의 재현율 향상을 위해 BM25 스파스 검색 병합 검토 가능.

---

## 3. Multi-Agent 시스템

### 3-1. 2단계 라우팅 구조

시스템은 2단계 라우팅 구조를 가진다. 1차 LawRouterEngine이 단일 의도를 빠르게 분기하고, 필요 시 SupervisorEngine이 복합 의도를 다중 에이전트로 오케스트레이션한다.

```
사용자 입력
    │
    ▼
┌─────────────────────────────────────────────────┐
│          LawRouterEngine (1차 분류)               │
│                                                   │
│  ┌──────────────┐  ┌──────────────┐              │
│  │ case_based_  │  │ procedure_   │              │
│  │ answer       │  │ guidance     │              │
│  └──────────────┘  └──────────────┘              │
│  ┌──────────────┐  ┌──────────────┐              │
│  │ allowance_   │  │ latest_news  │              │
│  │ calculator   │  │              │              │
│  └──────────────┘  └──────────────┘              │
│                                                   │
│   → 단일 의도: 해당 그래프로 직행                  │
│   → 복합 의도: SupervisorEngine으로 전달          │
└─────────────────────────────────────────────────┘
    │
    ▼ (복합 질문 시)
┌─────────────────────────────────────────────────┐
│             SupervisorEngine                     │
│   (Multi-Agent 오케스트레이션)                    │
└─────────────────────────────────────────────────┘
```

RouterEngine/LawRouterEngine(`backend/router_engine.py`)은 4개 모드를 분류하며, fallback으로 `case_based_answer`를 사용한다. 24줄 길이의 SYSTEM_PROMPT가 라우팅 기준을 정의한다.

### 3-2. Supervisor Graph

Supervisor는 LLM이 다음에 실행할 에이전트를 결정하는 패턴으로, 복합 질문을 여러 단계로 분할하여 처리한다.

```
                    ┌─────────────────┐
                    │   Supervisor     │ ← LLM이 다음 실행 에이전트 결정
                    │   (LLM Router)   │
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
        ┌───────────┐  ┌───────────┐  ┌───────────┐
        │ rag_router│  │ calculator│  │   news    │
        │  (법률RAG) │  │ (수당계산) │  │ (최신뉴스) │
        └─────┬─────┘  └─────┬─────┘  └─────┬─────┘
              │              │              │
              └──────────────┴──────────────┘
                             │
                    ┌────────▼─────────┐
                    │   Supervisor      │ ← 추가 작업 필요 여부 재판단
                    │  (재귀, 최대 3회)  │
                    └────────┬─────────┘
                             │
                          FINISH → END
```

**SupervisorState**

| 필드 | 타입 | 설명 |
|------|------|------|
| `question` | str | 사용자 원본 질문 (불변) |
| `next` | str | Supervisor가 결정한 다음 노드 |
| `intermediate_results` | dict | 각 에이전트 결과 누적 `{"rag": ..., "calculator": ..., "news": ...}` |
| `iteration` | int | 현재까지 실행 횟수 (`MAX_ITERATIONS=3` 제한) |
| `rag_sources` | list | RAG 검색 출처 (프론트엔드 표시용) |

**제어 흐름**(`backend/supervisor/graph.py`):

- `supervisor_node`: 이전 실행 결과와 `already_done` 목록을 LLM에 제공하여 중복 실행 방지
- `router_decision`: 조건부 엣지. `iteration >= MAX_ITERATIONS`면 무조건 `FINISH`로 강제 종료 (무한루프 방지)
- 각 서브 에이전트는 실행 후 항상 `supervisor`로 복귀 — Supervisor가 추가 작업 필요 여부를 재판단

복합 질문(예: "퇴직금 계산하고 관련 판례도 알려줘") 처리 시 `calculator → supervisor → rag_router → supervisor → FINISH` 순으로 순차 실행되며, 각 단계 결과가 `intermediate_results`에 누적되어 다음 에이전트가 참고할 수 있다.

### 3-3. ReAct 패턴

**Calculator Engine**

LangGraph의 표준 ReAct 에이전트(`backend/calculator/graph.py`)를 사용한다. `messages` 기반 상태로 대화 히스토리를 유지하여 멀티턴 계산(예: "3년 근무 추가"로 이전 입력에 누적)을 지원한다. 4개 도구를 사용하며, `calculator_prompt.md`에 만/억 단위 계산 규칙이 정의되어 있다.

**News Engine**

LangGraph의 명시적 그래프가 아닌 **수동 ReAct 루프**로 구현되어 있다.

```
LLM 추론 → Action 파싱 → Tool 실행 → Observation → LLM 재추론 → ... → Final Answer
```

- `MAX_STEPS`로 무한루프 방지
- `MAX_TOOL_RETRY` 연속 동일 쿼리 감지 시 조기 종료 (동일 검색 반복 방지)
- evidence 불충분 시 Final Answer 대신 재검색을 강제하는 규칙을 매 스텝 주입
- `NewsQueryRewriter`를 통해 사용자 질의를 뉴스 검색에 적합한 형태로 변환

### 3-4. ToolRegistry 및 MCP 연동

정식 MCP 프로토콜 서버는 미구현 상태이나, **MCP와 동일한 설계 원칙**(표준화된 Tool 명세, 동적 등록, 느슨한 결합)을 적용한 자체 Registry를 구현했다(`tools/registry.py`).

```python
class ToolRegistry:
    def register(self, tool: BaseTool): ...
    def run(self, name: str, **kwargs) -> ToolResult: ...
    def list_specs(self) -> list[dict]:
        return [t.to_mcp_spec() for t in self._tools.values()]  # MCP 스펙 호환
```

`to_mcp_spec()` 메서드를 통해 각 Tool이 MCP 표준 형식(`name`, `description`, `input_schema`)으로 자기 설명을 제공하므로, 향후 실제 MCP 서버로 전환 시 Tool 구현부 변경 없이 프로토콜 레이어만 추가하면 된다.

`valid_tools()` 화이트리스트 검증을 통해 LLM이 임의의 tool명을 생성해도 실제 등록된 tool만 실행되도록 제한한다.

### 3-5. 설계 평가

**강점**

- **Supervisor 복합 질문 처리**: 중복 방지와 반복 제한(MAX_ITERATIONS=3)을 통해 안정적인 다중 에이전트 오케스트레이션 구현.
- **2단계 라우팅**: LawRouterEngine(1차 빠른 분기) + Supervisor(2차 복합 처리)의 이중 구조로 단순 질문과 복합 질문을 효율적으로 분리.
- **ToolRegistry 플러그인 구조**: 싱글턴 + BaseTool 추상화로 신규 Tool 추가가 용이하며, MCP 스펙 호환성 확보.

**한계**

- **키워드 파싱 한계**: Supervisor의 LLM 출력 파싱이 키워드 기반으로 이루어져 있어 출력 형식 변화에 취약함. JSON structured output 도입 필요.
- **MCP Server 미구현**: 현재는 자체 Registry로 대체 중이나, 외부 시스템과의 표준화된 통신을 위해 MCP 서버 전환이 필요함.
- **동시성 부재**: 모든 에이전트가 순차 실행되어 복합 질문 처리 시간이 길어짐. asyncio 기반 병렬 실행 검토 가능.
- **에러 복구 미구현**: 서브 에이전트 실패 시 Supervisor 차원의 재시도/폴백 로직이 없음.

---

## 4. 근로계약서 OCR 분석 파이프라인

근로계약서 이미지를 업로드하면 4단계 파이프라인으로 분석한다(`backend/ocr_contract/pipeline.py`).

```
이미지 업로드 → OCR(PaddleOCR) → 문서 검증(2단 게이트) → LLM 추출(Zero-shot) → 규칙 엔진(위반 검사)
```

### OCR 도구 및 문서 검증

**OCR 엔진**은 PaddleOCR(`lang="korean"`)을 사용하며, 최대 너비 1,500px로 리사이즈 후 처리한다(`ocr_engine.py`).
**2단 게이트**로 근로계약서 여부를 검증한다(`contract_gate.py`). GATE 1은 키워드 휴리스틱(3개 그룹 중 2개 이상 충족 시 통과, 비용 0)이고, GATE 1이 uncertain인 경우에만 GATE 2(LLM Zero-shot 분류기, gpt-5.4-nano)가 판단하여 보수적으로 통과 처리한다.

### LLM 구조화 추출 (Zero-shot)

OCR 텍스트에서 8개 필수 계약 항목(임금, 근무장소, 소정근로시간, 휴게시간, 휴일, 연차, 계약기간, 업무내용)을 **Zero-shot**(예제 없이 규칙만 제시) 프롬프트로 JSON 추출한다(`llm/extractor.py`, `constants.py`). 추출 규칙으로 OCR 오타 보정(근료→근로), 빈 양식 null 처리, 추측 표현 금지, 원문 그대로 추출을 명시한다. LLM 출력 파싱 실패 시 기본값을 반환하여 파이프라인이 중단되지 않도록 한다.

### 규칙 기반 위반 검사

**LLM이 아닌 결정론적 규칙 엔진**이 추출값을 법정 기준과 비교한다.

| 검사 항목 | 기준 | 법적 근거 |
|-----------|------|-----------|
| 필수기재사항 누락 | 7개 항목(임금·근로시간·휴게시간·휴일·연차·근무장소·업무내용) 중 누락 | 근로기준법 제17조 |
| 최저임금 위반 | 시급 10,030원 미만 또는 월급÷209시간 환산 시 10,030원 미만 | 최저임금법 제6조 |
| 근로시간 초과 | 1일 12시간 초과 | 근로기준법 제50조·제53조 |
| 휴게시간 미달 | 4시간 이상 근로 시 30분 / 8시간 이상 시 60분 미만 | 근로기준법 제54조 |

각 항목은 정규식 기반 파서(`wage_parser.py`, `time_parser.py`, `break_parser.py`)로 텍스트에서 수치를 추출한 후 비교한다.

### 독소 조항 분석 방식

본 시스템은 "독소 조항"을 LLM이 직접 판단하지 않고, **LLM 구조화 추출 → 결정론적 규칙 엔진**의 계층적 접근을 취한다. 즉, LLM이 계약 조건을 추출하고 규칙 엔진이 이를 법정 기준(최저임금법, 근로기준법)과 비교하여 위반을 판단한다. LLM 환각에 의존하지 않고 명확한 법적 기준에 따라 판단할 수 있다는 장점이 있다. 문맥적 독소성(위약 조항, 부당한 입증 책임 등) 분석은 향후 과제로 남긴다.

---

## 5. 코드 최적화 및 품질

### 5-1. LLM 파라미터 정책

`temperature=0` 설정(`backend/config.py`)은 법률 도메인의 특수성을 고려한 의도적 설계 결정이다.

| 파라미터 | 값 | 설계 의도 |
|----------|-----|-----------|
| `temperature` | 0.0 | 동일 질의에 대해 항상 동일한 답변을 생성하여 법률 답변의 재현성과 일관성 확보 |
| `max_tokens` | (별도 설정) | 답변 길이 제어 |

법률 도메인에서는 창의적인 답변보다 정확하고 일관된 답변이 중요하므로, temperature=0은 적절한 선택이다. 단, 이로 인해 답변 다양성이 제한되므로 사용자 피드백 기반 temperature 동적 조정은 향후 개선 사항으로 고려할 수 있다.

### 5-2. 프롬프트 템플릿 관리

5개 프롬프트 템플릿을 외부 파일로 분리하여 관리한다(`utils/prompt_loader.py`).

| 템플릿 파일 | 용도 | 특징 |
|-------------|------|------|
| `answer_prompt.md` | 법률 답변 생성 | 124줄, 3단 구조(지침/컨텍스트/출력형식) |
| `procedure_prompt.md` | 절차 안내 | 단계별 행정 절차 서술 |
| `news_prompt.md` | 뉴스 ReAct | 검색 결과 기반 최신 동향 요약 |
| `calculator_prompt.md` | 수당 계산기 | 만/억 단위 계산 규칙 포함 |
| `precedent_summary_prompt.md` | 판례 요약 | 판례의 법리적 쟁점 추출 |

`prompt_loader.py`는 `string.Template.safe_substitute`를 사용한 템플릿 치환 방식으로, 프롬프트 수정 시 코드 변경 없이 파일만 수정하면 된다.

### 5-3. 예외 처리 전략

**양호한 사례**

| 파일 | 위치 | 처리 방식 |
|------|------|-----------|
| `backend/nodes/generation.py` | try/except → skip | LLM 호출 실패 시 해당 단계를 건너뛰고 전체 파이프라인 유지 |
| `backend/retrievers/law_retriever.py` | None 체크 | 검색 결과 부재 시 안전한 기본값 반환 |
| `backend/tools/registry.py` | ToolResult 반환 | 성공/실패를 구조화된 객체로 반환하여 상위에서 일괄 처리 |
| `backend/tools/news_search_tool.py` | 예외 구분 처리 | HTTPError/Timeout/Exception을 구분하여 로깅 및 대응 |
| `backend/calculator/core.py` | 경계값 검증 | 입력 파라미터 범위 강제 (`max(1, min(display, 10))`) |

**미흡한 사례**

| 파일 | 문제점 | 영향 |
|------|--------|------|
| `backend/services/answer_service.py` | `llm.invoke` 예외 미처리 | LLM 호출 실패 시 크래시 발생 가능 |
| `backend/nodes/retrieval.py` | 인덱스 오류 미체크 | ChromaDB 쿼리 실패 시 추적 불가 |
| `backend/services/procedure_service.py` | Log만 출력 | 오류 발생 시 복구 로직 없음 |

앞으로 개선이 필요한 사항으로는 `@exception_handler` 데코레이터 도입, `print`와 `logging`의 혼용 통일, 타입 힌트 완전 적용, `pytest` 기반 단위 테스트 도입 등이 있다.

### 5-4. 설계 평가

**강점**

- **계층적 모듈 구조**: `backend/` → `nodes/`, `retrievers/`, `services/`, `tools/` 등 기능별 명확한 계층 분리로 유지보수성 확보.
- **프롬프트 외부 파일 관리**: 코드 변경 없이 프롬프트 수정 가능. `prompt_loader.py`를 통한 일관된 로드 방식.
- **temperature=0 정책**: 법률 도메인에 적합한 일관성 우선 설계.
- **LLM-as-a-Judge(RAGAS) 평가 완료**: RAGAS 프레임워크 기반 자동 평가 시스템 구축 완료(04_test_plan_and_results.md 참조). Faithfulness 높은 수준, Context Precision/Recall은 질문 유형별 편차 존재.

**한계**

- **예외 처리 일관성 부족**: 파일별로 예외 처리 수준이 상이함. 통일된 예외 처리 프레임워크 도입 필요.
- **프롬프트 버전 관리 부재**: 템플릿 변경 이력 추적 불가. 프롬프트 버전 관리 체계 도입 필요.
- **인젝션 방어 부재**: 사용자 입력에 대한 프롬프트 인젝션 방어 로직 미구현.

---

## 6. 종합 평가

### 6-1. 평가 항목 요약

| 평가 영역 | 핵심 근거 |
|-----------|-----------|
| **Hybrid RAG 및 DB 연동** | SAC 이중 요약, 2-Path 하이브리드 검색, CrossEncoder 리랭킹 등 고급 RAG 기법 적용. 3개 그래프 변형으로 시나리오별 최적화. |
| **Multi-Agent 및 ReAct** | Supervisor+Router 2단계 라우팅 구조로 단일/복합 질문 모두 처리. ToolRegistry의 플러그인 아키텍처 우수. MCP Server 미구현, 동시성 부재는 향후 과제. |
| **코드 최적화 및 품질** | 계층적 모듈 구조 우수, 프롬프트 외부 파일 관리 도입. 예외 처리 일관성 부족, 인젝션 방어 미비. |
| **종합** | Hybrid RAG와 Multi-Agent 아키텍처의 설계 수준이 높고 실무 적용 가능한 수준. SAC, 2-Path Retrieval, Supervisor 패턴 등 고급 기법을 적극 도입. 코드 품질 영역(예외 처리 일관성, 테스트, 보안)은 지속적 개선 필요. |

> 시스템 성능 평가 결과(RAGAS 기반)는 별도 문서 `04_test_plan_and_results.md`에 상세 기술되어 있음.

### 6-2. 회고: 설계 진화 과정

이 프로젝트는 최종 아키텍처에 도달하기까지 여러 차례의 설계 반복과 실험을 거쳤다. 각 단계에서 발견된 문제점과 그에 따른 설계 변경을 추적하는 것은 현재 시스템의 설계 의도와 트레이드오프를 이해하는 데 중요하다.

#### 1단계 — 기본 검색: 단순 Vector Search의 한계

초기 시스템은 단순한 가정에서 출발했다. "Vector DB에 판례와 법령을 넣고 LLM이 추론하면 자연스럽게 좋은 답변이 나올 것"이라는 가정이었다. 법령과 판례 데이터를 ChromaDB에 임베딩하고, 사용자 질의와의 유사도 검색 결과를 LLM에 주입하는 단순한 파이프라인이었다.

그러나 현실은 달랐다. 사용자는 "3개월째 월급을 못 받고 있어요"처럼 사례 중심의 언어로 질문하는 반면, 법령은 "임금은 매월 1회 이상 일정한 날에 지급하여야 한다"는 추상적이고 규범적인 언어로 쓰여 있었다. 사용자의 구어체와 법률 문서 간의 **Vocabulary Mismatch**는 단순 의미 유사도로는 좁힐 수 없는 간극이었고, 법령과 판례 검색 모두 엉뚱한 결과를 반환했다.

이 경험은 이후 모든 설계 변경의 출발점이 되었다.

#### 2단계 — RAG 파이프라인 구축: 메타데이터와 프롬프트의 한계

LangGraph 기반 4개 노드(판례 검색 → 법령 검색 → 답변 생성 → 절차 안내)의 순차 실행 파이프라인을 구축했다. Vocabulary Mismatch 문제를 해결하기 위해 두 가지 접근을 시도했다:

- **메타데이터 추가**: 판례와 법령에 카테고리, 키워드 등 메타데이터를 추가하여 검색 정밀도 향상
- **프롬프트 엔지니어링**: 쟁점 추출 프롬프트를 정교하게 다듬어 LLM이 사례에서 법적 쟁점을 추출하도록 유도

그러나 프롬프트를 아무리 개선해도 사용자 사례를 법적 언어로 변환하는 데는 구조적 한계가 있었다. 더 중요한 발견은, 검색 단계에서 LLM이 잘못된 분류를 내리면 **잘못된 법령 → 잘못된 판례 → 잘못된 답변**으로 연쇄 오류가 발생한다는 점이었다. 이 경험에서 핵심 설계 원칙이 도출되었다:

> **LLM은 최종 답변 생성 단계에만 사용하고, 검색 단계는 결정론적 방법(ChromaDB, 메타데이터 필터, 정규식, Exact Match)만 사용한다.**

#### 3단계 — 2-Path Retrieval 도입: 판례 기반 + 질의 기반 하이브리드

법령 검색 단계에서 판례 참조조문 기반 검색(정밀도)과 사용자 질의 기반 검색(재현율)을 병행하는 2-Path Retrieval 전략을 도입했다.

- **Path 1 — 판례 기반 정밀 검색 (PRECEDENT_SCORE = 1.0)** : 판례의 `llm_brief`에서 정규식(`re.findall`)으로 "OO법 제N조" 형태의 참조조문을 추출하여 ChromaDB metadata를 정확 매칭
- **Path 2 — 질의 기반 의미 검색 (QUERY_SCORE = 0.6)** : 사용자 질문을 `similarity_search`로 법령 DB에 직접 검색하여 판례 경로가 놓친 케이스 보완

Rerank와 Query Rewrite도 추가로 실험했으나 오히려 성능이 저하되었다:

| 시도 | 결과 |
|------|:----:|
| Cross-Encoder 기반 Rerank | 성능 저하 |
| LLM Rerank (Reranker를 LLM으로 대체) | 성능 저하 |
| Rerank + 실패 시 Query Rewrite → 재검색 → Rerank | 성능 저하 |
| Query Rewrite (질의를 법률 용어로 재작성 후 검색) | 성능 저하 |

추가 LLM 호출이 오류 전파 지점을 늘리는 방향으로 작용했고, 결정론적 구조가 법률 도메인에서 더 안정적이라는 결론을 내렸다.

질의회시를 중간 매개체로 활용하는 실험도 진행했으나, 질의회시집 자체가 법률 용어로 구성된 경우가 많아 검색 품질이 기대만큼 개선되지 않았다. 질의회시 데이터는 별도 DB(`admin_interpretations`)로 구축하여 향후 확장을 대비했다.

#### 4단계 — SAC 적용: 검색과 생성의 역할 분리

가장 큰 전환점은 SAC(Summary-Augmented Chunking) 구조의 도입이었다. 검색용 텍스트와 답변 생성용 텍스트를 분리하여 각 단계의 요구사항에 최적화했다.

| 구분 | 저장 위치 | 역할 | 언어 수준 |
|------|-----------|------|-----------|
| **검색용 SAC** | `page_content` (ChromaDB 임베딩 대상) | 사용자 쿼리와의 유사도 매칭 | 구어체, 쟁점·결론 중심 |
| **답변용 브리프** | `metadata["llm_brief"]` | LLM 답변 생성 컨텍스트 | 법률 문어체 유지 |

파이프라인도 이에 맞춰 변경되었다:

```
사용자 질의 → 판례 SAC 검색용 Vector Search → 법령 검색 → 판례 재검증 → LLM 답변
```

사용자의 언어로 판례를 먼저 찾고, 그 판례가 근거로 삼은 법령을 역으로 추출한 뒤, 다시 그 법령으로 판례를 검증하는 **순환 검증 구조**로 발전했다. 찾을 때는 구어체로, 답변을 생성할 때는 법률 내용으로 — 두 목적을 분리한 것이 검색 품질의 가장 큰 도약 지점이었다.

#### 5단계 — CrossEncoder 리랭킹: 후보 재정렬로 정확도 개선

SAC 구조로 검색된 판례 후보(k=30)에 대해 CrossEncoder 리랭킹을 적용하여 정확도를 추가로 개선했다.

리랭킹 과정:
1. **Vector Search**: ChromaDB similarity_search로 k=30개 후보 추출
2. **사건번호 중복 제거**: 동일 사건번호를 가진 판례는 하나로 통합
3. **CrossEncoder 스코어링**: `Dongjin-kr/ko-reranker`로 각 (질문, llm_brief) 쌍의 관련도 점수 산출
4. **Top-5 선별**: 점수 기준 상위 5개 판례를 최종 컨텍스트로 사용

Vector Search 단독으로는 임베딩 유사도 상위 결과가 실제 법적 관련성과 다를 수 있기 때문에, CrossEncoder가 (질문, 문서) 쌍을 직접 비교하여 관련성 판단의 정확도를 높였다. SAC + 리랭킹의 조합은 검색 정확도 측면에서 가장 큰 성능 향상을 가져온 핵심 설계 결정이었다.

SAC 요약을 단일 형식으로 생성하는 대신, 판례의 **카테고리 메타데이터(임금, 해고, 산재, 직장 내 괴롭힘 등)에 따라 요약 방식을 차등 적용**하는 개선도 함께 이루어졌다. 같은 판례라도 임금 분쟁 맥락에서의 핵심 쟁점과 해고 분쟁 맥락에서의 핵심 쟁점은 다르기 때문이다.

#### 6단계 — Multi-Agent 시스템: Supervisor + Router + ToolRegistry

단일 RAG 엔진의 한계를 넘어 복합 질문 처리를 위한 Multi-Agent 시스템을 구축했다:

- **LawRouterEngine (1차 분류)**: 4개 모드(case_based_answer, procedure_guidance, allowance_calculator, latest_news)로 단일 의도를 빠르게 분기
- **SupervisorEngine (2차 오케스트레이션)**: 복합 의도를 LLM이 판단하여 RAG/Calculator/News 에이전트를 순차 실행, 최대 3회 반복으로 무한루프 방지
- **CalculatorEngine**: LangGraph ReAct 에이전트로 멀티턴 계산 지원, `messages` 기반 상태로 대화 히스토리 유지
- **NewsEngine**: 수동 ReAct 루프(Thought → Action → Observation)로 구현, `MAX_STEP`/`MAX_TOOL_RETRY`로 안정성 확보

ToolRegistry는 싱글턴 + BaseTool 추상화 패턴으로 설계되어 신규 Tool 추가가 용이하다. `valid_tools()` 화이트리스트 검증으로 LLM이 임의의 tool명을 생성해도 실제 등록된 tool만 실행되도록 제한했다.

#### 7단계 — MCP 호환 설계: 미래 확장성을 위한 준비

정식 MCP 프로토콜 서버는 미구현 상태이나, MCP와 동일한 설계 원칙(표준화된 Tool 명세, 동적 등록, 느슨한 결합)을 적용한 자체 Registry를 구현했다. `to_mcp_spec()` 메서드를 통해 각 Tool이 MCP 표준 형식으로 자기 설명을 제공하므로, 향후 실제 MCP 서버로 전환 시 Tool 구현부 변경 없이 프로토콜 레이어만 추가하면 된다.

#### 진화 단계 요약

| 단계 | 주요 변화 | 핵심 발견 |
|:----:|-----------|-----------|
| **1** | 단순 Vector Search 기반 법령 검색 | **Vocabulary Mismatch** 문제 확인 |
| **2** | LangGraph 4개 노드 RAG 파이프라인 | LLM 의존성의 연쇄 오류 위험 → **LLM 최소화 원칙** |
| **3** | 판례 참조조문 + 질의 유사도 2-Path Retrieval | Rerank/Query Rewrite 실패 → **결정론적 검색 확정** |
| **4** | SAC(Summary-Augmented Chunking) 적용 | **검색/생성 역할 분리**로 획기적 성능 향상 |
| **5** | CrossEncoder 리랭킹 + 카테고리 기반 SAC + Temperature=0 고정 | Bi-encoder 한계 보완, 맥락별 최적 요약, 법률 답변 일관성 |
| **6** | Supervisor + Router + ToolRegistry Multi-Agent | 복합 질문 처리, 플러그인형 확장 구조 |
| **7** | MCP 호환 ToolRegistry 설계 | 표준 프로토콜 전환 대비 확장성 확보 |

이 진화 과정을 통해 도출된 가장 중요한 설계 원칙은 두 가지다: **LLM은 답변 생성에만 사용하고 검색은 결정론적으로 수행한다**는 원칙과, **검색과 생성을 위한 텍스트를 분리한다**는 SAC 원칙이다. 현재 시스템은 이 두 원칙 위에 구축되었다.

---

## 7. 권장 개선 사항

| 우선순위 | 영역 | 개선 항목 | 기대 효과 |
|:--------:|------|-----------|-----------|
| **P0** | Multi-Agent | JSON structured output 도입 | LLM 출력 파싱 안정성 향상, 키워드 의존성 제거 |
| **P1** | RAG | BM25+Vector 하이브리드 검색 | 재현율 개선, 검색 품질 향상 |
| **P1** | 코드 품질 | `@exception_handler` 데코레이터 도입 | 예외 처리 일관성 확보 |
| **P1** | 코드 품질 | logging 통일 (print → logging) | 운영 모니터링 체계 구축 |
| **P1** | Multi-Agent | MCP Server 구현 | 외부 시스템과 표준화된 통신 |
| **P2** | Multi-Agent | asyncio 기반 병렬 실행 | 복합 질문 처리 속도 개선 |
| **P2** | 코드 품질 | pytest 단위 테스트 도입 | 회귀 검증 체계 구축 |
| **P2** | 최적화 | 프롬프트 버전 관리 | 템플릿 변경 이력 추적 |
| **P2** | 보안 | 프롬프트 인젝션 방어 | 악의적 입력 차단 |

---

## 8. 참고 자료

분석 파일(33개):

```
law_project/
├── backend/
│   ├── graph.py                          # RAG 그래프 정의 (4개 노드)
│   ├── nodes/graph_state.py              # GraphState 14개 필드
│   ├── nodes/retrieval.py                # 검색 로직
│   ├── nodes/generation.py               # LLM 답변 생성
│   ├── rag_engine.py                     # RAG 엔진 통합
│   ├── database.py                       # DB 연결
│   ├── config.py                         # 설정 (temperature=0)
│   ├── router_engine.py                  # LawRouterEngine (4개 모드)
│   ├── nodes/                            # 그래프 노드 모듈
│   ├── retrievers/
│   │   └── law_retriever.py              # 2-Path Retrieval
│   ├── services/                         # 서비스 레이어
│   ├── supervisor/
│   │   ├── graph.py                      # Supervisor 그래프
│   │   └── engine.py                     # Supervisor 엔진
│   ├── calculator/
│   │   ├── graph.py                      # ReAct 에이전트
│   │   ├── tools.py                      # 계산 도구 모듈
│   └── tools/
│       ├── registry.py                   # ToolRegistry (싱글턴)
│       ├── base.py                       # BaseTool 추상화
│       └── news_search_tool.py           # 뉴스 검색 도구
├── backend/utils/
│   ├── prompt_loader.py
├── backend/preprocess/
├── frontend/
│   ├── app.py                            # Streamlit UI
│   └── pages/qa.py                       # Q&A 인터페이스
├── backend/init_db.py                    # DB 초기화
├── main.py                               # 진입점
├── backend/constants/
└── README.md                             # 프로젝트 문서
```
