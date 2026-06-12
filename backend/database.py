"""
Chroma Vector DB 연결

LLM_PROVIDER에 따라 다른 벡터DB 경로 사용:
  - openai: vector_db/laws, vector_db/precedents, vector_db/qna
  - local:  vector_db/laws_local, vector_db/precedents_local, vector_db/qna_local

사전에 init_db.py를 실행하여 벡터DB를 생성해야 합니다.
"""
from langchain_chroma import Chroma
from backend.config import embedding, LLM_PROVIDER

DB_SUFFIX = "_local" if LLM_PROVIDER == "local" else ""

law_db = Chroma(
    persist_directory=f"vector_db/laws{DB_SUFFIX}",
    embedding_function=embedding
)

precedent_db = Chroma(
    persist_directory=f"vector_db/precedents{DB_SUFFIX}",
    embedding_function=embedding
)

qna_db = Chroma(
    persist_directory=f"vector_db/qna{DB_SUFFIX}",
    embedding_function=embedding
)
