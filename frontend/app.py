"""
frontend/app.py — 애플리케이션 메인 라우터
"""
import streamlit as st
from frontend.config import init_session, APP_NAME
from frontend.theme import load_css
from frontend.sidebar import render_sidebar
from frontend.pages.home import render_home
from frontend.pages.qa import render_qa
from frontend.pages.rights import render_rights
from frontend.pages.report import render_report
from frontend.pages.evidence import render_evidence
from frontend.pages.calculator import render_calculator
from frontend.pages.docwriter import render_docwriter
from frontend.pages.contract import render_contract
from frontend.pages.latestNews import render_latestNews


def main():
    # 초기화
    init_session()
    load_css()

    # 사이드바 렌더링
    render_sidebar()

    # 페이지 레지스트리 (if-elif 대신 dict lookup)
    PAGE_REGISTRY = {
        "home": render_home,
        "qa": render_qa,
        "rights": render_rights,
        "report": render_report,
        "evidence": render_evidence,
        "calculator": render_calculator,
        "docwriter": render_docwriter,
        "contract": render_contract,
        "latestNews": render_latestNews,
    }

    page = st.session_state.page
    render_fn = PAGE_REGISTRY.get(page, render_home)
    render_fn()

    # 푸터
    st.markdown(
        f"<div class='footer'>"
        f"⚖️ 노동 법률 AI 어시스턴트 v1.0 | "
        f"본 서비스는 참고용이며 법적 효력이 없습니다. | "
        f"© 2025"
        f"</div>",
        unsafe_allow_html=True,
    )
