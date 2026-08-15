from functools import lru_cache

from app.core.config import get_settings
from langchain_openai import ChatOpenAI


@lru_cache(maxsize=1)
def get_turn_interpreter_llm():
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required for the LLM turn interpreter.")

    return ChatOpenAI(
        model=settings.turn_interpreter_model,
        api_key=settings.openai_api_key,
        temperature=0,
    )