import argparse
import json
from pathlib import Path

from backend.services.precedent_summary_service import (
    summary_service
)

SOURCE_ROOT = Path("data/process/case")
CACHE_ROOT = Path("data/cache/sac")


def run(force=False):

    CACHE_ROOT.mkdir(
        parents=True,
        exist_ok=True
    )

    files = sorted(
        SOURCE_ROOT.rglob("*.json")
    )

    print(f"{len(files)}개 판례 발견")

    for idx, json_file in enumerate(files, 1):

        case_no = json_file.stem

        cache_file = (
            CACHE_ROOT /
            f"{case_no}.json"
        )

        if cache_file.exists() and not force:
            print(
                f"[{idx}] SKIP {case_no}"
            )
            continue

        print(
            f"[{idx}] SAC 생성: {case_no}"
        )

        try:

            with open(
                json_file,
                encoding="utf-8"
            ) as f:
                items = json.load(f)

            if isinstance(items, dict):
                items = [items]

            content = "\n\n".join(
                item.get(
                    "page_content",
                    ""
                )
                for item in items
            )

            metadata = (
                items[0].get(
                    "metadata",
                    {}
                )
                if items
                else {}
            )

            search_text, brief_text = (
                summary_service.make_dual_summary(
                    content
                )
            )

            save_data = {
                "case_no": case_no,
                "metadata": metadata,
                "search": search_text,
                "brief": brief_text
            }

            with open(
                cache_file,
                "w",
                encoding="utf-8"
            ) as f:
                json.dump(
                    save_data,
                    f,
                    ensure_ascii=False,
                    indent=2
                )

        except Exception as e:
            print(
                f"[ERROR] {case_no}: {e}"
            )

    print("SAC 생성 완료")


if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--force",
        action="store_true"
    )

    args = parser.parse_args()

    run(force=args.force)