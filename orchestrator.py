# orchestrator.py
from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END

from agents import sentiment_agent, purchase_agent, campaign_agent, marketer_agent

# -------- State --------
class AgentState(TypedDict, total=False):
    user_prompt: str
    route: str
    agent_outputs: List[Dict[str, Any]]
    final_decision: Dict[str, Any]

# -------- Nodes --------
def router_node(state: AgentState) -> Dict[str, Any]:
    """Decide which path to take; MUST return a dict update."""
    p = state["user_prompt"].lower()
    if "sentiment" in p and "purchase" in p:
        route = "sentiment+purchase"
    elif "sentiment" in p:
        route = "sentiment_only"
    elif "overall" in p or "best" in p or "strategy" in p:
        route = "all"
    else:
        route = "all"
    return {"route": route}

def sentiment_node(state: AgentState) -> Dict[str, Any]:
    out = sentiment_agent.run(state["user_prompt"])
    return {"agent_outputs": (state.get("agent_outputs", []) + [out])}

def purchase_node(state: AgentState) -> Dict[str, Any]:
    out = purchase_agent.run(state["user_prompt"])
    return {"agent_outputs": (state.get("agent_outputs", []) + [out])}

def campaign_node(state: AgentState) -> Dict[str, Any]:
    out = campaign_agent.run(state["user_prompt"])
    return {"agent_outputs": (state.get("agent_outputs", []) + [out])}

def marketer_node(state: AgentState) -> Dict[str, Any]:
    decision = marketer_agent.run(state.get("agent_outputs", []), state["user_prompt"])
    return {"final_decision": decision}

# -------- Build Graph --------
def build_graph():
    g = StateGraph(AgentState)

    g.add_node("Router", router_node)
    g.add_node("Sentiment", sentiment_node)
    g.add_node("Purchase", purchase_node)
    g.add_node("Campaign", campaign_node)
    g.add_node("Marketer", marketer_node)

    g.set_entry_point("Router")

    # From Router -> first step based on route
    g.add_conditional_edges(
        "Router",
        lambda s: s["route"],
        {
            "sentiment_only": "Sentiment",
            "sentiment+purchase": "Sentiment",
            "all": "Sentiment",
        },
    )

    # After Sentiment
    g.add_conditional_edges(
        "Sentiment",
        lambda s: s["route"],
        {
            "sentiment_only": "Marketer",
            "sentiment+purchase": "Purchase",
            "all": "Purchase",
        },
    )

    # After Purchase
    g.add_conditional_edges(
        "Purchase",
        lambda s: s["route"],
        {
            "sentiment+purchase": "Marketer",
            "all": "Campaign",
        },
    )

    # After Campaign
    g.add_edge("Campaign", "Marketer")

    # End
    g.add_edge("Marketer", END)

    return g.compile()

# -------- Public API --------
def run_flow(user_prompt: str) -> AgentState:
    app = build_graph()
    # Start with minimal state; Router will set route.
    state: AgentState = {
        "user_prompt": user_prompt,
        "agent_outputs": [],
    }
    return app.invoke(state)
