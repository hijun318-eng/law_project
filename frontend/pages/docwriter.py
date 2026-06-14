"""
서류 작성 도우미 페이지
"""
from datetime import datetime
import streamlit as st


def _generate_draft(doc_type, name, phone, company, address, situation, detail, amount, mode):
    """서류 초안 생성"""
    today = datetime.now().strftime("%Y년 %m월 %d일")

    if mode == "easy":
        difficulty_note = "※ 본 문서는 참고용 초안이며 법적 효력이 없습니다. 발송 전 법률 전문가의 검토를 권장합니다."
    else:
        difficulty_note = "※ 본 문서는 법률 전문가의 검토를 받지 않은 초안입니다. 실제 제출 시 변호사의 자문을 구하시기 바랍니다."

    if "진정서" in doc_type:
        law_refs = {
            "임금체불": "근로기준법 제36조(임금지급), 제43조(임금지급 방법), 제109조(벌칙)",
            "부당해고": "근로기준법 제23조(해고 등의 제한), 제27조(해고사유 등의 서면통지)",
            "직장 내 괴롭힘": "근로기준법 제76조의2, 제76조의3",
            "산업재해": "산업재해보상보험법 제5조",
            "기타": "근로기준법 관련 조항",
        }
        law_ref = law_refs.get(situation, "근로기준법 관련 조항")

        draft = f"""# 진정서

## 1. 신청인
- **성명**: {name}
- **연락처**: {phone or "미기재"}

## 2. 피신청인
- **상호/성명**: {company}
- **주소**: {address or "미기재"}

## 3. 진정 취지
{situation}과 관련하여 피신청인이 다음과 같은 위반행위를 하였으므로,
관계 법령에 따라 시정조치를 요청합니다.

## 4. 사실 관계
{detail}

## 5. 관련 법령
{law_ref}

## 6. 첨부 자료
- [ ] 근로계약서 사본
- [ ] 급여 명세서
- [ ] 출퇴근 기록
- [ ] 기타 증빙 자료

## 7. 참고
- **관할**: 관할 지방고용노동청
- **신고처**: 고용노동부 상담센터 ☎ 1350
- **처리기한**: 접수일로부터 30일 이내 조치 통보

---

위와 같이 진정서를 제출합니다.

{today}
**신청인**: {name} (서명/인)

{difficulty_note}"""

    elif "고소장" in doc_type:
        draft = f"""# 고소장

## 1. 고소인
- **성명**: {name}
- **연락처**: {phone or "미기재"}

## 2. 피고소인
- **성명/상호**: {company}
- **주소**: {address or "미기재"}

## 3. 고소 사실
{situation}와 관련하여 아래와 같은 범죄 사실이 있으므로, 엄중한 수사와 처벌을 요청합니다.

## 4. 범죄 사실
{detail}

## 5. 증거 방법
- [ ] 관련 서류 일체
- [ ] 녹음 파일 (해당 시)
- [ ] 사진/영상 자료
- [ ] 목격자 연락처
- [ ] 진단서 (해당 시)

## 6. 형사처벌 조항
- **{situation}** 관련 법률 위반
- 소멸시효 확인 필요

---

위와 같이 고소장을 제출합니다.

{today}
**고소인**: {name} (서명/인)

{difficulty_note}"""

    else:  # 내용증명
        amount_line = f"3. 금 {amount}원을 ...까지 지급하십시오." if amount else ""
        draft = f"""# 내용증명

## 발신인
- **성명**: {name}
- **연락처**: {phone or "미기재"}
- **주소**: [주소 입력]

## 수신인
- **성명/상호**: {company}
- **주소**: {address or "미기재"}

## 제목: {situation} 관련 시정 요구 및 손해배상 청구의 건

## 1. 사실 관계
{detail}

## 2. 요구 사항
1. 위 사실과 관련된 법적 위반 사항을 시정하십시오.
2. 이로 인한 손해를 배상하십시오.
{amount_line}

## 3. 법적 근거
근로기준법 및 관련 노동관계법에 따라 위 요구를 이행하지 않을 경우,
관할 고용노동청 진정 및 민사소송 등 법적 조치를 취할 예정입니다.

## 4. 발송일
{today}

---

**{name}** (서명/인)

{difficulty_note}"""

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

    mode = st.session_state.get("mode", "easy")

    if st.button("초안 생성", use_container_width=True, type="primary"):
        if not name or not company or not detail:
            st.warning("⚠️ 신청인 이름, 상대방, 사건 내용은 필수입니다.")
        else:
            _generate_draft(doc_type, name, phone, company, address, situation, detail, amount, mode)
