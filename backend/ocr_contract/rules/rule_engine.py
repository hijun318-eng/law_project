# import re
# from typing import Optional
# from backend.ocr_contract.config.constants import (
#     REQUIRED_FIELDS, RULE_CHECKS, MIN_HOURLY_WAGE
# )

# # ── 미기재 판정 ────────────────────────────────────────────
# _BLANK_PATTERNS = [
#     re.compile(r"^[년월일\s~부터까지\-\.]*$"),
#     re.compile(r"^[\s시분~\-_부터까지,·]+$"),
#     re.compile(r"^(원\s*){1,5}$"),
#     re.compile(r"있을\s*\(\s*\)\s*없을\s*\(\s*\)"),
#     re.compile(r"^[\s\-_·,\.]*$"),
#     re.compile(r"^매주\s+요일\s*$"),
# ]

# def _is_blank(value) -> bool:
#     if value is None:
#         return True
#     v = str(value).strip()
#     if not v or v.lower() == "null":
#         return True
#     hedges = ["추정", "것으로 보임", "인 것으로", "으로 보임"]
#     if any(kw in v for kw in hedges):
#         return True
#     return any(p.search(v) for p in _BLANK_PATTERNS)

# # ── 수치 파싱 ──────────────────────────────────────────────
# def _parse_hourly_wage(text: str) -> Optional[int]:
#     """시급 추출. 예: '시급 10,000원' → 10000"""
#     if not text:
#         return None
#     cleaned = text.replace(",", "").replace(" ", "")
#     m = re.search(r"시급(\d+)원?", cleaned)
#     return int(m.group(1)) if m else None

# def _parse_monthly_wage(text: str) -> Optional[int]:
#     """월급 추출. 예: '월 2,500,000원' → 2500000"""
#     if not text:
#         return None
#     cleaned = text.replace(",", "").replace(" ", "")
#     m = re.search(r"월급?(\d+)원?", cleaned)
#     if m:
#         return int(m.group(1))
#     m = re.search(r"기본급(\d+)원?", cleaned)
#     return int(m.group(1)) if m else None

# def _parse_work_hours(text: str) -> Optional[float]:
#     if not text:
#         return None

#     # HH:MM ~ HH:MM
#     m = re.search(r"(\d{1,2}):(\d{2})\s*[~\-]\s*(\d{1,2}):(\d{2})", text)
#     if m:
#         sh, sm, eh, em = map(int, m.groups())
#         return (eh * 60 + em - sh * 60 - sm) / 60

#     # N시[MM분][부터/~] N시[MM분][까지]  ← 이 패턴이 누락되어 있었음
#     m = re.search(
#         r"(오전|오후)?\s*(\d{1,2})\s*시\s*(\d{2})?\s*분?\s*(?:부터|~|\-)\s*(오전|오후)?\s*(\d{1,2})\s*시\s*(\d{2})?\s*분?",
#         text,
#     )
#     if m:
#         ap1, h1, m1, ap2, h2, m2 = m.groups()

#         def to_24h(hour: int, ampm: str) -> int:
#             if ampm == "오후" and hour != 12:
#                 return hour + 12
#             if ampm == "오전" and hour == 12:
#                 return 0
#             return hour

#         start = to_24h(int(h1), ap1 or "") * 60 + (int(m1) if m1 else 0)
#         end   = to_24h(int(h2), ap2 or "") * 60 + (int(m2) if m2 else 0)
#         return (end - start) / 60

#     return None


# def _parse_break_minutes(text: str) -> Optional[int]:
#     if not text:
#         return None

#     # HH:MM ~ HH:MM
#     m = re.search(r"(\d{1,2}):(\d{2})\s*[~\-]\s*(\d{1,2}):(\d{2})", text)
#     if m:
#         sh, sm, eh, em = map(int, m.groups())
#         return eh * 60 + em - sh * 60 - sm

#     # N시간 M분
#     m = re.search(r"(\d+)\s*시간\s*(?:(\d+)\s*분)?", text)
#     if m:
#         return int(m.group(1)) * 60 + (int(m.group(2)) if m.group(2) else 0)

#     # N분
#     m = re.search(r"(\d+)\s*분", text)
#     return int(m.group(1)) if m else None

# # ══════════════════════════════════════════════════════════
# # Rule Engine
# # ══════════════════════════════════════════════════════════
# def run_rule_engine(fields: dict) -> dict:
#     """
#     Deterministic Rule Engine.

#     반환 구조:
#     {
#         "is_valid":    bool,
#         "missing":     { field: law_ref },   # 필수기재사항 누락
#         "violations":  [ { type, field, detail, law_ref } ],  # 수치 위반
#         "warnings":    [ { type, field, detail } ],           # 확인 필요
#         "summary":     str,
#     }
#     """
#     missing:    dict[str, str] = {}
#     violations: list[dict]     = []
#     warnings:   list[dict]     = []

#     # ── A. 필수기재사항 누락 ──────────────────────────────
#     for field, law_ref in REQUIRED_FIELDS.items():
#         if _is_blank(fields.get(field)):
#             missing[field] = law_ref

