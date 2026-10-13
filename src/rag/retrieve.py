import time
import httpx
from sqlalchemy import select
from src.rag.embed import embed_texts
from src.rag.model import RagChunk, RagDocument
from src.utils.db import Session
from src.utils.settings import settings
from src.utils.trace import info


def label(row) -> str:
    page = f", p. {row.page_number}" if row.page_number else ""
    return f"{row.name}{page}"


def rerank(query: str, rows: list):
    """Ask Jina to rerank. Tries twice and returns None if it is unavailable."""
    for attempt in (1, 2):
        try:
            res = httpx.post(
                "https://api.jina.ai/v1/rerank",
                headers={"Authorization": f"Bearer {settings.JINA_API_KEY}"},
                json={
                    "model": settings.RERANK_MODEL,
                    "query": query,
                    "documents": [row.content for row in rows],
                    "top_n": settings.RAG_TOP_K,
                },
                timeout=30,
            )
            if res.status_code == 200:
                return res.json()["results"]
            info("retrieve: rerank attempt %d failed with HTTP %d", attempt, res.status_code)
        except httpx.HTTPError as e:
            info("retrieve: rerank attempt %d failed: %s", attempt, e)
        time.sleep(0.5)
    return None


def retrieve(query: str) -> list[dict]:
    """Vector search for candidates, then rerank with Jina. Returns the best chunks, best first."""
    started = time.perf_counter()
    vector = embed_texts([query])[0]
    info("retrieve: embedded the query in %.0fms", (time.perf_counter() - started) * 1000)

    started = time.perf_counter()
    with Session() as db:
        rows = db.execute(
            select(RagChunk.content, RagChunk.page_number, RagDocument.name, RagChunk.embedding.cosine_distance(vector).label("distance"))
            .join(RagDocument, RagDocument.id == RagChunk.document_id)
            .order_by(RagChunk.embedding.cosine_distance(vector))
            .limit(settings.RAG_CANDIDATES)
        ).all()
    info(
        "retrieve: vector search returned %d candidate(s) in %.0fms%s",
        len(rows), (time.perf_counter() - started) * 1000,
        f" (cosine distance {rows[0].distance:.3f} best, {rows[-1].distance:.3f} worst)" if rows else "",
    )
    if not rows:
        return []

    started = time.perf_counter()
    results = rerank(query, rows)
    if results is None:
        info("retrieve: rerank unavailable, using the vector-search order instead")
        return [{"text": row.content, "label": label(row)} for row in rows[:settings.RAG_TOP_K]]
    info("retrieve: rerank of %d candidate(s) took %.0fms", len(rows), (time.perf_counter() - started) * 1000)

    chunks = []
    for item in results:
        row = rows[item["index"]]
        kept = item["relevance_score"] >= settings.RERANK_MIN_SCORE
        info("retrieve: rerank score %.3f %s | %s", item["relevance_score"], "KEPT   " if kept else "DROPPED", label(row))
        if kept:
            chunks.append({"text": row.content, "label": label(row)})
    return chunks
