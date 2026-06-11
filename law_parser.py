"""
law_parser.py
pdfplumber/pdfminer 없이 subprocess로 pdftotext(poppler)를 호출해
국가법령정보센터 PDF를 조문(제X조) 단위로 분리한다.

설치 필요:
  macOS  → brew install poppler
  Ubuntu → sudo apt install poppler-utils

주요 함수:
  parse_law_pdf(pdf_path)         : PDF 1개 → Document 리스트
  parse_law_directory(dir)        : 폴더 내 PDF 전체 → Document 리스트
  process_all_pdfs(input, output) : PDF → JSON 저장 (data/process/law)
  process_all_mds(input, output)  : MD  → JSON 저장 (data/process/판례)
"""

import json
import re
import subprocess
from pathlib import Path
from typing import Optional

from langchain_core.documents import Document


# ── 정규식 ────────────────────────────────────────────────

RE_ARTICLE = re.compile(r'^(제(\d+)조(?:의\d+)?)\s*\((.+?)\)')
RE_CHAPTER = re.compile(r'^(제\d+장)\s+(.+)')
RE_SECTION = re.compile(r'^(제\d+절)\s+(.+)')
RE_ADDENDA = re.compile(r'^부칙\s*(?:<.+?>)?')
RE_NOISE   = re.compile(
    r'^(법제처|국가법령정보센터|www\.law\.go\.kr'
    r'|\d{1,3}$'
    r'|\[시행\s+\d{4}'
    r'|고용노동부|과학기술정보통신부|보건복지부'
    r'|환경부|국토교통부|법무부|행정안전부|기획재정부'
    r'|산업통상자원부|교육부|문화체육관광부)'
)


# ── 텍스트 추출 ───────────────────────────────────────────

import fitz


def _pdf_to_text(pdf_path: str) -> str:
    """
    Windows / Mac / Linux 공통

    PyMuPDF(fitz) 기반 PDF 텍스트 추출
    """

    try:

        doc = fitz.open(pdf_path)

        pages = []

        for page in doc:

            text = page.get_text("text")

            if text:
                pages.append(text)

        doc.close()

        return "\x0c".join(pages)

    except Exception as e:

        raise RuntimeError(
            f"PDF 읽기 실패 ({pdf_path}) : {e}"
        )


def _split_pages(raw: str) -> list[tuple[int, str]]:
    """페이지 구분자(\x0c)로 분리 → [(page_num, text), ...]"""
    return [(i + 1, p) for i, p in enumerate(raw.split("\x0c")) if p.strip()]


# ── 노이즈 제거 ───────────────────────────────────────────

def _clean_line(line: str) -> Optional[str]:
    s = line.strip()
    if not s:
        return None
    if re.match(r'^\d{1,3}$', s):
        return None
    if RE_NOISE.match(s):
        return None
    return s


# ── 메타 추출 ─────────────────────────────────────────────

def _extract_meta(raw: str, pdf_stem: str) -> dict:
    enacted_m = re.search(r'\[시행\s+([\d. ]+)\]', raw[:400])
    enacted   = enacted_m.group(1).strip() if enacted_m else ""

    abbr_m = re.search(r'약칭[:\s：]+([^\s\)\]]{2,20})', raw[:400])
    if abbr_m:
        law_name = abbr_m.group(1).strip()
    else:
        law_name = pdf_stem
        for line in raw.split('\n')[:15]:
            s = line.strip()
            if len(s) > 8 and '법' in s and not s.startswith('['):
                law_name = s
                break

    return {"enacted": enacted, "law_name": law_name}


# ── 조문 분리 ─────────────────────────────────────────────

