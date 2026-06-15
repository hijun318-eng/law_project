"""
서류 작성 도우미 페이지
"""

from pathlib import Path
import json
import sys
import io
import streamlit as st



FORMS_DIR = Path(__file__).resolve().parent.parent / "constants" / "forms"


def _get_field_value(form_id: str, section: dict, field: dict) -> str:
    section_id = section.get("id", "")
    field_key = field.get("key", "")
    widget_key = _widget_key(form_id, section_id, field_key)
    value = st.session_state.get(widget_key)

    if value is None:
        return ""

    field_type = field.get("type")
    if field_type == "file":
        if isinstance(value, list):
            return ", ".join([getattr(v, "name", "") for v in value if v is not None and getattr(v, "name", None)])
        return getattr(value, "name", "")

    if value == "" or value == []:
        return ""
    return str(value)


def _build_html_document(form_name: str, sections: list[dict], form_id: str) -> str:
    # 문서처럼 보이도록 섹션 구분 + 표형식(label/value) 출력
    def esc(x: str) -> str:
        return (
            x.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;")
        )

    form_name_escaped = esc(form_name or "")

    section_blocks = []
    for section in sections:
        section_title = section.get("title") or section.get("id") or ""
        section_title_escaped = esc(str(section_title))

        rows = []
        for field in section.get("fields") or []:
            label = field.get("label") or field.get("key") or ""
            label_escaped = esc(str(label))
            val = _get_field_value(form_id, section, field)
            val_escaped = esc(val if val is not None else "")
            rows.append(
                "<tr>"
                f"<th>{label_escaped}</th>"
                f"<td>{val_escaped}</td>"
                "</tr>"
            )

        table_html = (
            "<table>" + "".join(rows) + "</table>" if rows else "<div class='empty'>항목이 없습니다.</div>"
        )
        section_blocks.append(
            "<div class='section'>"
            f"<div class='section-title'>{section_title_escaped}</div>"
            f"{table_html}"
            "</div>"
        )

    sections_html = "".join(section_blocks)

    return f"""
 <!doctype html>
 <html lang='ko'>
 <head>
   <meta charset='utf-8'/>
   <style>
     @page {{ size: A4; margin: 18mm; }}
     body {{ font-family: 'Malgun Gothic','Gulim','Noto Sans KR',sans-serif; color:#000; font-size: 13px; }}
     .doc-title {{ font-size: 19px; font-weight: 700; margin-bottom: 18px; }}
     .section {{ margin: 22px 0 12px; page-break-inside: avoid; }}
     .section-title {{ font-size: 15px; font-weight: 700; border: 1px solid #222; padding: 10px 12px; background: #f6f6f6; }}
     table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
     th, td {{ border: 1px solid #444; padding: 10px 12px; vertical-align: top; }}
     th {{ width: 30%; background: #fafafa; text-align: left; }}
     td {{ width: 70%; white-space: pre-wrap; word-break: break-word; }}
     .empty {{ border: 1px dashed #888; padding: 14px; margin-top: 10px; }}
   </style>
 </head>
 <body>
   <div class='doc-title'>{form_name_escaped}</div>
   {sections_html}
 </body>
 </html>
 """


def _make_pdf_bytes_from_html(html: str) -> bytes:
    # Playwright(Chromium)으로 HTML -> PDF
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html, wait_until="networkidle")
        pdf_bytes = page.pdf(format="A4", print_background=True)
        browser.close()

    return pdf_bytes


def _find_kr_font_path() -> str | None:
    candidates = [
        r"C:\Windows\Fonts\malgun.ttf",
        r"C:\Windows\Fonts\malgunbd.ttf",
        r"C:\Windows\Fonts\gulim.ttc",
        r"C:\Windows\Fonts\gulimche.ttc",
        r"C:\Windows\Fonts\batang.ttc",
        r"C:\Windows\Fonts\batangche.ttc",
    ]
    for p in candidates:
        try:
            if Path(p).exists():
                return p
        except Exception:
            continue
    return None


