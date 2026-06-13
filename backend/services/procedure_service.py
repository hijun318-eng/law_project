from pathlib import Path
import json

from backend.config import llm
from backend.constants.procedure_map import PROCEDURE_MAP
from backend.utils.prompt_loader import load_prompt


class ProcedureService:

    def __init__(self):
        self.prompt_template = load_prompt("procedure_prompt.md")

    def generate(self, used_precedents: list[str]) -> str:

        if not used_precedents:
            return "관련 판례를 찾을 수 없습니다."

        precedent_no = used_precedents[0]

        root = Path("./data/process/case")

        category = None

        for path in root.rglob(f"{precedent_no}.json"):
            with open(path, "r", encoding="utf-8") as f:
                precedent = json.load(f)
            category = precedent[0]["metadata"]["category"]
            break

        if not category:
            return "판례 카테고리를 찾을 수 없습니다."

        info = PROCEDURE_MAP.get(category)

        if not info:
            return f"{category} 카테고리에 대한 절차 정보가 없습니다."

        prompt = self.prompt_template.format(
            category=category,
            agency=info["agency"],
            worker_actions="\n".join(info["worker_actions"]),
            evidence="\n".join(info["evidence"]),
            deadline=info["deadline"] or "없음",
        )

        return llm.invoke(prompt).content


procedure_service = ProcedureService()