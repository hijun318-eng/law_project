"""
RAGEngine — LangGraph 기반 법률 분석 엔진

사용법:
    from backend.rag_engine import RAGEngine
    engine = RAGEngine()
    result = engine.answer("질문 내용")
    print(result["answer"])
"""
from backend.graph import graph


class RAGEngine:
    """법률 RAG 엔진 (LangGraph 기반)"""

    def __init__(self):
        self.graph = graph

    def answer(self, question: str, top_k: int = 5) -> dict:
        """
        질문에 대한 법률 분석을 수행합니다.

        Args:
            question: 사용자 질문
            top_k:   (향후 확장) 검색 문서 수 제어

        Returns:
            {"answer": str, "sources": list[dict]}
        """
        result = self.graph.invoke({"question": question})

        # 소스 문서 정보 추출
        sources = self._format_sources(result)

        return {
            "answer": result.get("final_answer", ""),
            "sources": sources,
        }

    def _format_sources(self, state: dict) -> list:
        """그래프 실행 결과 state에서 소스 문서 리스트를 추출"""
        sources = []

        for doc in state.get("qna_docs", []):
            m = doc.metadata
            sources.append({
                "type": "qna",
                "title": m.get("title", ""),
                "ref_no": m.get("ref_no", ""),
                "ref_date": m.get("ref_date", ""),
                "chapter_title": m.get("chapter_title", ""),
            })

        for doc in state.get("law_docs", []):
            m = doc.metadata
            sources.append({
                "type": "law",
                "law_name": m.get("law_name", ""),
                "article_no": m.get("article_no", ""),
                "article_title": m.get("article_title", ""),
                "chapter_title": m.get("chapter_title", ""),
            })

        for doc in state.get("precedent_docs", []):
            m = doc.metadata
            sources.append({
                "type": "precedent",
                "case_no": (m.get("source_file", "")
                            .replace(".md", "")
                            .replace(".json", "")),
                "category": m.get("category", ""),
            })

        return sources