def _split_articles(pages: list[tuple[int, str]]) -> list[dict]:
    articles: list[dict] = []
    current: Optional[dict] = None
    cur_chapter = ""
    cur_section = ""

    for page_num, text in pages:
        for raw_line in text.split('\n'):
            line = _clean_line(raw_line)
            if not line:
                continue

            m = RE_CHAPTER.match(line)
            if m:
                cur_chapter = m.group(1) + " " + m.group(2)
                continue

            m = RE_SECTION.match(line)
            if m:
                cur_section = m.group(1) + " " + m.group(2)
                continue

            if RE_ADDENDA.match(line):
                if current:
                    articles.append(current)
                current = {
                    "article_no": "부칙", "article_title": line,
                    "article_full": line, "content": "",
                    "page": page_num, "chapter": cur_chapter, "section": cur_section,
                }
                continue

            m = RE_ARTICLE.match(line)
            if m:
                if current:
                    articles.append(current)
                article_no    = m.group(1)
                article_title = m.group(3)
                current = {
                    "article_no": article_no,
                    "article_title": article_title,
                    "article_full": f"{article_no} ({article_title})",
                    "content": line,
                    "page": page_num,
                    "chapter": cur_chapter,
                    "section": cur_section,
                }
                continue

            if current is not None:
                prev = current["content"]
                if prev.endswith('-'):
                    current["content"] = prev[:-1] + line
                elif prev and prev[-1] not in (' ', '\n'):
                    current["content"] += line
                else:
                    current["content"] += '\n' + line

    if current:
        articles.append(current)

    return articles


# ── 공개 API ──────────────────────────────────────────────

def parse_law_pdf(pdf_path: str, law_name: Optional[str] = None) -> list[Document]:
    """법령 PDF 1개 → 조문 단위 Document 리스트."""
    pdf_path = str(pdf_path)
    raw      = _pdf_to_text(pdf_path)
    meta     = _extract_meta(raw, Path(pdf_path).stem)
    if law_name:
        meta["law_name"] = law_name

    pages    = _split_pages(raw)
    articles = _split_articles(pages)

    docs: list[Document] = []
    for art in articles:
        content = art["content"].strip()
        if not content:
            continue
        m = {
            "law_name":      meta["law_name"],
            "article_no":    art["article_no"],
            "article_title": art["article_title"],
            "article_full":  art["article_full"],
            "source_pdf":    Path(pdf_path).name,
            "page":          art["page"],
            "enacted":       meta["enacted"],
        }
        if art["chapter"]: m["chapter"] = art["chapter"]
        if art["section"]: m["section"] = art["section"]
        docs.append(Document(page_content=content, metadata=m))

    return docs


def parse_law_directory(law_dir: str, glob: str = "**/*.pdf") -> list[Document]:
    """폴더 내 모든 법령 PDF → 조문 단위 Document 리스트."""
    all_docs: list[Document] = []
    for pdf_file in sorted(Path(law_dir).glob(glob)):
        print(f"파싱 중: {pdf_file.name}")
        try:
            docs = parse_law_pdf(str(pdf_file))
            print(f"  → 조문 {len(docs)}개")
            all_docs.extend(docs)
        except Exception as e:
            print(f"  ⚠ 오류 ({pdf_file.name}): {e}")
    print(f"\n총 {len(all_docs)}개 조문 Document 생성 완료")
    return all_docs


# ── 전처리: PDF → JSON 저장 ───────────────────────────────

def process_all_pdfs(input_dir="./data", output_dir="./data/process"):
    """
    data/law/*.pdf → data/process/law/*.json 으로 조문 단위 변환 저장.
    이미 process 폴더 안에 있는 파일은 건너뜀.
    """
    input_dir  = Path(input_dir)
    output_dir = Path(output_dir)

    pdf_files = [p for p in input_dir.rglob("*.pdf") if "process" not in p.parts]
    print(f"총 {len(pdf_files)}개 PDF 발견")

    for pdf_file in pdf_files:
        print(f"처리 중: {pdf_file}")
        try:
            docs = parse_law_pdf(str(pdf_file))

            output_file = (
                output_dir
                / pdf_file.relative_to(input_dir).parent
                / f"{pdf_file.stem}.json"
            )
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(
                    [{"page_content": d.page_content, "metadata": d.metadata} for d in docs],
                    f, ensure_ascii=False, indent=2
                )
            print(f"  → 조문 {len(docs)}개 저장 ({output_file})")

        except Exception as e:
            print(f"  ⚠ 오류 ({pdf_file.name}): {e}")

    print("PDF 전처리 완료")


# ── 전처리: MD → JSON 저장 ────────────────────────────────

