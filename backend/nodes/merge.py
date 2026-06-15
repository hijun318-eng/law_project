"""
판례 합산 노드 함수
"""
from pathlib import Path
from copy import deepcopy

from backend.nodes.graph_state import GraphState


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
            new_doc = deepcopy(doc)
            new_doc.metadata["source"] = "law_based"
            merged.append(new_doc)

    for doc in state.get("precedent_docs_direct", []):
        cn = Path(doc.metadata.get("source_file", "")).stem
        if cn not in seen:
            seen.add(cn)
            new_doc = deepcopy(doc)
            new_doc.metadata["source"] = "sac_direct"
            merged.append(new_doc)

    precedent_analysis = "\n\n".join([
        f"[판례:{Path(d.metadata.get('source_file','')).stem}]\n"
        f"{d.metadata.get('llm_brief', d.page_content)}"
        for d in merged[:5]
    ])

    used_precedents = [
        Path(d.metadata.get("source_file", "")).stem
        for d in merged[:5]
    ]

    return {
        "precedent_docs": merged[:5],
        "precedent_analysis": precedent_analysis,
        "used_precedents": used_precedents,
    }
