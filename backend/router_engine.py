"""backend/router_engine.py

홈 입력을 3개 모드 중 하나로 분류한 뒤, 해당 로직을 실행합니다.

모드
1) case_based_answer: 유사 법률/판례 추출 + 최종 답변 생성 (graph_answer)
2) procedure_guidance: 대응 절차 안내만 생성 (graph_procedure)
3) allowance_calculator: 수당 계산 (CalculatorEngine)
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.config import llm
from backend.calculator_engine import CalculatorEngine
from backend.graph import graph_answer, graph_procedure

from langchain_core.messages import HumanMessage, SystemMessage


ROUTE_CASE_BASED_ANSWER = "case_based_answer"
ROUTE_PROCEDURE_GUIDANCE = "procedure_guidance"
ROUTE_ALLOWANCE_CALCULATOR = "allowance_calculator"


SYSTEM_PROMPT = """
너는 노동법률 AI 라우터야.

아래의 3개 노드 중, 사용자의 질문이 가장 적합한 노드 ID 딱 1개만 반환해.

노드 목록
1. case_based_answer: 유사 법률/판례를 추출해서 최종 답변을 생성해야 하는 경우
2. procedure_guidance: 대응 절차(어디에 무엇을 언제 제출/신청해야 하는지) 안내만 필요한 경우
3. allowance_calculator: 주휴수당/연차수당/기타 수당 계산 같은 금액 계산이 필요한 경우

규칙
- 설명/수식어 없이 노드 ID만 출력해. 예: case_based_answer
- 목록에 없는 단어는 절대 출력하지 마.
""".strip()


@dataclass
class RouterResult:
    mode: str
    content: str


class LawRouterEngine:
    def __init__(self):
        self._llm = llm

    def route(self, question: str) -> str:
        resp = self._llm.invoke(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=f"사용자 질문: {question}"),
            ]
        )
        mode_raw = getattr(resp, "content", "")
        if isinstance(mode_raw, str):
            mode = (mode_raw or "").strip()
        else:
            mode = str(mode_raw).strip()
        if mode in {
            ROUTE_CASE_BASED_ANSWER,
            ROUTE_PROCEDURE_GUIDANCE,
            ROUTE_ALLOWANCE_CALCULATOR,
        }:
            return mode
        return ROUTE_CASE_BASED_ANSWER

    def run(self, question: str) -> RouterResult:
        mode = self.route(question)

        if mode == ROUTE_CASE_BASED_ANSWER:
            state = graph_answer.invoke({"question": question})
            return RouterResult(mode=mode, content=state.get("final_answer", ""))

        if mode == ROUTE_PROCEDURE_GUIDANCE:
            state = graph_procedure.invoke({"question": question})
            return RouterResult(mode=mode, content=state.get("procedure_guide", "skip"))

        # allowance_calculator
        engine = CalculatorEngine()
        res = engine.calculate(question)
        return RouterResult(mode=mode, content=res.get("answer", ""))


router_engine = LawRouterEngine()
