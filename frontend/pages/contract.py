"""
근로계약서 분석 페이지
"""
import streamlit as st


CLAUSE_DB = [
    {
        "pattern": "일방적 감봉",
        "keywords": ["감봉", "임금 삭감", "일방적", "회사 재량"],
        "danger": "위험",
        "explain_easy": "회사가 마음대로 월급을 깎을 수 있다는 조항은 법적으로 문제가 있어요. 근로기준법은 사용자가 임금을 마음대로 깎지 못하게 막고 있어요.",
        "explain_expert": "근로기준법 제43조(임금지급) 및 제95조(징계)에 따라 사용자는 정당한 사유 없이 임금을 삭감할 수 없습니다. 일방적 감봉 조항은 무효가 될 가능성이 높습니다.",
    },
    {
        "pattern": "포괄임금제",
        "keywords": ["포괄임금", "제반 수당", "연장수당 포함", "시간외수당 포함"],
        "danger": "주의",
        "explain_easy": "야근수당이나 휴일수당을 기본 월급에 이미 포함시켰다는 조항이에요. 법적으로 아예 효력이 없는 건 아니지만, 실제 계산했을 때 최저임금에 미달하면 무효예요.",
        "explain_expert": "포괄임금제는 근로기준법 제56조(연장·야간·휴일근로 가산)의 예외가 아닙니다. 대법원은 포괄임금제 계약이 유효하려면 '근로자에게 불이익이 없고' '합리적인 이유'가 있어야 한다고 판시했습니다(대법원 2012다20533).",
    },
    {
        "pattern": "경업금지 의무",
        "keywords": ["경업금지", "퇴직 후", "동종업계", "취업 제한"],
        "danger": "위험",
        "explain_easy": "퇴사 후에도 비슷한 업종에 취업하지 못하게 막는 조항이에요. 법적으로 인정받으려면 기간, 지역, 업종이 합리적으로 제한되어야 하고, 별도 보상이 있어야 해요.",
        "explain_expert": "대법원은 경업금지약정이 근로자의 직업선택의 자유를 침해할 경우 무효라고 판시했습니다. 합리적 범위(기간 1~2년, 지역 제한, 보상 수반)를 초과하면 부당합니다.",
    },
    {
        "pattern": "일방적 근무지 변경",
        "keywords": ["근무지 변경", "전근", "발령", "회사 사정"],
        "danger": "위험",
        "explain_easy": "회사가 마음대로 근무지를 바꿀 수 있다는 조항이에요. 법적으로는 인사권 범위 안에 있을 수 있지만, 생활근거지를 옮겨야 할 정도의 변경은 본인 동의가 필요해요.",
        "explain_expert": "전근발령이 부당한 인사권 남용인지 여부는 업무상 필요성과 근로자의 생활상 불이익을 비교형량하여 판단합니다(대법원 2005다342). 일방적 근무지 변경 조항은 권리남용 가능성이 있습니다.",
    },
    {
        "pattern": "위약금/위약벌",
        "keywords": ["위약금", "위약벌", "배상금", "중도 퇴사 시"],
        "danger": "위험",
        "explain_easy": "중간에 그만두면 돈을 내야 한다는 조항이에요. 근로기준법 제20조는 이런 위약금 조항을 명확히 금지하고 있어요. 무효인 조항이니 걱정 마세요.",
        "explain_expert": "근로기준법 제20조는 '사용자는 근로계약 불이행에 대한 위약금을 약정할 수 없다'고 명시합니다. 모든 위약금·위약벌 조항은 강행규정 위반으로 무효입니다.",
    },
    {
        "pattern": "퇴직금 중간정산 제한",
        "keywords": ["퇴직금 중간정산 불가", "퇴직금 지급 제한"],
        "danger": "주의",
        "explain_easy": "퇴직금을 중간에 받지 못하게 막는 조항이에요. 법적으로 퇴직금 중간정산은 주택 구입 등 일부 경우에만 가능해요. 조건이 안 되면 중간정산이 안 되는 게 맞아요.",
        "explain_expert": "근로자퇴직급여 보장법 제9조는 퇴직금 중간정산 사유를 제한적으로 열거합니다. 이 조항 자체가 불법은 아니지만, 법정 중간정산 사유가 발생했을 때도 제한한다면 무효입니다.",
    },
    {
        "pattern": "초과근무 수당 미지급",
        "keywords": ["초과근무 수당 포함", "무급", "추가 근무"],
        "danger": "위험",
        "explain_easy": "추가로 일해도 수당을 안 주겠다는 조항이에요. 근로기준법은 연장근로 시 반드시 추가 수당(50% 가산)을 주도록 하고 있어서 무효예요.",
        "explain_expert": "근로기준법 제56조(연장·야간·휴일근로)는 강행규정입니다. 초과근무 수당을 지급하지 않기로 하는 약정은 무효이며, 설사 근로자가 동의했다 하더라도 효력이 없습니다.",
    },
]


