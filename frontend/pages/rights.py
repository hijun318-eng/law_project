"""
상황별 권리 안내 페이지
"""
import streamlit as st
from frontend.pages.rights.data import RIGHTS_CASES


def render_rights():
    st.markdown('<p class="main-header">🔍 상황별 권리 안내</p>', unsafe_allow_html=True)
    st.markdown("부당해고, 임금체불 등 구체적인 상황에서의 권리와 법적 조치를 확인하세요.")

    col1, col2, col3 = st.columns(3)
    case_keys = list(RIGHTS_CASES.keys())
    for i, key in enumerate(case_keys):
        case = RIGHTS_CASES[key]
        col = [col1, col2, col3][i % 3]
        with col:
            if st.button(
                f"{case['icon']} **{key}**\n\n{case['desc']}",
                use_container_width=True,
                key=f"rights_btn_{i}",
                help=case['desc'],
            ):
                st.session_state.selected_case = key
                st.rerun()

    selected = st.session_state.get("selected_case")
    if not selected and case_keys:
        selected = case_keys[0]

    if selected and selected in RIGHTS_CASES:
        case = RIGHTS_CASES[selected]
        st.divider()
        st.markdown(f"## {case['icon']} {selected}")
        st.markdown(case["desc"])

        tab1, tab2, tab3, tab4 = st.tabs(["📜 관련 법 조항", "📋 조치 절차", "⏰ 신고 기한", "⚖️ 관련 판례"])

        with tab1:
            for law in case["laws"]:
                with st.container(border=True):
                    st.markdown(f"- {law}")

        with tab2:
            st.markdown("**권리 구제를 위한 절차:**")
            for j, proc in enumerate(case["procedures"], 1):
                st.markdown(f"**{j}.** {proc}")

        with tab3:
            st.markdown(f"**⏰ {case['deadline']}**")
            st.markdown("")
            with st.container(border=True):
                st.markdown("**💡 팁:** 신고 기한을 놓치면 권리를 보호받기 어려울 수 있으므로, 조기에 대응하는 것이 중요합니다.")

        with tab4:
            if case["precedents"]:
                for prec in case["precedents"]:
                    with st.container(border=True):
                        st.markdown(f"⚖️ {prec}")
            else:
                st.info("아직 등록된 판례가 없습니다.")