def process_all_mds(input_dir="./data", output_dir="./data/process"):
    """
    data/판례/*.md → data/process/판례/*.json 으로 변환 저장.
    metadata.source_file = 원본 파일명 (예: "2011다23149.md")
    """
    input_dir  = Path(input_dir)
    output_dir = Path(output_dir)

    md_files = [p for p in input_dir.rglob("*.md") if "process" not in p.parts]
    print(f"총 {len(md_files)}개 MD 발견")

    for md_file in md_files:
        print(f"처리 중: {md_file}")
        try:
            content = md_file.read_text(encoding="utf-8")

            output_file = (
                output_dir
                / md_file.relative_to(input_dir).parent
                / f"{md_file.stem}.json"
            )
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(
                    [{"page_content": content, "metadata": {"source_file": md_file.name}}],
                    f, ensure_ascii=False, indent=2
                )
            print(f"  → 저장 완료 ({output_file})")

        except Exception as e:
            print(f"  ⚠ 오류 ({md_file.name}): {e}")

    print("MD 전처리 완료")


import json
import re
import traceback

from pathlib import Path
from typing import Optional

import fitz

from langchain_core.documents import Document


# ============================================================
# 정규식
# ============================================================

RE_ARTICLE = re.compile(
    r"^(제\d+조(?:의\d+)?)\s*(?:\((.*?)\))?"
)

RE_CHAPTER = re.compile(
    r"^(제\d+장)\s+(.+)"
)

RE_SECTION = re.compile(
    r"^(제\d+절)\s+(.+)"
)

RE_ADDENDA = re.compile(
    r"^부칙\s*(?:<.+?>)?"
)

RE_NOISE = re.compile(
    r"^(법제처|국가법령정보센터|www\.law\.go\.kr"
    r"|\d{1,3}$"
    r"|\[시행\s+\d{4}"
    r"|고용노동부|과학기술정보통신부|보건복지부"
    r"|환경부|국토교통부|법무부|행정안전부|기획재정부"
    r"|산업통상자원부|교육부|문화체육관광부)"
)


# ============================================================
# PDF 텍스트 추출
# ============================================================

def _pdf_to_text(pdf_path: str) -> str:
    """
    Windows / Mac / Linux 공통

    PyMuPDF(fitz) 기반 PDF 텍스트 추출
    """

    try:

        doc = fitz.open(pdf_path)

        pages = []

        for page in doc:

            text = page.get_text("text")

            if text:
                pages.append(text)

        doc.close()

        return "\x0c".join(pages)

    except Exception as e:

        raise RuntimeError(
            f"PDF 읽기 실패 ({pdf_path}) : {e}"
        )


# ============================================================
# 페이지 분리
# ============================================================

def _split_pages(raw: str):

    return [
        (i + 1, page)
        for i, page in enumerate(raw.split("\x0c"))
        if page.strip()
    ]


# ============================================================
# 노이즈 제거
# ============================================================

def _clean_line(line: str):

    s = line.strip()

    if not s:
        return None

    if re.match(r"^\d{1,3}$", s):
        return None

    if RE_NOISE.match(s):
        return None

    return s


# ============================================================
# 메타 추출
# ============================================================

def _extract_meta(raw: str, pdf_stem: str):

    enacted_m = re.search(
        r"\[시행\s+([\d. ]+)\]",
        raw[:400]
    )

    enacted = (
        enacted_m.group(1).strip()
        if enacted_m
        else ""
    )

    abbr_m = re.search(
        r"약칭[:\s：]+([^\s\)\]]{2,20})",
        raw[:400]
    )

    if abbr_m:

        law_name = abbr_m.group(1).strip()

    else:

        law_name = pdf_stem

        for line in raw.split("\n")[:15]:

            s = line.strip()

            if (
                len(s) > 4
                and "법" in s
                and not s.startswith("[")
            ):
                law_name = s
                break

    return {
        "enacted": enacted,
        "law_name": law_name
    }


# ============================================================
# 조문 분리
# ============================================================

