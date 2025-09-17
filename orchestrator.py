from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END
import uuid
from typing import Optional

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
    """Route dynamically based on keywords in the user prompt.

    Improvements:
    - Recognize explicit 'based on <agent>' intent.
    - Use tightened keyword sets to avoid overlaps.
    - Fall back to keyword scanning across sentiment/purchase/campaign.
    - Default to all specialists + Marketer when nothing matches.
    """
    p_raw = state.get("user_prompt", "") or ""
    p = p_raw.lower()

    # tightened keyword lists
    sentiment_keywords = [
        "sentiment", "feel", "feeling", "emotion", "mood",
        "perception", "satisfaction", "buzz", "review", "reviews"
    ]
    purchase_keywords = [
        "purchase", "buy", "buying", "sales", "transaction", "revenue",
        "order", "orders", "acquisition", "spend", "sold", "salesdata", "sales data"
    ]
    campaign_keywords = [
        "campaign", "advertise", "advertisement", "ad", "ads", "marketing",
        "ctr", "click", "impression", "reach", "promotion", "performance", "creative"
    ]
    overall_keywords = [
        "strategy", "overall", "comprehensive", "complete", "recommendation",
        "best approach", "marketing strategy", "summary", "plan", "strategic"
    ]

    # 1) Check for explicit "based on <X>" patterns
    import re
    explicit_agent = None
    m = re.search(r"based on (the )?([a-z\s\-]+)", p)
    if m:
        target = m.group(2).strip()
        if any(tok in target for tok in ["sentiment", "feeling", "review", "satisfaction", "buzz"]):
            explicit_agent = "Sentiment"
        elif any(tok in target for tok in ["purchase", "buy", "sales", "transaction", "order", "acquisition"]):
            explicit_agent = "Purchase"
        elif any(tok in target for tok in ["campaign", "ad", "advert", "ctr", "click", "impression", "promotion"]):
            explicit_agent = "Campaign"

        if explicit_agent:
            chosen = [explicit_agent, "Marketer"]
            print(f"Router explicit 'based on' decision: '{p_raw}' -> route: {chosen}")
            return {"route": chosen}

    # 2) Fall back to keyword scanning
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

    # 3) Default to all if nothing matched
    if not chosen:
        chosen = ["Sentiment", "Purchase", "Campaign"]

    # Always add Marketer at the end
    if "Marketer" not in chosen:
        chosen.append("Marketer")

    print(f"Router decision: '{p_raw}' -> route: {chosen}")
    return {"route": chosen}


# -------- Nodes --------
def sentiment_node(state: AgentState) -> Dict[str, Any]:
    agent = SentimentAgent()
    user_prompt = state.get("user_prompt", "")
    out = agent.analyze_sentiment(user_prompt)
    out["agent"] = "sentiment"

    agent_outputs = state.get("agent_outputs", []) + [out]

    messages = state.get("messages", [])
    if user_prompt and (not messages or messages[-1].get("role") != "user" or messages[-1].get("content") != user_prompt):
        messages = messages + [{"role": "user", "content": user_prompt}]
    messages.append({"role": "assistant", "content": out})

    return {"agent_outputs": agent_outputs, "messages": messages}


def purchase_node(state: AgentState) -> Dict[str, Any]:
    agent = PurchaseAgent()
    user_prompt = state.get("user_prompt", "")
    out = agent.analyze_purchases(user_prompt)
    out["agent"] = "purchase"

    agent_outputs = state.get("agent_outputs", []) + [out]

    messages = state.get("messages", [])
    if user_prompt and (not messages or messages[-1].get("role") != "user" or messages[-1].get("content") != user_prompt):
        messages = messages + [{"role": "user", "content": user_prompt}]
    messages.append({"role": "assistant", "content": out})

    return {"agent_outputs": agent_outputs, "messages": messages}


def campaign_node(state: AgentState) -> Dict[str, Any]:
    agent = CampaignAgent()
    user_prompt = state.get("user_prompt", "")
    out = agent.analyze_campaigns(user_prompt)
    out["agent"] = "campaign"

    agent_outputs = state.get("agent_outputs", []) + [out]

    messages = state.get("messages", [])
    if user_prompt and (not messages or messages[-1].get("role") != "user" or messages[-1].get("content") != user_prompt):
        messages = messages + [{"role": "user", "content": user_prompt}]
    messages.append({"role": "assistant", "content": out})

    return {"agent_outputs": agent_outputs, "messages": messages}


