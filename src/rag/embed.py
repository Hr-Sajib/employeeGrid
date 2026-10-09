import httpx
from fastapi import HTTPException
from src.utils.settings import settings

BATCH_SIZE = 64


def embed_texts(texts: list[str]) -> list[list[float]]:
    vectors = []
    for i in range(0, len(texts), BATCH_SIZE):
        res = httpx.post(
            "https://openrouter.ai/api/v1/embeddings",
            headers={"Authorization": f"Bearer {settings.OPENROUTER_API_KEY}"},
            json={"model": settings.EMBEDDING_MODEL, "input": texts[i:i + BATCH_SIZE], "dimensions": settings.EMBEDDING_DIM},
            timeout=120,
        )
        if res.status_code != 200:
            raise HTTPException(502, f"Embedding error: {res.text}")
        vectors += [d["embedding"] for d in sorted(res.json()["data"], key=lambda d: d["index"])]
    return vectors
