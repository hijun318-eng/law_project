"""
수당 계산기 페이지
"""
import streamlit as st
from frontend.theme import C_SUCCESS, C_WARNING
from backend.calculator.core import (
    calc_retirement_pay,
    calc_annual_leave_pay,
    calc_weekly_allowance,
    calc_minimum_wage_check,
)
from backend.constants import MINIMUM_WAGE_2026, MINIMUM_WAGE_YEAR

try:
    from backend.calculator_engine import CalculatorEngine
    CALC_AVAILABLE = True
except ImportError:
    CALC_AVAILABLE = False


def _calc_retirement():
    st.markdown("### 퇴직금 계산기")
    st.caption("근로자퇴직급여 보장법에 따른 퇴직금을 계산합니다.")

    col1, col2 = st.columns(2)
    with col1:
        years = st.number_input("근속연수", min_value=0.0, max_value=50.0, value=3.0, step=0.5, format="%.1f")
    with col2:
        months = st.number_input("개월 수", min_value=0, max_value=11, value=0, step=1)

    total_days = int(years * 365 + months * 30.5)

    col1, col2 = st.columns(2)
    with col1:
        last_3m_salary = st.number_input("퇴직 전 3개월 총 임금 (원)", min_value=0, value=9000000, step=100000, format="%d")
    with col2:
        paid_days = st.number_input("3개월 총 일수", min_value=1, value=92, step=1)

    if paid_days > 0:
        avg_wage = last_3m_salary / paid_days
    else:
        avg_wage = 0

    st.info(f"📌 평균임금: 1일 **{avg_wage:,.0f}원**")

    if st.button("퇴직금 계산", use_container_width=True, type="primary"):
        result = calc_retirement_pay(years, months, last_3m_salary, paid_days)
        if result["success"]:
            st.markdown(f'<div class="calc-result">💰 예상 퇴직금: {result["severance"]:,}원</div>', unsafe_allow_html=True)
            st.markdown(f"""
            **계산 상세:**
            - 1일 평균임금: {result["avg_wage"]:,.0f}원
            - 근속일수: 약 {result["total_days"]}일
            - 산식: {result["avg_wage"]:,.0f}원 × 30일 × ({result["total_days"]}일 ÷ 365일)
            """)
        else:
            if "1년 미만" in str(result.get("error", "")):
                st.error("❌ 퇴직금은 1년 이상 근속 시 발생합니다.")
            else:
                st.error("❌ 임금 정보를 확인해주세요.")

    with st.container(border=True):
        st.markdown("**📋 유의사항**")
        st.markdown("""
        - 퇴직금은 1년 이상 근속한 근로자에게 지급됩니다.
        - 4주간을 평균하여 1주 소정근로시간이 15시간 미만인 근로자는 제외됩니다.
        - 실제 금액은 회사 규정과 개인 상황에 따라 다를 수 있습니다.
        """)


def _calc_annual():
    st.markdown("### 연차수당 계산기")
    st.caption("사용하지 않은 연차휴가에 대한 수당을 계산합니다.")

    col1, col2 = st.columns(2)
    with col1:
        years_worked = st.number_input("근속연수", min_value=0, max_value=30, value=2, step=1)
    with col2:
        daily_wage = st.number_input("1일 통상임금 (원)", min_value=0, value=80000, step=10000, format="%d")

    if years_worked < 1:
        annual_days = years_worked * 11
        st.info(f"📌 1년 미만 근로자: 월 1일 발생 (최대 11일)")
    else:
        annual_days = 15 + max(0, (years_worked - 1))
        st.info(f"📌 {years_worked}년차: 연 {annual_days}일 발생 (최대 25일)")

    used_days = st.number_input("사용한 연차 일수", min_value=0, max_value=annual_days, value=0, step=1)
    remaining = max(0, annual_days - used_days)

    if remaining == 0:
        remaining = st.number_input("미사용 연차 일수 (자동)", min_value=0, value=5, step=1)

    if st.button("연차수당 계산", use_container_width=True, type="primary"):
        result = calc_annual_leave_pay(years_worked, daily_wage, used_days)
        st.markdown(f'<div class="calc-result">💰 예상 연차수당: {result["amount"]:,}원</div>', unsafe_allow_html=True)
        st.markdown(f"""
        **계산 상세:**
        - {result["day_note"]}
        - 1일 통상임금: {result["daily_wage"]:,}원
        - 발생 연차: {result["total_days"]}일
        - 사용 연차: {result["used_days"]}일
        - 미사용 연차: {result["remaining"]}일
        - 산식: {result["daily_wage"]:,}원 × {result["remaining"]}일 = {result["amount"]:,}원
        """)


