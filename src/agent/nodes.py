import asyncio
import json
import re
import time
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from pydantic import BaseModel
from src.agent import prompts
from src.agent.calculator import calculate, evaluate
from src.agent.llm import make_llm
from src.agent.tools import TOOLS
from src.rag.retrieve import retrieve
from src.utils.settings import settings
from src.utils.trace import debug, info, short, traced

MAX_CALCULATIONS = 3
FALLBACK = "I couldn't verify an answer from the available data. Please rephrase your question or check the source documents."


# ---------- helpers ----------

def all_evidence(state) -> list[dict]:
    return state.get("tool_evidence", []) + state.get("doc_evidence", []) + state.get("calc_evidence", [])


def evidence_block(state) -> str:
    plan = state["plan"]
    lines = [f"[{e['id']}] {e['label']} -> {e['text']}" for e in state.get("tool_evidence", [])]
    lines += [f"[{e['id']}] ({e['label']}) {e['text']}" for e in state.get("doc_evidence", [])]
    lines += [f"[{e['id']}] {e['text']}" for e in state.get("calc_evidence", [])]
    if plan["needs_employee_data"] and not state.get("tool_evidence"):
        lines.append("(No employee data was retrieved.)")
    if plan["needs_documents"] and not state.get("doc_evidence"):
        lines.append("(The document search found nothing relevant.)")
    return "\n".join(lines) or "(none)"


def with_sources(draft: str, evidence: list[dict]) -> str:
    cited = [e for e in evidence if f"[{e['id']}]" in draft]
    if not cited:
        return draft
    return draft + "\n\nSources:\n" + "\n".join(f"[{e['id']}] {e['label']}" for e in cited)


# ---------- 1. router ----------

class Plan(BaseModel):
    needs_employee_data: bool
    needs_documents: bool
    doc_query: str = ""

router_llm = make_llm(settings.ROUTER_MODEL).with_structured_output(Plan)


@traced
async def router(state):
    plan = await router_llm.ainvoke([SystemMessage(prompts.ROUTER)] + state["history"])
    info("router decided: employee_data=%s documents=%s doc_query=%r", plan.needs_employee_data, plan.needs_documents, plan.doc_query)
    return {"plan": plan.model_dump()}


# ---------- 2a. employee data branch ----------

tools_llm = make_llm(settings.OPENROUTER_MODEL).bind_tools(TOOLS)
TOOLS_BY_NAME = {t.name: t for t in TOOLS}


@traced
async def employee_data(state):
    ai = await tools_llm.ainvoke([SystemMessage(prompts.TOOLS_AGENT)] + state["history"])
    if ai.tool_calls:
        info("employee_data: model requested %d tool call(s): %s", len(ai.tool_calls), [f"{c['name']}({c['args']})" for c in ai.tool_calls])
    else:
        info("employee_data: model called NO tools, so there is no employee evidence (its text reply: %s)", short(ai.content, 150))

    evidence = []
    for call in ai.tool_calls:
        tool = TOOLS_BY_NAME.get(call["name"])
        if tool is None:
            info("employee_data: unknown tool %r requested, skipped", call["name"])
            continue
        started = time.perf_counter()
        result = await tool.ainvoke(call["args"])
        text = json.dumps(result)
        info("employee_data: %s ran in %.0fms -> %s", call["name"], (time.perf_counter() - started) * 1000, short(text))
        debug("employee_data: full result of %s: %s", call["name"], text)
        args = ", ".join(f"{k}={v}" for k, v in call["args"].items())
        evidence.append({"id": f"E{len(evidence) + 1}", "label": f"{call['name']}({args})", "text": text})
    return {"tool_evidence": evidence}


# ---------- 2b. documents branch ----------

@traced
async def documents(state):
    query = state["plan"]["doc_query"] or state["history"][-1]["content"]
    info("documents: searching for %r", query)
    chunks = await asyncio.to_thread(retrieve, query)
    info("documents: %d chunk(s) kept: %s", len(chunks), [c["label"] for c in chunks])
    for i, chunk in enumerate(chunks, start=1):
        debug("documents: D%d (%s):\n%s", i, chunk["label"], chunk["text"])
    return {"doc_evidence": [{"id": f"D{i}", **chunk} for i, chunk in enumerate(chunks, start=1)]}


