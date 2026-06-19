# 시스템 아키텍처 설계

## 1. 전체 컴포넌트 구성

### 1-1. 컴포넌트 개요

| 컴포넌트 | 역할 | 비고 |
|---|---|---|
| LLM (GPT, gpt-5.4-nano) | 답변 생성, 라우팅 판단, 쿼리 재작성 | 검색 단계는 최소 사용, 답변 생성 단계에 집중 |
| Vector DB (Chroma) | 법령 / 판례 2개 독립 컬렉션 | `vector_db/laws`, `vector_db/precedents` |
| Cross-Encoder Reranker | 판례 후보 재정렬 | `Dongjin-kr/ko-reranker`, 한국어 특화 |
| LangGraph | Multi-Agent 오케스트레이션 | Supervisor 패턴 + Sequential 서브그래프 |
| 외부 API (MCP 방향) | 최신 뉴스 검색 | 네이버 뉴스 API, ReAct 패턴으로 호출 |

### 1-2. Hybrid RAG 설계 의도

법률 도메인 특유의 **Semantic Gap**(사용자 구어체 ↔ 법률 문어체) 문제를 해결하기 위해 검색 경로를 분리하고, 법령 검색 단계에서는 두 경로의 점수를 합산하는 하이브리드 스코어링을 적용했다.

```
사용자 질문
    ↓
[1] 판례 직접 검색 (Vector Search, k=30)
    구어체 SAC 요약 기반 후보 추출
    ↓
[2] Cross-Encoder Reranking
    (질문, 판례 brief) 쌍 단위로 재정렬 → 상위 5개 선별
    ↓
[3] 판례 → 참조조문 추출 (정규식)
    llm_brief에서 "OO법 제N조" 패턴 추출
    ↓
[4] 법령 하이브리드 검색 (LawRetriever)
    경로 A: 참조조문 → Chroma metadata 정확 매칭 (가중치 1.0)
    경로 B: 사용자 질의 → similarity_search 재현율 보완 (가중치 0.6)
    두 경로 결과를 병합하고, 판례 기반 결과를 우선 유지한 뒤 final_score 기준으로 재정렬
    ↓
[5] LLM 답변 생성
    법령 + 판례 컨텍스트를 결합하여 최종 답변 생성
```

**LawRetriever 하이브리드 스코어링 상세**

법령 검색 단계에서는 판례 기반 검색과 질의 기반 검색을 병행하고,
각 경로에 서로 다른 가중치를 부여하여 재정렬하는 하이브리드 검색 방식을 적용하였다.

판례 참조조문 경로와 질의 기반 경로를 함께 사용하여
정밀도와 재현율을 동시에 확보한다.

| 경로 | 점수 | 근거 |
|---|---|---|
| 판례 참조조문 → metadata 정확 매칭 | `PRECEDENT_SCORE = 1.0` | 판례가 실제로 인용한 조문이므로 법적 정합성이 가장 높음 |
| 사용자 질의 → Vector Search | `QUERY_SCORE = 0.6` | 판례 경로가 못 찾는 케이스를 보완하는 재현율 확보용 |
| 임베딩 유사도 가산 | `EMBEDDING_WEIGHT = 0.3` | metadata에 유사도 score가 있으면 추가 가산하여 동일 경로 내에서도 우선순위 세분화 |

최종적으로 `source` 필드를 `hybrid`/`precedent_based`/`query_based`/`unknown` 중 하나로 분류해, 답변 생성 단계에서 검색 결과의 출처를 추적할 수 있도록 하였다.

`confidence` 값은 전체 검색 결과 중 판례 기반 검색 결과의 비율로 계산한다.
현재는 검색 품질 분석 및 디버깅 지표로 활용하며, 향후 `confidence` 기반 검색 전략 분기에 활용할 수 있도록 설계하였다.

**Vector DB를 법령/판례로 분리한 이유**: 두 데이터의 검색 패턴이 다르다. 판례는 사용자 표현과의 유사도(구어체 SAC) 기반 검색이 효과적이고, 법령은 판례에서 추출한 조문 번호 기반 정밀 검색이 더 정확하다. 하나의 컬렉션에 두면 이 차이를 검색 전략에 반영할 수 없다.

**Reranker를 추가한 이유**: Vector Search 단독으로는 임베딩 유사도 상위 결과가 실제 법적 관련성과 다를 수 있다. Cross-Encoder는 (질문, 문서) 쌍을 직접 비교하므로 Bi-encoder 단독 검색보다 관련성 판단이 정확하다.

