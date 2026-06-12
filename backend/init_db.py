"""
벡터DB 생성 스크립트 (1회 실행)

data/process/의 JSON 파일을 읽어 Chroma 벡터DB를 생성합니다.
실행: python -m backend.init_db
"""
import argparse
import json
import sys
from pathlib import Path

from langchain_core.documents import Document
from langchain_chroma import Chroma

from backend.config import embedding

# 데이터 루트
DATA_ROOT = Path("data/process")


def build_law_db(force: bool = False) -> Chroma:
    """법령 JSON → Chroma DB 생성"""
    law_root = DATA_ROOT / "법률"

    if not law_root.exists():
        raise FileNotFoundError(
            f"폴더가 없습니다: {law_root.resolve()}\n"
            "law_parser.py의 process_all_pdfs()를 먼저 실행해 주세요."
        )

    json_files = sorted(law_root.rglob("*.json"))
    if not json_files:
        raise FileNotFoundError(
            f"{law_root} 안에 JSON 파일이 없습니다.\n"
            "law_parser.py의 process_all_pdfs()를 먼저 실행해 주세요."
        )

    print(f"JSON 파일 {len(json_files)}개 발견")
    all_law_docs = []

    for json_file in json_files:
        print(f"로딩 중: {json_file.name}")
        with open(json_file, "r", encoding="utf-8") as f:
            items = json.load(f)

        if isinstance(items, dict):
            items = [items]

        for item in items:
            meta = item.get("metadata", {})
            chapter_title = meta.get("chapter_title", "")
            article_title = meta.get("article_title", "")
            page_content = item.get("page_content", "")

            embedding_text = f"{chapter_title}\n\n{article_title}\n\n{page_content}"
            embedding_text = " ".join(embedding_text.split())

            all_law_docs.append(
                Document(page_content=embedding_text, metadata=meta)
            )

    if not all_law_docs:
        raise ValueError("로드된 법령 Document가 0개입니다.")

    print(f"\n총 {len(all_law_docs)}개 법령 Document 로드 완료")
    print("\n========== Document 예시 ==========")
    print(all_law_docs[0].page_content[:500])
    print("\n========== Metadata 예시 ==========")
    for k, v in all_law_docs[0].metadata.items():
        print(f"{k}: {v}")

    db_path = "vector_db/laws"
    if force:
        import shutil
        shutil.rmtree(db_path, ignore_errors=True)

    law_db = Chroma.from_documents(
        documents=all_law_docs,
        embedding=embedding,
        persist_directory=db_path,
    )

    print("\n법령 DB 생성 완료")
    print(f"저장 위치: {db_path}")
    return law_db


def build_precedent_db(force: bool = False) -> Chroma:
    """판례 JSON → Chroma DB 생성"""
    precedent_root = DATA_ROOT / "판례"

    if not precedent_root.exists():
        raise FileNotFoundError(
            f"폴더가 없습니다: {precedent_root.resolve()}"
        )

    all_docs = []
    for json_file in sorted(precedent_root.rglob("*.json")):
        print(f"로딩 중: {json_file.name}")
        with open(json_file, "r", encoding="utf-8") as f:
            items = json.load(f)

        if isinstance(items, dict):
            items = [items]

        for item in items:
            doc = Document(
                page_content=item["page_content"],
                metadata=item.get("metadata", {}),
            )
            all_docs.append(doc)

    print(f"\n총 {len(all_docs)}개 판례 Document 로드 완료")
    if all_docs:
        print("[메타데이터 예시]", all_docs[0].metadata)

    db_path = "vector_db/precedents"
    if force:
        import shutil
        shutil.rmtree(db_path, ignore_errors=True)

    precedent_db = Chroma.from_documents(
        documents=all_docs,
        embedding=embedding,
        persist_directory=db_path,
    )

    print("판례 DB 생성 완료")
    return precedent_db


def build_qna_db(force: bool = False) -> Chroma:
    """질의회시 JSON → Chroma DB 생성"""
    qna_root = DATA_ROOT / "질의회시집"

    if not qna_root.exists():
        raise FileNotFoundError(
            f"폴더가 없습니다: {qna_root.resolve()}"
        )

    qna_docs = []
    for json_file in sorted(qna_root.rglob("*.json")):
        print(f"로딩 중: {json_file.name}")
        with open(json_file, "r", encoding="utf-8") as f:
            items = json.load(f)

        if isinstance(items, dict):
            items = [items]

        for item in items:
            doc = Document(
                page_content=item["page_content"],
                metadata=item.get("metadata", {}),
            )
            qna_docs.append(doc)

    print(f"\n총 {len(qna_docs)}개 질의회시 Document 로드 완료")
    if qna_docs:
        print("[임베딩 대상 예시]", qna_docs[0].page_content)
        print("[메타데이터 키]", list(qna_docs[0].metadata.keys()))

    db_path = "vector_db/qna"
    if force:
        import shutil
        shutil.rmtree(db_path, ignore_errors=True)

    qna_db = Chroma.from_documents(
        documents=qna_docs,
        embedding=embedding,
        persist_directory=db_path,
    )

    print("질의회시 DB 생성 완료")
    return qna_db


def main():
    parser = argparse.ArgumentParser(description="벡터DB 생성 스크립트")
    parser.add_argument(
        "--force",
        action="store_true",
        help="기존 벡터DB를 삭제하고 다시 생성합니다.",
    )
    parser.add_argument(
        "--db",
        choices=["law", "precedent", "qna", "all"],
        default="all",
        help="생성할 DB (기본값: all)",
    )
    args = parser.parse_args()

    dbs = {
        "law": ("법령", build_law_db),
        "precedent": ("판례", build_precedent_db),
        "qna": ("질의회시", build_qna_db),
    }

    if args.db == "all":
        targets = dbs.values()
    else:
        targets = [dbs[args.db]]

    for name, builder in targets:
        print(f"\n{'='*60}")
        print(f"{name} DB 생성 시작")
        print(f"{'='*60}")
        try:
            builder(force=args.force)
            print(f"{name} DB 생성 완료\n")
        except (FileNotFoundError, ValueError) as e:
            print(f"[ERROR] {name} DB 생성 실패: {e}", file=sys.stderr)

    print("\n모든 DB 생성 작업 완료.")


if __name__ == "__main__":
    main()
