"""
LLM 및 Embedding 설정
"""
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings

load_dotenv(dotenv_path=".env")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

llm = ChatOpenAI(
    model="gpt-5.4-nano",
    temperature=0
)

embedding = OpenAIEmbeddings(
    model="text-embedding-3-small"
)