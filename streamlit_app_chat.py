# streamlit_app_chat.py
import streamlit as st
import requests
import json
import pandas as pd
import io
from datetime import datetime, timezone
from typing import List
from matplotlib import pyplot as plt
import uuid
import traceback

# Ensure a persistent thread_id per browser session (small non-invasive addition)
if "thread_id" not in st.session_state:
    st.session_state["thread_id"] = str(uuid.uuid4())

# CONFIG
API_BASE = st.secrets.get("API_BASE", "http://localhost:8000")
ACCENT_INDIGO = "#4F46E5"
ADOBE_RED = "#FF0000"
BG_GRADIENT = "linear-gradient(180deg, #f5f6fa 0%, #ffffff 100%)"

st.set_page_config(page_title="NextGen Marketer Chat", layout="wide", initial_sidebar_state="collapsed")

# CSS for modern chat UI (kept original + compact tile styles)
st.markdown(
    f"""
    <style>
    .stApp {{ background: {BG_GRADIENT}; }}
    .header {{
        position: sticky; top: 0; z-index: 9999;
        background: white; padding: 12px 20px; display:flex; align-items:center; justify-content:space-between;
        box-shadow: 0 6px 18px rgba(79,70,229,0.08);
        border-bottom: 1px solid #eee; border-radius: 0 0 10px 10px;
    }}
    .app-title {{ font-weight:700; color: {ACCENT_INDIGO}; font-size:20px; }}
    .sub-title {{ color: #6b7280; font-size:12px; }}
    .chat-window {{ height: 60vh; overflow:auto; padding: 20px; }}
    .msg-row {{ display:flex; margin-bottom:12px; align-items:flex-end; }}
    .msg-bubble {{
        max-width:70%; padding:12px 16px; border-radius:16px; box-shadow: 0 6px 18px rgba(16,24,40,0.06);
        transition: transform .12s ease, box-shadow .12s ease;
    }}
    .user {{ justify-content:flex-end; }}
    .user .msg-bubble {{ background: {ACCENT_INDIGO}; color:white; border-bottom-right-radius:4px; border-bottom-left-radius:16px; border-top-left-radius:16px; border-top-right-radius:16px; }}
    .assistant .msg-bubble {{ background: #ffffff; color:#111827; border-bottom-left-radius:4px; }}
    .msg-meta {{ font-size:11px; color:#6b7280; margin-top:6px; }}
    .footer {{
        position: sticky; bottom: 0; background: white; padding:10px; display:flex; gap:8px; align-items:center;
        box-shadow: 0 -6px 18px rgba(79,70,229,0.04);
    }}
    .emoji-btn {{ font-size:20px; cursor:pointer; border:none; background:transparent; }}
    .send-btn {{
        background: {ACCENT_INDIGO}; color:white; padding:8px 14px; border-radius:10px; border:none; font-weight:600;
    }}
    .action-red {{ background: {ADOBE_RED}; color:white; padding:6px 10px; border-radius:8px; border:none; }}
    .rounded-card {{ background:white; padding:12px; border-radius:12px; box-shadow: 0 6px 18px rgba(16,24,40,0.04); }}
    .small-muted {{ color:#6b7280; font-size:12px; }}

    /* Compact tile styles for agent insights/recs */
    .insight-tile {{ background: white; border: 1px solid #e6e9ee; border-radius: 8px; padding: 10px; margin: 8px; box-shadow: 0 2px 6px rgba(0,0,0,0.04); width: 280px; display:inline-block; vertical-align:top; }}
    .insight-tile .k {{ font-weight:700; color:#111827; font-size:13px; display:block; margin-bottom:4px; }}
    .insight-tile .v {{ font-size:13px; color:#6b7280; display:block; margin-bottom:6px; }}
    .rec-tile {{ background: white; border: 1px solid #e6e9ee; border-radius: 8px; padding: 10px; margin: 8px; box-shadow: 0 2px 6px rgba(0,0,0,0.04); width: 360px; display:inline-block; vertical-align:top; }}
    .rec-tile .idea {{ font-weight:700; font-size:14px; color:{ACCENT_INDIGO}; margin-bottom:6px; }}
    .rec-tile .conf {{ font-size:12px; color:#6b7280; margin-bottom:4px; }}

    </style>
    """, unsafe_allow_html=True)

# Header
st.markdown("""
<div class="header">
  <div>
    <div class="app-title">NextGen Marketer</div>
    <div class="sub-title">Multi-agent marketing assistant — Maruti demo</div>
  </div>
  <div>
    <button class="action-red" onclick="window.location.reload()">Reset</button>
  </div>
</div>
""", unsafe_allow_html=True)

