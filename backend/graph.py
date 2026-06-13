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

builder = StateGraph(GraphState)

# 노드 등록
builder.add_node("retrieve_precedent",        retrieve_precedent_node)
builder.add_node("retrieve_law",              retrieve_law_node)
builder.add_node("retrieve_precedent_by_law", retrieve_precedent_by_law_node)
builder.add_node("merge",                     merge_node)
builder.add_node("generate_answer",           generate_answer_node)
builder.add_node("procedure_guide",           procedure_guide_node)

# 엣지 연결 (순차 실행)
builder.set_entry_point("retrieve_precedent")
builder.add_edge("retrieve_precedent",        "retrieve_law")
builder.add_edge("retrieve_law",              "retrieve_precedent_by_law")
builder.add_edge("retrieve_precedent_by_law", "merge")
builder.add_edge("merge",                     "generate_answer")
# builder.add_edge("generate_answer", END)
builder.add_edge("generate_answer",           "procedure_guide")
builder.add_edge("procedure_guide",           END)

# 컴파일
graph = builder.compile()
