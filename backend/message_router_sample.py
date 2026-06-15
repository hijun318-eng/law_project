def route_user_query(user_input: str) -> dict:
    """
    사용자 질문을 분석하여 4가지 핵심 기능 노드 중 하나로 라우팅합니다.
    """
    system_prompt = """
    너는 사용자의 노동법률 관련 질의를 분석하여 가장 적합한 처리 노드(Node)를 결정하는 라우터 AI야.
    아래의 [4대 노드 목록]을 보고, 질문에 가장 알맞은 노드의 'ID' 딱 하나만 반환해줘.

    [4대 노드 목록]
    1. case_based_answer : 실제 상담 사례, 판례, 유사 사연 기반의 답변 생성이 필요할 때
    2. procedure_guidance : 진정서 접수, 구제신청 등 행정 절차나 고소/신고 프로세스 안내가 필요할 때
    3. allowance_calculator : 주휴수당, 연차수당, 해고예고수당 등 구체적인 금액 계산 기능이 필요할 때
    4. contract_news : 근로계약서 작성법, 필수 조항 검토 또는 최신 노동법/근로계약 관련 뉴스/이슈를 찾을 때

    [주의 규칙]
    - 설명이나 수식어 없이 오직 노드 ID(예: case_based_answer)만 텍스트로 출력해.
    - 목록에 없는 단어는 절대 출력하지 마.
    """

    response = client.chat.completions.create(
        model="gpt-5.4-nano",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"사용자 질문: {user_input}"}
        ],
        temperature=0.0
    )

    next_node = response.choices[0].message.content.strip()
    
    return {
        "next_node": next_node,
        "user_input": user_input
    }

print("4대 노드 기준 라우터 함수 정의 완료!")
# ==========================================
# 기능별 서브 노드(자식 함수) 정의
# ==========================================

def run_case_based_answer(state: dict) -> dict:
    print("▶ [노드 진입] 사례기반 답변생성"); state["final_output"] = {"type": "사례 답변", "content": "유사 판례 및 상담 사례 분석 결과..."}; return state

def run_procedure_guidance(state: dict) -> dict:
    print("▶ [노드 진입] 절차안내"); state["final_output"] = {"type": "절차 안내", "content": "고용노동부 진정 절차 및 시기 안내..."}; return state

def run_allowance_calculator(state: dict) -> dict:
    print("▶ [노드 진입] 수당계산기"); state["final_output"] = {"type": "수당 계산", "content": "입력 데이터 기반 주휴/연차 수당 연산 결과..."}; return state

def run_contract_news(state: dict) -> dict:
    print("▶ [노드 진입] 근로계약서 뉴스"); state["final_output"] = {"type": "근로계약/뉴스", "content": "최신 근로계약서 가이드라인 및 관련 법령 뉴스..."}; return state


# ==========================================
# 메인 그래프 컨트롤러
# ==========================================

def main_graph_orchestrator(user_query: str) -> dict:
    # 공유 상태(State) 백업
    state = {
        "user_input": user_query,
        "next_node": None,
        "final_output": None
    }
    
    # 1. 라우터 노드 실행
    router_output = route_user_query(state["user_input"])
    state["next_node"] = router_output["next_node"]
    
    # 2. 노드 팩토리 매핑
    node_map = {
        "case_based_answer": run_case_based_answer,
        "procedure_guidance": run_procedure_guidance,
        "allowance_calculator": run_allowance_calculator,
        "contract_news": run_contract_news
    }
    
    # 3. 분기 실행
    target_node_function = node_map.get(state["next_node"])
    if target_node_function:
        return target_node_function(state)
    else:
        print(f"❌ 매핑되지 않은 노드 ID: {state['next_node']}")
        return state

print("메인 그래프 오케스트레이터 정의 완료!")
# !pip install openai  # 만약 설치가 안 되어 있다면 주석을 풀고 실행하세요.

from openai import OpenAI

# OpenAI 클라이언트 초기화 (발급받으신 API 키를 직접 입력하거나 환경변수에 등록해야 합니다)
client = OpenAI()

print("OpenAI Client 초기화 완료!")