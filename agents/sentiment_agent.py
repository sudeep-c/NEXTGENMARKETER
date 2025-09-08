# agents/sentiment_agent.py
from utils.rag_utils import query_namespace
from utils.llm_utils import ask_ollama

# ---- Config ----
NAMESPACE = "sentiment"
MODEL = "gemma2:9b"         # fast + good enough; pull with: ollama pull llama3.2:3b
TOP_K = 4                      # fewer hits => faster
EVIDENCE_CHAR_LIMIT = 1000     # trim what we send to the LLM

def _pack_evidence_texts(hits):
    """Compact the retrieved docs into a short bullet list for the LLM."""
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
    """Ensure candidates is a list[str]."""
    out = []
    if isinstance(obj, list):
        for x in obj:
            out.append(x if isinstance(x, str) else str(x))
    elif isinstance(obj, str):
        out = [obj]
    return out[:3] or ["Campaign A"]  # sensible fallback

def _extract_max_score(scores):
    """Pick the max score from a list of numbers; fallback to 0.5."""
    if isinstance(scores, list) and scores:
        try:
            return float(max(scores))
        except Exception:
            return 0.5
    return 0.5

def run(user_prompt: str, top_k: int = TOP_K):
    # 1) Retrieve RAG evidence
    hits = query_namespace(NAMESPACE, user_prompt, k=top_k)

    # 2) Build compact evidence blob
    evidence_blob = _pack_evidence_texts(hits)

    # 3) Ask the LLM (JSON-only)
    prompt = f"""
You are a Sentiment Analysis Agent.

User question:
"{user_prompt}"

Evidence (summarized bullets from customer sentiment data):
{evidence_blob if evidence_blob else "- (no evidence found)"}

Task:
- Based ONLY on sentiment signals, propose 1–3 relevant campaign or product ideas.
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

    # 4) Normalize outputs (defensive)
    candidates = _normalize_candidates(parsed.get("candidates", []))
    score = _extract_max_score(parsed.get("scores"))
    rationale = str(parsed.get("rationale", ""))[:400]

    # 5) Return standard agent schema (trim evidence for UI)
    return {
        "agent": "sentiment",
        "candidates": candidates,
        "score": score,
        "rationale": rationale,
        "evidence": hits[:2],  # keep just a couple for UI transparency
    }

#gemma2:9b