def _calc_weekly():
    st.markdown("### 주휴수당 계산기")
    st.caption("1주 소정근로시간 15시간 이상인 근로자의 주휴수당을 계산합니다.")

    col1, col2 = st.columns(2)
    with col1:
        hourly_wage = st.number_input("시급 (원)", min_value=0, value=10000, step=500, format="%d")
    with col2:
        weekly_hours = st.number_input("1주 소정근로시간", min_value=0, max_value=40, value=40, step=1)

    if st.button("주휴수당 계산", use_container_width=True, type="primary"):
        _wk_result = calc_weekly_allowance(hourly_wage, weekly_hours)

        if not _wk_result["success"]:
            st.warning("⚠️ 1주 소정근로시간이 15시간 미만인 근로자는 주휴수당 지급 대상이 아닙니다.")
        else:
            weekly_allowance = _wk_result["weekly_allowance"]
            monthly_allowance = _wk_result["monthly_allowance"]

            st.markdown(f'<div class="calc-result">💰 주휴수당: 주 {weekly_allowance:,.0f}원</div>', unsafe_allow_html=True)
            st.markdown(f"""
            **계산 상세:**
            - 시급: {hourly_wage:,.0f}원
            - 1주 소정근로시간: {weekly_hours}시간
            - 주휴수당 산식: ({weekly_hours}시간 ÷ 40시간) × 8시간 × {hourly_wage:,.0f}원
            - 주 환산: {weekly_allowance:,.0f}원
            - 월 환산 (4.345주 기준): 약 {monthly_allowance:,.0f}원

            **📌 주의사항:**
            - 주 15시간 미만 근로자는 주휴수당 지급 대상이 아닙니다.
            - 주휴수당은 소정근로일을 개근해야 지급됩니다.
            """)


def _calc_min_wage():
    st.markdown("### 최저임금 위반 확인")
    st.caption(f"{MINIMUM_WAGE_YEAR}년 기준 최저시급 **{MINIMUM_WAGE_2026:,}원**을 기본값으로 확인합니다. 직접 최저시급을 입력할 수도 있습니다.")

    col1, col2 = st.columns(2)
    with col1:
        input_hourly = st.number_input("내 시급 (원)", min_value=0, value=10000, step=500, format="%d")
    with col2:
        daily_hours = st.number_input("1일 근무시간", min_value=1, max_value=24, value=8, step=1)
    weekly_days = st.number_input("주간 근무일수", min_value=1, max_value=7, value=5, step=1)

    # 사용자 지정 최저시급
    use_custom_min_wage = st.checkbox("최저시급 직접 입력", value=False,
                                       help="체크하면 기준 최저시급을 직접 입력할 수 있습니다.")
    if use_custom_min_wage:
        custom_min_wage = st.number_input(f"기준 최저시급 (원)", min_value=0, value=MINIMUM_WAGE_2026, step=100, format="%d",
                                           help=f"기본값은 {MINIMUM_WAGE_YEAR}년 법정 최저시급 {MINIMUM_WAGE_2026:,}원입니다.")
        current_min_wage = custom_min_wage if custom_min_wage > 0 else MINIMUM_WAGE_2026
        year_label = f"사용자 지정"
    else:
        current_min_wage = MINIMUM_WAGE_2026
        year_label = f"{MINIMUM_WAGE_YEAR}년"

    if st.button("최저임금 확인", use_container_width=True, type="primary"):
        result = calc_minimum_wage_check(input_hourly, daily_hours, weekly_days, current_min_wage)

        if result["success"]:
            st.markdown(f"""
            <div class="calc-result" style="color:{C_SUCCESS};">
            ✅ 최저임금 위반 아님 ({year_label} 기준)
            </div>
            """, unsafe_allow_html=True)
            st.markdown(f"""
            - 실질 시급: {result["effective_hourly"]:,.0f}원
            - 기준 최저시급: {result["current_min_wage"]:,}원 ({year_label})
            - 최저임금 대비: {result["ratio"]:.1f}%
            """)
        else:
            st.markdown(f"""
            <div class="calc-result" style="color:{C_WARNING};">
            ❌ 최저임금 위반 의심 ({year_label} 기준)
            </div>
            """, unsafe_allow_html=True)
            st.markdown(f"""
            - 실질 시급: {result["effective_hourly"]:,.0f}원
            - 기준 최저시급: {result["current_min_wage"]:,}원 ({year_label})
            - 최저임금 대비: {result["ratio"]:.1f}%
            - 예상 월 손해: 약 {result["monthly_shortage"]:,}원

            **📞 고용노동부 상담센터 1350으로 신고하세요.**
            """)


