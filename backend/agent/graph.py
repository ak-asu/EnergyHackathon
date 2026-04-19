"""LangGraph stress-test / comparison agent."""
from langgraph.graph import StateGraph, END
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from backend.agent.tools import evaluate_site, compare_sites
from backend.config import get_settings
from typing import TypedDict, Annotated
import operator

TOOLS = [evaluate_site, compare_sites]

_SYSTEM = """You are a BTM data center site analysis agent.
You have tools to evaluate coordinates and compare sites.
Always include specific numbers. Be concise."""


class AgentState(TypedDict):
    messages: Annotated[list, operator.add]


def build_agent():
    settings = get_settings()
    llm = ChatAnthropic(
        model='claude-opus-4-7',
        api_key=settings.anthropic_api_key,
    ).bind_tools(TOOLS)

    def agent_node(state: AgentState):
        msgs = [SystemMessage(content=_SYSTEM)] + state['messages']
        response = llm.invoke(msgs)
        return {'messages': [response]}

    def tool_node(state: AgentState):
        from langchain_core.messages import ToolMessage
        last = state['messages'][-1]
        results = []
        for call in last.tool_calls:
            tool_map = {t.name: t for t in TOOLS}
            result = tool_map[call['name']].invoke(call['args'])
            results.append(ToolMessage(content=str(result), tool_call_id=call['id']))
        return {'messages': results}

    def should_continue(state: AgentState):
        last = state['messages'][-1]
        return 'tools' if getattr(last, 'tool_calls', None) else END

    graph = StateGraph(AgentState)
    graph.add_node('agent', agent_node)
    graph.add_node('tools', tool_node)
    graph.set_entry_point('agent')
    graph.add_conditional_edges('agent', should_continue)
    graph.add_edge('tools', 'agent')
    return graph.compile()


_agent = None


def get_agent():
    global _agent
    if _agent is None:
        _agent = build_agent()
    return _agent
