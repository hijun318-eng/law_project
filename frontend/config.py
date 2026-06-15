"""
앱 설정, 색상 테마, 메뉴 정의, 세션 초기화, CSS
"""
import os
import sys
import uuid
import streamlit as st

# ── RAG 엔진 연결 (선택적) ────────────────────────────────
try:
    from backend.rag_engine import RAGEngine
    RAG_AVAILABLE = True
except ImportError as e:
    RAG_AVAILABLE = False
    print(f"[WARN] RAG 엔진 로드 실패: {e}")

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

# ── 색상 테마 ──────────────────────────────────────────────
C_PRIMARY = "#1B3A5C"       # 진한 남색 (법률 느낌)
C_ACCENT  = "#2E7DBA"       # 파랑
C_SUCCESS = "#2E7D32"       # 녹색
C_WARNING = "#E65100"       # 주황
C_BG_LIGHT = "#F5F7FA"     # 배경
C_CARD_BG = "#FFFFFF"      # 카드 배경

# ── 메뉴 정의 ──────────────────────────────────────────────
PAGES = {
    "home":         {"icon": "🏠",   "label": "홈",              "group": "시작"},
    "qa":           {"icon": "💬",   "label": "법률 Q&A",         "group": "MVP 기능"},
    "rights":       {"icon": "🔍",   "label": "상황별 권리 안내",  "group": "MVP 기능"},
    "report":       {"icon": "📞",   "label": "신고/접수 경로",    "group": "MVP 기능"},
    "evidence":     {"icon": "📋",   "label": "증거 관리 가이드",  "group": "MVP 기능"},
    "calculator":   {"icon": "🧮",   "label": "수당 계산기",       "group": "부가 기능"},
    "docwriter":    {"icon": "📝",   "label": "서류 작성 도우미",  "group": "부가 기능"},
    "contract":     {"icon": "🔎",   "label": "근로계약서 분석",   "group": "부가 기능"},
    "latestNews":     {"icon": "📰",   "label": "최신 뉴스",   "group": "부가 기능"},
}


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
            st.session_state.engine = RAGEngine() if RAG_AVAILABLE else None
        except Exception as e:
            st.session_state.engine = None
    if "news_engine" not in st.session_state:
        try:
            from backend.news_engine import NewsEngine
            from backend.config import llm
            st.session_state.news_engine = NewsEngine(llm)
        except Exception:
            st.session_state.news_engine = None

# ============================================================
# CSS 스타일
# ============================================================
def load_css():
    st.markdown(f"""
    <style>
        .stApp {{ background-color: {C_BG_LIGHT}; }}
        .main-header {{
            color: {C_PRIMARY};
            font-size: 1.8rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }}
        .sub-header {{
            color: #555;
            font-size: 1rem;
            margin-bottom: 1.5rem;
        }}
        .card {{
            background-color: {C_CARD_BG};
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            margin-bottom: 1rem;
            border: 1px solid #eee;
        }}
        .card-title {{
            font-size: 1.2rem;
            font-weight: 600;
            color: {C_PRIMARY};
            margin-bottom: 0.5rem;
        }}
        .card-subtitle {{
            color: #555;
            font-size: 0.9rem;
        }}
        .badge {{
            display: inline-block;
            padding: 0.2rem 0.6rem;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
            margin-right: 0.3rem;
        }}
        .badge-green {{ background-color: #E8F5E9; color: #2E7D32; }}
        .badge-blue {{ background-color: #E3F2FD; color: #1565C0; }}
        .badge-orange {{ background-color: #FFF3E0; color: #E65100; }}
        .badge-red {{ background-color: #FFEBEE; color: #C62828; }}
        .sidebar-menu-item {{
            padding: 0.5rem 0.8rem;
            border-radius: 8px;
            cursor: pointer;
            transition: background 0.2s;
            margin-bottom: 0.2rem;
        }}
        .sidebar-menu-item:hover {{
            background-color: #E3F2FD;
        }}
        .sidebar-menu-item.active {{
            background-color: #E3F2FD;
            border-left: 3px solid {C_ACCENT};
            font-weight: 600;
        }}
        .info-box {{
            background-color: #E3F2FD;
            border-left: 4px solid {C_ACCENT};
            padding: 1rem;
            border-radius: 6px;
            margin: 1rem 0;
        }}
        .warning-box {{
            background-color: #FFF3E0;
            border-left: 4px solid {C_WARNING};
            padding: 1rem;
            border-radius: 6px;
            margin: 1rem 0;
        }}
        .success-box {{
            background-color: #E8F5E9;
            border-left: 4px solid {C_SUCCESS};
            padding: 1rem;
            border-radius: 6px;
            margin: 1rem 0;
        }}
        .calc-result {{
            font-size: 2rem;
            font-weight: 700;
            color: {C_ACCENT};
            text-align: center;
            padding: 1rem;
        }}
        .footer {{
            text-align: center;
            color: #999;
            font-size: 0.8rem;
            margin-top: 3rem;
            padding: 1rem;
            border-top: 1px solid #eee;
        }}
    </style>
    """, unsafe_allow_html=True)
