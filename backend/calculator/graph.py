"""
LangGraph ReAct 계산기 그래프

create_react_agent를 사용하여 자연어 → 파라미터 추출 → 도구 호출 → 결과 반환

참고: 각 도구의 상세 파라미터 설명은 tool docstring에 정의되어 있으며,
create_react_agent가 자동으로 LLM에 전달합니다.
"""
from langgraph.prebuilt import create_react_agent
from backend.config import llm
from backend.calculator.tools import CALCULATOR_TOOLS

SYSTEM_PROMPT = """당신은 근로기준법 계산기 어시스턴트입니다.
사용자가 자연어로 계산을 요청하면 필요한 파라미터를 추출하여 적절한 도구를 호출하세요.

<규칙>
- 파라미터가 부족하면 구체적으로 무엇을 알려달라고 물어보세요.
- 숫자 파라미터는 반드시 정수 또는 실수로 변환하여 도구에 전달하세요.
- "월 300만원"은 last_3m_salary=9000000 (3개월치 합계)로 변환하세요.
- 사용자가 "퇴직금이라고만 말하면 근속년수, 월급 등 필요한 정보를 물어보세요.
- 사용자가 다른 최저임금 기준을 말하면 min_wage_per_hour 파라미터에 전달하세요.
- 한 번에 모든 파라미터를 추출할 수 없으면 필요한 것만 물어보고, 답변을 기다리세요.
"""

graph = create_react_agent(
    model=llm,
    tools=CALCULATOR_TOOLS,
    prompt=SYSTEM_PROMPT,
)