def _split_articles(pages):

    articles = []

    current = None

    cur_chapter = ""
    cur_section = ""

    for page_num, text in pages:

        for raw_line in text.split("\n"):

            line = _clean_line(raw_line)

            if not line:
                continue

            chapter_match = RE_CHAPTER.match(line)

            if chapter_match:

                cur_chapter = (
                    chapter_match.group(1)
                    + " "
                    + chapter_match.group(2)
                )

                continue

            section_match = RE_SECTION.match(line)

            if section_match:

                cur_section = (
                    section_match.group(1)
                    + " "
                    + section_match.group(2)
                )

                continue

            if RE_ADDENDA.match(line):

                if current:
                    articles.append(current)

                current = {
                    "article_no": "부칙",
                    "article_title": line,
                    "article_full": line,
                    "content": "",
                    "page": page_num,
                    "chapter": cur_chapter,
                    "section": cur_section,
                }

                continue

            article_match = RE_ARTICLE.match(line)

            if article_match:

                if current:
                    articles.append(current)

                article_no = article_match.group(1)

                article_title = (
                    article_match.group(2).strip()
                    if article_match.group(2)
                    else ""
                )

                current = {
                    "article_no": article_no,
                    "article_title": article_title,
                    "article_full": (
                        f"{article_no} ({article_title})"
                        if article_title
                        else article_no
                    ),
                    "content": line,
                    "page": page_num,
                    "chapter": cur_chapter,
                    "section": cur_section,
                }

                continue

            if current is not None:

                prev = current["content"]

                if prev.endswith("-"):

                    current["content"] = (
                        prev[:-1] + line
                    )

                else:

                    current["content"] += (
                        "\n" + line
                    )

    if current:
        articles.append(current)

    return articles


# ============================================================
# PDF 1개 → Document
# ============================================================

def parse_law_pdf(
    pdf_path: str,
    law_name: Optional[str] = None
):

    raw = _pdf_to_text(pdf_path)

    if not raw.strip():

        raise RuntimeError(
            f"텍스트 추출 실패: {pdf_path}"
        )

    meta = _extract_meta(
        raw,
        Path(pdf_path).stem
    )

    if law_name:
        meta["law_name"] = law_name

    pages = _split_pages(raw)

    articles = _split_articles(pages)

    docs = []

    for art in articles:

        content = art["content"].strip()

        if not content:
            continue

        metadata = {
            "law_name": meta["law_name"],
            "article_no": art["article_no"],
            "article_title": art["article_title"],
            "article_full": art["article_full"],
            "source_pdf": Path(pdf_path).name,
            "page": art["page"],
            "enacted": meta["enacted"],
        }

        if art["chapter"]:
            metadata["chapter"] = art["chapter"]

        if art["section"]:
            metadata["section"] = art["section"]

        docs.append(
            Document(
                page_content=content,
                metadata=metadata
            )
        )

    return docs


# ============================================================
# 전체 PDF → JSON
# ============================================================

def process_all_pdfs(
    input_dir="./data",
    output_dir="./data/process"
):

    input_dir = Path(input_dir)
    output_dir = Path(output_dir)

    pdf_files = [
        p
        for p in input_dir.rglob("*.pdf")
        if "process" not in p.parts
    ]

    print(f"총 {len(pdf_files)}개 PDF 발견")

    for pdf_file in pdf_files:

        print(f"\n처리 중: {pdf_file}")

        try:

            docs = parse_law_pdf(
                str(pdf_file)
            )

            output_file = (
                output_dir
                / pdf_file.relative_to(input_dir).parent
                / f"{pdf_file.stem}.json"
            )

            output_file.parent.mkdir(
                parents=True,
                exist_ok=True
            )

            with open(
                output_file,
                "w",
                encoding="utf-8"
            ) as f:

                json.dump(
                    [
                        {
                            "page_content": d.page_content,
                            "metadata": d.metadata,
                        }
                        for d in docs
                    ],
                    f,
                    ensure_ascii=False,
                    indent=2,
                )

            print(
                f"조문 {len(docs)}개 저장 완료"
            )

        except Exception as e:

            print(
                f"⚠ 오류 ({pdf_file.name})"
            )

            print(type(e).__name__)
            print(str(e))

            traceback.print_exc()

    print("\nPDF 전처리 완료")



# ── 단독 실행 ─────────────────────────────────────────────

if __name__ == "__main__":
    # PDF → data/process/law/*.json
    process_all_pdfs(input_dir="./data", output_dir="./data/process")
    # MD  → data/process/판례/*.json
    process_all_mds(input_dir="./data",  output_dir="./data/process")
