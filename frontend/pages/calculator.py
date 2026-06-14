"""
수당 계산기 페이지
"""
import streamlit as st
from frontend.config import C_SUCCESS, C_WARNING


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
        if total_days >= 365 and avg_wage > 0:
            severance = avg_wage * 30 * (total_days / 365)
            st.markdown(f'<div class="calc-result">💰 예상 퇴직금: {severance:,.0f}원</div>', unsafe_allow_html=True)
            st.markdown(f"""
            **계산 상세:**
            - 1일 평균임금: {avg_wage:,.0f}원
            - 근속일수: 약 {total_days}일
            - 산식: {avg_wage:,.0f}원 × 30일 × ({total_days}일 ÷ 365일)
            """)
        else:
            if total_days < 365:
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
        amount = daily_wage * remaining
        st.markdown(f'<div class="calc-result">💰 예상 연차수당: {amount:,.0f}원</div>', unsafe_allow_html=True)
        st.markdown(f"""
        **계산 상세:**
        - 1일 통상임금: {daily_wage:,.0f}원
        - 미사용 연차: {remaining}일
        - 산식: {daily_wage:,.0f}원 × {remaining}일 = {amount:,.0f}원
        """)


def _calc_weekly():
    st.markdown("### 주휴수당 계산기")
    st.caption("1주 소정근로시간 15시간 이상인 근로자의 주휴수당을 계산합니다.")

    col1, col2 = st.columns(2)
    with col1:
        hourly_wage = st.number_input("시급 (원)", min_value=0, value=10000, step=500, format="%d")
    with col2:
        weekly_hours = st.number_input("1주 소정근로시간", min_value=0, max_value=40, value=40, step=1)

    if weekly_hours >= 15:
        weekly_allowance = (weekly_hours / 40) * 8 * hourly_wage
        monthly_allowance = weekly_allowance * 4.345

        if st.button("주휴수당 계산", use_container_width=True, type="primary"):
            st.markdown(f'<div class="calc-result">💰 주휴수당: 주 {weekly_allowance:,.0f}원</div>', unsafe_allow_html=True)
            st.markdown(f"""
            **계산 상세:**
            - 시급: {hourly_wage:,.0f}원
            - 1주 소정근로시간: {weekly_hours}시간
            - 주휴수당 산식: ({weekly_hours}시간 ÷ 40시간) × 8시간 × {hourly_wage:,.0f}원
            - 월 환산: 약 {monthly_allowance:,.0f}원

            **📌 주의사항:**
            - 주 15시간 미만 근로자는 주휴수당 지급 대상이 아닙니다.
            - 주휴수당은 소정근로일을 개근해야 지급됩니다.
            """)
    else:
        st.warning("⚠️ 1주 소정근로시간이 15시간 미만인 근로자는 주휴수당 지급 대상이 아닙니다.")


def _calc_min_wage():
    st.markdown("### 최저임금 위반 확인")
    st.caption("2025년 기준 최저시급 **10,030원**을 기준으로 확인합니다.")

    MIN_WAGE_2025 = 10030

    col1, col2 = st.columns(2)
    with col1:
        input_hourly = st.number_input("내 시급 (원)", min_value=0, value=10000, step=500, format="%d")
    with col2:
        daily_hours = st.number_input("1일 근무시간", min_value=1, max_value=24, value=8, step=1)
    weekly_days = st.number_input("주간 근무일수", min_value=1, max_value=7, value=5, step=1)

    if st.button("최저임금 확인", use_container_width=True, type="primary"):
        weekly_hours = daily_hours * weekly_days
        if weekly_hours >= 15:
            effective_hours = weekly_hours + (weekly_hours / 40) * 8
        else:
            effective_hours = weekly_hours
        effective_hourly = (input_hourly * weekly_hours) / effective_hours if effective_hours > 0 else 0

        ratio = (effective_hourly / MIN_WAGE_2025) * 100

        if effective_hourly >= MIN_WAGE_2025:
            st.markdown(f"""
            <div class="calc-result" style="color:{C_SUCCESS};">
            ✅ 최저임금 위반 아님
            </div>
            """, unsafe_allow_html=True)
            st.markdown(f"""
            - 실질 시급: {effective_hourly:,.0f}원
            - 최저시급(2025): {MIN_WAGE_2025:,}원
            - 최저임금 대비: {ratio:.1f}%
            """)
        else:
            shortage = (MIN_WAGE_2025 - effective_hourly) * effective_hours / weekly_hours * weekly_hours * 4.345
            st.markdown(f"""
            <div class="calc-result" style="color:{C_WARNING};">
            ❌ 최저임금 위반 의심
            </div>
            """, unsafe_allow_html=True)
            st.markdown(f"""
            - 실질 시급: {effective_hourly:,.0f}원
            - 최저시급(2025): {MIN_WAGE_2025:,}원
            - 최저임금 대비: {ratio:.1f}%
            - 예상 월 손해: 약 {shortage:,.0f}원

            **📞 고용노동부 상담센터 1350으로 신고하세요.**
            """)


def render_calculator():
    st.markdown('<p class="main-header">🧮 수당 계산기</p>', unsafe_allow_html=True)
    st.markdown("퇴직금, 연차수당, 주휴수당, 최저임금을 자동으로 계산합니다.")

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