본 시스템은 판례 원문 전체가 아닌
사전에 생성한 SAC 기반 llm_brief를 대상으로 Reranking을 수행한다.

이를 통해 판례의 핵심 쟁점 중심으로 관련도를 평가할 수 있으며,
긴 판례 원문 전체를 비교하는 방식보다
추론 비용을 줄이면서 검색 품질을 향상시킬 수 있었다.


### 1-3. Graph DB 관련 의사결정

설계 단계에서 Neo4j 기반 `(Article)-[:CITED_IN]->(Precedent)` 그래프 구조를 검토했으나, 다음 이유로 프로토타입 단계에서는 도입하지 않았다.

Graph DB는 설계 단계에서 검토했으나, 현재 요구사항이 “판례 → 참조 조문 연결” 수준에 머물러 있어 Neo4j를 도입할 경우 얻는 이점 대비 운영 복잡도가 증가한다고 판단하였다. 

대신 판례 본문에 참조조문이 이미 "OO법 제N조" 형태의 텍스트로 명시되어 있다는 점을 활용해, **정규식 기반 추출 + 메타데이터 필터링**으로 동일한 연결 기능을 LLM 없이 결정론적으로 구현했다(`retrieve_precedent_node`의 `re.findall` 패턴 매칭). 이는 그래프 DB가 제공하는 관계 탐색의 일부 기능만 필요한 현재 요구사항에는 더 적은 복잡도로 동일한 효과를 낸다.

향후 조문 간 인용 관계,
법령 개정 이력,
판례 간 선후행 관계 등

다단계 관계 탐색 요구가 증가할 경우
Neo4j 기반 Graph RAG 구조로 확장할 수 있도록 설계 여지를 남겨두었다.

### 1-4. LLM 사용 최소화 원칙

법률 도메인에서는 검색 결과의 재현성과 근거 추적 가능성이 중요하다.

따라서 검색 단계는 LLM에 의존하지 않고

- Vector Search
- Cross-Encoder Reranking
- 정규식 기반 참조조문 추출
- Metadata Filtering

과 같은 결정론적 로직 중심으로 설계하였다.

LLM은 라우팅 판단과 최종 답변 생성 단계에만 사용하여,
동일 질의에 대해 일관된 검색 결과를 확보하고 환각(Hallucination) 가능성을 최소화하였다.

---

## 2. LangGraph 기반 Multi-Agent 구조

### 2-1. 전체 구조: Supervisor 패턴

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

**데이터 흐름 (SupervisorState)**

| 필드 | 타입 | 설명 |
|---|---|---|
| `question` | str | 사용자 원본 질문 (불변) |
| `next` | str | Supervisor가 결정한 다음 노드 |
| `intermediate_results` | dict | `{"rag": ..., "calculator": ..., "news": ...}` 각 에이전트 결과 누적 |
| `iteration` | int | 현재까지 실행 횟수 (`MAX_ITERATIONS=3` 제한) |
| `rag_sources` | list | RAG 검색에 사용된 법령/판례 출처 (프론트엔드 표시용) |

**제어 흐름**:
- `supervisor_node`: 이전 실행 결과(`intermediate_results`)와 `already_done` 목록을 LLM에 제공하여 중복 실행 방지
- `router_decision`: 조건부 엣지. `iteration >= MAX_ITERATIONS`면 무조건 `FINISH`로 강제 종료 (무한루프 방지)
- 각 서브 에이전트(`rag_router`, `calculator`, `news`)는 실행 후 항상 `supervisor`로 복귀 — Supervisor가 복합 질문에서 추가 작업 필요 여부를 재판단

복합 질문("퇴직금 계산하고 관련 판례도 알려줘") 처리 시 `calculator → supervisor → rag_router → supervisor → FINISH` 순으로 순차 실행되며, 각 단계 결과가 `intermediate_results`에 누적되어 다음 에이전트가 이전 결과를 참고할 수 있다(`rag_router_node`에서 `calc_result`를 질문에 합성).

### 2-2. RAG 서브그래프: Sequential 구조

```
retrieve_precedent → retrieve_law → generate_answer → procedure_guide → END
```

3가지 컴파일 변형을 동일 빌더에서 파생하여 재사용성을 확보했다.

