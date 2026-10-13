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
_progress = ContextVar("progress", default=None)   # async callback that receives one dict per step update


def set_progress(callback):
    _progress.set(callback)


async def _emit_step(step: dict):
    callback = _progress.get()
    if callback:
        try:
            await callback(step)
        except Exception:
            logger.exception("progress callback failed")


def _new_stats() -> dict:
    return {"nodes": [], "llm_calls": 0, "input_tokens": 0, "output_tokens": 0, "cost": 0.0, "final": {}, "start": time.perf_counter()}


def _stats_dict() -> dict:
    return _stats.get() or _new_stats()


def add_cost(amount: float):
    _stats_dict()["cost"] += amount or 0.0


def run_summary() -> dict:
    """Numbers about the current run, for the usage log. Safe to call even if the run crashed."""
    stats = _stats_dict()
    final, plan = stats["final"], stats["final"].get("plan", {})
    return {
        "path": " -> ".join(name for name, _ in stats["nodes"]),
        "total_ms": int((time.perf_counter() - stats["start"]) * 1000),
        "llm_calls": stats["llm_calls"], "input_tokens": stats["input_tokens"], "output_tokens": stats["output_tokens"],
        "cost": stats["cost"], "verdict": final.get("verdict"), "retries": final.get("retries", 0),
        "needs_employee_data": plan.get("needs_employee_data"), "needs_documents": plan.get("needs_documents"),
    }


def short(value, limit: int = 200) -> str:
    text = str(value).replace("\n", " ")
    return text if len(text) <= limit else text[:limit] + f"... (+{len(text) - limit} chars)"


def info(message: str, *args):
    logger.info(f"[{_run_id.get()}] " + message, *args)


def debug(message: str, *args):
    logger.debug(f"[{_run_id.get()}] " + message, *args)


def begin_run(conversation_id, history: list[dict]):
    _run_id.set(uuid.uuid4().hex[:8])
    _stats.set(_new_stats())
    info("===== RUN START conversation=%s history=%d message(s)", conversation_id, len(history))
    info("user message: %s", short(history[-1]["content"], 200))
    debug("SENSITIVE (may contain employee data) full history: %s", history)


def end_run(final: dict):
    stats = _stats_dict()
    stats["final"] = {"verdict": final.get("verdict"), "retries": final.get("retries", 0), "plan": final.get("plan", {})}
    total = (time.perf_counter() - stats["start"]) * 1000
    plan = final.get("plan", {})
    info("plan: employee_data=%s documents=%s doc_query=%r", plan.get("needs_employee_data"), plan.get("needs_documents"), plan.get("doc_query"))
    info(
        "evidence: employee=%d documents=%d calculations=%d",
        len(final.get("tool_evidence", [])), len(final.get("doc_evidence", [])), len(final.get("calc_evidence", [])),
    )
    info("path: %s", " -> ".join(name for name, _ in stats["nodes"]))
    info("node timings: %s", " | ".join(f"{name} {ms:.0f}ms" for name, ms in stats["nodes"]))
    info("answer: %d chars (the text itself is only logged at DEBUG)", len(final.get("answer", "")))
    debug("SENSITIVE full answer:\n%s", final.get("answer", ""))
    info(
        "===== RUN END verdict=%s retries=%d total=%.0fms llm_calls=%d tokens in/out=%d/%d cost=$%.6f",
        final.get("verdict"), final.get("retries", 0), total, stats["llm_calls"], stats["input_tokens"], stats["output_tokens"], stats["cost"],
    )


def traced(label: str, describe=None):
    """Wrap a graph node: log it, time it, and tell the UI which step is running.
    `describe(result, state)` returns a short detail shown once the step is done."""
    def decorator(fn):
        @functools.wraps(fn)
        async def wrapper(state):
            step = {"id": uuid.uuid4().hex[:6], "node": fn.__name__, "label": label}
            info("--> node %s started", fn.__name__)
            await _emit_step({**step, "status": "running"})
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
            try:
                detail = describe(result, state) if describe else ""
            except Exception:
                detail = ""
            await _emit_step({**step, "status": "done", "detail": detail})
            return result
        return wrapper
    return decorator


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
        debug("SENSITIVE LLM prompt (node=%s):\n%s", node, "\n".join(f"  [{m.type}] {m.content}" for m in msgs))

    def on_llm_end(self, response, *, run_id, **kwargs):
        ms = (time.perf_counter() - self._starts.pop(run_id, time.perf_counter())) * 1000
        message = response.generations[0][0].message
        usage = getattr(message, "usage_metadata", None) or {}
        stats = _stats_dict()
        stats["llm_calls"] += 1
        stats["input_tokens"] += usage.get("input_tokens", 0)
        stats["output_tokens"] += usage.get("output_tokens", 0)
        cost = (message.response_metadata.get("token_usage") or {}).get("cost") or 0.0
        stats["cost"] += cost
        tool_calls = getattr(message, "tool_calls", [])
        info(
            "LLM call <- %.0fms tokens in/out=%s/%s cost=$%.6f finish=%s tool_calls=%s reply=%d chars",
            ms, usage.get("input_tokens", "?"), usage.get("output_tokens", "?"), cost,
            message.response_metadata.get("finish_reason", "?"), [c["name"] for c in tool_calls] or "none", len(str(message.content)),
        )
        debug("SENSITIVE LLM full reply: %s | tool calls: %s", message.content, [(c["name"], c["args"]) for c in tool_calls])

    def on_llm_error(self, error, *, run_id, **kwargs):
        self._starts.pop(run_id, None)
        logger.error(f"[{_run_id.get()}] LLM call FAILED: %r", error)
