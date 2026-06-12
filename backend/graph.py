"""
LangGraph StateGraph 빌드 + compile

7개 노드를 순차적으로 연결한 그래프를 생성합니다.
graph 객체를 외부에서 import하여 사용합니다.
"""
from langgraph.graph import StateGraph, END
from backend.nodes import (
    GraphState,
    retrieve_qna_node,
    extract_issue_node,
    retrieve_law_node,
    analyze_law_node,
    retrieve_precedent_node,
    analyze_precedent_node,
    generate_answer_node,
)

builder = StateGraph(GraphState)

# 노드 등록
builder.add_node("retrieve_qna", retrieve_qna_node)
builder.add_node("extract_issue", extract_issue_node)
builder.add_node("retrieve_law", retrieve_law_node)
builder.add_node("analyze_law", analyze_law_node)
builder.add_node("retrieve_precedent", retrieve_precedent_node)
builder.add_node("analyze_precedent", analyze_precedent_node)
builder.add_node("generate_answer", generate_answer_node)

# 엣지 연결 (순차 실행)
builder.set_entry_point("retrieve_qna")

builder.add_edge("retrieve_qna", "extract_issue")
builder.add_edge("extract_issue", "retrieve_law")
builder.add_edge("retrieve_law", "analyze_law")
builder.add_edge("analyze_law", "retrieve_precedent")
builder.add_edge("retrieve_precedent", "analyze_precedent")
builder.add_edge("analyze_precedent", "generate_answer")
builder.add_edge("generate_answer", END)

# 컴파일
graph = builder.compile()
