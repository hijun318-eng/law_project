# backend/news_engine.py 
import json
import logging
from backend.tools.registry import registry
from backend.utils.prompt_loader import load_prompt
from backend.news.news_normalizer import normalize_news

logger = logging.getLogger(__name__)

MAX_STEPS      = 5
MAX_TOOL_RETRY = 2  # 동일 tool 연속 허용 횟수

class NewsEngine:
    def __init__(self, llm):
        self.llm    = llm
        self.prompt = load_prompt("news_prompt.md")

    def answer(self, question: str) -> dict:
        tool_specs = json.dumps(registry.list_specs(), ensure_ascii=False, indent=2)
        messages = [
            {"role": "system", "content": self.prompt.replace("{tool_specs}", tool_specs)},
            {"role": "user",   "content": question},
        ]

        steps: list[dict]  = []
        action_history: list[str] = []
        valid_tools = registry.list_tools()

        for step in range(MAX_STEPS):
            res  = self.llm.invoke(messages)
            text = res.content.strip()
            messages.append({"role": "assistant", "content": text})
            logger.debug(f"[Step {step}] LLM output:\n{text}")

            # ── Final Answer ──────────────────────────────────
            if "Final Answer:" in text:
                if not steps: 
                    messages.append({
                        "role": "user",
                        "content": (
                            "검색을 먼저 수행해야 합니다. "
                            "Final Answer 전에 반드시 news_search tool을 호출하세요. "
                            "사용자 질문에서 키워드를 2~3가지로 확장하여 검색하세요."
                        ),
                    })
                    continue
                
                final = text.split("Final Answer:", 1)[-1].strip()
                logger.info(f"Final Answer reached at step {step}")
                return {"answer": final, "steps": steps}

            # ── Action 파싱 ───────────────────────────────────
            action = self._parse_action(text)
            if not action:
                logger.warning(f"[Step {step}] No valid Action found.")
                messages.append({
                    "role": "user",
                    "content": (
                        "Action이 감지되지 않았습니다. "
                        "반드시 아래 형식으로 작성하세요:\n"
                        'Action: {"tool": "news_search", "args": {"query": "검색어"}}'
                    ),
                })
                continue

            tool = action.get("tool")
            args = action.get("args", {})

            # ── Tool 유효성 검사 ──────────────────────────────
            if tool not in valid_tools:
                messages.append({
                    "role": "user",
                    "content": f"ERROR: '{tool}'은 존재하지 않는 tool입니다. 사용 가능: {sorted(valid_tools)}",
                })
                continue

            # ── Loop detection (이력 기반) ────────────────────
            action_key = json.dumps(action, sort_keys=True, ensure_ascii=False)
            recent = action_history[-MAX_TOOL_RETRY:]
            if len(recent) == MAX_TOOL_RETRY and all(k == action_key for k in recent):
                logger.warning("Tool loop detected. Stopping.")
                return {
                    "answer": "동일한 검색이 반복되어 답변을 제공할 수 없습니다. 질문을 구체적으로 바꿔주세요.",
                    "steps":   steps,
                    "warning": True,
                }
            action_history.append(action_key)

            # ── Tool 실행 ─────────────────────────────────────
            result = registry.run(tool, **args)

            if not result.success:
                obs = {"error": result.error, "evidence": []}
                logger.error(f"Tool '{tool}' failed: {result.error}")
            else:
                if tool == "news_search":
                    obs = normalize_news(
                        args.get("query", ""),
                        result.data["results"],
                        top_k=5,
                    )
                else:
                    obs = result.data

            steps.append({"step": step, "action": action, "observation": obs})

            # ── Observation 주입 ──────────────────────────────
            evidence_list = obs.get("evidence", []) if isinstance(obs, dict) else []

            if not evidence_list:
                rule = (
                    "검색 결과가 없습니다. "
                    "다른 키워드나 법령명으로 반드시 재검색하세요. "
                    "포기하지 말고 유사어로 시도하세요."
                )
            else:
                rule = (
                    "evidence 외 정보 사용 금지. "
                    "evidence가 질문을 충분히 커버하지 못하면 "
                    "Final Answer 대신 다른 쿼리로 재검색하세요."
                )

            messages.append({
                "role": "user",
                "content": json.dumps(
                    {"rule": rule, "evidence": obs},
                    ensure_ascii=False,
                ),
            })

        logger.warning("MAX_STEPS reached without Final Answer.")
        return {"answer": "분석 한도를 초과했습니다. 질문을 더 구체적으로 입력해주세요.", "steps": steps, "warning": True}

    def _parse_action(self, text: str) -> dict | None:
        if "Action:" not in text:
            return None
        try:
            part  = text.split("Action:", 1)[1]
            start = part.find("{")
            if start == -1:
                return None

            depth = 0
            end   = -1
            for i, ch in enumerate(part[start:], start):
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        end = i
                        break

            if end == -1:
                return None

            raw = part[start:end + 1].replace("\n", " ").replace("  ", " ")
            return json.loads(raw)

        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Action parse failed: {e}")
            return None