# agents/campaign_agent.py
from utils.rag_utils import query_namespace
from utils.llm_utils import ask_ollama

# ---- Config ----
NAMESPACE = "campaign"
MODEL = "llama3.1:8b"         # fast; pull with: ollama pull llama3.2:3b
TOP_K = 4
EVIDENCE_CHAR_LIMIT = 1000

def _pack_evidence_texts(hits):
    parts, total = [], 0
    for h in hits:
        t = (h.get("text", "") or "").strip().replace("\n", " ")
        if not t:
            continue
        if total + len(t) > EVIDENCE_CHAR_LIMIT:
            t = t[: max(0, EVIDENCE_CHAR_LIMIT - total)]
        parts.append(f"- {t}")
        total += len(t)
        if total >= EVIDENCE_CHAR_LIMIT:
            break
    return "\n".join(parts)

def _normalize_candidates(obj):
    out = []
    if isinstance(obj, list):
        for x in obj:
            out.append(x if isinstance(x, str) else str(x))
    elif isinstance(obj, str):
        out = [obj]
    return out[:3] or ["Campaign C"]

def _extract_max_score(scores):
    if isinstance(scores, list) and scores:
        try:
            return float(max(scores))
        except Exception:
            return 0.5
    return 0.5

def run(user_prompt: str, top_k: int = TOP_K):
    hits = query_namespace(NAMESPACE, user_prompt, k=top_k)
    evidence_blob = _pack_evidence_texts(hits)

    prompt = f"""
You are a Campaign Performance Agent.

User question:
"{user_prompt}"

Evidence (summarized bullets from historical campaign performance: channels, messages, CTR, conversions):
{evidence_blob if evidence_blob else "- (no evidence found)"}

Task:
- Based ONLY on historical performance patterns, propose 1–3 campaign strategy ideas.
- For each idea, assign a confidence score between 0.0 and 1.0 (float).
- Keep reasoning concise.
- Return STRICT JSON with these keys exactly:
  {{
    "candidates": ["<string>", "..."],
    "scores": [<float>, ...],
    "rationale": "<string>"
  }}
"""
    parsed = ask_ollama(prompt, model=MODEL, json_mode=True)

    candidates = _normalize_candidates(parsed.get("candidates", []))
    score = _extract_max_score(parsed.get("scores"))
    rationale = str(parsed.get("rationale", ""))[:400]

    return {
        "agent": "campaign",
        "candidates": candidates,
        "score": score,
        "rationale": rationale,
        "evidence": hits[:2],
    }

#llama3.1:8b