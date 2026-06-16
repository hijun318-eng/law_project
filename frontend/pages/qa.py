"""
노동권리 진단 페이지
"""
import traceback
import streamlit as st

from frontend.pages.qa_data import FAQS


def _fallback_answer(question: str) -> str:
    """RAG 엔진 없을 때 기본 응답"""
    if "해고" in question:
        return (
            "**해고 관련 안내**\n\n"
            "사용자는 정당한 이유 없이 근로자를 해고할 수 없습니다(근로기준법 제23조).\n\n"
            "**주요 절차:**\n"
            "1. 해고 사유와 시기를 서면으로 통지해야 함 (근로기준법 제27조)\n"
            "2. 해고 예고: 즉시 해고 시 30일분 통상임금 지급 (근로기준법 제26조)\n"
            "3. 부당해고 구제: 해고일로부터 3개월 이내 노동위원회에 신청\n\n"
            "정확한 법률 판단은 노동위원회나 법률 전문가와 상담하세요."
        )
    elif "야근" in question or "연장" in question or "시간외" in question:
        return (
            "**야근(연장근로) 수당 안내**\n\n"
            "1주 40시간을 초과하는 연장근로에 대해 통상임금의 50%를 가산하여 지급해야 합니다(근로기준법 제56조).\n\n"
            "**야간근로(22:00~06:00)**: 통상임금의 50% 추가 가산\n"
            "**휴일근로**: 통상임금의 50% 가산 (8시간 초과 시 100%)\n\n"
            "※ 예: 시급 10,000원인 근로자가 2시간 연장근로 시\n"
            "  → 10,000원 × 1.5 × 2시간 = 30,000원"
        )
    elif "연차" in question:
        return (
            "**연차 휴가 안내**\n\n"
            "근로기준법 제60조에 따른 연차 유급휴가:\n\n"
            "| 근속기간 | 연차 일수 |\n"
            "|---------|----------|\n"
            "| 1년 미만 | 월 1일 (최대 11일) |\n"
            "| 1년 | 15일 |\n"
            "| 2년 | 15일 |\n"
            "| 3년 | 16일 |\n"
            "| 4년 이상 | 1년마다 1일 추가 (최대 25일) |\n\n"
            "사용하지 못한 연차는 연차수당으로 보상받을 수 있습니다."
        )
    elif "임금체불" in question or "체불" in question:
        return (
            "**임금체불 시 대처 방법**\n\n"
            "임금은 매월 1회 이상 정기적으로 지급해야 합니다(근로기준법 제43조, 제36조).\n\n"
            "**대처 절차:**\n"
            "1. 사업주에게 임금 지급 요청 (문자·메일 등 기록 남길 것)\n"
            "2. 관할 고용노동청에 진정 제기 (☎ 1350)\n"
            "3. 근로감독관 조사 → 시정 지시\n"
            "4. 그래도 해결 안 되면 민사소송 또는 법률구조공단 상담(☎ 132)\n\n"
            "임금채권 소멸시효는 **3년**이므로 빠른 신고가 중요합니다."
        )
    else:
        return (
            "**법률 상담 안내**\n\n"
            "질문해주신 내용에 대해 정확한 답변을 제공하기 위해 "
            "보다 구체적인 정보가 필요합니다.\n\n"
            "**참고할 수 있는 상담처:**\n"
            "- 고용노동부 상담센터: ☎ 1350\n"
            "- 대한법률구조공단: ☎ 132\n"
            "- 노동위원회: www.nlrc.go.kr\n\n"
            "더 자세한 내용을 입력해주시면 맞춤형 정보를 제공해드리겠습니다."
        )


