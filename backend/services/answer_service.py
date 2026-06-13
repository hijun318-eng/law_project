import re

from backend.config import llm
from backend.utils.prompt_loader import load_prompt
from string import Template

class AnswerService:

    def __init__(self):
        self.prompt_template = load_prompt("answer_prompt.md")

    def generate(self, law_analysis, precedent_analysis, question, law_source: str = "unknown"):

        law_context = self._build_law_context(law_analysis)

        precedent_context = "\n\n".join(
            (precedent_analysis or "").split("\n\n")[:3]
        )

        prompt = Template(self.prompt_template).safe_substitute(
            law_context=law_context,
            precedent_context=precedent_context,
            question=question,
            law_source=law_source,
        )

        answer = llm.invoke(prompt).content

        return {
            "final_answer": answer
        }

    @staticmethod
    def _build_law_context(law_analysis: list) -> str:
        parts = []
        seen = set()

        for d in law_analysis[:3]:
            aid = f"{d['law_name']}_{d['article_no']}"
            if aid in seen:
                continue
            seen.add(aid)
            parts.append(
                f"<article>\n"
                f"<source>{d['law_name']} {d['article_no']} {d['article_title']}</source>\n"
                f"<content>{d['page_content']}</content>\n"
                f"</article>"
            )

        return "\n".join(parts)


answer_service = AnswerService()