# ---------- 3. synthesizer + calculator ----------

synth_llm = make_llm(settings.OPENROUTER_MODEL)
synth_llm_with_calc = synth_llm.bind_tools([calculate])


@traced
async def synthesizer(state):
    can_calculate = len(state.get("calc_evidence", [])) < MAX_CALCULATIONS
    info(
        "synthesizer: evidence=%s calculator=%s retry=%d%s",
        [e["id"] for e in all_evidence(state)] or "none",
        "on" if can_calculate else "off (limit reached)",
        state.get("retries", 0),
        f" feedback={state['issues']}" if state.get("issues") else "",
    )
    debug("synthesizer: evidence block:\n%s", evidence_block(state))

    system = prompts.SYNTHESIZER + "\n\nEVIDENCE:\n" + evidence_block(state)
    messages = [SystemMessage(system)] + state["history"] + state.get("messages", [])
    if state.get("issues"):
        messages.append(HumanMessage("Your previous draft had these problems: " + "; ".join(state["issues"]) + ". Write a corrected answer."))
    ai = await (synth_llm_with_calc if can_calculate else synth_llm).ainvoke(messages)

    draft = ai.content.replace("【", "[").replace("】", "]")   # some models use full-width brackets
    if ai.tool_calls:
        info("synthesizer: asked the calculator for %s", [c["args"].get("expression") for c in ai.tool_calls])
    else:
        info("synthesizer: draft written (%d chars): %s", len(draft), short(draft))
    return {"messages": [ai], "draft": draft}


@traced
def calculator(state):
    evidence = list(state.get("calc_evidence", []))
    replies = []
    for call in state["messages"][-1].tool_calls:
        expression = call["args"].get("expression", "")
        text = f"{expression} = {evaluate(expression)}"
        evidence.append({"id": f"C{len(evidence) + 1}", "label": text, "text": text})
        info("calculator: [%s] %s", evidence[-1]["id"], text)
        replies.append(ToolMessage(content=f"[{evidence[-1]['id']}] {text}", tool_call_id=call["id"]))
    return {"messages": replies, "calc_evidence": evidence}


# ---------- 4. verifier ----------

class Check(BaseModel):
    supported: bool
    issues: list[str] = []

verifier_llm = make_llm(settings.VERIFIER_MODEL).with_structured_output(Check)


@traced
async def verifier(state):
    evidence = all_evidence(state)
    plan = state["plan"]
    issues = []
    checking = bool(evidence or plan["needs_employee_data"] or plan["needs_documents"])
    info("verifier: draft=%d chars, evidence=%s, check=%s", len(state["draft"]), [e["id"] for e in evidence] or "none", "on" if checking else "skipped (nothing to verify)")

    if checking:
        known = {e["id"] for e in evidence}
        for cited in set(re.findall(r"\[([EDC]\d+)\]", state["draft"])):
            if cited not in known:
                issues.append(f"it cites [{cited}] but no such evidence exists")
        if issues:
            info("verifier: citation check FAILED: %s", issues)
        else:
            info("verifier: citation check passed, asking %s to check the facts", settings.VERIFIER_MODEL)
            check = await verifier_llm.ainvoke([
                SystemMessage(prompts.VERIFIER),
                HumanMessage(f"EVIDENCE:\n{evidence_block(state)}\n\nDRAFT:\n{state['draft']}"),
            ])
            info("verifier: fact check supported=%s issues=%s", check.supported, check.issues)
            if not check.supported:
                issues = check.issues or ["the draft is not supported by the evidence"]

    retries = state.get("retries", 0)
    if not issues:
        info("verifier: verdict=pass")
        return {"verdict": "pass", "issues": [], "answer": with_sources(state["draft"], evidence)}
    if retries < 1:
        info("verifier: verdict=retry (sending the problems back to the synthesizer)")
        return {"verdict": "retry", "issues": issues, "retries": retries + 1}
    info("verifier: verdict=fallback (still failing after a retry, sending the safe message)")
    return {"verdict": "fallback", "answer": FALLBACK}
