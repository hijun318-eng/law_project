"""
근로계약서 분석 페이지
"""
import streamlit as st

from frontend.pages.contract_data import CLAUSE_DB


def render_contract():
    st.markdown('<p class="main-header">🔎 근로계약서 독소조항 분석</p>', unsafe_allow_html=True)
    st.markdown("근로계약서 내용을 입력하거나 붙여넣으면 불리한 조항(독소조항)을 분석하여 설명해드립니다.")

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
                            st.markdown(f"**📌 설명:** {issue['explain']}")
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
                st.markdown(clause["explain"])