def _wrap_text(s: str, max_chars: int = 35) -> list[str]:
    if not s:
        return []
    out = []
    cur = s
    while len(cur) > max_chars:
        out.append(cur[:max_chars])
        cur = cur[max_chars:]
    if cur:
        out.append(cur)
    return out


def _make_pil_pdf_bytes(form_name: str, sections: list[dict], form_id: str) -> bytes:
    # HTML->PDF가 불가능한 환경(Playwright subprocess 미지원 등)에서 사용할 fallback.
    # PIL로 문서형(섹션 헤더 + 표형 label/value) 이미지를 만들고, PDF로 저장.
    from PIL import Image, ImageDraw, ImageFont

    font_path = _find_kr_font_path()
    title_font = ImageFont.truetype(font_path, 24) if font_path else ImageFont.load_default()
    section_font = ImageFont.truetype(font_path, 18) if font_path else ImageFont.load_default()
    label_font = ImageFont.truetype(font_path, 14) if font_path else ImageFont.load_default()
    value_font = ImageFont.truetype(font_path, 14) if font_path else ImageFont.load_default()

    # A4 @ 150dpi
    dpi = 150
    width, height = int(595 * dpi / 72), int(842 * dpi / 72)
    margin = 40
    x0 = margin
    y = margin

    pages = []
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    def new_page():
        nonlocal img, draw, y
        pages.append(img)
        img = Image.new("RGB", (width, height), "white")
        draw = ImageDraw.Draw(img)
        y = margin

    # Form title
    y += 2
    draw.text((x0, y), form_name, fill="black", font=title_font)
    y += 30

    col1_w = int((width - 2 * margin) * 0.28)
    col2_w = (width - 2 * margin) - col1_w
    row_h = 34

    # Render each section
    for section in sections:
        section_title = str(section.get("title") or section.get("id") or "")

        # Table header (항목/값 헤더 제거 + 해당 위치에 title 표시)
        if y + row_h > height - margin:
            new_page()
        draw.rectangle([x0, y, x0 + col1_w + col2_w, y + row_h], outline="black", width=1, fill="#f6f6f6")
        draw.text((x0 + 10, y + 7), section_title, fill="black", font=section_font)
        y += row_h

        # Table rows
        for field in section.get("fields") or []:
            label = str(field.get("label") or field.get("key") or "")
            value = _get_field_value(form_id, section, field)
            if not value:
                continue

            # wrap label/value
            label_lines = _wrap_text(label, 18)
            value_lines = _wrap_text(value, 32)
            row_lines = max(len(label_lines), len(value_lines), 1)
            cur_row_h = 22 + (row_lines - 1) * 18

            if y + cur_row_h > height - margin:
                new_page()
                # re-draw section title header after page break
                if y + row_h > height - margin:
                    new_page()
                draw.rectangle([x0, y, x0 + col1_w + col2_w, y + row_h], outline="black", width=1, fill="#f6f6f6")
                draw.text((x0 + 10, y + 7), section_title, fill="black", font=section_font)
                y += row_h

            # cells
            draw.rectangle([x0, y, x0 + col1_w, y + cur_row_h], outline="black", width=1)
            draw.rectangle([x0 + col1_w, y, x0 + col1_w + col2_w, y + cur_row_h], outline="black", width=1)

            # text positions
            label_y = y + 6
            for ln in label_lines:
                draw.text((x0 + 10, label_y), ln, fill="black", font=label_font)
                label_y += 18
            value_y = y + 6
            for vn in value_lines:
                draw.text((x0 + col1_w + 10, value_y), vn, fill="black", font=value_font)
                value_y += 18

            y += cur_row_h

        # 섹션 사이 여백
        y += 12

    pages.append(img)
    if len(pages) == 1:
        # Single page
        buf = io.BytesIO()
        pages[0].save(buf, format="PDF")
        return buf.getvalue()

    buf = io.BytesIO()
    pages[0].save(buf, format="PDF", save_all=True, append_images=pages[1:])
    return buf.getvalue()


