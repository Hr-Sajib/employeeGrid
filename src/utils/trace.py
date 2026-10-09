"""Logging for the agent. INFO shows the journey; set AGENT_LOG_LEVEL=DEBUG to also see full prompts, replies and results."""
import asyncio
import functools
import logging
import os
import time
import uuid
from contextvars import ContextVar
from logging.handlers import RotatingFileHandler
from langchain_core.callbacks import BaseCallbackHandler
from src.utils.settings import settings

logger = logging.getLogger("agent")
logger.setLevel(settings.AGENT_LOG_LEVEL.upper())

if not logger.handlers:
    os.makedirs("logs", exist_ok=True)
    file_handler = RotatingFileHandler("logs/agent.log", maxBytes=5_000_000, backupCount=3, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(file_handler)

# Each request gets its own run id and stats. ContextVars keep them separate between users.
_run_id = ContextVar("run_id", default="-")
_stats = ContextVar("stats", default=None)


def _stats_dict() -> dict:
    return _stats.get() or {"nodes": [], "llm_calls": 0, "input_tokens": 0, "output_tokens": 0, "start": time.perf_counter()}


def short(value, limit: int = 200) -> str:
    text = str(value).replace("\n", " ")
    return text if len(text) <= limit else text[:limit] + f"... (+{len(text) - limit} chars)"


def info(message: str, *args):
    logger.info(f"[{_run_id.get()}] " + message, *args)


def debug(message: str, *args):
    logger.debug(f"[{_run_id.get()}] " + message, *args)


def begin_run(conversation_id, history: list[dict]):
    _run_id.set(uuid.uuid4().hex[:8])
    _stats.set({"nodes": [], "llm_calls": 0, "input_tokens": 0, "output_tokens": 0, "start": time.perf_counter()})
    info("===== RUN START conversation=%s history=%d message(s)", conversation_id, len(history))
    info("user message: %s", short(history[-1]["content"], 500))
    debug("full history: %s", history)


def end_run(final: dict):
    stats = _stats_dict()
    total = (time.perf_counter() - stats["start"]) * 1000
    plan = final.get("plan", {})
    info("plan: employee_data=%s documents=%s doc_query=%r", plan.get("needs_employee_data"), plan.get("needs_documents"), plan.get("doc_query"))
    info(
        "evidence: employee=%d documents=%d calculations=%d",
        len(final.get("tool_evidence", [])), len(final.get("doc_evidence", [])), len(final.get("calc_evidence", [])),
    )
    info("path: %s", " -> ".join(name for name, _ in stats["nodes"]))
    info("node timings: %s", " | ".join(f"{name} {ms:.0f}ms" for name, ms in stats["nodes"]))
    info("answer (%d chars): %s", len(final.get("answer", "")), short(final.get("answer", ""), 400))
    debug("full answer:\n%s", final.get("answer", ""))
    info(
        "===== RUN END verdict=%s retries=%d total=%.0fms llm_calls=%d tokens in/out=%d/%d",
        final.get("verdict"), final.get("retries", 0), total, stats["llm_calls"], stats["input_tokens"], stats["output_tokens"],
    )


def traced(fn):
    """Wrap a graph node: log when it starts and finishes, how long it took, and which state keys it wrote."""
    @functools.wraps(fn)
    async def wrapper(state):
        info("--> node %s started", fn.__name__)
        started = time.perf_counter()
        try:
            result = fn(state)
            if asyncio.iscoroutine(result):
                result = await result
        except Exception:
            logger.exception(f"[{_run_id.get()}] node %s FAILED", fn.__name__)
            raise
        ms = (time.perf_counter() - started) * 1000
        _stats_dict()["nodes"].append((fn.__name__, ms))
        info("<-- node %s finished in %.0fms, wrote: %s", fn.__name__, ms, ", ".join(result.keys()))
        return result
    return wrapper


class LLMLogger(BaseCallbackHandler):
    """Pass in the graph config. Logs every model call: which node, model, size, time, tokens and tool calls."""
    run_inline = True

    def __init__(self):
        self._starts = {}

    def on_chat_model_start(self, serialized, messages, *, run_id, metadata=None, **kwargs):
        self._starts[run_id] = time.perf_counter()
        node = (metadata or {}).get("langgraph_node", "?")
        params = kwargs.get("invocation_params") or {}
        msgs = messages[0]
        info(
            "LLM call -> node=%s model=%s messages=%d prompt_chars=%d",
            node, params.get("model") or params.get("model_name") or "?", len(msgs), sum(len(str(m.content)) for m in msgs),
        )
        debug("LLM prompt (node=%s):\n%s", node, "\n".join(f"  [{m.type}] {m.content}" for m in msgs))

    def on_llm_end(self, response, *, run_id, **kwargs):
        ms = (time.perf_counter() - self._starts.pop(run_id, time.perf_counter())) * 1000
        message = response.generations[0][0].message
        usage = getattr(message, "usage_metadata", None) or {}
        stats = _stats_dict()
        stats["llm_calls"] += 1
        stats["input_tokens"] += usage.get("input_tokens", 0)
        stats["output_tokens"] += usage.get("output_tokens", 0)
        calls = [f"{c['name']}({c['args']})" for c in getattr(message, "tool_calls", [])]
        info(
            "LLM call <- %.0fms tokens in/out=%s/%s finish=%s tool_calls=%s reply=%s",
            ms, usage.get("input_tokens", "?"), usage.get("output_tokens", "?"),
            message.response_metadata.get("finish_reason", "?"), calls or "none", short(message.content, 150),
        )
        debug("LLM full reply: %s", message.content)

    def on_llm_error(self, error, *, run_id, **kwargs):
        self._starts.pop(run_id, None)
        logger.error(f"[{_run_id.get()}] LLM call FAILED: %r", error)
