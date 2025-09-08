# multi_agent_workflow.py
from langgraph.graph import StateGraph, END
from typing import Dict, Any
import json

from campaign_agent import CampaignAgent
from purchase_agent import PurchaseAgent
from sentiment_agent import SentimentAgent
from marketer_agent import MarketerAgent

class AgentState(dict):
    pass

def run_campaign(state: AgentState) -> AgentState:
    ag = CampaignAgent()
    campaign_output = ag.analyze_campaigns(state.get("user_query", "Analyze campaign performance"))
    state["campaign_output"] = campaign_output
    return state

def run_purchase(state: AgentState) -> AgentState:
    ag = PurchaseAgent()
    purchase_output = ag.analyze_purchases(state.get("user_query", "Analyze purchase data"))
    state["purchase_output"] = purchase_output
    return state

def run_sentiment(state: AgentState) -> AgentState:
    ag = SentimentAgent()
    sentiment_output = ag.analyze_sentiment(state.get("user_query", "Analyze sentiment"))
    state["sentiment_output"] = sentiment_output
    return state

def run_marketer(state: AgentState) -> AgentState:
    ag = MarketerAgent()
    campaign_out = state.get("campaign_output", {})
    purchase_out = state.get("purchase_output", {})
    sentiment_out = state.get("sentiment_output", {})
    final = ag.combine_insights(campaign_out, purchase_out, sentiment_out)
    state["final_strategy"] = final
    return state

def build_workflow():
    wf = StateGraph(AgentState)
    wf.add_node("campaign_agent", run_campaign)
    wf.add_node("purchase_agent", run_purchase)
    wf.add_node("sentiment_agent", run_sentiment)
    wf.add_node("marketer_agent", run_marketer)
    wf.add_edge("campaign_agent", "purchase_agent")
    wf.add_edge("purchase_agent", "sentiment_agent")
    wf.add_edge("sentiment_agent", "marketer_agent")
    wf.add_edge("marketer_agent", END)
    wf.set_entry_point("campaign_agent")
    return wf
