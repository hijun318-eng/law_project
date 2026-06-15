#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
casenote.kr 판례 크롤러
https://casenote.kr 에서 사건번호로 판례를 검색하고
전문을 마크다운 파일로 저장합니다.
"""
import requests
from bs4 import BeautifulSoup
import time
import os
import re
import sys

# ─── 설정 ───────────────────────────────────────────────────────────────
CASE_NUMBERS = [
    # ── A. 임금 ──
    # A-1. 임금의 정의/범위
    "2011다23149",
    # A-2. 최저임금
    "2006다64245", "2018도6486", "2014다44673",
    # A-3. 임금체불
    "98도1260",    "2001도204",   "2017도4343", "2022도2188",
    # A-4. 통상임금
    "89다카2292",  "94다19501",   "2010다91046", "2012다89399",
    "2015다73067",
    # A-5. 평균임금
    "97다5015",    "90누2772",    "2022두64518",
    # ── B. 근로시간 ──
    # B-2. 연장·야간·휴일근로 및 수당
    "2020도15393", "2012다106423",
    # B-3. 포괄임금제
    "96다24699",   "2008다57852", "2008다6052",
    # ── C. 퇴직 ──
    # C-1. 퇴직금/퇴직급여
    "93다26168",   "2007다90760", "2016다255910",
    # C-2. 해고 (정당성, 절차)
    "97누18189",
    # C-3. 권고사직/자진퇴사 구분
    "91다36666",   "90다11554",   "2002다11458",
    # ── D. 근로계약 ──
    # D-1. 근로계약서 작성 의무
    "2020도16541",
    # D-2. 근로자성 판단 (기존, 재크롤)
    "2004다29736", "2006도777",   "2009다51417",
    # D-3. 수습/시용 기간
    "2019두55859", "2002다62432",
    # ── E. 4대보험 / 산재 ──
    # E-2. 산업재해 인정 기준
    "2006두4912",  "2017두45933", "2019두62604",
    # ── F. 직장 내 권리 ──
    # F-1. 직장 내 괴롭힘
    "2020다270503", "2021두54330",
    # F-2. 직장 내 성희롱
    "1998두7579",  "2007두22498", "2017두74702",
    # F-3. 육아휴직 / 모성보호
    "2018두47264", "2015두51651", "2012두4852",
    "2017두76005", "2019두38571",
]

BASE_URL = "https://casenote.kr"
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cases")
DELAY = 1.5  # 서버 부하 방지 지연(초)

# ─── 분류별 저장 경로 매핑 ───────────────────────────────────────────────
CLASSIFICATION_MAP = {
    # A. 임금
    "2011다23149": "A. 임금/A-1. 임금의 정의범위",
    "2006다64245": "A. 임금/A-2. 최저임금",
    "2018도6486":  "A. 임금/A-2. 최저임금",
    "2014다44673": "A. 임금/A-2. 최저임금",
    "98도1260":    "A. 임금/A-3. 임금체불",
    "2001도204":   "A. 임금/A-3. 임금체불",
    "2017도4343":  "A. 임금/A-3. 임금체불",
    "2022도2188":  "A. 임금/A-3. 임금체불",
    "89다카2292":  "A. 임금/A-4. 통상임금",
    "94다19501":   "A. 임금/A-4. 통상임금",
    "2010다91046": "A. 임금/A-4. 통상임금",
    "2012다89399": "A. 임금/A-4. 통상임금",
    "2015다73067": "A. 임금/A-4. 통상임금",
    "97다5015":    "A. 임금/A-5. 평균임금",
    "90누2772":    "A. 임금/A-5. 평균임금",
    "2022두64518": "A. 임금/A-5. 평균임금",
    # B. 근로시간
    "2020도15393": "B. 근로시간/B-2. 연장·야간·휴일근로 및 수당",
    "2012다106423":"B. 근로시간/B-2. 연장·야간·휴일근로 및 수당",
    "96다24699":   "B. 근로시간/B-3. 포괄임금제",
    "2008다57852": "B. 근로시간/B-3. 포괄임금제",
    "2008다6052":  "B. 근로시간/B-3. 포괄임금제",
    # C. 퇴직
    "93다26168":   "C. 퇴직/C-1. 퇴직금퇴직급여",
    "2007다90760": "C. 퇴직/C-1. 퇴직금퇴직급여",
    "2016다255910":"C. 퇴직/C-1. 퇴직금퇴직급여",
    "97누18189":   "C. 퇴직/C-2. 해고 (정당성, 절차)",
    "91다36666":   "C. 퇴직/C-3. 권고사직자진퇴사 구분",
    "90다11554":   "C. 퇴직/C-3. 권고사직자진퇴사 구분",
    "2002다11458": "C. 퇴직/C-3. 권고사직자진퇴사 구분",
    # D. 근로계약
    "2020도16541": "D. 근로계약/D-1. 근로계약서 작성 의무",
    "2004다29736": "D. 근로계약/D-2. 근로자성 판단",
    "2006도777":   "D. 근로계약/D-2. 근로자성 판단",
    "2009다51417": "D. 근로계약/D-2. 근로자성 판단",
    "2019두55859": "D. 근로계약/D-3. 수습시용 기간",
    "2002다62432": "D. 근로계약/D-3. 수습시용 기간",
    # E. 4대보험 / 산재
    "2006두4912":  "E. 4대보험 - 산재/E-2. 산업재해 인정 기준",
    "2017두45933": "E. 4대보험 - 산재/E-2. 산업재해 인정 기준",
    "2019두62604": "E. 4대보험 - 산재/E-2. 산업재해 인정 기준",
    # F. 직장 내 권리
    "2020다270503":"F. 직장 내 권리/F-1. 직장 내 괴롭힘",
    "2021두54330": "F. 직장 내 권리/F-1. 직장 내 괴롭힘",
    "1998두7579":  "F. 직장 내 권리/F-2. 직장 내 성희롱",
    "2007두22498": "F. 직장 내 권리/F-2. 직장 내 성희롱",
    "2017두74702": "F. 직장 내 권리/F-2. 직장 내 성희롱",
    "2018두47264": "F. 직장 내 권리/F-3. 육아휴직 모성보호",
    "2015두51651": "F. 직장 내 권리/F-3. 육아휴직 모성보호",
    "2012두4852":  "F. 직장 내 권리/F-3. 육아휴직 모성보호",
    "2017두76005": "F. 직장 내 권리/F-3. 육아휴직 모성보호",
    "2019두38571": "F. 직장 내 권리/F-3. 육아휴직 모성보호",
}


def get_output_path(case_number: str) -> str:
    """분류 매핑에 따라 저장 경로 반환, 없으면 cases/직행"""
    subdir = CLASSIFICATION_MAP.get(case_number)
    if subdir:
        return os.path.join(OUTPUT_DIR, *subdir.split("/"))
    return OUTPUT_DIR

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# ─── 유틸리티 ───────────────────────────────────────────────────────────
def clean_text(text: str) -> str:
    """여백 정리"""
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_panels(soup) -> list:
    """panel 섹션(판시사항, 판결요지, 참조조문, 참조판례) 추출"""
    panels = soup.select("div.panel")
    results = []
    for panel in panels:
        heading_el = panel.select_one("div.panel-heading")
        if not heading_el:
            continue
        heading = clean_text(heading_el.text)
        # 중요 섹션만 추출
        if heading not in ("판시사항", "판결요지", "참조조문", "참조판례"):
            continue

        # 내용 div 찾기
        content_el = panel.select_one(
            "div.issue, div.summary, div.reflaws, div.refcases"
        )
        if content_el:
            content = content_el.decode_contents().strip()
        else:
            # 내용 div가 없으면 heading 이후의 모든 div 텍스트
            content = ""
            for child in panel.find_all("div", recursive=False):
                if "panel-heading" not in child.get("class", []):
                    content += child.get_text(" ", strip=True) + "\n"
            content = content.strip()

        results.append((heading, content))
    return results


def extract_reason(soup) -> str:
    """판결문 본문(주문 + 이유) 추출"""
    reason_div = soup.select_one("div.reason")
    if not reason_div:
        return ""

    # p 태그들을 순회하며 텍스트 수집
    parts = []
    for child in reason_div.find_all("p", recursive=False):
        cls = child.get("class", [])
        text = child.get_text(" ", strip=True)
        if not text:
            continue
        if "sub-title" in cls:
            parts.append(f"\n**{text}**\n")
        else:
            parts.append(text)

    return "\n\n".join(parts)


def extract_pro_content(soup) -> tuple:
    """PRO 콘텐츠 페이지(일반판례 비공개)에서 정보 추출"""
    case_body = soup.select_one("div.cn-case-body")
    if not case_body:
        return "", "", ""
    
    # 사건 정보 표
    abstract_table = case_body.select_one("table.table-in-abstract")
    abstract_text = ""
    if abstract_table:
        rows = abstract_table.find_all("tr")
        for row in rows:
            cells = row.find_all(["th", "td"])
            row_text = " | ".join(clean_text(c.text) for c in cells if clean_text(c.text))
            if row_text:
                abstract_text += row_text + "\n"
    
    # 주문
    order_parts = []
    for title_p in case_body.select("p.title"):
        order_title = clean_text(title_p.text)
        if order_title:
            order_parts.append(f"**{order_title}**")
        # 다음 형제 p.main-sentence
        nxt = title_p.find_next_sibling("p")
        if nxt and "main-sentence" in nxt.get("class", []):
            order_parts.append(clean_text(nxt.text))
    
    # 재판장 정보 (PRO 페이지에서는 judges div가 없으므로 텍스트에서 추출)
    body_text = case_body.get_text()
    judge_text = ""
    # 일반적으로 "재판장 대법관 XXX" 패턴
    judge_lines = []
    for line in body_text.split("\n"):
        line = line.strip()
        if any(kw in line for kw in ["재판장", "주심", "대법관"]):
            judge_lines.append(line)
    judge_text = "\n".join(judge_lines)
    
    return abstract_text, "\n\n".join(order_parts), judge_text


def extract_reason_or_fallback(soup) -> str:
    """reason 추출, 없으면 PRO fallback 주문 추출"""
    reason = extract_reason(soup)
    if reason:
        return reason
    
    # PRO fallback
    _, order_text, _ = extract_pro_content(soup)
    return order_text


def extract_judges(soup) -> str:
    """재판장 정보 추출 (일반 + PRO fallback)"""
    judges_div = soup.select_one("div.judges")
    if judges_div:
        judges = judges_div.select("div.judge")
        lines = []
        for j in judges:
            role = j.select_one("div.judge-role")
            title = j.select_one("div.judge-title")
            name = j.select_one("div.judge-name")
            parts = []
            if role and role.text.strip():
                parts.append(role.text.strip())
            if title and title.text.strip():
                parts.append(title.text.strip())
            if name and name.text.strip():
                parts.append(name.text.strip())
            if parts:
                lines.append(" ".join(parts))
        if lines:
            return "\n".join(lines)
    
    # PRO fallback
    _, _, judge_text = extract_pro_content(soup)
    return judge_text


def extract_proceedings(soup) -> str:
    """소송경과 추출 (사이드바)"""
    sidebox = None
    for sb in soup.select("div.cn-sidebox"):
        if "소송경과" in sb.text:
            sidebox = sb
            break
    
    if not sidebox:
        return ""
    
    info = sidebox.select_one("div.cn-sidebox-info-container")
    if not info:
        return ""
    
    lines = []
    for item in info.find_all(["div", "p", "a"], recursive=True):
        text = clean_text(item.text)
        if text and len(text) > 3:
            lines.append(text)
    
    return "\n".join(lines)


def extract_metadata(soup) -> str:
    """판결 메타데이터(원고, 피고, 원심판결 등) 추출"""
    # PRO 페이지의 abstract table 활용
    abstract_text, _, _ = extract_pro_content(soup)
    if abstract_text:
        return abstract_text
    
    # 일반 페이지: panel과 reason 사이의 내용
    reason_div = soup.select_one("div.reason")
    if not reason_div:
        return ""

    metadata_parts = []
    for sibling in reason_div.find_all_previous():
        if sibling.find_parent("div.panel"):
            continue
        if sibling.find_parent("div.judges"):
            continue
        if sibling is reason_div:
            continue
        
        tag = sibling.name
        text = clean_text(sibling.text)
        if not text or len(text) < 5:
            continue
        if tag in ("script", "style", "nav", "button", "header", "footer"):
            continue
        if not sibling.find_parent("div.cn-case-body"):
            continue
        
        metadata_parts.append(text)

    seen = set()
    unique_parts = []
    for p in reversed(metadata_parts):
        if p not in seen and len(p) > 10:
            seen.add(p)
            unique_parts.append(p)
    
    return "\n\n".join(unique_parts)


def extract_case_number_from_title(title_text: str) -> str:
    """제목에서 사건번호 추출 시도"""
    m = re.search(r"(\d{0,2}\d{2}[가-힣]+\d+)", title_text)
    return m.group(1) if m else ""


# ─── 메인 크롤링 ────────────────────────────────────────────────────────
def crawl_case(case_number: str) -> dict | None:
    """단일 판례 크롤링"""
    # 1단계: search URL로 시도
    url = f"{BASE_URL}/search/?q={case_number}"
    
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        resp.encoding = "utf-8"
    except requests.exceptions.RequestException as e:
        print(f"  ✗ 요청 실패: {e}")
        return None

    # 검색 결과 페이지인지 확인
    if "/search/" in resp.url:
        soup_check = BeautifulSoup(resp.text, "html.parser")
        title_tag = soup_check.title
        if title_tag and "검색결과" in title_tag.text:
            # 2단계: /대법원/사건번호 URL로 직접 접근
            from urllib.parse import quote
            encoded_cn = quote(case_number)
            direct_url = f"{BASE_URL}/%EB%8C%80%EB%B2%95%EC%9B%90/{encoded_cn}"
            print(f"  ↻ search 미적용, 대법원 URL 직접 시도...")
            try:
                resp = requests.get(direct_url, headers=HEADERS, timeout=20)
                resp.raise_for_status()
                resp.encoding = "utf-8"
            except requests.exceptions.RequestException as e:
                print(f"  ✗ 대법원 URL 요청 실패: {e}")
                return None
    
    soup = BeautifulSoup(resp.text, "html.parser")
    
    # 1. 제목
    title_el = soup.select_one("div.cn-case-title h1")
    if not title_el:
        # fallback: h1 직접
        title_el = soup.select_one("h1")
    if not title_el:
        print("  ✗ 제목을 찾을 수 없음")
        return None
    title = clean_text(title_el.text)
    print(f"  ✓ 제목: {title[:60]}...")
    
    # 2. panel 섹션
    panels = extract_panels(soup)
    
    # 3. reason (판결문 본문)
    reason = extract_reason_or_fallback(soup)
    
    # 4. judges (재판장)
    judges = extract_judges(soup)
    
    # 5. proceedings (소송경과)
    proceedings = extract_proceedings(soup)
    
    return {
        "case_number": case_number,
        "title": title,
        "panels": panels,
        "reason": reason,
        "judges": judges,
        "proceedings": proceedings,
    }


def to_markdown(data: dict) -> str:
    """크롤링 데이터를 마크다운으로 변환"""
    lines = []
    
    # 제목
    lines.append(f"# {data['title']}")
    lines.append("")
    
    # panel 섹션
    for heading, content in data["panels"]:
        lines.append(f"## {heading}")
        lines.append("")
        # HTML을 텍스트로 변환
        text = BeautifulSoup(content, "html.parser").get_text(" ", strip=True)
        text = clean_text(text)
        lines.append(text)
        lines.append("")
    
    # 판결문 본문
    if data["reason"]:
        lines.append("## 주문 및 이유")
        lines.append("")
        lines.append(data["reason"])
        lines.append("")
    
    # 재판장
    if data["judges"]:
        lines.append("## 재판장")
        lines.append("")
        lines.append(data["judges"])
        lines.append("")
    
    # 소송경과
    if data["proceedings"]:
        lines.append("## 소송경과")
        lines.append("")
        lines.append(data["proceedings"])
        lines.append("")
    
    return "\n".join(lines)


# ─── 실행 ───────────────────────────────────────────────────────────────
def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print(f"⚖️  casenote.kr 판례 크롤러")
    print(f"   출력 디렉토리: {OUTPUT_DIR}")
    print(f"   대상 건수: {len(CASE_NUMBERS)}건\n")
    
    success = 0
    fail = 0
    skipped = []
    
    for i, cn in enumerate(CASE_NUMBERS, 1):
        print(f"[{i}/{len(CASE_NUMBERS)}] {cn} ...")
        result = crawl_case(cn)
        
        if result is None:
            print(f"  → 저장 안 함 (데이터 없음)")
            fail += 1
            skipped.append(cn)
        else:
            md = to_markdown(result)
            safe_name = cn.replace("/", "_").replace("\\", "_")
            out_dir = get_output_path(cn)
            os.makedirs(out_dir, exist_ok=True)
            filepath = os.path.join(out_dir, f"{safe_name}.md")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(md)
            print(f"  → 저장 완료: {filepath}")
            success += 1
        
        # 서버 부하 방지 (마지막이 아니면)
        if i < len(CASE_NUMBERS):
            time.sleep(DELAY)
    
    print(f"\n{'='*50}")
    print(f"크롤링 완료!")
    print(f"  성공: {success}건")
    print(f"  실패/없음: {fail}건")
    if skipped:
        print(f"  건너뜀: {', '.join(skipped)}")
    print(f"  저장 위치: {OUTPUT_DIR}")
    
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
