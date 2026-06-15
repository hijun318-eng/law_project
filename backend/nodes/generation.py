"""
LLM 답변 및 절차 안내 생성 노드 함수
"""
from backend.services.answer_service import answer_service
from backend.services.procedure_service import procedure_service

from backend.nodes.graph_state import GraphState


# ==========================================================
# NODE 5: LLM 답변
# ==========================================================
def generate_answer_node(state: GraphState) -> dict:
    return answer_service.generate(
        law_analysis=state["law_analysis"],
        precedent_analysis=state["precedent_analysis"],
        question=state["question"],
        law_source=state.get("law_source", "unknown"),
    )


# ==========================================================
# NODE 6: 절차 안내
# ==========================================================
def procedure_guide_node(state: GraphState) -> dict:
    try:
        return {
            "procedure_guide": procedure_service.generate(
                used_precedents=state.get("used_precedents", []),
            ),
        }
    except Exception:
        return {
            "procedure_guide": "skip",
        }
