"""
서류 작성 도우미 페이지
"""

from pathlib import Path
import json
import streamlit as st


FORMS_DIR = Path(__file__).resolve().parent.parent / "constants" / "forms"


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
