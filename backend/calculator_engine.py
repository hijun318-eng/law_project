"""
CalculatorEngine — LangGraph ReAct 기반 계산기 엔진

사용법:
    from backend.calculator_engine import CalculatorEngine
    engine = CalculatorEngine()
    result = engine.calculate("퇴직금 계산해줘, 3년 근무, 월 300만원")
    print(result["answer"])
"""
from backend.calculator.graph import graph


class CalculatorEngine:
    """계산기 ReAct 엔진 (LangGraph ReAct 기반)"""

    def __init__(self):
        self.graph = graph

    def calculate(self, query: str) -> dict:
        """
        자연어 질문에 대한 계산을 수행합니다.

        Args:
            query: 자연어 질문 (예: "퇴직금 계산해줘, 3년 근무, 월 300만원")

        Returns:
            {"answer": str} — 계산 결과 문자열
        """
        from langchain_core.messages import HumanMessage

        result = self.graph.invoke({
            "messages": [HumanMessage(content=query)]
        })

        # 마지막 AIMessage (tool_call 제외) 찾기
        answer = ""
        for msg in reversed(result["messages"]):
            if (
                hasattr(msg, "content")
                and isinstance(msg.content, str)
                and msg.content.strip()
                and not getattr(msg, "tool_calls", None)
            ):
                # AIMessage면서 tool_calls가 없는 메시지 = 최종 응답
                if hasattr(msg, "type") and msg.type == "ai":
                    answer = msg.content
                    break

        return {"answer": answer or "죄송합니다. 계산 결과를 생성하지 못했습니다."}

    def stream_calculate(self, query: str):
        """
        계산 과정을 실시간으로 스트리밍합니다.

        Args:
            query: 자연어 질문

        Yields:
            event dict from graph.stream()
        """
        from langchain_core.messages import HumanMessage

        for event in self.graph.stream(
            {"messages": [HumanMessage(content=query)]}
        ):
            yield event
