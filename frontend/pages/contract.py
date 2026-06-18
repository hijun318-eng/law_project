"""
근로계약서 분석 페이지
"""
import tempfile
from pathlib import Path

import streamlit as st

from backend.ocr_contract.pipeline import analyze_contract
from backend.ocr_contract.rules.validators.contract_gate import NotAContractError
from frontend.theme import load_css


# ── 헬퍼 ─────────────────────────────────────────────────────────────────────

def _save_upload(uploaded_file) -> str:
    """업로드 파일을 임시 경로에 저장하고 경로를 반환한다."""
    suffix = Path(uploaded_file.name).suffix or ".jpg"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
        f.write(uploaded_file.getbuffer())
        return f.name


def _render_field_table(fields: dict) -> None:
    rows = ""
    for name, value in fields.items():
        if value and str(value).strip() not in ("null", ""):
            val_html = f'<span class="field-value">{value}</span>'
        else:
            val_html = '<span class="field-empty">미기재</span>'
        rows += f"""
        <div class="field-row">
            <span class="field-name">{name}</span>
            {val_html}
        </div>"""
    st.markdown(f'<div class="result-card">{rows}</div>', unsafe_allow_html=True)


def _render_missing(missing: dict) -> None:
    if not missing:
        st.markdown(
            '<div class="result-card pass">✅ 모든 필수기재사항이 기재되어 있습니다.</div>',
            unsafe_allow_html=True,
        )
        return

    for field, law_ref in missing.items():
        st.markdown(
            f"""<div class="result-card fail">
                <span class="badge badge-red">누락</span>&nbsp;
                <strong>{field}</strong>
                <div style="margin-top:6px;font-size:13px;color:#64748B;">{law_ref}</div>
            </div>""",
            unsafe_allow_html=True,
        )


def _render_violations(violations: list, warnings: list) -> None:
    if not violations and not warnings:
        st.markdown(
            '<div class="result-card pass">✅ 검출된 법정기준 위반이 없습니다.</div>',
            unsafe_allow_html=True,
        )
        return

    for item in violations:
        st.markdown(
            f"""<div class="result-card fail">
                <span class="badge badge-red">위반</span>&nbsp;
                <strong>{item['field']}</strong>
                <span style="font-size:12px;color:#94A3B8;margin-left:6px;">{item['type']}</span>
                <div style="margin-top:8px;font-size:14px;color:#1E293B;">{item['detail']}</div>
                <div style="margin-top:4px;font-size:12px;color:#94A3B8;">근거: {item['law_ref']}</div>
            </div>""",
            unsafe_allow_html=True,
        )

    for w in warnings:
        st.markdown(
            f"""<div class="result-card warn">
                <span class="badge badge-yellow">확인 필요</span>&nbsp;
                <strong>{w['field']}</strong>
                <span style="font-size:12px;color:#94A3B8;margin-left:6px;">{w['type']}</span>
                <div style="margin-top:8px;font-size:14px;color:#1E293B;">{w['detail']}</div>
            </div>""",
            unsafe_allow_html=True,
        )


def _render_summary(summary: str, is_valid: bool) -> None:
    if is_valid:
        bg, border, icon = "#F0FDF4", "#86EFAC", "✅"
    else:
        bg, border, icon = "#FFF1F2", "#FCA5A5", "❌"

    st.markdown(
        f"""<div style="background:{bg};border:1px solid {border};border-radius:12px;
                        padding:16px 20px;margin-top:8px;font-size:15px;font-weight:600;">
            {icon}&nbsp; {summary}
        </div>""",
        unsafe_allow_html=True,
    )

# ── 메인 렌더 함수 ────────────────────────────────────────────────────────────

def render_contract():
    load_css()
    st.markdown('<p class="main-header">🔎 근로계약서 분석</p>', unsafe_allow_html=True)
    st.markdown(
        "근로 계약서 사진을 업로드하면 필수기재사항 누락과 법정기준 위반 여부를 분석합니다.",
    )

    st.divider()

    uploaded = st.file_uploader(
        "근로 계약서 이미지 업로드",
        type=["jpg", "jpeg", "png"],
        help="JPG 또는 PNG 파일을 업로드하세요.",
        label_visibility="collapsed",
    )

    if uploaded is None:
        return

    # 업로드된 이미지 미리보기
    col_img, col_info = st.columns([1, 1], gap="large")
    with col_img:
        st.image(uploaded, caption="업로드된 이미지", use_container_width=True)

    with col_info:
        st.markdown("#### 분석 준비")
        st.markdown(f"- **파일명**: {uploaded.name}")
        st.markdown(f"- **크기**: {uploaded.size / 1024:.1f} KB")
        analyze_btn = st.button("🔍 분석 시작", type="primary", use_container_width=True)

    if not analyze_btn:
        return

    # ── 분석 실행 ─────────────────────────────────────────────────────────────
    image_path = _save_upload(uploaded)

    with st.spinner("분석 중입니다. 잠시 기다려주세요..."):
        try:
            result = analyze_contract(image_path)

        except NotAContractError as e:
            st.error("업로드된 파일이 근로계약서가 아닙니다. 다시 업로드해주세요.")
            with st.expander("상세 사유 보기"):
                st.markdown(f"**검증 단계**: {e.gate} 게이트")
                st.markdown(f"**사유**: {e.reason}")
            return

        except Exception as e:
            st.error(f"분석 중 오류가 발생했습니다: {e}")
            return

    # ── 결과 출력 ─────────────────────────────────────────────────────────────
    v = result["validation"]
    st.divider()

    # 요약 배너
    # _render_summary(result["summary"], v["is_valid"])

    # 탭 제목 — 이모지 제거 (Streamlit 이모지 파싱 오류 방지)
    missing_count   = len(v["missing"])
    violation_count = len(v["violations"])
    tab_label_missing    = "필수기재사항" if missing_count == 0   else f"필수기재사항 ❌ {missing_count}건 누락"
    tab_label_violations = "법정기준"    if violation_count == 0 else f"법정기준 ❌ {violation_count}건 위반"

    tab_fields, tab_missing, tab_violations = st.tabs([
        "계약 정보",
        tab_label_missing,
        tab_label_violations,
    ])

    with tab_fields:
        st.markdown('<div class="section-title">추출된 계약 정보</div>', unsafe_allow_html=True)
        _render_field_table(result["fields"])

    with tab_missing:
        st.markdown('<div class="section-title">필수기재사항 (근로기준법 제17조)</div>', unsafe_allow_html=True)
        _render_missing(v["missing"])

    with tab_violations:
        st.markdown('<div class="section-title">법정기준 위반 검사</div>', unsafe_allow_html=True)
        _render_violations(v["violations"], v["warnings"])