# Layout: left chat + right panel
col1, col2 = st.columns([2, 1])

# Session state messages
if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {"role": "assistant", "text": "Hi — ask me about campaigns, purchases, or sentiment (e.g., 'Why are SUV campaigns underperforming?')"},
    ]
if "raw_state" not in st.session_state:
    st.session_state["raw_state"] = {}

def render_chat():
    st.markdown('<div class="chat-window">', unsafe_allow_html=True)
    for m in st.session_state["messages"]:
        role = m.get("role")
        text = m.get("text")
        meta = m.get("meta", "")
        align = "user" if role == "user" else "assistant"
        bubble_html = f"""
        <div class="msg-row {align}">
          <div class="msg-bubble" style="{ 'background:'+('#4F46E5')+'; color:white;' if role=='user' else '' }">
            {text}
            <div class="msg-meta">{meta}</div>
          </div>
        </div>
        """
        st.markdown(bubble_html, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with col1:
    st.markdown('<div class="rounded-card">', unsafe_allow_html=True)
    render_chat()
    st.markdown('</div>', unsafe_allow_html=True)

    # footer input bar
    # fix label warning by using label_visibility='collapsed'
    with st.form(key="message_form", clear_on_submit=False):
        col_f1, col_f2, col_f3 = st.columns([0.04, 1, 0.15])
        with col_f1:
            emoji = st.selectbox("emoji", options=["🙂","🤔","🔥","💡","📈"], index=0, key="emoji_select", label_visibility="collapsed")
        with col_f2:
            user_input = st.text_input("message", placeholder="Ask agents anything about campaigns, purchases, sentiment...", key="user_input", label_visibility="collapsed")
        with col_f3:
            submit = st.form_submit_button("Send", help="Send query", on_click=None)
        if submit and user_input:
            # append user message
            st.session_state["messages"].append({"role":"user","text": user_input, "meta": datetime.now(timezone.utc).isoformat()})
            # call API
            try:
                payload = {"query": user_input, "thread_id": st.session_state.get("thread_id")}
                r = requests.post(f"{API_BASE}/strategy", json=payload, timeout=120)
                r.raise_for_status()
                data = r.json()
                # Persist thread id returned by server (if any) so backend memory is consistent
                if isinstance(data, dict) and data.get("thread_id"):
                    st.session_state["thread_id"] = data["thread_id"]

                # store raw state for trace panel
                st.session_state["raw_state"] = data.get("raw_state", data)

                # Build assistant bubble from final_strategy/final_decision -> executive_summary + recs
                final = {}
                if isinstance(data, dict):
                    final = data.get("final_strategy") or data.get("final_decision") or data.get("final_campaign") or {}

                assistant_text = final.get("executive_summary", "No summary returned.")
                recs = []
                if isinstance(final, dict):
                    recs = final.get("strategic_recommendations") or final.get("recommendations") or []
                if recs:
                    assistant_text += "\n\nRecommendations:\n" + "\n".join([f"- {x}" for x in recs[:5]])

                # push assistant message
                st.session_state["messages"].append({"role":"assistant","text": assistant_text, "meta": "confidence: "+("high" if data.get("valid_schema") else "low")})
            except Exception as e:
                tb = traceback.format_exc()
                st.session_state["messages"].append({"role":"assistant","text": f"Error calling API: {e}", "meta": ""})
                print("Error calling API:", tb)

with col2:
    st.markdown('<div class="rounded-card">', unsafe_allow_html=True)
    st.markdown("### Quick Metrics")
    raw = st.session_state.get("raw_state", {})
    # derive some quick KPIs if available from raw_state fields (flexible)
    campaign_out = raw.get("campaign_output") or {}
    purchase_out = raw.get("purchase_output") or {}
    sentiment_out = raw.get("sentiment_output") or {}
    final_out = raw.get("final_decision") or raw.get("final_strategy") or raw.get("final_campaign") or {}

    # Basic KPIs (safe access)
    avg_ctr = campaign_out.get("key_metrics", {}).get("avg_ctr") if campaign_out else None
    avg_conv = campaign_out.get("key_metrics", {}).get("avg_conversion_rate") if campaign_out else None
    top_channel = campaign_out.get("key_metrics", {}).get("top_channel") if campaign_out else None

    # fallback to purchase KPI or final decision if present
    if not avg_ctr and purchase_out.get("key_metrics"):
        avg_ctr = purchase_out["key_metrics"].get("ctr") or avg_ctr

    st.markdown(f"**Avg CTR:** {avg_ctr or '—'}")
    st.markdown(f"**Avg Conv Rate:** {avg_conv or '—'}")
    st.markdown(f"**Top Channel:** {top_channel or '—'}")
    st.markdown("---")

    # Agent Trace - only show sections for agents that ran in the last raw_state
    route = raw.get("route", []) if isinstance(raw, dict) else []
    routed_agents = [r.lower() for r in route] if route else []

    st.markdown("### Agent Trace")
    # Helper functions for small tile rendering (same format as app.py)
    def render_insight_tile_html(insight: dict):
        audience = insight.get("audience_segment") or insight.get("audience") or insight.get("segment") or "-"
        product = insight.get("product_focus") or insight.get("product") or "-"
        region = insight.get("region") or insight.get("regions") or "-"
        signal = insight.get("signal") or insight.get("note") or ""
        confidence = insight.get("confidence")
        conf_text = f"{confidence:.2f}" if isinstance(confidence, (float, int)) else (str(confidence) if confidence else "-")
        html = f"""
        <div class="insight-tile">
          <div class="k">Audience</div><div class="v">{audience}</div>
          <div class="k">Product</div><div class="v">{product}</div>
          <div class="k">Region</div><div class="v">{region}</div>
          <div class="k">Signal</div><div class="v">{st.experimental_singleton(lambda s=signal: s)()}</div>
          <div class="k">Confidence</div><div class="v">{conf_text}</div>
        </div>
        """
        return html

    def render_rec_tile_html(rec: dict):
        idea = rec.get("idea") or rec.get("campaign_name") or rec.get("concept") or str(rec)
        confidence = rec.get("confidence")
        conf_text = f"{confidence:.2f}" if isinstance(confidence, (float, int)) else (str(confidence) if confidence else "-")
        html = f"""
        <div class="rec-tile">
          <div class="idea">{idea}</div>
          <div class="conf">Confidence: {conf_text}</div>
        </div>
        """
        return html

    # For each routed agent, produce an expander and show tiles
    agent_outputs = raw.get("agent_outputs") or []
    # convert to list of dicts if needed
    if isinstance(agent_outputs, dict):
        agent_outputs = [agent_outputs]

    for out in agent_outputs:
        agent_name = out.get("agent", "Agent").capitalize()
        if out.get("agent", "").lower() not in routed_agents:
            # if agent was not routed, skip or show disabled
            continue

        with st.expander(f"🔎 {agent_name} Agent Output", expanded=False):
            # summary
            summary = out.get("summary") or out.get("summary_text") or "No summary available"
            st.markdown(f"**Summary:** {summary}")

            # insights
            insights = out.get("insights") or []
            if isinstance(insights, dict):
                insights = [insights]
            if insights:
                st.markdown("**Insights:**")
                html_blocks = []
                for ins in insights:
                    if isinstance(ins, dict):
                        html_blocks.append(render_insight_tile_html(ins))
                    else:
                        # fallback string
                        html_blocks.append(f"<div class='insight-tile'><div class='k'>Signal</div><div class='v'>{ins}</div></div>")
                st.markdown("".join(html_blocks), unsafe_allow_html=True)
            else:
                st.info("No insights found for this agent.")

            # recommendations
            recs = out.get("recommendations") or out.get("recommendation") or []
            if isinstance(recs, dict):
                recs = [recs]
            if recs:
                st.markdown("**Recommendations:**")
                html_blocks = []
                for r in recs:
                    if isinstance(r, dict):
                        html_blocks.append(render_rec_tile_html(r))
                    else:
                        html_blocks.append(f"<div class='rec-tile'><div class='idea'>{r}</div><div class='conf'>Confidence: -</div></div>")
                st.markdown("".join(html_blocks), unsafe_allow_html=True)
            else:
                st.info("No recommendations found for this agent.")

    st.markdown("---")
    st.markdown("### Final Marketer Strategy")
    final = raw.get("final_decision") or raw.get("final_strategy") or raw.get("final_campaign") or {}
    if final:
        # show executive summary
        exec_sum = final.get("executive_summary") or final.get("summary") or "No summary available"
        st.markdown(f"**Executive Summary:** {exec_sum}")
        # final campaign (if any)
        fc = final.get("final_campaign") or final.get("final_strategy") or final.get("final_campaign")
        if isinstance(final.get("final_campaign"), dict):
            fc = final.get("final_campaign")
        else:
            fc = final if "campaign_name" in final else fc

        if fc and isinstance(fc, dict) and fc.get("campaign_name"):
            st.markdown("**Final Campaign (preview)**")
            st.markdown(render_rec_tile_html(fc), unsafe_allow_html=True)
        else:
            st.info("No final campaign available.")

    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<div style='text-align:center; padding:8px; color:#6b7280;'>Model: v1.0 • Embedding: mxbai-embed-large • UI by NextGen Marketer</div>", unsafe_allow_html=True)