| 그래프 | 경로 | 용도 |
|---|---|---|
| `graph` | 전체 4단계 | 통합 답변 + 절차 안내 |
| `graph_answer` | `retrieve_law → generate_answer → END` | 답변만 필요한 경우 (Router의 case_based_answer) |
| `graph_procedure` | `retrieve_law → procedure_guide → END` | 절차 안내만 필요한 경우 (Router의 procedure_guidance) |

`_build_base_graph()`로 공통 노드 등록부를 공유하고, 끝부분 엣지만 다르게 연결하는 방식으로 중복 코드 없이 3가지 시나리오를 처리한다.

### 2-3. 상위 라우팅: LawRouterEngine

Supervisor와 별개로, 홈 화면 입력을 4개 모드로 1차 분류하는 라우터가 존재한다.

```python
case_based_answer    # 법리 해석 + 유사 판례 필요
procedure_guidance   # 순수 절차 문의
allowance_calculator # 금액 계산
latest_news           # 최신 동향
```

이는 Supervisor의 복합 질문 처리와는 다른 레이어로, **단일 의도가 명확한 질문**을 빠르게 해당 그래프로 직행시켜 불필요한 Supervisor 반복을 줄이는 역할을 한다. 즉 시스템은 2단계 라우팅 구조를 가진다 — 1차 LawRouterEngine(단일 의도 빠른 분기) → 필요 시 SupervisorEngine(복합 의도 다중 에이전트 오케스트레이션).

### 2-4. ReAct 패턴: NewsEngine, CalculatorEngine

`NewsEngine`은 LangGraph의 명시적 그래프가 아닌 **수동 ReAct 루프**로 구현되어 있다.

```
LLM 추론 → Action 파싱 → Tool 실행 → Observation → LLM 재추론 → ... → Final Answer
```

- `MAX_STEPS`로 무한루프 방지
- `MAX_TOOL_RETRY` 연속 동일 쿼리 감지 시 조기 종료 (동일 검색 반복 방지)
- evidence가 불충분하면 Final Answer 대신 재검색을 강제하는 규칙을 매 스텝 주입

`CalculatorEngine`은 LangGraph의 표준 ReAct 에이전트(`backend/calculator/graph.py`)를 사용하며, `messages` 기반 상태로 대화 히스토리를 유지해 멀티턴 계산(예: "3년 근무 추가"로 이전 입력에 누적)을 지원한다.

---

## 3. MCP 호환 외부 연동 설계

### 3-1. 현재 구조: Tool Registry 패턴

정식 MCP 프로토콜 서버는 미구현 상태이나, **MCP와 동일한 설계 원칙**(표준화된 Tool 명세, 동적 등록, 느슨한 결합)을 적용한 자체 Registry를 구현했다.

```python
class ToolRegistry:
    def register(self, tool: BaseTool): ...
    def run(self, name: str, **kwargs) -> ToolResult: ...
    def list_specs(self) -> list[dict]:
        return [t.to_mcp_spec() for t in self._tools.values()]  # MCP 스펙 호환
```

`to_mcp_spec()` 메서드를 통해 각 Tool이 MCP 표준 형식(`name`, `description`, `input_schema`)으로 자기 설명을 제공하므로, 향후 실제 MCP 서버로 전환 시 Tool 구현부 변경 없이 프로토콜 레이어만 추가하면 된다.

### 3-2. 라우팅 설계

```
NewsEngine (ReAct)
    ↓
registry.list_specs() → LLM에 사용 가능한 tool 명세 제공
    ↓
LLM이 Action으로 tool 호출 결정
    ↓
registry.run(tool_name, **args) → 실행
    ↓
유효하지 않은 tool 호출 시: "ERROR: 존재하지 않는 tool" 메시지로 재시도 유도
```

`valid_tools()` 화이트리스트 검증을 통해 LLM이 임의의 tool명을 생성해도 실제 등록된 tool만 실행되도록 제한한다.

### 3-3. 보안 설계

| 항목 | 조치 |
|---|---|
| API 키 관리 | `.env` 환경변수로 분리, 코드에 하드코딩 금지 (`NAVER_CLIENT_ID/SECRET`) |
| 키 부재 시 동작 | 경고 로그만 남기고 graceful degradation (서비스 전체 중단 방지) |
| 입력 검증 | `display` 파라미터 범위 강제 (`max(1, min(display, 10))`)로 비정상 요청 방지 |
| 외부 응답 처리 | HTML 태그/엔티티 제거(`_clean`)로 XSS성 콘텐츠 정제 후 프론트엔드 전달 |

