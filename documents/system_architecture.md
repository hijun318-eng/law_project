# 시스템 아키텍처 설계

## 1. 전체 컴포넌트 구성

### 1-1. 컴포넌트 개요

| 컴포넌트 | 역할 | 비고 |
|---|---|---|
| LLM (GPT) | 답변 생성, 라우팅 판단, 쿼리 재작성 | 검색 단계는 최소 사용, 답변 생성 단계에 집중 |
| Vector DB (Chroma) | 법령 / 판례 / 질의회시 3개 독립 컬렉션 | `vector_db/laws`, `vector_db/precedents`, `vector_db/qna` |
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
| `precedent_context_docs` | list | retrieve_precedent | generate_answer |
| `ref_articles_from_precedent` | list[str] | retrieve_precedent | retrieve_law (내부 law_retriever) |
| `law_docs` | list | retrieve_law | _format_sources |
| `law_analysis` | list[dict] | retrieve_law | generate_answer |
| `law_source` | str | retrieve_law | generate_answer (출처 신뢰도 표시) |
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
