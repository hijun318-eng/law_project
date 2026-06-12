"""
LLM 및 Embedding 설정

LLM_PROVIDER 환경변수로 OpenAI / 로컬 전환:
  - LLM_PROVIDER=openai (기본값): OpenAI API (gpt-5.4-nano + text-embedding-3-small)
  - LLM_PROVIDER=local: LM Studio (Qwen2.5 3B) + sentence-transformers (multilingual-e5-small)
"""
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings

load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")  # "openai" | "local"

if LLM_PROVIDER == "local":
    # ── 로컬 LLM (LM Studio: OpenAI 호환 API) ──
    llm = ChatOpenAI(
        model=os.getenv("LOCAL_LLM_MODEL", "qwen2.5-3b-instruct"),
        temperature=0,
        base_url=os.getenv("LOCAL_LLM_BASE_URL", "http://localhost:1234/v1"),
        api_key="not-needed",
    )
    # ── 로컬 임베딩 (sentence-transformers) ──
    from langchain_huggingface import HuggingFaceEmbeddings

    class LocalEmbeddings(HuggingFaceEmbeddings):
        """E5 모델의 query/passage prefix를 자동으로 추가합니다."""

        def embed_documents(self, texts):
            return super().embed_documents([f"passage: {t}" for t in texts])

        def embed_query(self, text):
            return super().embed_query(f"query: {text}")

    embedding = LocalEmbeddings(
        model_name=os.getenv("LOCAL_EMBEDDING_MODEL", "intfloat/multilingual-e5-small"),
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
else:
    # ── OpenAI API ──
    llm = ChatOpenAI(
        model="gpt-5.4-nano",
        temperature=0,
    )
    embedding = OpenAIEmbeddings(
        model="text-embedding-3-small"
    )
