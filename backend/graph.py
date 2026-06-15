"""
LangGraph StateGraph 빌드 + compile

7개 노드를 순차적으로 연결한 그래프를 생성합니다.
graph 객체를 외부에서 import하여 사용합니다.
"""
from langgraph.graph import StateGraph, END

from backend.nodes import (
    GraphState,
    retrieve_precedent_node,
    retrieve_law_node,
    retrieve_precedent_by_law_node,
    merge_node,
    generate_answer_node,
    procedure_guide_node,
)


def _build_base_graph() -> StateGraph:
    builder = StateGraph(GraphState)

    # 엣지 연결 (순차 실행)
    builder.set_entry_point("retrieve_precedent")
    builder.add_edge("retrieve_precedent",        "retrieve_law")
    builder.add_edge("retrieve_law",              "retrieve_precedent_by_law")
    builder.add_edge("retrieve_precedent_by_law", "merge")
    builder.add_edge("merge",                     "generate_answer")
    builder.add_edge("generate_answer",           "procedure_guide")
    builder.add_edge("procedure_guide",           END)

    # 엣지 연결 (공통: retrieval -> merge)
    builder.set_entry_point("retrieve_precedent")
    builder.add_edge("retrieve_precedent",        "retrieve_law")
    builder.add_edge("retrieve_law",              "retrieve_precedent_by_law")
    builder.add_edge("retrieve_precedent_by_law", "merge")
    return builder


# 기존 호환: 통합 그래프 (generate_answer -> procedure_guide)
_builder = _build_base_graph()
_builder.add_edge("merge", "generate_answer")
_builder.add_edge("generate_answer", "procedure_guide")
_builder.add_edge("procedure_guide", END)
graph = _builder.compile()


# answer-only 그래프: merge -> generate_answer -> END
_builder_answer = _build_base_graph()
_builder_answer.add_edge("merge", "generate_answer")
_builder_answer.add_edge("generate_answer", END)
graph_answer = _builder_answer.compile()


# procedure-only 그래프: merge -> procedure_guide -> END
_builder_procedure = _build_base_graph()
_builder_procedure.add_edge("merge", "procedure_guide")
_builder_procedure.add_edge("procedure_guide", END)
graph_procedure = _builder_procedure.compile()
