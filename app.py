# app.py
import json
import streamlit as st
from orchestrator import run_flow

# try:
#     from utils.llm_utils import ask_ollama
#     _ = ask_ollama("ping", model="llama3.1:8b", json_mode=False)
#     _ = ask_ollama("ping", model="gemma2:9b", json_mode=False)
# except Exception:
#     pass

# ---------- Page config ----------
st.set_page_config(page_title="Next-Gen Marketer", page_icon="📈", layout="wide")

# ---------- CSS ----------
st.markdown("""
<style>
:root{
  --bg:#faf7fb; --surface:#ffffff; --card:#ffffffcc;
  --primary:#6b4eff; --secondary:#ff4ecb; --muted:#a09bb2; --text:#1b102a;
  --radius:18px; --shadow:0 8px 24px rgba(32,0,64,0.10);
}
html, body, [data-testid="block-container"]{
  background: radial-gradient(1200px 600px at 15% -10%, #ffe9f6 0%, #faf7fb 45%, #f7f2ff 100%);
  color: var(--text);
}
header {visibility: hidden;}
.container{ max-width: 1200px; margin: 0 auto; padding: 12px 16px 40px; }
.hero{ display:flex; align-items:center; gap:18px; margin: 12px 0 18px; }
.logo{ width:48px; height:48px; display:grid; place-items:center; border-radius:14px;
       background: linear-gradient(135deg, var(--secondary), var(--primary)); color:#fff; font-weight:700; box-shadow: var(--shadow); }
.h1{ font-size: 28px; font-weight: 800; letter-spacing:-0.02em; }
.h2{ font-size: 18px; color: var(--muted); margin-top:2px; }
.panel{ background: var(--surface); border-radius: var(--radius); box-shadow: var(--shadow);
        padding: 18px; border: 1px solid rgba(107,78,255,0.08); }
.btn-primary button{ background: linear-gradient(135deg, var(--primary), #9d7bff) !important;
        color: #fff !important; border:none !important; border-radius:12px !important; box-shadow: var(--shadow); }
.chips {display:flex; flex-wrap:wrap; gap:8px; margin-top:8px;}
.card{ background: var(--card); backdrop-filter: blur(8px); border-radius: var(--radius);
       box-shadow: var(--shadow); padding: 14px; border: 1px solid rgba(107,78,255,0.10); }
.card h4{ margin: 0 0 6px; font-size: 15px;}
.badge{ display:inline-flex; align-items:center; gap:6px; background: #f7f2ff; color:#5a3cff;
        border-radius:999px; padding:6px 10px; font-size:12px; border:1px solid rgba(107,78,255,0.18); }
.kv{ display:grid; grid-template-columns: 140px 1fr; gap:8px; margin:4px 0;}
.kv .k{ color:var(--muted); } .kv .v{ font-weight:600; }
hr.sep{ border:none; height:1px; background: linear-gradient(90deg, transparent, rgba(107,78,255,0.25), transparent); margin: 12px 0; }
.small{ color: var(--muted); font-size: 12px; }
pre { white-space: pre-wrap; }
</style>
""", unsafe_allow_html=True)

# ---------- Header ----------
st.markdown("""
<div class="container">
  <div class="hero">
    <div class="logo">NG</div>
    <div>
      <div class="h1">Next-Gen Marketer</div>
      <div class="h2">Multi-agent orchestration · RAG · Generative campaign ideation</div>
    </div>
  </div>
""", unsafe_allow_html=True)

# ---------- Helpers ----------
def stringify_channels(ch):
    """Render channels field safely as a comma-separated string."""
    if isinstance(ch, list):
        out = []
        for item in ch:
            if isinstance(item, str):
                out.append(item)
            elif isinstance(item, dict):
                val = item.get("name") or item.get("channel") or item.get("type")
                out.append(str(val) if val is not None else json.dumps(item, ensure_ascii=False))
            else:
                out.append(str(item))
        return ", ".join(out) if out else "—"
    return str(ch or "—")

def normalize_agent_outputs(outs_raw):
    """Ensure each agent output is a dict with expected keys to avoid UI crashes."""
    safe = []
    for o in outs_raw or []:
        if isinstance(o, dict):
            safe.append(o)
        else:
            safe.append({
                "agent": "unknown",
                "candidates": [],
                "score": 0.0,
                "rationale": str(o),
                "evidence": []
            })
    return safe

