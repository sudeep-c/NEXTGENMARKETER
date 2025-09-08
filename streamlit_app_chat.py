# streamlit_app_chat.py
import streamlit as st
import requests
import json
import pandas as pd
import io
from datetime import datetime, timedelta
from typing import List
from matplotlib import pyplot as plt

# CONFIG
API_BASE = st.secrets.get("API_BASE", "http://localhost:8000")
ACCENT_INDIGO = "#4F46E5"
ADOBE_RED = "#FF0000"
BG_GRADIENT = "linear-gradient(180deg, #f5f6fa 0%, #ffffff 100%)"

st.set_page_config(page_title="NextGen Marketer Chat", layout="wide", initial_sidebar_state="collapsed")

# CSS for modern chat UI
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
    with st.form(key="message_form", clear_on_submit=False):
        col_f1, col_f2, col_f3 = st.columns([0.04, 1, 0.15])
        with col_f1:
            emoji = st.selectbox("", options=["🙂","🤔","🔥","💡","📈"], index=0, key="emoji_select")
        with col_f2:
            user_input = st.text_input("", placeholder="Ask agents anything about campaigns, purchases, sentiment...", key="user_input")
        with col_f3:
            submit = st.form_submit_button("Send", help="Send query", on_click=None)
        if submit and user_input:
            # append user message
            st.session_state["messages"].append({"role":"user","text": user_input, "meta": datetime.utcnow().isoformat()})
            # call API
            try:
                r = requests.post(f"{API_BASE}/strategy", json={"query": user_input}, timeout=120)
                r.raise_for_status()
                data = r.json()
                final = data.get("final_strategy", {})
                # assistant summary bubble
                assistant_text = final.get("executive_summary", "No summary returned.")
                # attach recommendations
                recs = final.get("strategic_recommendations", [])
                if recs:
                    assistant_text += "\n\nRecommendations:\n" + "\n".join([f"- {x}" for x in recs])
                # push assistant message
                st.session_state["messages"].append({"role":"assistant","text": assistant_text, "meta": "confidence: "+("high" if data.get("valid_schema") else "low")})
                # store raw state for trace panel
                st.session_state["raw_state"] = data.get("raw_state", {})
            except Exception as e:
                st.session_state["messages"].append({"role":"assistant","text": f"Error calling API: {e}", "meta": ""})

with col2:
    st.markdown('<div class="rounded-card">', unsafe_allow_html=True)
    st.markdown("### Quick Metrics")
    raw = st.session_state.get("raw_state", {})
    # derive some quick KPIs if available
    campaign_out = raw.get("campaign_output", {})
    purchase_out = raw.get("purchase_output", {})
    sentiment_out = raw.get("sentiment_output", {})
    # Display sample KPIs (fallback placeholders)
    avg_ctr = campaign_out.get("key_metrics", {}).get("avg_ctr") if campaign_out else None
    avg_conv = campaign_out.get("key_metrics", {}).get("avg_conversion_rate") if campaign_out else None
    top_channel = campaign_out.get("key_metrics", {}).get("top_channel") if campaign_out else None
    st.markdown(f"**Avg CTR:** {avg_ctr or '—'}")
    st.markdown(f"**Avg Conv Rate:** {avg_conv or '—'}")
    st.markdown(f"**Top Channel:** {top_channel or '—'}")
    st.markdown("---")
    st.markdown("### Agent Trace")
    with st.expander("Campaign Agent Output"):
        st.code(json.dumps(campaign_out or "Not available", indent=2), language="json")
    with st.expander("Purchase Agent Output"):
        st.code(json.dumps(purchase_out or "Not available", indent=2), language="json")
    with st.expander("Sentiment Agent Output"):
        st.code(json.dumps(sentiment_out or "Not available", indent=2), language="json")
    with st.expander("Final Marketer Strategy"):
        st.code(json.dumps(raw.get("final_strategy", "Not available"), indent=2), language="json")
    st.markdown("---")
    st.markdown("### Retrieved Documents")
    docs = {}
    # docs are stored under _retrieved_documents in agent outputs
    if campaign_out and campaign_out.get("_retrieved_documents"):
        docs['campaigns'] = campaign_out["_retrieved_documents"]
    if purchase_out and purchase_out.get("_retrieved_documents"):
        docs['purchases'] = purchase_out["_retrieved_documents"]
    if sentiment_out and sentiment_out.get("_retrieved_documents"):
        docs['sentiments'] = sentiment_out["_retrieved_documents"]
    for k, v in docs.items():
        st.markdown(f"**{k}**")
        df = pd.DataFrame(v.get("metadatas", []))
        if not df.empty:
            st.dataframe(df.head(10))
        else:
            st.write("No metadata available")
    st.markdown('</div>', unsafe_allow_html=True)

# Footer / small print
st.markdown("<div style='text-align:center; padding:8px; color:#6b7280;'>Model: v1.0 • Embedding: mxbai-embed-large • UI by NextGen Marketer</div>", unsafe_allow_html=True)
