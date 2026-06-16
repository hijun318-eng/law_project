"""
LangGraph 노드 함수 + GraphState 정의

기존 backend/nodes.py에서 모듈 분할:
  - graph_state.py:  GraphState (TypedDict)
  - retrieval.py:    검색 노드 3개 (판례 직접 검색, 법령 검색, 법령 기반 판례 검색)
  - generation.py:   LLM 답변 생성 + 절차 안내 생성
"""
from backend.nodes.graph_state import GraphState
from backend.nodes.retrieval import (
    retrieve_precedent_node,
    retrieve_law_node,
)
from backend.nodes.generation import (
    generate_answer_node,
    procedure_guide_node,
)

__all__ = [
    "GraphState",
    "retrieve_precedent_node",
    "retrieve_law_node",
    "generate_answer_node",
    "procedure_guide_node",
]