#     # ── B. 최저임금 ───────────────────────────────────────
#     wage_text = fields.get("임금") or ""
#     rule_wage = RULE_CHECKS["최저임금"]

#     hourly  = _parse_hourly_wage(wage_text)
#     monthly = _parse_monthly_wage(wage_text)

#     if hourly is not None:
#         if hourly < rule_wage["min_hourly_wage"]:
#             violations.append({
#                 "type":    "최저임금_위반",
#                 "field":   "임금",
#                 "detail":  f"시급 {hourly:,}원 < 최저시급 {MIN_HOURLY_WAGE:,}원",
#                 "law_ref": rule_wage["law_ref"],
#             })
#     elif monthly is not None:
#         # 주 40시간 기준 월 209시간으로 환산
#         derived = int(monthly / 209)
#         if derived < rule_wage["min_hourly_wage"]:
#             violations.append({
#                 "type":    "최저임금_위반",
#                 "field":   "임금",
#                 "detail":  f"월급 {monthly:,}원 ÷ 209h = 환산시급 {derived:,}원 < {MIN_HOURLY_WAGE:,}원",
#                 "law_ref": rule_wage["law_ref"],
#             })
#     elif not _is_blank(wage_text):
#         # 임금은 기재됐으나 수치 파싱 불가
#         warnings.append({
#             "type":   "임금_파싱불가",
#             "field":  "임금",
#             "detail": f"임금 기재값 '{wage_text}'에서 시급·월급 금액을 파싱할 수 없어 최저임금 검사를 생략했습니다. 수동 확인이 필요합니다.",
#         })

#     # ── C. 소정근로시간 + 휴게시간 연계 검사 ─────────────
#     work_text  = fields.get("소정근로시간") or ""
#     break_text = fields.get("휴게시간") or ""

#     work_hours    = _parse_work_hours(work_text)
#     break_minutes = _parse_break_minutes(break_text) if not _is_blank(break_text) else None

#     if work_hours is not None:
#         # C-1. 1일 최대 근로시간
#         max_h = RULE_CHECKS["1일_최대근로"]["max_daily_hours"]
#         if work_hours > max_h:
#             violations.append({
#                 "type":    "최대근로시간_초과",
#                 "field":   "소정근로시간",
#                 "detail":  f"1일 근로 {work_hours}시간 > 법정 상한 {max_h}시간(연장 포함)",
#                 "law_ref": RULE_CHECKS["1일_최대근로"]["law_ref"],
#             })

#         # C-2. 휴게시간 기준 — 미기재도 위반으로 처리
#         if work_hours >= RULE_CHECKS["휴게시간_8시간"]["work_hours_threshold"]:
#             required = RULE_CHECKS["휴게시간_8시간"]["min_break_minutes"]
#             rule_ref = RULE_CHECKS["휴게시간_8시간"]["law_ref"]
#         elif work_hours >= RULE_CHECKS["휴게시간_4시간"]["work_hours_threshold"]:
#             required = RULE_CHECKS["휴게시간_4시간"]["min_break_minutes"]
#             rule_ref = RULE_CHECKS["휴게시간_4시간"]["law_ref"]
#         else:
#             required = 0
#             rule_ref = ""

#         if required > 0:
#             if break_minutes is None:
#                 violations.append({
#                     "type":    "휴게시간_미기재_위반",
#                     "field":   "휴게시간",
#                     "detail":  f"근로 {work_hours}시간 → 최소 {required}분 부여 의무 있으나 휴게시간 미기재",
#                     "law_ref": rule_ref,
#                 })
#             elif break_minutes < required:
#                 violations.append({
#                     "type":    "휴게시간_부족",
#                     "field":   "휴게시간",
#                     "detail":  f"근로 {work_hours}h → 최소 {required}분 필요, 기재 {break_minutes}분",
#                     "law_ref": rule_ref,
#                 })
#     elif not _is_blank(work_text):
#         warnings.append({
#             "type":   "소정근로시간_파싱불가",
#             "field":  "소정근로시간",
#             "detail": f"소정근로시간 기재값 '{work_text}'을 파싱할 수 없어 근로시간·휴게시간 검사를 생략했습니다. 수동 확인이 필요합니다.",
#         })

#     # ── D. 요약 ───────────────────────────────────────────
#     issues = len(missing) + len(violations)
#     if issues == 0 and not warnings:
#         summary = "✅ 필수기재사항 모두 기재, 주요 법정 기준 충족"
#     elif issues == 0:
#         summary = f"⚠️  위반은 없으나 수동 확인 필요 항목 {len(warnings)}건"
#     else:
#         parts = []
#         if missing:
#             parts.append(f"필수항목 누락 {len(missing)}건")
#         if violations:
#             parts.append(f"법정기준 위반 {len(violations)}건")
#         summary = "❌ " + ", ".join(parts)

#     return {
#         "is_valid":   issues == 0,
#         "missing":    missing,
#         "violations": violations,
#         "warnings":   warnings,
#         "summary":    summary,
#     }