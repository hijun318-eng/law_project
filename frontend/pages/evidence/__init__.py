"""
증거 관리 가이드 페이지
"""
import streamlit as st
from frontend.pages.evidence.data import EVIDENCE_GUIDE


def render_evidence():
    st.markdown('<p class="main-header">📋 증거 관리 가이드</p>', unsafe_allow_html=True)
    st.markdown("상황별로 필요한 증거를 사전에 준비하여 권리 구제에 대비하세요.")

    case_keys = list(EVIDENCE_GUIDE.keys())
    selected = st.selectbox(
        "상황 선택",
        case_keys,
        format_func=lambda x: f"{EVIDENCE_GUIDE[x]['icon']} {x}",
    )

    if selected and selected in EVIDENCE_GUIDE:
        guide = EVIDENCE_GUIDE[selected]
        st.markdown(f"### {guide['icon']} {selected}")
        st.markdown(guide["desc"])

        st.markdown("#### 📌 필수 증거 목록")
        st.markdown("⭐ 중요도가 높은 순서대로 정리했습니다.")

        for item, importance, note in guide["items"]:
            with st.container(border=True):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**{item}**")
                    st.caption(note)
                with col2:
                    st.markdown(f"<div style='text-align:right'>{importance}</div>", unsafe_allow_html=True)

        st.divider()
        with st.container(border=True):
            st.markdown("#### 💡 증거 수집 팁")
            st.markdown("""
            1. **원본 보존**: 모든 증거는 원본을 안전하게 보관하세요.
            2. **백업 필수**: 디지털 증거는 클라우드, 이메일 등 여러 곳에 백업.
            3. **타임라인 기록**: 사건 발생 일시, 장소, 관련자를 상세히 기록.
            4. **법적 효율 확인**: 녹음 증거는 대화 당사자 참여 시 증거 능력 인정.
            5. **사전 준비**: 문제 발생 전부터 체계적으로 증거를 수집·보관.
            """)
