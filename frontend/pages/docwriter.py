"""
서류 작성 도우미 페이지
"""
from datetime import datetime
import streamlit as st

from frontend.pages.docwriter_data import (
    TEMPLATE_COMPLAINT,
    TEMPLATE_CRIMINAL,
    TEMPLATE_CERTIFIED,
    LAW_REFS,
)


def _generate_draft(doc_type, name, phone, company, address, situation, detail, amount):
    """서류 초안 생성"""
    today = datetime.now().strftime("%Y년 %m월 %d일")
    difficulty_note = "※ 본 문서는 참고용 초안이며 법적 효력이 없습니다. 발송 전 법률 전문가의 검토를 권장합니다."

    # 공통 치환 변수
    subs = {
        "name": name or "미기재",
        "phone": phone or "미기재",
        "company": company or "미기재",
        "address": address or "미기재",
        "situation": situation,
        "detail": detail,
        "today": today,
        "difficulty_note": difficulty_note,
    }

    if "진정서" in doc_type:
        subs["law_ref"] = LAW_REFS.get(situation, "근로기준법 관련 조항")
        draft = TEMPLATE_COMPLAINT.substitute(**subs)

    elif "고소장" in doc_type:
        draft = TEMPLATE_CRIMINAL.substitute(**subs)

    else:  # 내용증명
        subs["amount_line"] = f"3. 금 {amount}원을 ...까지 지급하십시오." if amount else ""
        draft = TEMPLATE_CERTIFIED.substitute(**subs)

    with st.container(border=True):
        st.markdown("### 📄 생성된 초안")
        st.text_area("", draft, height=400, key="draft_output")
        st.download_button(
            label="📥 텍스트 파일로 다운로드",
            data=draft.encode("utf-8"),
            file_name=f"{situation}_{doc_type.split()[0]}_{today.replace(' ', '_')}.txt",
            mime="text/plain",
            use_container_width=True,
        )


def render_docwriter():
    st.markdown('<p class="main-header">📝 서류 작성 도우미</p>', unsafe_allow_html=True)
    st.markdown("법적 분쟁 시 필요한 서류의 초안을 작성합니다. 아래 정보를 입력해주세요.")

    doc_type = st.selectbox(
        "서류 유형 선택",
        ["진정서 (고용노동청)", "고소장 (경찰청)", "내용증명 (법무법인/등기)"],
    )

    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("신청인 이름", placeholder="홍길동")
            phone = st.text_input("연락처", placeholder="010-1234-5678")
        with col2:
            company = st.text_input("상대방 (회사명/개인)", placeholder="(주)회사명")
            address = st.text_input("상대방 주소", placeholder="서울시 강남구...")

    with st.container(border=True):
        st.markdown("**사건 내용**")
        situation = st.selectbox(
            "상황 유형",
            ["임금체불", "부당해고", "직장 내 괴롭힘", "산업재해", "기타"],
        )
        detail = st.text_area(
            "상세 내용",
            placeholder="발생 일시, 장소, 구체적인 사실 관계를 상세히 입력해주세요.",
            height=150,
        )
        amount = st.text_input("청구 금액 (해당 시)", placeholder="예: 5,000,000원")

    if st.button("초안 생성", use_container_width=True, type="primary"):
        if not name or not company or not detail:
            st.warning("⚠️ 신청인 이름, 상대방, 사건 내용은 필수입니다.")
        else:
            _generate_draft(doc_type, name, phone, company, address, situation, detail, amount)
