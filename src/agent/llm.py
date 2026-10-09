from langchain_openai import ChatOpenAI
from src.utils.settings import settings


def make_llm(model: str) -> ChatOpenAI:
    return ChatOpenAI(
        model=model,
        base_url="https://openrouter.ai/api/v1",
        api_key=settings.OPENROUTER_API_KEY,
        timeout=60,
        extra_body={"provider": {"sort": "latency"}, "reasoning": {"effort": "low"}},
    )
