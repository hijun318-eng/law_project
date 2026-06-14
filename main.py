"""
노동 법률 종합 AI 어시스턴트 — 진입점
============================================
Streamlit 실행: streamlit run main.py

frontend/app.py 에서 실제 main()을 import 합니다.
"""
import os
import sys

# ── 경로 설정 ──────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
LAW_TEST_DIR = os.path.join(PROJECT_ROOT, "law_test")
for p in [PROJECT_ROOT, LAW_TEST_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

from frontend.app import main

if __name__ == "__main__":
    main()
