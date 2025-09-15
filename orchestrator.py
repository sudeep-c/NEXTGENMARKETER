# orchestrator.py
from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END

from agents.sentiment_agent import SentimentAgent
from agents.purchase_agent import PurchaseAgent
from agents.campaign_agent import CampaignAgent
from agents.marketer_agent import MarketerAgent


# -------- State --------
class AgentState(TypedDict, total=False):
    user_prompt: str
    route: List[str]          # list of agents to run in order
    agent_outputs: List[Dict[str, Any]]
    final_decision: Dict[str, Any]


# -------- Router --------
def router_node(state: AgentState) -> Dict[str, Any]:
    """Route dynamically based on keywords in the user prompt."""
    p = state["user_prompt"].lower()

    # Keyword dictionaries
    sentiment_keywords = [
        "sentiment", "feeling", "emotion", "mood",
        "perception", "customer satisfaction", "buzz", "review"
    ]
    purchase_keywords = [
        "purchase", "buying", "sales", "transaction", "revenue",
        "orders", "acquisition", "spend"
    ]
    campaign_keywords = [
        "campaign", "advertisement", "ad", "marketing campaign",
        "ctr", "click", "impression", "reach", "promotion", "performance"
    ]
    overall_keywords = [
        "strategy", "overall", "comprehensive", "complete",
        "recommendation", "best approach", "marketing strategy",
        "overall strategy", "summary", "plan"
    ]

    chosen = []

    if any(word in p for word in overall_keywords):
        chosen = ["Sentiment", "Purchase", "Campaign"]
    else:
        if any(word in p for word in sentiment_keywords):
            chosen.append("Sentiment")
        if any(word in p for word in purchase_keywords):
            chosen.append("Purchase")
        if any(word in p for word in campaign_keywords):
            chosen.append("Campaign")

    # Default to all if nothing matched
    if not chosen:
        chosen = ["Sentiment", "Purchase", "Campaign"]

    # Always add Marketer at the end
    chosen.append("Marketer")

    print(f"Router decision: '{p}' -> route: {chosen}")
    return {"route": chosen}


# -------- Nodes --------
def sentiment_node(state: AgentState) -> Dict[str, Any]:
    agent = SentimentAgent()
    out = agent.analyze_sentiment(state["user_prompt"])
    out["agent"] = "sentiment"
    return {"agent_outputs": state.get("agent_outputs", []) + [out]}


def purchase_node(state: AgentState) -> Dict[str, Any]:
    agent = PurchaseAgent()
    out = agent.analyze_purchases(state["user_prompt"])
    out["agent"] = "purchase"
    return {"agent_outputs": state.get("agent_outputs", []) + [out]}


def campaign_node(state: AgentState) -> Dict[str, Any]:
    agent = CampaignAgent()
    out = agent.analyze_campaigns(state["user_prompt"])
    out["agent"] = "campaign"
    return {"agent_outputs": state.get("agent_outputs", []) + [out]}


def marketer_node(state: AgentState) -> Dict[str, Any]:
    agent = MarketerAgent()

    outputs = state.get("agent_outputs", [])
    sentiment_out = next((o for o in outputs if o.get("agent") == "sentiment"), {})
    purchase_out = next((o for o in outputs if o.get("agent") == "purchase"), {})
    campaign_out = next((o for o in outputs if o.get("agent") == "campaign"), {})

    decision = agent.combine_insights(campaign_out, purchase_out, sentiment_out)
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

    # Router expands into first node in the route list
    g.add_conditional_edges(
        "Router",
        lambda s: s["route"][0],
        {
            "Sentiment": "Sentiment",
            "Purchase": "Purchase",
            "Campaign": "Campaign",
            "Marketer": "Marketer",  # edge case: only marketer
        },
    )

    # After Sentiment
    g.add_conditional_edges(
        "Sentiment",
        lambda s: next((r for r in s["route"] if r not in ["Sentiment"]), "Marketer"),
        {
            "Purchase": "Purchase",
            "Campaign": "Campaign",
            "Marketer": "Marketer",
        },
    )

    # After Purchase
    g.add_conditional_edges(
        "Purchase",
        lambda s: next((r for r in s["route"] if r not in ["Sentiment", "Purchase"]), "Marketer"),
        {
            "Campaign": "Campaign",
            "Marketer": "Marketer",
        },
    )

    # After Campaign
    g.add_conditional_edges(
        "Campaign",
        lambda s: "Marketer",
        {"Marketer": "Marketer"},
    )

    # End
    g.add_edge("Marketer", END)

    return g.compile()


# -------- Public API --------
def run_flow(user_prompt: str) -> AgentState:
    app = build_graph()
    state: AgentState = {
        "user_prompt": user_prompt,
        "agent_outputs": [],
    }
    return app.invoke(state)
