from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode
from src.agent.tools import ENABLED_TOOLS
from src.utils.settings import settings

SYSTEM_PROMPT = (
    "You are an HR assistant. Use the available tools whenever the user asks about "
    "employee data; never guess employee data. Ask the user to confirm before deleting an employee. "
    "For anything else, answer directly."
)

llm = ChatOpenAI(
    model=settings.OPENROUTER_MODEL,
    base_url="https://openrouter.ai/api/v1",
    api_key=settings.OPENROUTER_API_KEY,
    timeout=60,
    extra_body={"provider": {"sort": "latency"}, "reasoning": {"effort": "low"}},
).bind_tools(ENABLED_TOOLS)


async def agent_node(state: MessagesState):
    return {"messages": [await llm.ainvoke([SystemMessage(SYSTEM_PROMPT)] + state["messages"])]}


def needs_tool(state: MessagesState) -> str:
    return "tools" if state["messages"][-1].tool_calls else END


builder = StateGraph(MessagesState)
builder.add_node("agent", agent_node)
builder.add_node("tools", ToolNode(ENABLED_TOOLS))
builder.add_edge(START, "agent")
builder.add_conditional_edges("agent", needs_tool, ["tools", END])
builder.add_edge("tools", "agent")
graph = builder.compile()


async def run_agent(messages: list[dict]) -> str:
    result = await graph.ainvoke({"messages": messages})
    return result["messages"][-1].content