@st.cache_data
def load_forms():
    forms = []
    if not FORMS_DIR.exists():
        return [], f"서식 디렉토리를 찾을 수 없습니다: {FORMS_DIR}"

    errors = []
    for p in sorted(FORMS_DIR.glob("*.json")):
        try:
            with open(p, "r", encoding="utf-8") as f:
                forms.append(json.load(f))
        except Exception as e:
            errors.append(f"{p.name}: {e}")

    return forms, (errors or None)


def _widget_key(form_id: str, section_id: str, field_key: str) -> str:
    return f"{form_id}__{section_id}__{field_key}"


def _clear_form_inputs(prev_form_id: str) -> None:
    prefix = f"{prev_form_id}__"
    for k in list(st.session_state.keys()):
        if str(k).startswith(prefix):
            del st.session_state[k]


def _render_field(form_id: str, section: dict, field: dict) -> None:
    section_id = section.get("id", "")
    field_key = field.get("key", "")
    key = _widget_key(form_id, section_id, field_key)

    label = field.get("label") or field_key
    field_type = field.get("type")

    if field_type == "text":
        st.text_input(label, key=key)
    elif field_type == "textarea":
        rows = field.get("rows")
        height = 150
        if isinstance(rows, (int, float)):
            height = max(80, min(420, int(rows) * 20))
        st.text_area(label, key=key, height=height)
    elif field_type == "radio":
        options = field.get("options") or []
        if len(options) >= 5:
            st.selectbox(label, options, key=key)
        else:
            st.radio(label, options, key=key)
    elif field_type in ("number", "currency"):
        st.number_input(label, key=key, step=1)
    elif field_type == "date":
        st.date_input(label, key=key)
    elif field_type == "file":
        st.file_uploader(
            label,
            key=key,
            accept_multiple_files=bool(field.get("multiple", False)),
        )
    else:
        st.text_input(label, key=key)


def render_docwriter():
    st.markdown('<p class="main-header">📝 서류 작성 도우미</p>', unsafe_allow_html=True)
    st.markdown("아래에서 서류 유형과 필수 항목을 입력합니다. (초안 생성 기능은 제외됨)")

    forms, load_error = load_forms()
    if not forms:
        st.error("서식 데이터를 불러오지 못했습니다.")
        if load_error:
            st.write(load_error)
        return

    form_names = [f.get("form_name") for f in forms if f.get("form_name")]
    if not form_names:
        st.error("form_name을 찾을 수 없습니다.")
        return

    form_by_name = {f.get("form_name"): f for f in forms}

    selected_name = st.selectbox("서류 유형 선택", form_names)
    selected_form = form_by_name[selected_name]
    form_id = selected_form.get("form_id")
    sections = selected_form.get("sections") or []

    if "current_form_id" not in st.session_state:
        st.session_state.current_form_id = form_id

    if st.session_state.current_form_id != form_id:
        _clear_form_inputs(st.session_state.current_form_id)
        st.session_state.current_form_id = form_id

    for section in sections:
        title = section.get("title") or ""
        st.markdown(f"### {title}")
        for field in section.get("fields") or []:
            _render_field(form_id, section, field)

    selected_form_name = selected_name or ""
    html_doc = _build_html_document(selected_form_name, sections, form_id)

    st.markdown("---")
    if st.button("📄 PDF로 다운로드", use_container_width=True, type="primary"):
        try:
            try:
                pdf_bytes = _make_pdf_bytes_from_html(html_doc)
            except NotImplementedError:
                pdf_bytes = _make_pil_pdf_bytes(selected_form_name, sections, form_id)
            st.session_state.docwriter_pdf_bytes = pdf_bytes
            st.session_state.docwriter_pdf_filename = (
                f"{selected_form_name}.pdf".replace("/", "_").replace("\\", "_")
            )
        except Exception as e:
            st.error(f"PDF 생성에 실패했습니다: {e}")

    if "docwriter_pdf_bytes" in st.session_state:
        st.download_button(
            label="📥 PDF 파일 다운로드",
            data=st.session_state.docwriter_pdf_bytes,
            file_name=st.session_state.get("docwriter_pdf_filename", "form.pdf"),
            mime="application/pdf",
            use_container_width=True,
        )
