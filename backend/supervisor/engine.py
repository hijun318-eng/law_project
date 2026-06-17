"""
SupervisorEngine — RAGEngine과 동일한 stream_answer 인터페이스 제공

프론트엔드(qa.py)에서 engine.stream_answer(question)을 호출하면
SupervisorGraph가 복합 질문에 대해 여러 서브 에이전트를 순차 실행하고
그 결과를 스트리밍 형태로 전달합니다.
"""
from backend.supervisor.graph import (
    supervisor_graph,
    NODE_LABELS,
)


class SupervisorEngine:
    """
    Supervisor 기반 법률 분석 엔진

    RAGEngine과 동일한 .stream_answer() 시그니처를 제공하여
    프론트엔드 변경 없이 Supervisor로 교체 가능하게 함
    """

    def __init__(self):
        self.graph = supervisor_graph

    def stream_answer(self, question: str):
        """
        Supervisor 그래프를 실행하고 각 단계별 결과를 스트리밍합니다.

        Yields:
            (node_name: str, label: str, detail: str | dict)
              - 각 서브 에이전트 실행 완료 시: (node_name, label, log_message)
              - 마지막 yield: ("done", "✅ 분석 완료", {"answer": ..., "sources": [...]})
        """
        # 초기 상태
        state = {
            "question": question,
            "messages": [],
            "next": "supervisor",
            "intermediate_results": {},
            "final_answer": "",
            "iteration": 0,
            "error": "",
            "rag_sources": [],
        }

        latest_state = dict(state)  # streaming 중 누적 상태 추적

        for event in self.graph.stream(state):
            for node_name, output in event.items():
                # 로그가 있으면 yield
                log = output.get("log", "")
                if log:
                    label = NODE_LABELS.get(node_name, node_name)
                    yield (node_name, label, log)

                # 상태 누적 (다음 supervisor 판단에 사용)
                latest_state.update(output)

        # 그래프 종료 후 최종 답변 조합
        answer = self._build_final_answer(latest_state)
        sources = latest_state.get("rag_sources", [])

        yield ("done", "✅ 분석 완료", {
            "answer": answer,
            "procedure": "",
            "sources": sources,
        })

    def answer(self, question: str) -> dict:
        """
        동기 실행 (streaming 없이 최종 결과만 반환)
        RAGEngine.answer()와 동일한 시그니처
        """
        result = self.graph.invoke({
            "question": question,
            "messages": [],
            "next": "supervisor",
            "intermediate_results": {},
            "final_answer": "",
            "iteration": 0,
            "error": "",
            "rag_sources": [],
        })
        answer = self._build_final_answer(result)
        sources = result.get("rag_sources", [])
        return {"answer": answer, "sources": sources}

    @staticmethod
    def _build_final_answer(state: dict) -> str:
        """각 에이전트 결과를 하나의 최종 답변으로 통합"""
        intermediate = state.get("intermediate_results", {})
        rag = intermediate.get("rag", "")
        calc = intermediate.get("calculator", "")
        news = intermediate.get("news", "")

        # RAG 답변이 메인 — 계산 결과가 포함되어 있음
        if rag:
            answer = rag
            # 뉴스 결과가 RAG 답변에 포함되지 않은 것으로 보이면 추가
            if news and ("최신 뉴스" not in rag[:200] if len(rag) > 200 else True):
                answer += f"\n\n---\n\n{news}"
            return answer

        # RAG 없이 계산만
        if calc:
            answer = f"🧮 **계산 결과**\n\n{calc}"
            if news:
                answer += f"\n\n---\n\n{news}"
            return answer

        # 뉴스만
        if news:
            return news

        return "질문을 분석할 수 없습니다. 다시 입력해주세요."
