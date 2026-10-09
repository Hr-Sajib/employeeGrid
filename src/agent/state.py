from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages


class AgentState(TypedDict, total=False):
    history: list[dict]          # the chat so far: [{"role": "user", "content": "..."}, ...]
    plan: dict                   # router output: which branches are needed
    tool_evidence: list[dict]    # [{"id": "E1", "label": "...", "text": "..."}]
    doc_evidence: list[dict]     # [{"id": "D1", "label": "Policy manual, p. 4", "text": "..."}]
    calc_evidence: list[dict]    # [{"id": "C1", "label": "5200 * 0.1 = 520", "text": "5200 * 0.1 = 520"}]
    messages: Annotated[list, add_messages]   # synthesizer <-> calculator conversation
    draft: str
    issues: list[str]            # problems found by the verifier
    verdict: str                 # "pass" | "retry" | "fallback"
    retries: int
    answer: str                  # final answer sent to the user
