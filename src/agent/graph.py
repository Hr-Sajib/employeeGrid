import logging
from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy
from src.agent.nodes import calculator, documents, employee_data, router, synthesizer, verifier
from src.agent.state import AgentState
from src.utils.trace import LLMLogger, begin_run, end_run, info, set_progress


def pick_branches(state: AgentState) -> list[str]:
    plan = state["plan"]
    branches = []
    if plan["needs_employee_data"]:
        branches.append("employee_data")
    if plan["needs_documents"]:
        branches.append("documents")
    branches = branches or ["synthesizer"]
    info("route after router -> %s", branches)
    return branches


def after_synthesizer(state: AgentState) -> str:
    next_node = "calculator" if state["messages"][-1].tool_calls else "verifier"
    info("route after synthesizer -> %s", next_node)
    return next_node


def after_verifier(state: AgentState) -> str:
    next_node = "synthesizer" if state["verdict"] == "retry" else END
    info("route after verifier -> %s (verdict=%s)", next_node, state["verdict"])
    return next_node


# Retries a node when it raises a transient error (timeout, 5xx, rate limit) after 0.5 s, then 1 s. Max 3 attempts.
RETRY = RetryPolicy(max_attempts=3, initial_interval=0.5, backoff_factor=2.0)

builder = StateGraph(AgentState)
builder.add_node("router", router, retry_policy=RETRY)
builder.add_node("employee_data", employee_data, retry_policy=RETRY)
builder.add_node("documents", documents, retry_policy=RETRY)
builder.add_node("synthesizer", synthesizer, retry_policy=RETRY)
builder.add_node("calculator", calculator)
builder.add_node("verifier", verifier, retry_policy=RETRY)

builder.add_edge(START, "router")
builder.add_conditional_edges("router", pick_branches, ["employee_data", "documents", "synthesizer"])
builder.add_edge("employee_data", "synthesizer")
builder.add_edge("documents", "synthesizer")
builder.add_conditional_edges("synthesizer", after_synthesizer, ["calculator", "verifier"])
builder.add_edge("calculator", "synthesizer")
builder.add_conditional_edges("verifier", after_verifier, ["synthesizer", END])
graph = builder.compile()


async def run_agent(history: list[dict], conversation_id=None, on_step=None) -> str:
    begin_run(conversation_id, history)
    set_progress(on_step)
    try:
        result = await graph.ainvoke({"history": history}, config={"callbacks": [LLMLogger()]})
    except Exception:
        logging.getLogger("agent").exception("RUN FAILED")
        raise
    end_run(result)
    return result["answer"]