def render_contract():
    st.markdown('<p class="main-header">🔎 근로계약서 독소조항 분석</p>', unsafe_allow_html=True)
    st.markdown("근로계약서 내용을 입력하거나 붙여넣으면 불리한 조항(독소조항)을 분석하여 설명해드립니다.")

    mode = st.session_state.get("mode", "easy")

    tab1, tab2 = st.tabs(["📄 계약서 분석", "📚 독소조항 사전"])

    with tab1:
        with st.container(border=True):
            contract_text = st.text_area(
                "근로계약서 내용을 입력하세요",
                placeholder="근로계약서 조항들을 복사하여 붙여넣으세요.\n\n예:\n- 제1조(근무시간) 1일 8시간, 1주 40시간으로 한다.\n- 제2조(임금) 제반 수당을 포함하여 월 250만원으로 한다.\n- 제3조(전근) 회사는 업무상 필요 시 근무지를 변경할 수 있다.",
                height=250,
            )

            if st.button("분석 시작", use_container_width=True, type="primary") and contract_text:
                st.divider()
                st.markdown("### 분석 결과")
                found_issues = []
                for clause in CLAUSE_DB:
                    for kw in clause["keywords"]:
                        if kw in contract_text:
                            found_issues.append(clause)
                            break

                if found_issues:
                    for issue in found_issues:
                        with st.container(border=True):
                            st.markdown(f"#### {issue['pattern']}  🟠{issue['danger']}")
                            if mode == "easy":
                                st.markdown(f"**📌 설명:** {issue['explain_easy']}")
                            else:
                                st.markdown(f"**📌 법적 분석:** {issue['explain_expert']}")
                else:
                    st.success("✅ 입력된 내용에서 일반적인 독소조항이 발견되지 않았습니다. 다만, 전문가의 추가 검토를 권장합니다.")

                st.divider()
                st.info("💡 **면책 안내**: 이 분석은 참고용이며 법적 효력이 없습니다. 중요한 계약은 반드시 법률 전문가의 검토를 받으세요.")

        with st.container(border=True):
            st.markdown("#### ✅ 계약서 체크리스트")
            checkboxes = [
                "근로계약서를 서면(종이 또는 전자문서)으로 작성했는가?",
                "임금(급여), 근무시간, 휴게시간이 명시되어 있는가?",
                "연차휴가, 주휴일, 공휴일에 관한 규정이 있는가?",
                "퇴직금, 퇴사 절차에 관한 규정이 있는가?",
                "야간·연장·휴일근로 수당에 대한 규정이 있는가?",
            ]
            for cb in checkboxes:
                st.checkbox(cb, key=f"chk_{hash(cb)}")

    with tab2:
        st.markdown("### 📚 독소조항 사전")
        st.markdown("근로계약서에서 흔히 발견되는 불리한 조항들을 정리했습니다.")

        for clause in CLAUSE_DB:
            with st.expander(f"{clause['pattern']} ({clause['danger']})"):
                if mode == "easy":
                    st.markdown(clause["explain_easy"])
                else:
                    st.markdown(clause["explain_expert"])
