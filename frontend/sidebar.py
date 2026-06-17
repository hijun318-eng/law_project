"""
사이드바 렌더링
"""
import streamlit as st
from frontend.config import APP_NAME, APP_SUBTITLE, ENGINE_AVAILABLE
from frontend.theme import C_PRIMARY, C_ACCENT
from frontend.menu import PAGES


def render_sidebar():
    with st.sidebar:
        # 로고/타이틀
        st.markdown(
            f"<div style='text-align: center; padding: 1rem 0;'>"
            f"<div style='font-size: 2.5rem;'>⚖️</div>"
            f"<div style='font-size: 1.2rem; font-weight: 700; color: {C_PRIMARY};'>{APP_NAME}</div>"
            f"<div style='font-size: 0.75rem; color: #888;'>{APP_SUBTITLE}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

        st.divider()

        # ── 메뉴 그룹 ──
        current_page = st.session_state.get("page", "home")

        menu_groups = {}
        for page_id, info in PAGES.items():
            group = info["group"]
            if group not in menu_groups:
                menu_groups[group] = []
            menu_groups[group].append((page_id, info))

        for group_name, items in menu_groups.items():
            st.markdown(
                f"<div style='font-size: 0.7rem; color: #999; text-transform: uppercase; "
                f"letter-spacing: 0.5px; margin: 0.5rem 0;'>{group_name}</div>",
                unsafe_allow_html=True,
            )
            for page_id, info in items:
                active = current_page == page_id
                if st.button(
                    f"{info['icon']} {info['label']}",
                    key=f"menu_{page_id}",
                    use_container_width=True,
                    help=f"{info['label']} 페이지로 이동",
                ):
                    st.session_state.page = page_id
                    st.rerun()

        st.divider()

        # ── 시스템 상태 ──
        with st.expander("🔧 시스템 상태", expanded=False):
            if ENGINE_AVAILABLE:
                engine = st.session_state.get("engine")
                if engine is not None:
                    try:
                        health = engine.check_health()
                        st.markdown(f"🤖 LLM: {'✅ 연결됨' if health['llm_connected'] else '❌ 연결 안 됨'}")
                        st.markdown(f"📚 법령 DB: {health['document_count']}개 조문")
                    except Exception:
                        st.markdown("🤖 LLM: ❌ 상태 확인 불가")
                else:
                    st.markdown("🤖 LLM: ❌ 엔진 미초기화 (LM Studio 필요)")
            else:
                st.markdown("🤖 LLM: ⚠️ 모듈 미설치")
            st.markdown(f"🆔 세션: {st.session_state.get('session_id', '-')[:8]}...")

        # ── 푸터 ──
        st.divider()
        st.markdown(
            f"<div style='text-align: center; color: #bbb; font-size: 0.7rem; padding-bottom: 0.5rem;'>"
            f"본 서비스는 참고용이며 법적 효력이 없습니다."
            f"</div>",
            unsafe_allow_html=True,
        )