# ---------- Controls Panel ----------
with st.container():
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    col_prompt, col_run = st.columns([5, 1])
    with col_prompt:
        default_prompt = "Give me top 5 campaign ideas based on customer sentiments"
        prompt = st.text_area("Your brief", value=default_prompt, height=90, label_visibility="collapsed")
    with col_run:
        st.markdown('<div class="btn-primary">', unsafe_allow_html=True)
        run_clicked = st.button("Run Orchestration ▶", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="chips">', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("💬 Sentiment-only ideas", use_container_width=True):
            prompt = "Give me top 5 campaign ideas based on customer sentiments"
    with c2:
        if st.button("🛒 Sentiment + Purchase strategy", use_container_width=True):
            prompt = "Recommend a strategy using sentiments + purchase behavior"
    with c3:
        if st.button("🏆 Best overall strategy", use_container_width=True):
            prompt = "What's the best overall campaign strategy?"
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ---------- Run & Results ----------
if run_clicked:
    with st.spinner("Running multi-agent workflow…"):
        result = run_flow(prompt)

    # Orchestrator meta
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown("#### Orchestrator")
    st.markdown(
        f'<span class="badge">Route: <b>{result.get("route","")}</b></span>',
        unsafe_allow_html=True
    )

    # Agent outputs (defensive)
    st.markdown('<hr class="sep"/>', unsafe_allow_html=True)
    st.markdown("#### Specialist Agents")
    outs = normalize_agent_outputs(result.get("agent_outputs", []))

    # Grid of cards
    cols = st.columns(3)
    for idx, out in enumerate(outs):
        with cols[idx % 3]:
            agent = out.get("agent", "agent")
            try:
                score = float(out.get("score", 0.0) or 0.0)
            except Exception:
                score = 0.0
            candidates = out.get("candidates", []) or ["—"]
            rationale = out.get("rationale", "")
            evidence = out.get("evidence", []) or []

            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown(f'<h4>{agent.title()} Agent</h4>', unsafe_allow_html=True)
            st.markdown(f'<span class="badge">Confidence: {score:.2f}</span>', unsafe_allow_html=True)
            st.markdown(
                '<div class="kv"><div class="k">Candidates</div><div class="v">'
                + ", ".join([f"`{str(c)}`" for c in candidates[:5]]) + '</div></div>',
                unsafe_allow_html=True
            )
            if rationale:
                st.markdown(f'<div class="kv"><div class="k">Rationale</div><div class="v">{rationale}</div></div>',
                            unsafe_allow_html=True)

            if evidence:
                with st.expander("Evidence (top snippets)"):
                    for ev in evidence[:3]:
                        if isinstance(ev, dict):
                            txt = (ev.get("text","") or "")[:500]
                            meta = ev.get("metadata", {})
                        else:
                            txt = str(ev)[:500]
                            meta = {}
                        st.code(txt)
                        if meta:
                            st.caption(f"meta: {meta}")
            st.markdown('</div>', unsafe_allow_html=True)

    # Final decision
    st.markdown('<hr class="sep"/>', unsafe_allow_html=True)
    st.markdown("#### Final Campaign Proposal")
    final = result.get("final_decision", {}) or {}

    campaign_name = final.get("campaign_name") or "New Campaign"
    product = final.get("product") or "—"
    region = final.get("region") or "—"
    segment = final.get("segment") or "—"
    concept = final.get("concept") or "—"
    brief = final.get("content_brief") or "—"

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(f'<h4>✨ {campaign_name}</h4>', unsafe_allow_html=True)
    st.markdown(f'''
    <div class="kv"><div class="k">Product</div><div class="v">{product}</div></div>
    <div class="kv"><div class="k">Region</div><div class="v">{region}</div></div>
    <div class="kv"><div class="k">Segment</div><div class="v">{segment}</div></div>
    <div class="kv"><div class="k">Channels</div><div class="v">{stringify_channels(final.get("channels"))}</div></div>
    <div class="kv"><div class="k">Concept</div><div class="v">{concept}</div></div>
    ''', unsafe_allow_html=True)

    with st.expander("Content Brief"):
        st.write(brief)

    pretty = json.dumps(final, indent=2, ensure_ascii=False)
    st.download_button("Download Campaign JSON", data=pretty, file_name="campaign_proposal.json")
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)  # panel

# ---------- Footer ----------
st.markdown("""
<div class="small" style="text-align:center; margin-top:18px;">
  Built with RAG + multi-agent orchestration (LangGraph) · Palette: off-white · pink · purple
</div>
</div>
""", unsafe_allow_html=True)
