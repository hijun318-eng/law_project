"""
LangGraph 노드 함수 + GraphState 정의
"""
import json
from pathlib import Path
import re
from typing import TypedDict
from copy import deepcopy


from backend.database import law_db, precedent_db
from backend.services.answer_service import answer_service
from backend.services.procedure_service import procedure_service
from backend.retrievers.law_retriever import law_retriever
from backend.utils.law_normalizer import normalize_law_name, normalize_article_no

class GraphState(TypedDict):
    question: str
    precedent_docs_direct: list
    ref_articles_from_precedent: list[str]
    law_docs: list
    law_analysis: list
    law_source: str
    law_confidence: float
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
    docs = precedent_db.similarity_search(state["question"], k=8)

    seen   = set()
    unique = []
    for doc in docs:
        cn = Path(doc.metadata.get("source_file", "")).stem
        if cn not in seen:
            seen.add(cn)
            unique.append(doc)
        if len(unique) >= 5:
            break

    # llm_brief에서 참조조문 추출
    ref_articles_from_precedent = []
    seen_refs = set()
    
    for doc in unique:
        brief = doc.metadata.get("llm_brief", "")
   
        matches = re.findall(
            r'([가-힣\s·]{2,30}(?:법|법률))\s*(제\d+조(?:의\d+)?)',
            brief
        )
        for raw_law, raw_article in matches:
            law_name   = normalize_law_name(raw_law)     # 공백 제거
            article_no = normalize_article_no(raw_article)  # "제2조" 형식 통일
            article_id = f"{law_name}|{article_no}"     # 구분자 '|' 사용
 
            if article_id not in seen_refs:
                seen_refs.add(article_id)
                ref_articles_from_precedent.append(article_id)

    return {
        "precedent_docs_direct":        unique,
        "ref_articles_from_precedent":  ref_articles_from_precedent,
    }

# ==========================================================
# NODE 2: 법령 검색
# ==========================================================
def retrieve_law_node(state: GraphState) -> dict:
    result = law_retriever.retrieve(state)

    law_docs = result.get("docs", [])
    law_source = result.get("source", "unknown")
    law_confidence = result.get("confidence", 0.0)

    law_analysis = [
        {
            "law_name": d.metadata.get("law_name", ""),
            "article_no": d.metadata.get("article_no", ""),
            "article_title": d.metadata.get("article_title", ""),
            "page_content": d.page_content[:500],
            "score": d.metadata.get("final_score", 0.0),
        }
        for d in law_docs[:5]
    ]

    return {
        "law_docs": law_docs,
        "law_analysis": law_analysis,
        "law_source": law_source,
        "law_confidence": law_confidence,
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

    if not article_refs:
        return {"precedent_docs_law": []}

    search_query = " ".join(article_refs[:3])
    docs = precedent_db.similarity_search(search_query, k=5)

    seen = set()
    result = []
    
    for doc in docs:
        key = Path(doc.metadata.get("source_file", "")).stem
        
        if key not in seen:
            seen.add(key)
            doc.metadata["source"] = "law_based"
            result.append(doc)

    return {"precedent_docs_law": result}


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


# ==========================================================
# NODE 5: LLM 답변
# ==========================================================
def generate_answer_node(state: GraphState) -> dict:
    return answer_service.generate(
        law_analysis=state["law_analysis"],
        precedent_analysis=state["precedent_analysis"],
        question=state["question"],
        law_source=state.get("law_source", "unknown")
    )


# ==========================================================
# NODE 6: 절차 안내 
# ==========================================================
def procedure_guide_node(state: GraphState) -> dict:
    try:
        return {
            "procedure_guide": procedure_service.generate(
                used_precedents=state.get("used_precedents", [])
            )
        }
    except Exception:
        return {
            "procedure_guide": "skip"
        }