def _render_source(src: dict, idx: int):
    """소스 문서 한 건을 Streamlit 마크다운으로 렌더링"""
    stype = src.get("type", "")
    if stype == "law":
        st.markdown(f"**{idx}. ⚖️ {src.get('law_name', '')} {src.get('article_no', '')}**")
        if src.get("article_title"):
            st.caption(f"📄 {src['article_title']}")
        if src.get("chapter_title"):
            st.caption(f"📂 {src['chapter_title']}")
    elif stype == "qna":
        st.markdown(f"**{idx}. 📖 {src.get('title', '')}**")
        if src.get("ref_no"):
            st.caption(f"📎 {src['ref_no']} ({src.get('ref_date', '')})")
    elif stype == "precedent":
        st.markdown(f"**{idx}. 📜 {src.get('case_no', '')}**")
        if src.get("category"):
            st.caption(f"📂 {src['category']}")
    else:
        st.markdown(f"**{idx}. {src.get('title', src.get('law_name', src.get('case_no', '문서')))}**")


def _qa_answer(question: str):
    """Q&A 질문 처리 (st.chat_message + st.empty 실시간 텍스트 스트리밍)"""
    if not question.strip():
        return

    # 1. user 메시지를 session_state에 먼저 저장하고 직접 렌더링
    st.session_state.qa_messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    progress_log = []
    answer = ""
    sources = []
    engine = st.session_state.get("engine")

    if engine is not None:
        try:
            with st.chat_message("assistant"):
                answer_placeholder = st.empty()
                status = st.status("🔍 법률 분석 진행 중...", expanded=True)

                for node_name, label, detail in engine.stream_answer(question):
                    if node_name == "done":
                        answer = detail.get("answer", "")
                        procedure = detail.get("procedure", "")
                        sources = detail.get("sources", [])

                        answer_placeholder.markdown(answer)

                        if procedure and procedure not in ("skip", "관련 판례를 찾을 수 없습니다."):
                            st.divider()
                            st.subheader("📋 대응 절차 안내")
                            st.markdown(procedure)
                        status.update(label="✅ 분석 완료", state="complete")
                        progress_log.append(
                            ("done", "✅ 분석 완료", f"답변 {len(answer)}자, 출처 {len(sources)}건")
                        )
                    else:
                        status.update(label=label, state="running")
                        if detail:
                            short = (detail[:80] + "...") if isinstance(detail, str) and len(detail) > 80 else detail
                            status.write(f"> {short}")
                        progress_log.append((node_name, label, detail if isinstance(detail, str) else ""))

        except Exception as e:
            traceback.print_exc()
            answer = f"⚠️ 오류가 발생했습니다: {str(e)}"
            sources = []
            st.error(f"RAG 엔진 오류: {e}")
    else:
        with st.chat_message("assistant"):
            answer = _fallback_answer(question)
            st.markdown(answer)

    st.session_state.qa_messages.append({
        "role": "assistant",
        "content": answer,
        "sources": sources,
        "progress": progress_log,
    })


def render_qa():
    st.markdown('<p class="main-header">💬 노동권리 진단</p>', unsafe_allow_html=True)
    st.markdown("근로기준법 및 노동관계법에 관한 질문에 AI가 답변합니다.")

    engine = st.session_state.get("engine")
    if engine is None:
        st.warning("⚠️ RAG 엔진이 연결되지 않아 기본 정보 기반으로 답변을 제공합니다. LM Studio 실행 후 재시작해주세요.")

    for msg in st.session_state.qa_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("progress"):
                with st.expander("📋 분석 진행 과정", expanded=True):
                    for node_name, label, detail in msg["progress"]:
                        st.markdown(f"**{label}**")
                        if isinstance(detail, str) and detail:
                            st.caption(detail[:300])
            if "sources" in msg and msg["sources"]:
                with st.expander(f"📚 근거 자료 ({len(msg['sources'])}개)", expanded=False):
                    for i, src in enumerate(msg["sources"], 1):
                        _render_source(src, i)
                        st.divider()

    if prompt := st.chat_input("법률 질문을 입력해주세요..."):
        _qa_answer(prompt)

    if not st.session_state.qa_messages:
        st.markdown("### 💡 자주 묻는 질문")
        cols = st.columns(2)
        for i, q in enumerate(FAQS):
            if cols[i % 2].button(q, use_container_width=True, key=f"faq_{i}"):
                _qa_answer(q)