def marketer_node(state: AgentState) -> Dict[str, Any]:
    """
    Run MarketerAgent to combine available specialist outputs into a final decision.
    Also append a marketer entry into agent_outputs so UIs that iterate agent_outputs
    will display the marketer's result consistently.
    """
    agent = MarketerAgent()

    outputs = state.get("agent_outputs", [])
    sentiment_out = next((o for o in outputs if o.get("agent") == "sentiment"), {})
    purchase_out = next((o for o in outputs if o.get("agent") == "purchase"), {})
    campaign_out = next((o for o in outputs if o.get("agent") == "campaign"), {})

    # combine_insights expects (campaign, purchase, sentiment)
    decision = agent.combine_insights(campaign_out, purchase_out, sentiment_out)

    # Ensure decision is a dict
    if decision is None:
        decision = {}
    if not isinstance(decision, dict):
        # defensive: try to wrap into a dict under an obvious key
        decision = {"executive_summary": str(decision)}

    # keep agent_outputs as-is, but append a marketer record for traceability
    agent_outputs = state.get("agent_outputs", []).copy()

    # Create a safe marketer "agent output" entry so UI can display it
    marketer_entry = {
        "agent": "marketer",
        # copy top-level useful keys if present (non-destructive)
        "summary": decision.get("executive_summary") or decision.get("summary") or "No summary available",
        "key_findings": decision.get("key_findings", {}),
        "final_campaign": decision.get("final_campaign", {}),
        "strategic_recommendations": decision.get("strategic_recommendations", decision.get("recommendations", [])),
        # also include raw decision for debugging / PDF export
        "raw_decision": decision,
    }

    agent_outputs.append(marketer_entry)

    # append marketer assistant message to conversational messages
    messages = state.get("messages", [])
    messages = messages + []  # defensive copy
    messages.append({"role": "assistant", "content": decision})

    # Return final_decision (used by caller) and updated messages and agent_outputs
    return {"final_decision": decision, "messages": messages, "agent_outputs": agent_outputs}



# -------- Build Graph --------
def build_graph():
    g = StateGraph(AgentState)

    g.add_node("Router", router_node)
    g.add_node("Sentiment", sentiment_node)
    g.add_node("Purchase", purchase_node)
    g.add_node("Campaign", campaign_node)
    g.add_node("Marketer", marketer_node)

    g.set_entry_point("Router")

    g.add_conditional_edges(
        "Router",
        lambda s: s["route"][0],
        {
            "Sentiment": "Sentiment",
            "Purchase": "Purchase",
            "Campaign": "Campaign",
            "Marketer": "Marketer",
        },
    )

    g.add_conditional_edges(
        "Sentiment",
        lambda s: next((r for r in s["route"] if r not in ["Sentiment"]), "Marketer"),
        {
            "Purchase": "Purchase",
            "Campaign": "Campaign",
            "Marketer": "Marketer",
        },
    )

    g.add_conditional_edges(
        "Purchase",
        lambda s: next((r for r in s["route"] if r not in ["Sentiment", "Purchase"]), "Marketer"),
        {
            "Campaign": "Campaign",
            "Marketer": "Marketer",
        },
    )

    g.add_conditional_edges(
        "Campaign",
        lambda s: "Marketer",
        {"Marketer": "Marketer"},
    )

    g.add_edge("Marketer", END)

    from langgraph.checkpoint.memory import InMemorySaver
    from langgraph.store.memory import InMemoryStore

    checkpointer = InMemorySaver()
    store = InMemoryStore()

    return g.compile(checkpointer=checkpointer, store=store)


# -------- Public API --------
def run_flow(user_prompt: str, thread_id: Optional[str] = None) -> AgentState:
    app = build_graph()

    if thread_id is None:
        thread_id = str(uuid.uuid4())

    state: AgentState = {
        "user_prompt": user_prompt,
        "agent_outputs": [],
    }

    config = {"configurable": {"thread_id": thread_id}}

    try:
        return app.invoke(state, config=config)
    except TypeError:
        return app.invoke(state)
