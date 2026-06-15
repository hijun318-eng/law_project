"""
신고/접수 경로 페이지
"""
import streamlit as st
from frontend.pages.report.data import REPORT_CHANNELS, DEADLINE_INFO


def render_report():
    st.markdown('<p class="main-header">📞 신고/접수 경로 안내</p>', unsafe_allow_html=True)
    st.markdown("상황에 맞는 기관을 선택하여 신고 절차와 방법을 확인하세요.")

    channels = list(REPORT_CHANNELS.keys())
    selected_ch = st.selectbox(
        "기관 선택",
        channels,
        format_func=lambda x: f"{REPORT_CHANNELS[x]['icon']} {x}",
    )

    if selected_ch:
        ch = REPORT_CHANNELS[selected_ch]
        st.markdown(f"### {ch['icon']} {selected_ch}")
        st.markdown(ch["desc"])

        col1, col2 = st.columns([1, 1])
        with col1:
            with st.container(border=True):
                st.markdown("#### 📞 연락처 및 접수 방법")
                for icon, method, detail in ch["methods"]:
                    st.markdown(f"- **{icon} {method}**: {detail}")

        with col2:
            with st.container(border=True):
                st.markdown("#### 🌐 관할 범위")
                st.markdown(ch["jurisdiction"])

        with st.container(border=True):
            st.markdown("#### 📋 처리 절차")
            for j, step in enumerate(ch["process"], 1):
                st.markdown(f"**{j}.** {step}")

        st.divider()
        with st.container(border=True):
            st.markdown("#### ⏰ 함께 보기: 소멸시효 정보")
            for title, desc in DEADLINE_INFO.items():
                st.markdown(f"- **{title}**: {desc}")