def render_calculator():
    st.markdown('<p class="main-header">🧮 수당 계산기</p>', unsafe_allow_html=True)
    st.markdown("퇴직금, 연차수당, 주휴수당, 최저임금을 자동으로 계산합니다.")

    tab1, tab2 = st.tabs(["📝 입력 폼", "💬 채팅 계산"])

    # ════════════════════════════════════════
    # TAB 1: 기존 입력 폼 (변경 없음)
    # ════════════════════════════════════════
    with tab1:
        calc_type = st.selectbox(
            "계산 유형 선택",
            ["퇴직금 계산", "연차수당 계산", "주휴수당 계산", "최저임금 위반 확인"],
        )

        if calc_type == "퇴직금 계산":
            _calc_retirement()
        elif calc_type == "연차수당 계산":
            _calc_annual()
        elif calc_type == "주휴수당 계산":
            _calc_weekly()
        elif calc_type == "최저임금 위반 확인":
            _calc_min_wage()

    # ════════════════════════════════════════
    # TAB 2: 채팅 계산 (ReAct 에이전트)
    # ════════════════════════════════════════
    with tab2:
        if not CALC_AVAILABLE:
            st.warning("⚠️ CalculatorEngine을 불러올 수 없습니다. 백엔드 모듈을 확인해주세요.")
            return

        # 세션 상태 초기화
        if "calc_chat_messages" not in st.session_state:
            st.session_state.calc_chat_messages = []

        # 채팅 메시지 히스토리 표시 (먼저 표시 — 입력창은 항상 메시지 아래)
        for msg in st.session_state.calc_chat_messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # 채팅 입력 처리 (메시지 아래에 위치)
        if prompt := st.chat_input("자연어로 계산을 입력하세요 (예: 퇴직금 계산해줘, 3년 근무, 월 300만원)"):
            # 사용자 메시지 추가
            st.session_state.calc_chat_messages.append({"role": "user", "content": prompt})

            # 어시스턴트 응답 생성
            with st.spinner("🧮 계산 중..."):
                try:
                    engine = getattr(st.session_state, "_calc_engine", None)
                    if engine is None:
                        assert CALC_AVAILABLE  # guard above ensures this
                        engine = CalculatorEngine()  # type: ignore[name-defined]
                        st.session_state._calc_engine = engine

                    # 모든 대화 기록을 컨텍스트로 전달
                    result = engine.calculate(
                        prompt,
                        conversation_history=st.session_state.calc_chat_messages[:-1],
                    )
                    answer = result.get("answer", "결과를 생성하지 못했습니다.")
                except Exception as e:
                    answer = f"계산 중 오류가 발생했습니다: {e}"

            st.session_state.calc_chat_messages.append({"role": "assistant", "content": answer})
            st.rerun()
