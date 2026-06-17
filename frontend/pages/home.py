"""
홈 페이지
"""
import streamlit as st
from frontend.config import ENGINE_AVAILABLE

try:
    from backend.router_engine import router_engine
except Exception:
    router_engine = None


def render_home():
    st.markdown('<p class="main-header">🏠 노동 법률 AI 어시스턴트</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-header">근로기준법 · 노동관계법 관련 모든 정보를 한 곳에서 확인하세요.</p>',
        unsafe_allow_html=True,
    )

    st.divider()
    st.subheader("🔎 홈 검색")
    st.markdown("**질문을 입력하세요**")
    colA, colB = st.columns([5, 1])
    with colA:
        query = st.text_input(
            "질문을 입력하세요",
            placeholder="예: 해고가 부당한지 알려줘 / 임금체불 절차 알려줘 / 주휴수당 계산해줘 / 최근 노동법 관련 이슈 찾아줘",
            label_visibility="collapsed"
        )
    with colB:
        clicked = st.button("검색", use_container_width=True, type="primary")

    if clicked and query and router_engine is not None:
        with st.spinner("분석 중... "):
            try:
                result = router_engine.run(query.strip())
                st.divider()
                
                # 🌟 [수정됨] 라우터 분기 결과에 따른 헤더 출력
                if result.mode == "case_based_answer":
                    st.markdown("### 💡 최종 답변")
                elif result.mode == "procedure_guidance":
                    st.markdown("### 📋 대응 절차")
                elif result.mode == "latest_news":
                    st.markdown("### 📰 최신 뉴스")
                else:
                    st.markdown("### 🧮 계산 결과")
                    
                st.markdown(result.content)
            except Exception as e:
                st.error(f"라우터 실행 오류: {e}")

    if clicked and query and router_engine is None:
        st.warning("라우터 엔진을 불러올 수 없습니다. 백엔드 구성을 확인해주세요.")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        with st.container(border=True):
            st.markdown("#### 💬 노동권리 진단")
            st.markdown("법률 질문에 대한 답변을 AI가 제공합니다.")
            if st.button("바로가기", key="home_qa", use_container_width=True):
                st.session_state.page = "qa"
                st.rerun()
    with col2:
        with st.container(border=True):
            st.markdown("#### 🔍 상황별 권리 안내")
            st.markdown("부당해고, 임금체불 등 상황별 권리 확인")
            if st.button("바로가기", key="home_rights", use_container_width=True):
                st.session_state.page = "rights"
                st.rerun()
    with col3:
        with st.container(border=True):
            st.markdown("#### 🧮 수당 계산기")
            st.markdown("퇴직금, 연차수당, 주휴수당 계산")
            if st.button("바로가기", key="home_calc", use_container_width=True):
                st.session_state.page = "calculator"
                st.rerun()
    with col4:
        with st.container(border=True):
            st.markdown("#### 📞 신고/접수 경로")
            st.markdown("기관별 신고 절차와 방법 안내")
            if st.button("바로가기", key="home_report", use_container_width=True):
                st.session_state.page = "report"
                st.rerun()

    st.divider()
    st.markdown("### ⚡ 빠른 상담")
    if ENGINE_AVAILABLE:
        st.info("아래 질문을 클릭하면 노동권리 진단 페이지에서 상담을 시작합니다.")
        quick_qs = [
            "해고 통보는 언제 해야 하나요?",
            "야근 수당은 어떻게 계산하나요?",
            "연차 휴가는 며칠인가요?",
            "임금 체불 시 어떻게 해야 하나요?",
        ]
        cols = st.columns(2)
        for i, q in enumerate(quick_qs):
            if cols[i % 2].button(q, use_container_width=True, key=f"quick_{i}"):
                st.session_state.qa_messages = []
                st.session_state.page = "qa"
                st.rerun()
    else:
        st.info("💡 RAG 엔진이 연결되지 않았습니다. 좌측 메뉴를 통해 각 기능을 이용할 수 있습니다.")

    st.divider()
    st.markdown("### 📢 공지사항")
    st.markdown("""
    - 본 서비스가 제공하는 정보는 참고용이며 법적 효력이 없습니다.
    - 정확한 법률 판단이 필요한 경우 법률 전문가와 상담하시기 바랍니다.
    - 모든 상담 내용은 익명으로 처리되며, 서비스 개선을 위해 활용될 수 있습니다.
    """)