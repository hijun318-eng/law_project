"""
최종 답변 생성 서비스
법령/판례 컨텍스트를 조합하여 LLM 답변을 생성합니다.
"""
import re

from backend.config import llm
from backend.utils.prompt_loader import load_prompt


class AnswerService:

    def __init__(self):
        self.prompt_template = load_prompt("answer_prompt.md")

    def generate(self, law_analysis, precedent_analysis, question):

        law_context = self._build_law_context(law_analysis)

        precedent_context = "\n\n".join(
            (precedent_analysis or "").split("\n\n")[:3]
        )

        prompt = self.prompt_template
        prompt = prompt.replace("{law_context}", law_context)
        prompt = prompt.replace("{precedent_context}", precedent_context)
        prompt = prompt.replace("{question}", question)

        answer = llm.invoke(prompt).content

        used_precedents = re.findall(
            r"\b\d{4}[가-힣]{1,3}\d+\b",
            answer
        )

        return {
            "final_answer": answer,
            "used_precedents": used_precedents,
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