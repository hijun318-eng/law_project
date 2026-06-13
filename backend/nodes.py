"""
LangGraph 노드 함수 + GraphState 정의
"""
import json
from pathlib import Path
from typing import TypedDict

from backend.database import law_db, precedent_db
from backend.services.answer_service import answer_service
from backend.services.procedure_service import procedure_service


class GraphState(TypedDict):
    question: str
    precedent_docs_direct: list
    law_docs: list
    law_analysis: list
    precedent_docs_law: list
    precedent_docs: list
    precedent_analysis: str
    final_answer: str
    used_precedents: list[str]
    procedure_guide: str


# ==========================================================
# NODE 1: 판례 직접 검색
# ==========================================================
def retrieve_precedent_node(state: GraphState) -> dict:
    docs = precedent_db.similarity_search(state["question"], k=5)
    return {"precedent_docs_direct": docs}


# ==========================================================
# NODE 2: 법령 검색
# ==========================================================
def retrieve_law_node(state: GraphState) -> dict:
    docs = law_db.similarity_search(state["question"], k=7)

    law_analysis = [
        {
            "law_name": d.metadata.get("law_name", ""),
            "article_no": d.metadata.get("article_no", ""),
            "article_title": d.metadata.get("article_title", ""),
            "page_content": d.page_content[:500],
        }
        for d in docs[:5]
        if d.metadata.get("article_no")
    ]

    return {
        "law_docs": docs,
        "law_analysis": law_analysis,
    }


# ==========================================================
# NODE 3: 법령 기반 판례 검색
# ==========================================================
def retrieve_precedent_by_law_node(state: GraphState) -> dict:
    article_refs = [
        f"{d['law_name']} {d['article_no']}"
        for d in state["law_analysis"]
        if d.get("law_name") and d.get("article_no")
    ]

    precedent_docs_law = []
    found = set()

    if article_refs:
        search_query = " ".join(article_refs[:3])
        docs = precedent_db.similarity_search(search_query, k=5)

        for doc in docs:
            cn = Path(doc.metadata.get("source_file", "")).stem
            if cn not in found:
                found.add(cn)
                doc.metadata["source"] = "law_based"
                precedent_docs_law.append(doc)

    return {"precedent_docs_law": precedent_docs_law}


# ==========================================================
# NODE 4: merge
# ==========================================================
def merge_node(state: GraphState) -> dict:
    merged = []
    seen = set()

    for doc in state.get("precedent_docs_law", [])[:3]:
        cn = Path(doc.metadata.get("source_file", "")).stem
        if cn not in seen:
            seen.add(cn)
            doc.metadata["source"] = "law_based"
            merged.append(doc)

    for doc in state.get("precedent_docs_direct", []):
        cn = Path(doc.metadata.get("source_file", "")).stem
        if cn not in seen:
            seen.add(cn)
            doc.metadata["source"] = "sac_direct"
            merged.append(doc)

    parts = []
    for doc in merged[:5]:
        cn = Path(doc.metadata.get("source_file", "")).stem
        brief = doc.metadata.get("llm_brief", doc.page_content)
        parts.append(f"[판례:{cn}]\n{brief}")

    return {
        "precedent_docs": merged[:5],
        "precedent_analysis": "\n\n".join(parts),
    }


# ==========================================================
# NODE 5: LLM 답변
# ==========================================================
def generate_answer_node(state: GraphState) -> dict:
    return answer_service.generate(
        law_analysis=state["law_analysis"],
        precedent_analysis=state["precedent_analysis"],
        question=state["question"],
    )


# ==========================================================
# NODE 6: 절차 안내 
# ==========================================================
def procedure_guide_node(state: GraphState) -> dict:

    return {
        "procedure_guide": procedure_service.generate(
            used_precedents=state.get("used_precedents", [])
        )
    }