### 3-4. 성능 설계

| 항목 | 조치 |
|---|---|
| 타임아웃 | `REQUEST_TIMEOUT=5`초로 외부 API 응답 대기 제한 |
| 예외 처리 | `HTTPError`, `Timeout`, 일반 `Exception` 분리 처리 → 실패해도 `ToolResult(success=False)`로 그래프 흐름 유지 |
| 반복 검색 방지 | 동일 쿼리 연속 호출 시(`MAX_TOOL_RETRY`) 조기 종료 — 불필요한 API 비용/지연 차단 |
| 결과 수 제한 | `display` 최대 10건으로 토큰 사용량 제어 |

### 3-5. 확장 방향

현재 뉴스 검색 1종만 연동되어 있으나, Registry 패턴 덕분에 고용노동부 Open API, 국가법령정보센터 API 등 신규 외부 연동 추가 시 `BaseTool`을 상속한 클래스 구현 + `registry.register()` 호출만으로 확장 가능하다. 정식 MCP 서버 전환 시에는 `ToolRegistry`를 MCP Server 어댑터로 감싸는 구조를 계획한다.

---

## 4. 컴포넌트 간 인터페이스 정의

### 4-1. GraphState 스키마 (RAG 서브그래프)

| 필드 | 타입 | 생성 노드 | 소비 노드 |
|---|---|---|---|
| `question` | str | 입력 | 전체 노드 |
| `precedent_docs_direct` | list | retrieve_precedent | (디버깅/소스 표시) |
| `precedent_analysis` | str | retrieve_precedent | generate_answer |
| `precedent_docs` | list | retrieve_precedent | generate_answer (병합된 최종 판례) |
| `precedent_context_docs` | list | retrieve_precedent | generate_answer |
| `ref_articles_from_precedent` | list[str] | retrieve_precedent | retrieve_law (내부 law_retriever) |
| `law_docs` | list | retrieve_law | _format_sources |
| `law_analysis` | list[dict] | retrieve_law | generate_answer |
| `law_source` | str | retrieve_law | generate_answer (출처 신뢰도 표시) |
| `law_context` | str | retrieve_law | generate_answer (LLM 주입용 컨텍스트) |
| `law_confidence` | float | retrieve_law | (확장: 임계값 기반 분기용) |
| `final_answer` | str | generate_answer | procedure_guide, 출력 |
| `used_precedents` | list[str] | generate_answer | procedure_guide |
| `procedure_guide` | str | procedure_guide | 출력 |

### 4-2. 프롬프트 → 파싱 계층 데이터 흐름

```
[법령/판례 검색 결과 (Document 리스트)]
    ↓ 가공 (각 노드 내부)
[law_analysis: list[dict], precedent_analysis: str]
    ↓ answer_prompt.md 템플릿 치환 (string.Template.safe_substitute)
[LLM 입력 프롬프트]
    ↓ llm.invoke()
[LLM 원본 텍스트 응답]
    ↓ 정규식 파싱 (re.findall, json.loads + 마크다운 펜스 제거)
[구조화된 결과: used_precedents, 절차 안내 JSON 등]
```

**파싱 안정성 확보 방법**:
- LLM JSON 응답은 항상 ` ```json ` 펜스 제거 후 `json.loads` 시도, 실패 시 안전한 기본값(`None`, 빈 리스트)으로 폴백
- 판례 참조조문 추출은 LLM이 아닌 정규식(`re.findall`)으로 처리하여 결정론적 결과 보장 — 같은 입력에 항상 같은 출력

### 4-3. 메모리 컴포넌트 (대화 히스토리)

`CalculatorEngine`은 멀티턴 계산을 위해 `conversation_history`를 입력으로 받아 LangChain 메시지 객체(`HumanMessage`, `AIMessage`)로 변환 후 그래프에 전달한다.

```
[프론트엔드 세션 메시지 리스트: {"role": ..., "content": ...}]
    ↓ 변환
[LangChain BaseMessage 리스트]
    ↓ graph.invoke({"messages": messages})
[ReAct 그래프 내부에서 tool_calls 포함 메시지 누적]
    ↓ 필터링 (AIMessage이며 tool_calls 없는 마지막 메시지)
