"""
노동 법률 종합 AI 어시스턴트 - Streamlit UI
=============================================
MVP 기능: 법률 Q&A, 상황별 권리 안내, 신고 경로 안내, 증거 가이드
부가 기능: 계산기, 서류 작성, 근로계약서 분석, 쉬운말 토글
"""
import os
import sys
import uuid
import json
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import Optional

import streamlit as st

# ── 경로 설정 ──────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
LAW_TEST_DIR = os.path.join(PROJECT_ROOT, "law_test")
for p in [PROJECT_ROOT, LAW_TEST_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

# ── RAG 엔진 연결 (선택적) ────────────────────────────────
try:
    from backend.rag_engine import RAGEngine
    from src.history_db import HistoryDB
    RAG_AVAILABLE = True
except ImportError as e:
    RAG_AVAILABLE = False
    import traceback
    print(f"[WARN] RAG 엔진 로드 실패: {e}")

# ============================================================
# 앱 설정
# ============================================================
st.set_page_config(
    page_title="노동 법률 AI 어시스턴트",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

APP_NAME = "노동 법률 AI 어시스턴트"
APP_SUBTITLE = "근로기준법 · 노동관계법 종합 상담 플랫폼"

# ── 색상 테마 ──────────────────────────────────────────────
C_PRIMARY = "#1B3A5C"       # 진한 남색 (법률 느낌)
C_ACCENT  = "#2E7DBA"       # 파랑
C_SUCCESS = "#2E7D32"       # 녹색
C_WARNING = "#E65100"       # 주황
C_BG_LIGHT = "#F5F7FA"     # 배경
C_CARD_BG = "#FFFFFF"      # 카드 배경

# ── 메뉴 정의 ──────────────────────────────────────────────
PAGES = {
    "home":         {"icon": "🏠",   "label": "홈",              "group": "시작"},
    "qa":           {"icon": "💬",   "label": "법률 Q&A",         "group": "MVP 기능"},
    "rights":       {"icon": "🔍",   "label": "상황별 권리 안내",  "group": "MVP 기능"},
    "report":       {"icon": "📞",   "label": "신고/접수 경로",    "group": "MVP 기능"},
    "evidence":     {"icon": "📋",   "label": "증거 관리 가이드",  "group": "MVP 기능"},
    "calculator":   {"icon": "🧮",   "label": "수당 계산기",       "group": "부가 기능"},
    "docwriter":    {"icon": "📝",   "label": "서류 작성 도우미",  "group": "부가 기능"},
    "contract":     {"icon": "🔎",   "label": "근로계약서 분석",   "group": "부가 기능"},
}

# ============================================================
# 정적 데이터
# ============================================================

# ── 상황별 권리 안내 데이터 ────────────────────────────────
RIGHTS_CASES = {
    "부당해고": {
        "icon": "🚫",
        "desc": "정당한 이유 없이 해고당한 경우",
        "laws": [
            "근로기준법 제23조(해고 등의 제한) - 정당한 이유 없는 해고 금지",
            "근로기준법 제24조(경영상 이유에 의한 해고) - 경영상 해고 요건",
            "근로기준법 제27조(해고사유 등의 서면통지) - 해고 서면 통지 의무",
        ],
        "procedures": [
            "해고 통지일로부터 3개월 이내에 노동위원회에 구제 신청",
            "관할 지방노동위원회에 부당해고 구제신청서 제출",
            "노동위원회 조정 → 심판 절차 진행",
            "불복 시 중앙노동위원회 재심 → 행정소송",
        ],
        "deadline": "해고일로부터 3개월 (노동위원회 구제신청)",
        "precedents": [
            "대법원 2020다270503 - 해고의 정당성 판단 기준",
            "대법원 2017두76005 - 경영상 해고 요건 판단",
        ],
    },
    "임금체불": {
        "icon": "💰",
        "desc": "임금을 정해진 기일까지 받지 못한 경우",
        "laws": [
            "근로기준법 제36조(임금지급) - 매월 1회 이상 정기 지급",
            "근로기준법 제43조(임금지급 방법) - 통화로 직접 지급 원칙",
            "근로기준법 제109조(벌칙) - 임금체불 시 3년 이하 징역 또는 3천만원 이하 벌금",
        ],
        "procedures": [
            "사업장 소재지 관할 고용노동청에 진정 제기",
            "고용노동부 근로감독관 조사 진행",
            "체불 임금 확인 시 시정 지시 → 사건 송치",
            "임금채권은 퇴직 후 3년간 소멸시효 정지 가능",
        ],
        "deadline": "임금채권 소멸시효: 3년 (근로기준법 제49조)",
        "precedents": [
            "대법원 2016다255910 - 임금체불과 지연이자",
            "대법원 2007다90760 - 임금채권 소멸시효 중단",
        ],
    },
    "직장 내 괴롭힘": {
        "icon": "⚠️",
        "desc": "직장 내에서의 괴롭힘·폭언·따돌림 피해",
        "laws": [
            "근로기준법 제76조의2(직장 내 괴롭힘 금지) - 직장 내 괴롭힘 정의와 금지",
            "근로기준법 제76조의3(조치 의무) - 사용자의 피해자 보호 의무",
            "근로기준법 제76조의4(징계 등) - 가해자에 대한 징계",
        ],
        "procedures": [
            "사내 고충처리위원회 또는 인사부문에 신고",
            "증거 수집 후 고용노동청 진정 가능",
            "피해자 보호 조치 요청 (근무장소 변경, 유급휴가 등)",
            "정신적 손해배상 청구 (민사소송)",
        ],
        "deadline": "진정 제출에 별도 기한 없음 (조기 대응 권장)",
        "precedents": [
            "대법원 2020다270503 - 직장 내 괴롭힘 인정 기준",
        ],
    },
    "직장 내 성희롱": {
        "icon": "🔞",
        "desc": "직장에서의 성적 언동으로 인한 피해",
        "laws": [
            "남녀고용평등법 제12조(직장 내 성희롱 금지)",
            "근로기준법 제76조의2(직장 내 괴롭힘 금지)",
            "성폭력처벌법 - 성폭력 범죄 처벌",
        ],
        "procedures": [
            "사내 성희롱 고충처리위원회 신고",
            "증거 확보 후 고용노동청 진정",
            "경찰 고소 (형사 절차)",
            "손해배상 청구 (민사소송)",
        ],
        "deadline": "형사 고소: 범죄일로부터 3년, 민사: 3년",
        "precedents": [
            "대법원 2017두74702 - 직장 내 성희롱 판단 기준",
            "대법원 2007두22498 - 사용자 책임 인정",
        ],
    },
    "산업재해": {
        "icon": "🏥",
        "desc": "업무 중 발생한 사고나 질병",
        "laws": [
            "산업재해보상보험법 제5조(업무상 재해 인정 기준)",
            "근로기준법 제78조(재해보상) - 요양보상, 휴업보상 등",
            "산업안전보건법 제41조(안전조치 의무)",
        ],
        "procedures": [
            "사업주에게 재해 발생 통보 (즉시)",
            "관할 근로복지공단에 요양급여 신청",
            "산재 인정 시 요양급여, 휴업급여 지급",
            "불복 시 산재심사위원회 심사 청구",
        ],
        "deadline": "산재 요양신청: 요양 개시일로부터 3년",
        "precedents": [
            "대법원 2019두62604 - 업무상 재해 인정 범위",
            "대법원 2017두45933 - 과로사 인정 기준",
        ],
    },
    "육아휴직": {
        "icon": "👶",
        "desc": "임신·출산·육아로 인한 휴직 관련 권리",
        "laws": [
            "남녀고용평등법 제19조(육아휴직) - 만 8세 이하 자녀 육아휴직",
            "근로기준법 제74조(임산부 보호) - 출산전후휴가 90일",
            "고용보험법 - 육아휴직 급여 지급",
        ],
        "procedures": [
            "사업주에게 육아휴직 신청서 제출 (휴직 개시 30일 전)",
            "고용센터에 육아휴직 급여 신청",
            "최대 1년간 육아휴직 가능",
            "육아휴직 후 원직 복직 보장",
        ],
        "deadline": "육아휴직 급여 신청: 휴직 종료일로부터 12개월",
        "precedents": [
            "대법원 2019두38571 - 육아휴직 사용자의 불이익 처우 금지",
            "대법원 2018두47264 - 육아휴직 급여 지급 기준",
        ],
    },
}


# ── 신고/접수 경로 데이터 ──────────────────────────────────
REPORT_CHANNELS = {
    "고용노동부(고용노동청)": {
        "icon": "🏛️",
        "desc": "임금체불, 부당해고, 직장 내 괴롭힘 등 신고",
        "methods": [
            ("📞", "전화 상담", "1350 (고용노동부 상담센터, 무료)"),
            ("💻", "온라인 신고", "www.moel.go.kr → 민원신청"),
            ("🏢", "방문 신고", "관할 지방고용노동청·지청 민원실"),
            ("📱", "모바일", "고용노동부 앱 → 민원신고"),
        ],
        "process": [
            "민원 접수 → 담당 근로감독관 배정",
            "사실 조사 (현장 출동, 자료 제출 요구)",
            "위반 확인 → 시정 지시 / 과태료 부과 / 사건 송치",
            "조치 결과 통보 (접수일로부터 30일 이내)",
        ],
        "jurisdiction": "전국 지방고용노동청 및 지청",
    },
    "노동위원회": {
        "icon": "⚖️",
        "desc": "부당해고·부당징계 구제 신청, 노동쟁의 조정",
        "methods": [
            ("📞", "전화 문의", "지방노동위원회 대표번호"),
            ("🏢", "방문 접수", "관할 지방노동위원회 사무국"),
            ("💻", "온라인 접수", "www.nlrc.go.kr → 전자민원"),
        ],
        "process": [
            "구제신청서 제출 (해고일로부터 3개월 이내)",
            "조정 절차 (화해 권고)",
            "심판 절차 (심문회의 개최)",
            "판정 → 불복 시 중앙노동위원회 재심",
        ],
        "jurisdiction": "전국 11개 지방노동위원회",
    },
    "근로복지공단": {
        "icon": "🏥",
        "desc": "산업재해 보상, 요양급여 신청",
        "methods": [
            ("📞", "전화 상담", "1588-0075 (고객센터)"),
            ("💻", "온라인 신청", "www.kcomwel.or.kr → 민원신청"),
            ("🏢", "방문 접수", "관할 근로복지공단 지사"),
        ],
        "process": [
            "요양급여 신청서 제출 (사업주 확인 필요)",
            "업무상 재해 여부 조사",
            "승인 시 요양급여·휴업급여 지급",
            "불복 시 산재심사위원회 심사 청구",
        ],
        "jurisdiction": "전국 57개 지사",
    },
    "경찰청(수사기관)": {
        "icon": "🚔",
        "desc": "임금체불(고의성), 근로기준법 위반 사범 수사",
        "methods": [
            ("📞", "긴급 신고", "112 (범죄 신고)"),
            ("🏢", "방문 신고", "관할 경찰서 민원실"),
            ("💻", "온라인 신고", "경찰청 사이버민원센터"),
        ],
        "process": [
            "고소장 접수 → 수사 착수",
            "피의자 조사, 증거 수집",
            "검찰 송치 → 기소 여부 결정",
            "법원 재판 진행",
        ],
        "jurisdiction": "전국 경찰서",
    },
    "국가인권위원회": {
        "icon": "🤝",
        "desc": "직장 내 차별, 인권 침해 상담 및 진정",
        "methods": [
            ("📞", "전화 상담", "1331 (인권콜센터)"),
            ("💻", "온라인 접수", "www.humanrights.go.kr → 진정접수"),
            ("🏢", "방문 접수", "국가인권위원회 및 지역사무소"),
        ],
        "process": [
            "진정 접수 → 사실 조사",
            "조정 절차 (화해 권고)",
            "시정 권고 (법적 구속력 없음)",
            "권고 불수용 시 의견 표명",
        ],
        "jurisdiction": "서울 본원 및 부산·광주·대구·대전 사무소",
    },
    "대한법률구조공단": {
        "icon": "⚖️",
        "desc": "무료 법률 상담 및 소송 지원",
        "methods": [
            ("📞", "전화 상담", "132 (법률구조콜센터)"),
            ("💻", "온라인 상담", "www.klac.or.kr → 법률상담"),
            ("🏢", "방문 상담", "전국 지부 및 출장소"),
        ],
        "process": [
            "법률 상담 신청 (소득 기준 심사)",
            "구조 결정 → 변호사 선임",
            "소송 대리 또는 법률 서류 작성 지원",
            "승소 시 일부 성공보수 납부",
        ],
        "jurisdiction": "전국 19개 지부 및 55개 출장소",
    },
}

# ── 증거 관리 가이드 데이터 ────────────────────────────────
EVIDENCE_GUIDE = {
    "부당해고": {
        "icon": "🚫",
        "desc": "정당한 이유 없는 해고에 대비한 증거",
        "items": [
            ("해고 통지서", "⭐⭐⭐⭐⭐", "해고 사유, 해고일자, 해고 방법이 기재된 문서. 서면 통지가 가장 확실한 증거"),
            ("근로계약서", "⭐⭐⭐⭐⭐", "근무 조건, 계약 기간, 해고 관련 조항 확인"),
            ("급여 명세서", "⭐⭐⭐⭐", "최종 급여 수령일 확인, 임금체불 여부 확인"),
            ("출퇴근 기록", "⭐⭐⭐⭐", "근무 사실 입증 (타임카드, 출입 기록)"),
            ("업무 관련 대화록", "⭐⭐⭐", "해고 과정에서의 대화 녹음·메모 (녹취 시 사전 동의 필요)"),
            ("업무 메일/문자", "⭐⭐⭐", "해고 관련 통보 내용, 업무 지시 내역"),
            ("목격자 진술", "⭐⭐⭐", "동료 근로자의 진술 확보"),
        ],
    },
    "임금체불": {
        "icon": "💰",
        "desc": "임금·수당 미지급에 대비한 증거",
        "items": [
            ("근로계약서", "⭐⭐⭐⭐⭐", "약정 임금, 지급일, 수당 조건 확인"),
            ("급여 명세서", "⭐⭐⭐⭐⭐", "임금 체불 내역 및 지급 내역 확인"),
            ("출퇴근 기록", "⭐⭐⭐⭐", "실제 근무 시간 입증 (시간외근무 포함)"),
            ("통장 내역", "⭐⭐⭐⭐", "임금 입금 내역, 체불 시점 확인"),
            ("업무 메일/문자", "⭐⭐⭐", "임금 관련 회사와의 소통 내역"),
            ("근무 일지", "⭐⭐⭐", "개인 작성 근무 기록"),
            ("노동조합 확인", "⭐⭐", "노동조합의 체불 사실 확인서"),
        ],
    },
    "직장 내 괴롭힘": {
        "icon": "⚠️",
        "desc": "괴롭힘·폭언·따돌림 피해 증거",
        "items": [
            ("대화 녹음·녹취", "⭐⭐⭐⭐⭐", "괴롭힘 상황의 녹음 (단, 대화 당사자 참여 시 합법)"),
            ("메일/메신저 기록", "⭐⭐⭐⭐⭐", "폭언·비하 발언이 포함된 대화 내역 저장"),
            ("진료 기록", "⭐⭐⭐⭐", "정신적 피해에 대한 병원 진단서 및 치료 기록"),
            ("목격자 진술", "⭐⭐⭐⭐", "동료 직원의 목격 사실 확인서"),
            ("업무 기록", "⭐⭐⭐", "괴롭힘으로 인한 업무 수행 곤란 증명"),
            ("사내 신고 기록", "⭐⭐⭐", "인사부문·고충처리위원회 신고 사실 및 조치 내역"),
        ],
    },
    "산업재해": {
        "icon": "🏥",
        "desc": "업무상 사고·질병 관련 증거",
        "items": [
            ("진단서 및 진료 기록", "⭐⭐⭐⭐⭐", "의사의 상세 진단서, 진료비 내역"),
            ("사고 발생 보고서", "⭐⭐⭐⭐⭐", "사업주에게 제출한 사고 보고서"),
            ("목격자 진술", "⭐⭐⭐⭐", "사고 목격자의 사실 확인서"),
            ("CCTV 영상", "⭐⭐⭐⭐", "사고 현장이 촬영된 CCTV (보존 요청 필요)"),
            ("업무 기록", "⭐⭐⭐", "과로·스트레스 관련 업무량 증명 자료"),
            ("출퇴근 기록", "⭐⭐⭐", "사고 당일 근무 사실 입증"),
        ],
    },
    "직장 내 성희롱": {
        "icon": "🔞",
        "desc": "성적 언동 피해 증거",
        "items": [
            ("대화 기록", "⭐⭐⭐⭐⭐", "성희롱 발언이 포함된 메일·메신저·문자 내역"),
            ("녹음 파일", "⭐⭐⭐⭐", "성희롱 상황 녹음 (단, 대화 당사자 참여 시 증거 능력 있음)"),
            ("진료 기록", "⭐⭐⭐⭐", "정신적 충격에 대한 정신과 진단서"),
            ("사내 신고 기록", "⭐⭐⭐⭐", "인사부문 또는 고충위원회 신고 내역"),
            ("목격자 진술", "⭐⭐⭐", "목격자 또는 유사 피해자 진술"),
            ("CCTV 영상", "⭐⭐⭐", "사건 발생 장소의 CCTV (신속한 보존 요청 필요)"),
        ],
    },
}

# ── 소멸시효 데이터 ────────────────────────────────────────
DEADLINE_INFO = {
    "임금채권": "3년 (근로기준법 제49조) - 퇴직 후에도 3년간 청구 가능",
    "퇴직금": "14일 이내 지급 의무 (근로기준법 제36조), 소멸시효 3년",
    "재해보상청구권": "2년 (산업재해보상보험법) - 요양급여, 휴업급여 등",
    "노동위원회 구제신청": "3개월 (부당해고/부당징계) - 해고일로부터 3개월 이내",
    "민사 손해배상": "3년 (불법행위) 또는 10년 (채무불이행)",
    "형사 고소": "3년~5년 (범죄 종류에 따라 상이)",
}


# ============================================================
# 세션 상태 초기화
# ============================================================
def init_session():
    if "page" not in st.session_state:
        st.session_state.page = "home"
    if "mode" not in st.session_state:
        st.session_state.mode = "easy"  # "easy" or "expert"
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    if "qa_messages" not in st.session_state:
        st.session_state.qa_messages = []
    if "engine" not in st.session_state:
        try:
            st.session_state.engine = RAGEngine() if RAG_AVAILABLE else None
        except Exception as e:
            st.session_state.engine = None


# ============================================================
# CSS 스타일
# ============================================================
def load_css():
    st.markdown(f"""
    <style>
        .stApp {{ background-color: {C_BG_LIGHT}; }}
        .main-header {{
            color: {C_PRIMARY};
            font-size: 1.8rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }}
        .sub-header {{
            color: #555;
            font-size: 1rem;
            margin-bottom: 1.5rem;
        }}
        .card {{
            background-color: {C_CARD_BG};
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            margin-bottom: 1rem;
            border: 1px solid #eee;
        }}
        .card-title {{
            font-size: 1.2rem;
            font-weight: 600;
            color: {C_PRIMARY};
            margin-bottom: 0.5rem;
        }}
        .card-subtitle {{
            color: #555;
            font-size: 0.9rem;
        }}
        .badge {{
            display: inline-block;
            padding: 0.2rem 0.6rem;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
            margin-right: 0.3rem;
        }}
        .badge-green {{ background-color: #E8F5E9; color: #2E7D32; }}
        .badge-blue {{ background-color: #E3F2FD; color: #1565C0; }}
        .badge-orange {{ background-color: #FFF3E0; color: #E65100; }}
        .badge-red {{ background-color: #FFEBEE; color: #C62828; }}
        .sidebar-menu-item {{
            padding: 0.5rem 0.8rem;
            border-radius: 8px;
            cursor: pointer;
            transition: background 0.2s;
            margin-bottom: 0.2rem;
        }}
        .sidebar-menu-item:hover {{
            background-color: #E3F2FD;
        }}
        .sidebar-menu-item.active {{
            background-color: #E3F2FD;
            border-left: 3px solid {C_ACCENT};
            font-weight: 600;
        }}
        .info-box {{
            background-color: #E3F2FD;
            border-left: 4px solid {C_ACCENT};
            padding: 1rem;
            border-radius: 6px;
            margin: 1rem 0;
        }}
        .warning-box {{
            background-color: #FFF3E0;
            border-left: 4px solid {C_WARNING};
            padding: 1rem;
            border-radius: 6px;
            margin: 1rem 0;
        }}
        .success-box {{
            background-color: #E8F5E9;
            border-left: 4px solid {C_SUCCESS};
            padding: 1rem;
            border-radius: 6px;
            margin: 1rem 0;
        }}
        .calc-result {{
            font-size: 2rem;
            font-weight: 700;
            color: {C_ACCENT};
            text-align: center;
            padding: 1rem;
        }}
        .footer {{
            text-align: center;
            color: #999;
            font-size: 0.8rem;
            margin-top: 3rem;
            padding: 1rem;
            border-top: 1px solid #eee;
        }}
    </style>
    """, unsafe_allow_html=True)


# ============================================================
# 페이지 렌더러
# ============================================================

# ── 홈 ─────────────────────────────────────────────────────
def render_home():
    st.markdown('<p class="main-header">🏠 노동 법률 AI 어시스턴트</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">근로기준법 · 노동관계법 관련 모든 정보를 한 곳에서 확인하세요.</p>', unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        with st.container(border=True):
            st.markdown("#### 💬 법률 Q&A")
            st.markdown("법률 질문에 대한 답변을 AI가 제공합니다.")
            if st.button("바로가기", key="home_qa", use_container_width=True):
                st.session_state.page = "qa"
                st.rerun()
    with col2:
        with st.container(border=True):
            st.markdown("#### 🔍 상황별 권리 안내")
            st.markdown("부당해고, 임금체불 등 상황별 권리 확인")
            if st.button("바로가기", key="home_rights", use_container_width=True):
                st.session_state.page = "rights"
                st.rerun()
    with col3:
        with st.container(border=True):
            st.markdown("#### 🧮 수당 계산기")
            st.markdown("퇴직금, 연차수당, 주휴수당 계산")
            if st.button("바로가기", key="home_calc", use_container_width=True):
                st.session_state.page = "calculator"
                st.rerun()
    with col4:
        with st.container(border=True):
            st.markdown("#### 📞 신고/접수 경로")
            st.markdown("기관별 신고 절차와 방법 안내")
            if st.button("바로가기", key="home_report", use_container_width=True):
                st.session_state.page = "report"
                st.rerun()

    st.divider()
    st.markdown("### ⚡ 빠른 상담")
    if RAG_AVAILABLE:
        st.info("아래 질문을 클릭하면 법률 Q&A 페이지에서 상담을 시작합니다.")
        quick_qs = [
            "해고 통보는 언제 해야 하나요?",
            "야근 수당은 어떻게 계산하나요?",
            "연차 휴가는 며칠인가요?",
            "임금 체불 시 어떻게 해야 하나요?",
        ]
        cols = st.columns(2)
        for i, q in enumerate(quick_qs):
            if cols[i % 2].button(q, use_container_width=True, key=f"quick_{i}"):
                st.session_state.qa_messages = []
                st.session_state.page = "qa"
                st.rerun()
    else:
        st.info("💡 RAG 엔진이 연결되지 않았습니다. 좌측 메뉴를 통해 각 기능을 이용할 수 있습니다.")

    st.divider()
    st.markdown("### 📢 공지사항")
    st.markdown("""
    - 본 서비스가 제공하는 정보는 참고용이며 법적 효력이 없습니다.
    - 정확한 법률 판단이 필요한 경우 법률 전문가와 상담하시기 바랍니다.
    - 모든 상담 내용은 익명으로 처리되며, 서비스 개선을 위해 활용될 수 있습니다.
    """)


# ── Q&A ────────────────────────────────────────────────────
def render_qa():
    st.markdown('<p class="main-header">💬 법률 Q&A</p>', unsafe_allow_html=True)
    st.markdown("근로기준법 및 노동관계법에 관한 질문에 AI가 답변합니다.")

    # RAG 엔진 상태 확인
    engine = st.session_state.get("engine")
    if engine is None:
        st.warning("⚠️ RAG 엔진이 연결되지 않아 기본 정보 기반으로 답변을 제공합니다. LM Studio 실행 후 재시작해주세요.")

    # 채팅 히스토리 표시
    for msg in st.session_state.qa_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("progress"):
                with st.expander("📋 분석 진행 과정", expanded=True):
                    for node_name, label, detail in msg["progress"]:
                        st.markdown(f"**{label}**")
                        if isinstance(detail, str) and detail:
                            st.caption(detail[:300])
            if "sources" in msg and msg["sources"]:
                with st.expander(f"📚 근거 자료 ({len(msg['sources'])}개)", expanded=False):
                    for i, src in enumerate(msg["sources"], 1):
                        _render_source(src, i)
                        st.divider()

    # 입력창 (FAQ보다 먼저 처리해야 _qa_answer 후 FAQ 체크가 정확함)
    if prompt := st.chat_input("법률 질문을 입력해주세요..."):
        _qa_answer(prompt)

    # 초기 FAQ (빈 채팅일 때만 표시)
    if not st.session_state.qa_messages:
        st.markdown("### 💡 자주 묻는 질문")
        faqs = [
            "해고 통보는 언제 해야 하나요?",
            "야근 수당은 어떻게 계산하나요?",
            "연차 휴가는 며칠인가요?",
            "임금 체불 시 어떻게 해야 하나요?",
            "주 52시간 근무제란 무엇인가요?",
            "육아휴직 기간과 급여는?",
        ]
        cols = st.columns(2)
        for i, q in enumerate(faqs):
            if cols[i % 2].button(q, use_container_width=True, key=f"faq_{i}"):
                _qa_answer(q)


def _qa_answer(question: str):
    """Q&A 질문 처리 (st.chat_message + st.empty 실시간 텍스트 스트리밍)"""
    if not question.strip():
        return

    # 1. user 메시지를 session_state에 먼저 저장하고 직접 렌더링
    st.session_state.qa_messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    progress_log = []
    answer = ""
    sources = ""
    engine = st.session_state.get("engine")

    if engine is not None:
        try:
            # 2. assistant 채팅 버블 영역을 status 보다 먼저 생성
            with st.chat_message("assistant"):
                answer_placeholder = st.empty()

            # 3. status 박스로 진행상황 표시
            status = st.status("🔍 법률 분석 진행 중...", expanded=True)

            full_answer = ""
            for node_name, label, detail in engine.stream_answer(question):
                if node_name == "token":
                    # 채팅 버블 안에서 실시간 텍스트 갱신
                    full_answer += detail
                    answer_placeholder.markdown(full_answer + "▌")
                    status.update(
                        label=f"💡 답변 생성 중... ({len(full_answer)}자)",
                        state="running",
                    )

                elif node_name == "done":
                    answer_placeholder.markdown(full_answer)
                    answer = detail.get("answer", "")
                    sources = detail.get("sources", [])
                    status.update(label="✅ 분석 완료", state="complete")
                    progress_log.append(
                        ("done", "✅ 분석 완료", f"답변 {len(answer)}자, 출처 {len(sources)}건")
                    )

                else:
                    status.update(label=label, state="running")
                    if detail:
                        short = (detail[:80] + "...") if isinstance(detail, str) and len(detail) > 80 else detail
                        status.write(f"> {short}")
                    progress_log.append((node_name, label, detail if isinstance(detail, str) else ""))

            if full_answer:
                progress_log.append(
                    ("stream_token", "💡 답변 생성 (스트리밍)", f"총 {len(full_answer)}자")
                )

        except Exception as e:
            answer = f"⚠️ 오류가 발생했습니다: {str(e)}"
            sources = []
            st.error(f"RAG 엔진 오류: {e}")
    else:
        with st.chat_message("assistant"):
            st.markdown(_fallback_answer(question))

    st.session_state.qa_messages.append({
        "role": "assistant",
        "content": answer,
        "sources": sources,
        "progress": progress_log,
    })


def _render_source(src: dict, idx: int):
    """소스 문서 한 건을 Streamlit 마크다운으로 렌더링"""
    stype = src.get("type", "")
    if stype == "law":
        st.markdown(f"**{idx}. ⚖️ {src.get('law_name', '')} {src.get('article_no', '')}**")
        if src.get("article_title"):
            st.caption(f"📄 {src['article_title']}")
        if src.get("chapter_title"):
            st.caption(f"📂 {src['chapter_title']}")
    elif stype == "qna":
        st.markdown(f"**{idx}. 📖 {src.get('title', '')}**")
        if src.get("ref_no"):
            st.caption(f"📎 {src['ref_no']} ({src.get('ref_date', '')})")
    elif stype == "precedent":
        st.markdown(f"**{idx}. 📜 {src.get('case_no', '')}**")
        if src.get("category"):
            st.caption(f"📂 {src['category']}")
    else:
        st.markdown(f"**{idx}. {src.get('title', src.get('law_name', src.get('case_no', '문서')))}**")


def _fallback_answer(question: str) -> str:
    """RAG 엔진 없을 때 기본 응답"""
    question_lower = question.lower()

    if "해고" in question:
        return (
            "**해고 관련 안내**\n\n"
            "사용자는 정당한 이유 없이 근로자를 해고할 수 없습니다(근로기준법 제23조).\n\n"
            "**주요 절차:**\n"
            "1. 해고 사유와 시기를 서면으로 통지해야 함 (근로기준법 제27조)\n"
            "2. 해고 예고: 즉시 해고 시 30일분 통상임금 지급 (근로기준법 제26조)\n"
            "3. 부당해고 구제: 해고일로부터 3개월 이내 노동위원회에 신청\n\n"
            "정확한 법률 판단은 노동위원회나 법률 전문가와 상담하세요."
        )
    elif "야근" in question or "연장" in question or "시간외" in question:
        return (
            "**야근(연장근로) 수당 안내**\n\n"
            "1주 40시간을 초과하는 연장근로에 대해 통상임금의 50%를 가산하여 지급해야 합니다(근로기준법 제56조).\n\n"
            "**야간근로(22:00~06:00)**: 통상임금의 50% 추가 가산\n"
            "**휴일근로**: 통상임금의 50% 가산 (8시간 초과 시 100%)\n\n"
            "※ 예: 시급 10,000원인 근로자가 2시간 연장근로 시\n"
            "  → 10,000원 × 1.5 × 2시간 = 30,000원"
        )
    elif "연차" in question:
        return (
            "**연차 휴가 안내**\n\n"
            "근로기준법 제60조에 따른 연차 유급휴가:\n\n"
            "| 근속기간 | 연차 일수 |\n"
            "|---------|----------|\n"
            "| 1년 미만 | 월 1일 (최대 11일) |\n"
            "| 1년 | 15일 |\n"
            "| 2년 | 15일 |\n"
            "| 3년 | 16일 |\n"
            "| 4년 이상 | 1년마다 1일 추가 (최대 25일) |\n\n"
            "사용하지 못한 연차는 연차수당으로 보상받을 수 있습니다."
        )
    elif "임금체불" in question or "체불" in question:
        return (
            "**임금체불 시 대처 방법**\n\n"
            "임금은 매월 1회 이상 정기적으로 지급해야 합니다(근로기준법 제43조, 제36조).\n\n"
            "**대처 절차:**\n"
            "1. 사업주에게 임금 지급 요청 (문자·메일 등 기록 남길 것)\n"
            "2. 관할 고용노동청에 진정 제기 (☎ 1350)\n"
            "3. 근로감독관 조사 → 시정 지시\n"
            "4. 그래도 해결 안 되면 민사소송 또는 법률구조공단 상담(☎ 132)\n\n"
            "임금채권 소멸시효는 **3년**이므로 빠른 신고가 중요합니다."
        )
    else:
        return (
            "**법률 상담 안내**\n\n"
            "질문해주신 내용에 대해 정확한 답변을 제공하기 위해 "
            "보다 구체적인 정보가 필요합니다.\n\n"
            "**참고할 수 있는 상담처:**\n"
            "- 고용노동부 상담센터: ☎ 1350\n"
            "- 대한법률구조공단: ☎ 132\n"
            "- 노동위원회: www.nlrc.go.kr\n\n"
            "더 자세한 내용을 입력해주시면 맞춤형 정보를 제공해드리겠습니다."
        )


# ── 상황별 권리 안내 ──────────────────────────────────────
def render_rights():
    st.markdown('<p class="main-header">🔍 상황별 권리 안내</p>', unsafe_allow_html=True)
    st.markdown("부당해고, 임금체불 등 구체적인 상황에서의 권리와 법적 조치를 확인하세요.")

    col1, col2, col3 = st.columns(3)
    case_keys = list(RIGHTS_CASES.keys())
    for i, key in enumerate(case_keys):
        case = RIGHTS_CASES[key]
        col = [col1, col2, col3][i % 3]
        with col:
            if st.button(
                f"{case['icon']} **{key}**\n\n{case['desc']}",
                use_container_width=True,
                key=f"rights_btn_{i}",
                help=case['desc'],
            ):
                st.session_state.selected_case = key
                st.rerun()

    selected = st.session_state.get("selected_case")
    if not selected and case_keys:
        selected = case_keys[0]

    if selected and selected in RIGHTS_CASES:
        case = RIGHTS_CASES[selected]
        st.divider()
        st.markdown(f"## {case['icon']} {selected}")
        st.markdown(case["desc"])

        tab1, tab2, tab3, tab4 = st.tabs(["📜 관련 법 조항", "📋 조치 절차", "⏰ 신고 기한", "⚖️ 관련 판례"])

        with tab1:
            for law in case["laws"]:
                with st.container(border=True):
                    st.markdown(f"- {law}")

        with tab2:
            st.markdown("**권리 구제를 위한 절차:**")
            for j, proc in enumerate(case["procedures"], 1):
                st.markdown(f"**{j}.** {proc}")

        with tab3:
            st.markdown(f"**⏰ {case['deadline']}**")
            st.markdown("")
            with st.container(border=True):
                st.markdown("**💡 팁:** 신고 기한을 놓치면 권리를 보호받기 어려울 수 있으므로, 조기에 대응하는 것이 중요합니다.")

        with tab4:
            if case["precedents"]:
                for prec in case["precedents"]:
                    with st.container(border=True):
                        st.markdown(f"⚖️ {prec}")
            else:
                st.info("아직 등록된 판례가 없습니다.")


# ── 신고/접수 경로 ────────────────────────────────────────
def render_report():
    st.markdown('<p class="main-header">📞 신고/접수 경로 안내</p>', unsafe_allow_html=True)
    st.markdown("상황에 맞는 기관을 선택하여 신고 절차와 방법을 확인하세요.")

    # 기관 선택
    channels = list(REPORT_CHANNELS.keys())
    selected_ch = st.selectbox(
        "기관 선택",
        channels,
        format_func=lambda x: f"{REPORT_CHANNELS[x]['icon']} {x}",
    )

    if selected_ch:
        ch = REPORT_CHANNELS[selected_ch]
        st.markdown(f"### {ch['icon']} {selected_ch}")
        st.markdown(ch["desc"])

        col1, col2 = st.columns([1, 1])
        with col1:
            with st.container(border=True):
                st.markdown("#### 📞 연락처 및 접수 방법")
                for icon, method, detail in ch["methods"]:
                    st.markdown(f"- **{icon} {method}**: {detail}")

        with col2:
            with st.container(border=True):
                st.markdown("#### 🌐 관할 범위")
                st.markdown(ch["jurisdiction"])

        with st.container(border=True):
            st.markdown("#### 📋 처리 절차")
            for j, step in enumerate(ch["process"], 1):
                st.markdown(f"**{j}.** {step}")

        # 소멸시효 정보 함께 표시
        st.divider()
        with st.container(border=True):
            st.markdown("#### ⏰ 함께 보기: 소멸시효 정보")
            for title, desc in DEADLINE_INFO.items():
                st.markdown(f"- **{title}**: {desc}")


# ── 증거 관리 가이드 ──────────────────────────────────────
def render_evidence():
    st.markdown('<p class="main-header">📋 증거 관리 가이드</p>', unsafe_allow_html=True)
    st.markdown("상황별로 필요한 증거를 사전에 준비하여 권리 구제에 대비하세요.")

    case_keys = list(EVIDENCE_GUIDE.keys())
    selected = st.selectbox(
        "상황 선택",
        case_keys,
        format_func=lambda x: f"{EVIDENCE_GUIDE[x]['icon']} {x}",
    )

    if selected and selected in EVIDENCE_GUIDE:
        guide = EVIDENCE_GUIDE[selected]
        st.markdown(f"### {guide['icon']} {selected}")
        st.markdown(guide["desc"])

        st.markdown("#### 📌 필수 증거 목록")
        st.markdown("⭐ 중요도가 높은 순서대로 정리했습니다.")

        for item, importance, note in guide["items"]:
            stars = importance
            with st.container(border=True):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**{item}**")
                    st.caption(note)
                with col2:
                    st.markdown(f"<div style='text-align:right'>{stars}</div>", unsafe_allow_html=True)

        st.divider()
        with st.container(border=True):
            st.markdown("#### 💡 증거 수집 팁")
            st.markdown("""
            1. **원본 보존**: 모든 증거는 원본을 안전하게 보관하세요.
            2. **백업 필수**: 디지털 증거는 클라우드, 이메일 등 여러 곳에 백업.
            3. **타임라인 기록**: 사건 발생 일시, 장소, 관련자를 상세히 기록.
            4. **법적 효율 확인**: 녹음 증거는 대화 당사자 참여 시 증거 능력 인정.
            5. **사전 준비**: 문제 발생 전부터 체계적으로 증거를 수집·보관.
            """)


# ── 계산기 ────────────────────────────────────────────────
def render_calculator():
    st.markdown('<p class="main-header">🧮 수당 계산기</p>', unsafe_allow_html=True)
    st.markdown("퇴직금, 연차수당, 주휴수당, 최저임금을 자동으로 계산합니다.")

    calc_type = st.selectbox(
        "계산 유형 선택",
        ["퇴직금 계산", "연차수당 계산", "주휴수당 계산", "최저임금 위반 확인"],
    )

    if calc_type == "퇴직금 계산":
        _calc_retirement()
    elif calc_type == "연차수당 계산":
        _calc_annual()
    elif calc_type == "주휴수당 계산":
        _calc_weekly()
    elif calc_type == "최저임금 위반 확인":
        _calc_min_wage()


def _calc_retirement():
    st.markdown("### 퇴직금 계산기")
    st.caption("근로자퇴직급여 보장법에 따른 퇴직금을 계산합니다.")

    col1, col2 = st.columns(2)
    with col1:
        years = st.number_input("근속연수", min_value=0.0, max_value=50.0, value=3.0, step=0.5, format="%.1f")
    with col2:
        months = st.number_input("개월 수", min_value=0, max_value=11, value=0, step=1)

    total_days = int(years * 365 + months * 30.5)

    col1, col2 = st.columns(2)
    with col1:
        last_3m_salary = st.number_input("퇴직 전 3개월 총 임금 (원)", min_value=0, value=9000000, step=100000, format="%d")
    with col2:
        paid_days = st.number_input("3개월 총 일수", min_value=1, value=92, step=1)

    if paid_days > 0:
        avg_wage = last_3m_salary / paid_days
    else:
        avg_wage = 0

    st.info(f"📌 평균임금: 1일 **{avg_wage:,.0f}원**")

    if st.button("퇴직금 계산", use_container_width=True, type="primary"):
        if total_days >= 365 and avg_wage > 0:
            severance = avg_wage * 30 * (total_days / 365)
            st.markdown(f'<div class="calc-result">💰 예상 퇴직금: {severance:,.0f}원</div>', unsafe_allow_html=True)
            st.markdown(f"""
            **계산 상세:**
            - 1일 평균임금: {avg_wage:,.0f}원
            - 근속일수: 약 {total_days}일
            - 산식: {avg_wage:,.0f}원 × 30일 × ({total_days}일 ÷ 365일)
            """)
        else:
            if total_days < 365:
                st.error("❌ 퇴직금은 1년 이상 근속 시 발생합니다.")
            else:
                st.error("❌ 임금 정보를 확인해주세요.")

    with st.container(border=True):
        st.markdown("**📋 유의사항**")
        st.markdown("""
        - 퇴직금은 1년 이상 근속한 근로자에게 지급됩니다.
        - 4주간을 평균하여 1주 소정근로시간이 15시간 미만인 근로자는 제외됩니다.
        - 실제 금액은 회사 규정과 개인 상황에 따라 다를 수 있습니다.
        """)


def _calc_annual():
    st.markdown("### 연차수당 계산기")
    st.caption("사용하지 않은 연차휴가에 대한 수당을 계산합니다.")

    col1, col2 = st.columns(2)
    with col1:
        years_worked = st.number_input("근속연수", min_value=0, max_value=30, value=2, step=1)
    with col2:
        daily_wage = st.number_input("1일 통상임금 (원)", min_value=0, value=80000, step=10000, format="%d")

    # 근속연수별 연차 계산
    if years_worked < 1:
        annual_days = years_worked * 11  # 월 단위로
        st.info(f"📌 1년 미만 근로자: 월 1일 발생 (최대 11일)")
    else:
        annual_days = 15 + max(0, (years_worked - 1))  # 2년부터 1일씩 추가
        st.info(f"📌 {years_worked}년차: 연 {annual_days}일 발생 (최대 25일)")

    used_days = st.number_input("사용한 연차 일수", min_value=0, max_value=annual_days, value=0, step=1)
    remaining = max(0, annual_days - used_days)

    if remaining == 0:
        remaining = st.number_input("미사용 연차 일수 (자동)", min_value=0, value=5, step=1)

    if st.button("연차수당 계산", use_container_width=True, type="primary"):
        amount = daily_wage * remaining
        st.markdown(f'<div class="calc-result">💰 예상 연차수당: {amount:,.0f}원</div>', unsafe_allow_html=True)
        st.markdown(f"""
        **계산 상세:**
        - 1일 통상임금: {daily_wage:,.0f}원
        - 미사용 연차: {remaining}일
        - 산식: {daily_wage:,.0f}원 × {remaining}일 = {amount:,.0f}원
        """)


def _calc_weekly():
    st.markdown("### 주휴수당 계산기")
    st.caption("1주 소정근로시간 15시간 이상인 근로자의 주휴수당을 계산합니다.")

    col1, col2 = st.columns(2)
    with col1:
        hourly_wage = st.number_input("시급 (원)", min_value=0, value=10000, step=500, format="%d")
    with col2:
        weekly_hours = st.number_input("1주 소정근로시간", min_value=0, max_value=40, value=40, step=1)

    if weekly_hours >= 15:
        # 주휴수당 = (1주 근무시간 / 40) * 8 * 시급
        weekly_allowance = (weekly_hours / 40) * 8 * hourly_wage
        monthly_allowance = weekly_allowance * 4.345  # 월 평균 주 수

        if st.button("주휴수당 계산", use_container_width=True, type="primary"):
            st.markdown(f'<div class="calc-result">💰 주휴수당: 주 {weekly_allowance:,.0f}원</div>', unsafe_allow_html=True)
            st.markdown(f"""
            **계산 상세:**
            - 시급: {hourly_wage:,.0f}원
            - 1주 소정근로시간: {weekly_hours}시간
            - 주휴수당 산식: ({weekly_hours}시간 ÷ 40시간) × 8시간 × {hourly_wage:,.0f}원
            - 월 환산: 약 {monthly_allowance:,.0f}원

            **📌 주의사항:**
            - 주 15시간 미만 근로자는 주휴수당 지급 대상이 아닙니다.
            - 주휴수당은 소정근로일을 개근해야 지급됩니다.
            """)
    else:
        st.warning("⚠️ 1주 소정근로시간이 15시간 미만인 근로자는 주휴수당 지급 대상이 아닙니다.")


def _calc_min_wage():
    st.markdown("### 최저임금 위반 확인")
    st.caption("2025년 기준 최저시급 **10,030원**을 기준으로 확인합니다.")

    MIN_WAGE_2025 = 10030

    col1, col2 = st.columns(2)
    with col1:
        input_hourly = st.number_input("내 시급 (원)", min_value=0, value=10000, step=500, format="%d")
    with col2:
        daily_hours = st.number_input("1일 근무시간", min_value=1, max_value=24, value=8, step=1)
    weekly_days = st.number_input("주간 근무일수", min_value=1, max_value=7, value=5, step=1)

    if st.button("최저임금 확인", use_container_width=True, type="primary"):
        weekly_hours = daily_hours * weekly_days
        # 주휴포함 실질 시급 계산
        if weekly_hours >= 15:
            effective_hours = weekly_hours + (weekly_hours / 40) * 8
        else:
            effective_hours = weekly_hours
        effective_hourly = (input_hourly * weekly_hours) / effective_hours if effective_hours > 0 else 0

        ratio = (effective_hourly / MIN_WAGE_2025) * 100

        if effective_hourly >= MIN_WAGE_2025:
            st.markdown(f"""
            <div class="calc-result" style="color:{C_SUCCESS};">
            ✅ 최저임금 위반 아님
            </div>
            """, unsafe_allow_html=True)
            st.markdown(f"""
            - 실질 시급: {effective_hourly:,.0f}원
            - 최저시급(2025): {MIN_WAGE_2025:,}원
            - 최저임금 대비: {ratio:.1f}%
            """)
        else:
            shortage = (MIN_WAGE_2025 - effective_hourly) * effective_hours / weekly_hours * weekly_hours * 4.345
            st.markdown(f"""
            <div class="calc-result" style="color:{C_WARNING};">
            ❌ 최저임금 위반 의심
            </div>
            """, unsafe_allow_html=True)
            st.markdown(f"""
            - 실질 시급: {effective_hourly:,.0f}원
            - 최저시급(2025): {MIN_WAGE_2025:,}원
            - 최저임금 대비: {ratio:.1f}%
            - 예상 월 손해: 약 {shortage:,.0f}원

            **📞 고용노동부 상담센터 1350으로 신고하세요.**
            """, unsafe_allow_html=True)


# ── 서류 작성 도우미 ──────────────────────────────────────
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
{f"3. 금 {amount}원을 2025년 7월 31일까지 지급하십시오." if amount else ""}

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


# ── 근로계약서 분석 ───────────────────────────────────────
def render_contract():
    st.markdown('<p class="main-header">🔎 근로계약서 독소조항 분석</p>', unsafe_allow_html=True)
    st.markdown("근로계약서 내용을 입력하거나 붙여넣으면 불리한 조항(독소조항)을 분석하여 설명해드립니다.")

    mode = st.session_state.get("mode", "easy")

    # 독소조항 DB (샘플)
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
            "explain_expert": "부당해고 구제: 대법원은 경업금지약정이 근로자의 직업선택의 자유를 침해할 경우 무효라고 판시했습니다. 합리적 범위(기간 1~2년, 지역 제한, 보상 수반)를 초과하면 부당합니다.",
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
                        danger_color = {"위험": "red", "주의": "orange"}.get(issue["danger"], "gray")
                        with st.container(border=True):
                            st.markdown(f"#### {issue['pattern']}  🟠{issue['danger']}")
                            if mode == "easy":
                                st.markdown(f"**📌 설명:** {issue['explain_easy']}")
                            else:
                                st.markdown(f"**📌 법적 분석:** {issue['explain_expert']}")
                else:
                    st.success("✅ 입력된 내용에서 일반적인 독소조항이 발견되지 않았습니다. 다만, 전문가의 추가 검토를 권장합니다.")

                st.divider()
                with st.info("💡 **면책 안내**: 이 분석은 참고용이며 법적 효력이 없습니다. 중요한 계약은 반드시 법률 전문가의 검토를 받으세요."):
                    pass

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


# ============================================================
# 사이드바
# ============================================================
def render_sidebar():
    with st.sidebar:
        # 로고/타이틀
        st.markdown(
            f"<div style='text-align: center; padding: 1rem 0;'>"
            f"<div style='font-size: 2.5rem;'>⚖️</div>"
            f"<div style='font-size: 1.2rem; font-weight: 700; color: {C_PRIMARY};'>{APP_NAME}</div>"
            f"<div style='font-size: 0.75rem; color: #888;'>{APP_SUBTITLE}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

        st.divider()

        # ── 메뉴 그룹 ──
        current_page = st.session_state.get("page", "home")

        # Define menu groups
        menu_groups = {}
        for page_id, info in PAGES.items():
            group = info["group"]
            if group not in menu_groups:
                menu_groups[group] = []
            menu_groups[group].append((page_id, info))

        for group_name, items in menu_groups.items():
            st.markdown(f"<div style='font-size: 0.7rem; color: #999; text-transform: uppercase; letter-spacing: 0.5px; margin: 0.5rem 0;'>{group_name}</div>", unsafe_allow_html=True)
            for page_id, info in items:
                active = current_page == page_id
                btn_style = (
                    f"background-color: #E3F2FD; border-left: 3px solid {C_ACCENT}; font-weight: 600;"
                    if active else ""
                )
                if st.button(
                    f"{info['icon']} {info['label']}",
                    key=f"menu_{page_id}",
                    use_container_width=True,
                    help=f"{info['label']} 페이지로 이동",
                ):
                    st.session_state.page = page_id
                    st.rerun()

        st.divider()

        # ── 모드 토글 ──
        st.markdown("#### 🎯 설명 모드")
        current_mode = st.session_state.get("mode", "easy")
        mode_labels = {"easy": "쉬운 말로 설명", "expert": "전문적으로 설명"}
        new_mode = st.radio(
            "설명 모드",
            options=["easy", "expert"],
            format_func=lambda x: mode_labels[x],
            index=0 if current_mode == "easy" else 1,
            label_visibility="collapsed",
            key="mode_radio",
        )
        if new_mode != current_mode:
            st.session_state.mode = new_mode
            st.rerun()

        if current_mode == "easy":
            st.caption("법률 용어를 쉽게 풀어서 설명합니다.")
        else:
            st.caption("법조문과 판례를 포함한 전문적인 설명을 제공합니다.")

        st.divider()

        # ── 시스템 상태 ──
        with st.expander("🔧 시스템 상태", expanded=False):
            if RAG_AVAILABLE:
                engine = st.session_state.get("engine")
                if engine is not None:
                    try:
                        health = engine.check_health()
                        st.markdown(f"🤖 LLM: {'✅ 연결됨' if health['llm_connected'] else '❌ 연결 안 됨'}")
                        st.markdown(f"📚 법령 DB: {health['document_count']}개 조문")
                    except Exception:
                        st.markdown("🤖 LLM: ❌ 상태 확인 불가")
                else:
                    st.markdown("🤖 LLM: ❌ 엔진 미초기화 (LM Studio 필요)")
            else:
                st.markdown("🤖 LLM: ⚠️ 모듈 미설치")
            st.markdown(f"💬 설명 모드: {'쉬운 말' if current_mode == 'easy' else '전문가'}")
            st.markdown(f"🆔 세션: {st.session_state.get('session_id', '-')[:8]}...")

        # ── 푸터 ──
        st.divider()
        st.markdown(
            f"<div style='text-align: center; color: #bbb; font-size: 0.7rem; padding-bottom: 0.5rem;'>"
            f"본 서비스는 참고용이며 법적 효력이 없습니다."
            f"</div>",
            unsafe_allow_html=True,
        )


# ============================================================
# 메인 라우터
# ============================================================
def main():
    # 초기화
    init_session()
    load_css()

    # 사이드바 렌더링
    render_sidebar()

    # 페이지 라우팅
    page = st.session_state.page

    if page == "home":
        render_home()
    elif page == "qa":
        render_qa()
    elif page == "rights":
        render_rights()
    elif page == "report":
        render_report()
    elif page == "evidence":
        render_evidence()
    elif page == "calculator":
        render_calculator()
    elif page == "docwriter":
        render_docwriter()
    elif page == "contract":
        render_contract()
    else:
        render_home()

    # 푸터
    st.markdown(
        f"<div class='footer'>"
        f"⚖️ 노동 법률 AI 어시스턴트 v1.0 | "
        f"본 서비스는 참고용이며 법적 효력이 없습니다. | "
        f"© 2025"
        f"</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
