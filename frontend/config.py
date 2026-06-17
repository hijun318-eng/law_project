"""
앱 설정 및 세션 초기화

분할:
  - theme.py:  색상 테마 + CSS 스타일 (load_css)
  - menu.py:   페이지 메뉴 정의 (PAGES)
  - config.py: 세션 초기화 + 모듈 설정
"""
import os
import sys
import uuid
import streamlit as st

# ── Supervisor 엔진 연결 (선택적) ─────────────────────────
try:
    from backend.supervisor.engine import SupervisorEngine
    ENGINE_AVAILABLE = True
except ImportError as e:
    ENGINE_AVAILABLE = False
    print(f"[WARN] Supervisor 엔진 로드 실패: {e}")

# ============================================================
# 앱 설정
# ============================================================
st.set_page_config(
    page_title="노동 법률 AI 어시스턴트",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

APP_NAME = "노동 법률 AI 어시스턴트"
APP_SUBTITLE = "근로기준법 · 노동관계법 종합 상담 플랫폼"


# ============================================================
# 세션 상태 초기화
# ============================================================
def init_session():
    if "page" not in st.session_state:
        st.session_state.page = "home"
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    if "qa_messages" not in st.session_state:
        st.session_state.qa_messages = []
    if "engine" not in st.session_state:
        try:
            st.session_state.engine = SupervisorEngine() if ENGINE_AVAILABLE else None
        except Exception as e:
            st.session_state.engine = None
    if "news_engine" not in st.session_state:
        try:
            from backend.news_engine import NewsEngine
            from backend.config import llm
            st.session_state.news_engine = NewsEngine(llm)
        except Exception:
            st.session_state.news_engine = None
