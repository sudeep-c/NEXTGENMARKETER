# agents/marketer_agent.py
import json
from utils.llm_utils import ask_ollama

MODEL = "llama3.1:8b"   # better synthesis/creativity; pull with: ollama pull llama3.1:8b

def _normalize_channels(ch):
    if isinstance(ch, list):
        out = []
        for item in ch:
            if isinstance(item, str):
                out.append(item)
            elif isinstance(item, dict):
                v = item.get("name") or item.get("channel") or item.get("type")
                out.append(str(v) if v is not None else None)
            else:
                out.append(str(item))
        return [c for c in out if c] or ["Email"]
    if isinstance(ch, str):
        return [ch] if ch else ["Email"]
    return ["Email"]

def run(agent_outputs, user_prompt: str):
    # Keep payload compact for speed
    try:
        compact_outputs = []
        for o in agent_outputs:
            if isinstance(o, dict):
                compact_outputs.append({
                    "agent": o.get("agent"),
                    "candidates": o.get("candidates", [])[:3],
                    "score": o.get("score", 0.0),
                    "rationale": (o.get("rationale") or "")[:200],
                })
            else:
                compact_outputs.append({"agent": "unknown", "candidates": [], "score": 0.0, "rationale": str(o)[:200]})
        insights = json.dumps(compact_outputs, ensure_ascii=False)
    except Exception:
        insights = str(agent_outputs)[:2000]

    prompt = f"""
You are a Creative Marketing Strategist AI.

User question:
"{user_prompt}"

Insights from specialist agents (JSON, compact):
{insights}

Task:
- Generate ONE NEW campaign idea (new concept, not a past campaign).
- Output STRICT JSON with EXACT keys:
  {{
    "campaign_name": "<string>",
    "product": "<string>",
    "region": "<string>",
    "segment": "<string>",
    "concept": "<string>",
    "channels": ["Email","Push","SMS"],  // array of strings only
    "content_brief": "<string>"
  }}
Keep it concise and actionable.
"""
    resp = ask_ollama(prompt, model=MODEL, json_mode=True)

    # Harden channels to list[str]
    resp["channels"] = _normalize_channels(resp.get("channels", []))
    # Add minimal defaults to avoid UI crashes
    resp.setdefault("campaign_name", "New Campaign")
    resp.setdefault("product", "—")
    resp.setdefault("region", "—")
    resp.setdefault("segment", "—")
    resp.setdefault("concept", "—")
    resp.setdefault("content_brief", "—")
    return resp