[최종 답변 문자열]
```

`SupervisorEngine`은 별도로 `intermediate_results` 딕셔너리를 그래프 State 내에 유지하여 동일 요청 내에서 여러 에이전트 간 결과를 공유하는 단기 메모리로 활용한다(대화 간 영속 메모리는 미구현).

### 4-4. 스트리밍 인터페이스 (RAGEngine / SupervisorEngine 공통)

두 엔진 모두 동일한 시그니처로 프론트엔드에 노출되어 교체 가능하다.

```python
def stream_answer(self, question: str):
    yield (node_name: str, label: str, detail: str | dict)
    # 마지막: yield ("done", "분석 완료", {"answer", "procedure", "sources"})
```

---

## 5. 설계 진화 과정

본 시스템은 최종 아키텍처에 도달하기까지 여러 차례의 설계 반복과 실험을 거쳤다. 각 단계에서 발견된 문제점과 그에 따른 설계 변경을 추적하는 것은 현재 아키텍처의 설계 의도와 트레이드오프를 이해하는 데 중요하다.

### 1단계 — 기본 검색: 단순 Vector Search의 한계

초기 시스템은 단순한 가정에서 출발했다: "Vector DB에 판례와 법령을 넣고 LLM이 추론하면 자연스럽게 좋은 답변이 나올 것이다."

```
사용자 질의 → 법령 Vector Search → 판례 Vector Search → LLM 답변
```

그러나 사용자 질의("3개월째 월급을 못 받고 있어요")와 법률 문서("임금은 매월 1회 이상 일정한 날에 지급하여야 한다") 사이에는 근본적인 언어적 간극이 존재했다. 사용자의 구어체와 법률 문어체 간의 **Vocabulary Mismatch**는 단순 의미 유사도로는 좁힐 수 없는 문제였으며, 법령과 판례 검색 모두 엉뚱한 결과를 반환했다.

이 경험은 이후 모든 설계 변경의 출발점이 되었다.

### 2단계 — RAG 파이프라인 구축: 메타데이터와 프롬프트의 한계

LangGraph 기반 4개 노드(판례 검색 → 법령 검색 → 답변 생성 → 절차 안내)의 순차 실행 파이프라인을 구축했다. Vocabulary Mismatch 문제를 해결하기 위해 두 가지 접근을 시도했다:

- **메타데이터 추가**: 판례와 법령에 카테고리, 키워드 등 메타데이터를 추가하여 검색 정밀도 향상
- **프롬프트 엔지니어링**: 쟁점 추출 프롬프트를 정교하게 다듬어 LLM이 사례에서 법적 쟁점을 잘 추출하도록 유도

그러나 프롬프트를 아무리 개선해도 사용자 사례를 법적 언어로 변환하는 데는 구조적 한계가 있었다. 더 중요한 발견은, 검색 단계에서 LLM이 잘못된 분류를 내리면 **잘못된 법령 → 잘못된 판례 → 잘못된 답변**으로 연쇄 오류가 발생한다는 점이었다.

이 경험에서 핵심 설계 원칙이 도출되었다:

> **LLM은 최종 답변 생성 단계에만 사용하고, 검색 단계는 결정론적 방법(ChromaDB, 메타데이터 필터, 정규식, Exact Match)만 사용한다.**

이 원칙은 이후 모든 검색 관련 설계 결정의 기준이 되었다.

### 3단계 — 2-Path Retrieval 도입: 판례 기반 + 질의 기반 하이브리드

BM25 키워드 검색과 Vector 의미 검색을 결합한 하이브리드 방식을 선행 실험했다. 법령 특유의 조문 번호나 고유 법률 용어 검색에서는 키워드 매칭이 강점을 보였으나, Vocabulary Mismatch 문제의 근본적 해결에는 이르지 못했다.

이를 바탕으로 법령 검색 단계에 **2-Path Retrieval** 전략을 도입했다:

- **Path 1 — 판례 기반 정밀 검색 (PRECEDENT_SCORE = 1.0)**: 판례의 `llm_brief`에서 정규식(`re.findall`)으로 "OO법 제N조" 형태의 참조조문을 추출하여 ChromaDB metadata를 정확 매칭
- **Path 2 — 질의 기반 의미 검색 (QUERY_SCORE = 0.6)**: 사용자 질문을 `similarity_search`로 법령 DB에 직접 검색하여 판례 경로가 놓친 케이스 보완

Rerank와 Query Rewrite도 추가로 실험했으나 오히려 성능이 저하되었다:

| 시도 | 결과 |
|------|:----:|
| Cross-Encoder 기반 Rerank | 성능 저하 (법령 검색 결과) |
| LLM Rerank (Reranker를 LLM으로 대체) | 성능 저하 |
| Rerank + 실패 시 Query Rewrite → 재검색 → Rerank | 성능 저하 |
| Query Rewrite (질의를 법률 용어로 재작성 후 검색) | 성능 저하 |

당시의 Rerank 시도는 모두 추가 LLM 호출이 오류 전파 지점을 늘리는 방향으로 작용했다. 이 경험을 바탕으로 법령 검색 단계는 결정론적 구조로 확정했다. (한편, 이후 SAC 도입 후 판례 검색 결과에 Cross-Encoder 리랭킹을 적용한 것은 별도 단계에서 성공하여 현재 시스템(Section 1-2)에 포함되었다.)

법령 검색의 한계를 우회하기 위한 또 다른 접근으로, **질의회시를 중간 매개체로 활용**하는 실험도 진행했다. 사용자 사례와 형식이 가장 유사한 문서라는 가정하에 질의회시 → 법령 → 판례 순의 파이프라인을 실험했으나, 질의회시집 자체가 법률 용어로 구성된 경우가 많아 검색 품질이 기대만큼 개선되지 않았다. 질의회시 데이터는 별도 ChromaDB 컬렉션(`admin_interpretations`)으로 구축하여 향후 확장을 대비했다.

### 4단계 — SAC 적용: 검색과 생성의 역할 분리

가장 큰 전환점은 **검색용 텍스트와 답변 생성용 텍스트를 분리**하는 SAC(Summary-Augmented Chunking) 구조의 도입이었다.

| 구분 | 저장 위치 | 역할 | 언어 수준 |
|------|-----------|------|-----------|
| **검색용 SAC** | `page_content` (ChromaDB 임베딩 대상) | 사용자 쿼리와의 유사도 매칭 | 구어체, 쟁점·결론 중심 |
| **답변용 브리프** | `metadata["llm_brief"]` | LLM 답변 생성 컨텍스트 | 법률 문어체 유지 |

핵심은 **찾을 때는 구어체로, 답변을 생성할 때는 법률 내용으로** 각각 다른 텍스트를 사용하는 것이다. 사용자 질의와 의미적으로 가까운 SAC 요약으로 판례를 먼저 찾고, 해당 판례가 인용한 법령을 역으로 추출한 뒤, 법령을 기준으로 판례를 재검증하는 **순환 검증 구조**로 파이프라인이 발전했다.

```
사용자 질의 → 판례 SAC 검색 → 법령 검색 → 판례 재검증 → LLM 답변
```

이 변경은 검색 품질에 가장 큰 성능 향상을 가져온 핵심 설계 결정이었다.

### 5단계 — CrossEncoder 리랭킹: 후보 재정렬로 정확도 개선

SAC 구조로 검색된 판례 후보(k=30)에 대해 CrossEncoder 리랭킹을 적용하여 정확도를 추가로 개선했다.

리랭킹 과정:
1. **Vector Search**: ChromaDB `similarity_search`로 k=30개 후보 추출
2. **사건번호 중복 제거**: 동일 사건번호를 가진 판례는 하나로 통합
3. **CrossEncoder 스코어링**: `Dongjin-kr/ko-reranker`로 각 (질문, llm_brief) 쌍의 관련도 점수 산출
4. **Top-5 선별**: 점수 기준 상위 5개 판례를 최종 컨텍스트로 사용

Vector Search 단독으로는 임베딩 유사도 상위 결과가 실제 법적 관련성과 다를 수 있기 때문에, CrossEncoder가 (질문, 문서) 쌍을 직접 비교하여 관련성 판단의 정확도를 높였다. 이는 3단계에서 법령 검색에 Rerank를 시도했다가 실패한 것과 달리, SAC 구조로 검색 품질이 먼저 개선된 상태에서 CrossEncoder를 적용했기에 성공할 수 있었다.

SAC 요약을 단일 형식으로 생성하는 대신, 판례의 **카테고리 메타데이터(임금, 해고, 산재, 직장 내 괴롭힘 등)에 따라 요약 방식을 차등 적용**하는 개선도 함께 이루어졌다. 같은 판례라도 임금 분쟁 맥락에서의 핵심 쟁점과 해고 분쟁 맥락에서의 핵심 쟁점은 다르기 때문이다. 이를 통해 검색 정밀도와 관련성이 한층 향상되었다.

한편, 법률 도메인의 특수성을 고려하여 LLM 생성 파라미터는 `temperature=0`으로 고정했다. 이는 동일 질의에 대해 항상 동일한 답변을 생성하여 법률 답변의 **재현성(Reproducibility)과 일관성(Consistency)**을 확보하기 위한 결정이다. 생성 파라미터를 고정하는 대신, 검색 단계의 다단계 Retrieval(판례 검색 → 리랭킹 → 참조조문 추출 → 법령 검색)을 통해 질의의 복잡도에 따라 LLM 입력 컨텍스트가 동적으로 구성되도록 설계했다. 즉, **생성 파라미터 변동 대신 Retrieval 기반의 동적 컨텍스트 제어** 방식을 채택한 것이다.

### 6단계 — Multi-Agent 시스템: Supervisor + Router + ToolRegistry

단일 RAG 엔진의 한계를 넘어 복합 질문 처리를 위한 Multi-Agent 시스템을 구축했다:

- **LawRouterEngine (1차 분류)**: 4개 모드(case_based_answer, procedure_guidance, allowance_calculator, latest_news)로 단일 의도를 빠르게 분기
- **SupervisorEngine (2차 오케스트레이션)**: 복합 의도를 LLM이 판단하여 RAG/Calculator/News 에이전트를 순차 실행, 최대 3회 반복으로 무한루프 방지
- **CalculatorEngine**: LangGraph ReAct 에이전트로 멀티턴 계산 지원, `messages` 기반 상태로 대화 히스토리 유지
- **NewsEngine**: 수동 ReAct 루프(Thought → Action → Observation)로 구현, `MAX_STEP`/`MAX_TOOL_RETRY`로 안정성 확보

ToolRegistry는 싱글턴 + BaseTool 추상화 패턴으로 설계되어 신규 Tool 추가가 용이하다. `valid_tools()` 화이트리스트 검증으로 LLM이 임의의 tool명을 생성해도 실제 등록된 tool만 실행되도록 제한했다.

### 7단계 — MCP 호환 설계: 미래 확장성을 위한 준비

정식 MCP 프로토콜 서버는 미구현 상태이나, MCP와 동일한 설계 원칙(표준화된 Tool 명세, 동적 등록, 느슨한 결합)을 적용한 자체 Registry를 구현했다. `to_mcp_spec()` 메서드를 통해 각 Tool이 MCP 표준 형식으로 자기 설명을 제공하므로, 향후 실제 MCP 서버로 전환 시 Tool 구현부 변경 없이 프로토콜 레이어만 추가하면 된다.

### 진화 단계 요약

| 단계 | 주요 변화 | 핵심 발견 |
|:----:|-----------|-----------|
| **1** | 단순 Vector Search 기반 법령 검색 | **Vocabulary Mismatch** 문제 확인 |
| **2** | LangGraph 4개 노드 RAG 파이프라인 | LLM 의존성의 연쇄 오류 위험 → **LLM 최소화 원칙** |
| **3** | 판례 참조조문 + 질의 유사도 2-Path Retrieval | Rerank/Query Rewrite 실패 → **결정론적 검색 확정** |
| **4** | SAC(Summary-Augmented Chunking) 적용 | **검색/생성 역할 분리**로 획기적 성능 향상 |
| **5** | CrossEncoder 리랭킹 + 카테고리 기반 SAC + Temperature=0 고정 | Bi-encoder 한계 보완, 맥락별 최적 요약, 법률 답변 일관성 |
| **6** | Supervisor + Router + ToolRegistry Multi-Agent | 복합 질문 처리, 플러그인형 확장 구조 |
| **7** | MCP 호환 ToolRegistry 설계 | 표준 프로토콜 전환 대비 |

이 진화 과정을 통해 도출된 가장 중요한 설계 원칙은 두 가지다: **LLM은 답변 생성에만 사용하고 검색은 결정론적으로 수행한다**는 원칙과, **검색과 생성을 위한 텍스트를 분리한다**는 SAC 원칙이다. 현재 아키텍처는 이 두 원칙 위에 구축되었다.
