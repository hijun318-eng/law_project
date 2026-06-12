"""
RAGEngine — LangGraph 기반 법률 분석 엔진

사용법:
    from backend.rag_engine import RAGEngine
    engine = RAGEngine()
    result = engine.answer("질문 내용")
    print(result["answer"])
    
    # 진행상황 스트리밍:
    for node_name, label, detail in engine.stream_answer("질문 내용"):
        print(f"{label}: {detail}")
"""
from backend.graph import graph

# 각 노드의 한글 레이블 및 설명
NODE_LABELS = {
    "retrieve_qna":         "📖 유사 질의회시 검색",
    "extract_issue":        "📌 법률 쟁점 추출",
    "retrieve_law":         "⚖️ 관련 법령 검색",
    "analyze_law":          "📝 법률 조문 분석",
    "retrieve_precedent":   "🔍 관련 판례 검색",
    "analyze_precedent":    "📜 판례 분석",
    "generate_answer":      "💡 최종 답변 생성",
}


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

    def stream_answer(self, question: str, top_k: int = 5):
        """
        그래프 실행 과정을 실시간으로 스트리밍합니다.

        각 노드 완료 시마다 (node_name, label, detail) 튜플을 yield합니다.
        마지막 yield는 node_name="done"이며 detail에 최종 결과를 담습니다.

        Args:
            question: 사용자 질문
            top_k:   (향후 확장)

        Yields:
            (node_name: str, label: str, detail: str | dict)
        """
        result = {}
        for event in self.graph.stream({"question": question}):
            for node_name, output in event.items():
                result.update(output)
                label = NODE_LABELS.get(node_name, node_name)
                detail = self._format_stream_detail(node_name, output)
                yield node_name, label, detail

        # 최종 결과
        sources = self._format_sources(result)
        yield "done", "✅ 분석 완료", {
            "answer": result.get("final_answer", ""),
            "sources": sources,
        }

    def _format_stream_detail(self, node_name: str, output: dict):
        """스트리밍 중 각 노드 출력을 읽을 수 있는 형태로 변환"""
        if node_name == "retrieve_qna":
            docs = output.get("qna_docs", [])
            return f"질의회시 {len(docs)}건 검색됨"
        elif node_name == "extract_issue":
            summary = output.get("issue_summary", "") or ""
            return summary[:200] if len(summary) > 200 else summary
        elif node_name == "retrieve_law":
            docs = output.get("law_docs", [])
            return f"법령 {len(docs)}개 검색됨"
        elif node_name == "analyze_law":
            analysis = output.get("law_analysis", "") or ""
            return analysis[:200] if len(analysis) > 200 else analysis
        elif node_name == "retrieve_precedent":
            docs = output.get("precedent_docs", [])
            return f"판례 {len(docs)}건 검색됨"
        elif node_name == "analyze_precedent":
            analysis = output.get("precedent_analysis", "") or ""
            return analysis[:200] if len(analysis) > 200 else analysis
        elif node_name == "generate_answer":
            answer = output.get("final_answer", "") or ""
            return f"답변 {len(answer)}자 생성 완료"
        return ""

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
