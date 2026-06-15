"""
frontend/pages/latestNews.py
최신 노동법 뉴스 페이지
"""

import streamlit as st
from datetime import datetime
from backend.tools.news_search_tool import NewsSearchTool


# ─────────────────────────────────────────────
# util
# ─────────────────────────────────────────────
def format_date(pub_date: str) -> str:
    try:
        dt = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %z")
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return pub_date


# ─────────────────────────────────────────────
# main page
# ─────────────────────────────────────────────
def render_latestNews():
    st.markdown("## 📰 최신 노동법 뉴스")

    # ── 검색 UI ─────────────────────────────────────
    col1, col2 = st.columns([4, 1])

    with col1:
        query = st.text_input(
            "검색어",
            value="노동법 개정 시행",
            placeholder="예: 중대재해처벌법 판결, 최저임금 2026",
            label_visibility="collapsed",
        )

    with col2:
        search_clicked = st.button("🔍 검색", use_container_width=True)

    st.divider()

    # ── 초기 상태 ───────────────────────────────────
    if not search_clicked:
        st.caption("검색어를 입력하고 검색 버튼을 눌러주세요.")
        return

    if not query.strip():
        st.warning("검색어를 입력해주세요.")
        return

    query = query.strip()

    # ── Tool 실행 (빠른 뉴스 데이터) ────────────────
    tool = NewsSearchTool()

    with st.spinner("뉴스 검색 중..."):
        result = tool.run(query=query, display=10)

    if not result.success:
        st.error(f"검색 실패: {result.error}")
        return

    items = result.data.get("results", [])

    if not items:
        st.info("관련 기사를 찾지 못했습니다. 다른 검색어를 시도해보세요.")
        return

    # ─────────────────────────────────────────────
    # UX 핵심: 먼저 UI 자리 확보 (non-blocking 구조)
    # ─────────────────────────────────────────────
    ai_placeholder = st.empty()

    st.caption(f"'{query}' 검색 결과 {len(items)}건")

    # ── 뉴스 목록 먼저 렌더링 (즉시 표시) ─────────────
    for item in items:
        with st.container(border=True):
            st.markdown(f"**{item.get('title', '')}**")
            st.caption(format_date(item.get("pubDate", "")))
            st.write(item.get("description", ""))
            st.link_button("기사 보기 →", item.get("link", "#"))

    # ─────────────────────────────────────────────
    # AI 요약 (placeholder에 비동기로 채움)
    # ─────────────────────────────────────────────
    engine = st.session_state.get("news_engine")

    with ai_placeholder.container(border=True):
        st.markdown("#### 🤖 AI 요약")
        st.caption("검색된 기사들을 AI가 통합 분석합니다.")

        if engine is None:
            st.warning("AI 요약을 사용하려면 엔진이 초기화되어야 합니다.")
        else:
            with st.spinner("AI 분석 중... (10~20초 소요)"):
                try:
                    ai_result = engine.answer(query)

                    if ai_result.get("warning"):
                        st.warning(ai_result.get("answer", "요약 실패"))
                    else:
                        st.markdown(ai_result.get("answer", "요약 결과 없음"))


                except Exception as e:
                    st.error(f"AI 요약 실패: {e}")