"""
뉴스 엔진 통합 테스트
실행: python -m backend.test_news
"""
import json
import sys
import textwrap
from datetime import datetime

# ── ANSI 색상 ──────────────────────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

# ── 출력 헬퍼 ──────────────────────────────────────────────
def section(title: str):
    bar = "─" * 60
    print(f"\n{BOLD}{CYAN}{bar}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{bar}{RESET}")

def ok(msg: str):
    print(f"  {GREEN}✔  {msg}{RESET}")

def fail(msg: str):
    print(f"  {RED}✘  {msg}{RESET}")

def info(label: str, value):
    print(f"  {YELLOW}{label:<18}{RESET} {value}")

def print_news_item(idx: int, item: dict):
    print(f"\n  {BOLD}[{idx}] {item.get('title', '제목 없음')}{RESET}")
    desc = item.get("description", "")
    wrapped = textwrap.fill(desc, width=70, initial_indent="       ", subsequent_indent="       ")
    print(wrapped)
    info("날짜", item.get("pubDate", "-"))
    info("링크", item.get("link", "-"))
    score = item.get("score")
    if score is not None:
        info("관련도 점수", f"{score:.4f}")

def print_step(step: dict):
    action = step.get("action", {})
    obs    = step.get("observation", {})
    print(f"\n  {YELLOW}▶ Step {step.get('step', '?')}{RESET}")
    info("Tool", action.get("tool", "-"))
    info("Query", action.get("args", {}).get("query", "-"))
    count = obs.get("count", len(obs.get("evidence", [])))
    info("결과 수", count)


# ══════════════════════════════════════════════════════════
# TEST 1 — NewsSearchTool 단독
# ══════════════════════════════════════════════════════════
def test_tool():
    section("TEST 1 · NewsSearchTool 단독 실행")
    try:
        from backend.tools.news_search_tool import NewsSearchTool

        tool   = NewsSearchTool()
        result = tool.run(query="중대재해처벌법 최신 판결")

        if not result.success:
            fail(f"API 호출 실패: {result.error}")
            return False

        items = result.data.get("results", [])
        ok(f"API 호출 성공 — {len(items)}건 수신")
        info("검색어", result.data.get("query", "-"))

        for i, item in enumerate(items, 1):
            print_news_item(i, item)

        return True

    except Exception as e:
        fail(f"예외 발생: {e}")
        return False


# ══════════════════════════════════════════════════════════
# TEST 2 — ToolRegistry
# ══════════════════════════════════════════════════════════
def test_registry():
    section("TEST 2 · ToolRegistry 확인")
    try:
        from backend.tools.registry import registry
        from backend.tools.news_search_tool import NewsSearchTool

        # 중복 등록 방지
        if "news_search" not in registry.list_tools():
            registry.register(NewsSearchTool())

        specs = registry.list_specs()
        ok(f"등록된 tool 수: {len(specs)}")

        for spec in specs:
            print(f"\n  {BOLD}· {spec['name']}{RESET}")
            info("설명", spec.get("description", "-"))
            required = spec.get("inputSchema", {}).get("required", [])
            info("필수 인자", ", ".join(required) if required else "없음")
            props = spec.get("inputSchema", {}).get("properties", {})
            for pname, pinfo in props.items():
                default = pinfo.get("default", "")
                default_str = f"  (기본값: {default})" if default != "" else ""
                info(f"  - {pname}", f"{pinfo.get('description', '')}{default_str}")

        return True

    except Exception as e:
        fail(f"예외 발생: {e}")
        return False


# ══════════════════════════════════════════════════════════
# TEST 3 — NewsEngine (ReAct 전체 흐름)
# ══════════════════════════════════════════════════════════
def test_engine():
    section("TEST 3 · NewsEngine 전체 실행")
    try:
        from backend.tools.registry import registry
        from backend.tools.news_search_tool import NewsSearchTool
        from backend.news_engine import NewsEngine
        from backend.config import llm

        if "news_search" not in registry.list_tools():
            registry.register(NewsSearchTool())

        engine   = NewsEngine(llm=llm)
        question = "최근 노동법 개정 내용 알려줘"

        info("질문", question)
        print()

        start  = datetime.now()
        result = engine.answer(question)
        elapsed = (datetime.now() - start).total_seconds()

        # 경고 여부
        if result.get("warning"):
            fail(f"경고 발생: {result.get('answer')}")
            return False

        ok(f"정상 완료 ({elapsed:.1f}초)")

        # ReAct Steps
        steps = result.get("steps", [])
        if steps:
            print(f"\n  {BOLD}[ ReAct Steps — {len(steps)}회 ]{RESET}")
            for s in steps:
                print_step(s)
        else:
            fail("steps가 비어있습니다 (tool 미호출 가능성)")

        # 최종 답변
        answer = result.get("answer", "")
        print(f"\n  {BOLD}{GREEN}[ Final Answer ]{RESET}")
        print()
        for line in answer.splitlines():
            print(f"  {line}")

        return True

    except ImportError as e:
        fail(f"import 실패 (config.py / llm 확인 필요): {e}")
        return False
    except Exception as e:
        fail(f"예외 발생: {e}")
        import traceback
        traceback.print_exc()
        return False


# ══════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════
if __name__ == "__main__":
    print(f"\n{BOLD}뉴스 엔진 통합 테스트  ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}){RESET}")

    results = {
        "tool":     test_tool(),
        "registry": test_registry(),
        "engine":   test_engine(),
    }

    # 최종 요약
    section("테스트 결과 요약")
    all_pass = True
    for name, passed in results.items():
        if passed:
            ok(f"TEST {name:<12} PASS")
        else:
            fail(f"TEST {name:<12} FAIL")
            all_pass = False

    print()
    if all_pass:
        print(f"  {BOLD}{GREEN}모든 테스트 통과{RESET}\n")
        sys.exit(0)
    else:
        print(f"  {BOLD}{RED}일부 테스트 실패 — 위 로그를 확인하세요{RESET}\n")
        sys.exit(1)