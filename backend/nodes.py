"""
LangGraph 노드 함수 + GraphState 정의
7개 노드 함수와 GraphState를 포함합니다.
"""

from typing import TypedDict

from backend.config import llm
from backend.database import qna_db, law_db, precedent_db
from backend.prompts import (
    PROMPT_EXTRACT_ISSUE,
    PROMPT_ANALYZE_LAW,
    PROMPT_ANALYZE_PRECEDENT,
    PROMPT_GENERATE_ANSWER,
)


class GraphState(TypedDict):
    question: str
    qna_docs: list
    issue_summary: str
    law_docs: list
    law_analysis: str
    precedent_docs: list
    precedent_analysis: str
    final_answer: str


def retrieve_qna_node(state):
    question = state["question"]
    docs = qna_db.similarity_search(question, k=10)
    print("\n===== QNA(질의회시) RETRIEVAL =====")
    for i, doc in enumerate(docs, 1):
        print(f"\n[QNA {i}]")
        print("metadata title:", doc.metadata.get("title", ""))
        print("질의(임베딩 대상):", doc.page_content)
    return {"qna_docs": docs}


def extract_issue_node(state):
    question = state["question"]
    qna_context_parts = []
    for doc in state["qna_docs"]:
        m = doc.metadata
        label = f"[{m.get('chapter_title','')} / {m.get('title','')} / {m.get('ref_no','')}, {m.get('ref_date','')}]"
        full_content = m.get("full_content", doc.page_content)
        qna_context_parts.append(f"{label}\n{full_content[:600]}")
    qna_context = "\n\n".join(qna_context_parts)
    prompt = PROMPT_EXTRACT_ISSUE.format(question=question, qna_context=qna_context)
    issue_summary = llm.invoke(prompt).content.strip()
    print("\n===== EXTRACTED ISSUE =====")
    print(issue_summary)
    return {"issue_summary": issue_summary}


def retrieve_law_node(state):
    question = state["question"]
    issue_summary = state.get("issue_summary", "")
    search_query = f"{question}\n\n{issue_summary}" if issue_summary else question
    docs = law_db.similarity_search(search_query, k=5)
    print("\n===== LAW RETRIEVAL =====")
    for i, doc in enumerate(docs, 1):
        print(f"\n[LAW {i}]")
        print("metadata:", doc.metadata)
        print(doc.page_content[:500])
    return {"law_docs": docs}


def analyze_law_node(state):
    question = state["question"]
    law_context_parts = []
    for doc in state["law_docs"]:
        m = doc.metadata
        parts = [p for p in [m.get("law_name",""), m.get("chapter",""), f"{m.get('article_no','')} ({m.get('article_title','')})" if m.get("article_title") else m.get("article_no","")] if p]
        label = " / ".join(parts)
        if m.get("page"):
            label += f" / {m['page']}p"
        if m.get("source_pdf"):
            label += f" [{m['source_pdf']}]"
        law_context_parts.append(f"[출처: {label}]\n{doc.page_content}")
    law_context = "\n\n".join(law_context_parts)
    prompt = PROMPT_ANALYZE_LAW.format(question=question, law_context=law_context)
    result = llm.invoke(prompt).content
    return {"law_analysis": result}


def retrieve_precedent_node(state):
    keyword_prompt = f"""
다음 사용자 사례와 법률 분석에서
판례 검색에 사용할 핵심 법률 쟁점 키워드를
10단어 이내로 추출하세요.

사용자 사례: {state['question']}
추출된 쟁점: {state.get('issue_summary', '')}
법률 분석 요약: {state['law_analysis'][:300]}

출력: 키워드만, 문장 금지
"""
    search_query = llm.invoke(keyword_prompt).content.strip()
    print("\n===== PRECEDENT SEARCH QUERY =====")
    print(search_query)
    docs = precedent_db.similarity_search(search_query, k=5)
    print("\n===== PRECEDENT RETRIEVAL =====")
    for i, doc in enumerate(docs, 1):
        print(f"\n[PRECEDENT {i}]")
        print("metadata:", doc.metadata)
        print(doc.page_content[:500])
    return {"precedent_docs": docs}


def analyze_precedent_node(state):
    precedent_context_parts = []
    for doc in state["precedent_docs"]:
        m = doc.metadata
        source_file = m.get("source_file", "알 수 없는 판례")
        case_no = source_file.replace(".md", "").replace(".json", "")
        precedent_context_parts.append(f"[판례: {case_no}]\n{doc.page_content}")
    precedent_context = "\n\n".join(precedent_context_parts)
    prompt = PROMPT_ANALYZE_PRECEDENT.format(question=state["question"], precedent_context=precedent_context)
    result = llm.invoke(prompt).content
    return {"precedent_analysis": result}


def generate_answer_node(state):
    qna_context_parts = []
    for doc in state.get("qna_docs", []):
        m = doc.metadata
        label = f"[{m.get('title','')} / {m.get('ref_no','')}, {m.get('ref_date','')}]"
        full_content = m.get("full_content", doc.page_content)
        qna_context_parts.append(f"{label}\n{full_content[:400]}")
    qna_context = "\n\n".join(qna_context_parts)
    prompt = PROMPT_GENERATE_ANSWER.format(
        question=state["question"],
        issue_summary=state.get("issue_summary", ""),
        law_analysis=state["law_analysis"],
        precedent_analysis=state["precedent_analysis"],
        qna_context=qna_context,
    )
    answer = llm.invoke(prompt).content
    return {"final_answer": answer}
