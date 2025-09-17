# llm_utils.py  (patched)
import ollama
import json
import logging
from typing import Optional, Any, Dict

logger = logging.getLogger("llm_utils")
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(ch)

# Default options you were using; we keep these but allow caller override
OLLAMA_OPTIONS = {
    "keep_alive": "30m",  # keep model hot in VRAM/RAM
    "num_ctx": 2048,      # context size
    "num_predict": 400,   # response token cap (increase if you get truncation)
    "temperature": 0.2,
    "top_p": 0.9,
    # "num_thread": 0,    # optional
}

def _safe_json_load(s: str) -> Optional[Any]:
    """Try to parse JSON string s; return Python object or None."""
    try:
        return json.loads(s)
    except Exception:
        return None

def _extract_largest_brace_group(s: str) -> Optional[str]:
    """
    Find the largest substring that starts with '{' and ends with '}' (by outermost match).
    This is a heuristic to pull JSON out of mixed output.
    """
    start = s.find('{')
    end = s.rfind('}')
    if start == -1 or end == -1 or end <= start:
        return None
    candidate = s[start:end+1]
    return candidate

def _close_braces_heuristic(s: str) -> str:
    """
    If JSON was cut off, attempt to balance braces by appending missing closing braces.
    Simple heuristic: count '{' vs '}' and append '}' as needed.
    """
    opens = s.count('{')
    closes = s.count('}')
    if opens > closes:
        s = s + ('}' * (opens - closes))
    return s

def ask_ollama(prompt: str, model: str, json_mode: bool = True, options: Optional[Dict] = None, repair_attempts: int = 2) -> Any:
    """
    Ask Ollama for an answer. If json_mode=True, attempt robust JSON parsing and
    repair via additional calls if the model returns invalid JSON.
    - options: dict to override OLLAMA_OPTIONS for this call (e.g., {"num_predict": 800})
    - repair_attempts: number of attempts to ask the model to repair its own output
    Returns:
      - parsed JSON (dict/list) on success
      - string content if json_mode=False
      - on failure (after retries): {"error":"Invalid JSON","raw": "<raw content>"}
    """
    opts = dict(OLLAMA_OPTIONS)
    if options:
        opts.update(options)

    # Primary LLM call
    try:
        resp = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            options=opts,
            stream=False,
        )
    except Exception as e:
        logger.exception("ollama.chat failed: %s", e)
        return {"error": "ollama_error", "exception": str(e)}

    content = resp.get("message", {}).get("content", "")
    if not json_mode:
        return content

    # 1) Try direct JSON parse
    parsed = _safe_json_load(content)
    if parsed is not None:
        return parsed

    # 2) Try extracting largest {...} substring and parse
    candidate = _extract_largest_brace_group(content)
    if candidate:
        parsed = _safe_json_load(candidate)
        if parsed is not None:
            return parsed

    # 3) Ask the model to repair the JSON (few-shot / direct instruction)
    # We send a compact repair prompt and include the original raw content.
    repair_prompt_template = (
        "The previous response was supposed to be valid JSON but it is invalid or truncated.\n"
        "Please extract and return only the corrected, valid JSON object (no explanation, no markdown).\n"
        "Here is the raw output that needs fixing:\n\n"
        "<<<RAW_OUTPUT>>>\n\n"
        "Return just valid JSON (object or array). If fields are truncated, try to complete them reasonably."
    )

    repair_prompt = repair_prompt_template.replace("<<<RAW_OUTPUT>>>", content)

    # On repair attempts, increase allowed token budget (num_predict) to give model room to return full JSON
    repair_opts = dict(opts)
    # bump token budget a bit (caller can increase more explicitly)
    repair_opts["num_predict"] = max(repair_opts.get("num_predict", 400), 800)

    attempt = 0
    while attempt < repair_attempts:
        attempt += 1
        try:
            repair_resp = ollama.chat(
                model=model,
                messages=[{"role": "user", "content": repair_prompt}],
                options=repair_opts,
                stream=False,
            )
        except Exception as e:
            logger.exception("ollama.chat (repair) failed on attempt %d: %s", attempt, e)
            break

        repair_content = repair_resp.get("message", {}).get("content", "")

        # Try parse repaired content
        parsed = _safe_json_load(repair_content)
        if parsed is not None:
            return parsed

        # Try extracting {} from repair_content
        candidate = _extract_largest_brace_group(repair_content)
        if candidate:
            parsed = _safe_json_load(candidate)
            if parsed is not None:
                return parsed

        # If repair attempt didn't produce valid JSON, loop and retry (up to repair_attempts)

    # 4) Heuristic: try to close unmatched braces on the original output and parse
    closed = _close_braces_heuristic(content)
    parsed = _safe_json_load(closed)
    if parsed is not None:
        return parsed

    # 5) Heuristic: try to close braces on the last candidate substring
    if candidate:
        candidate_closed = _close_braces_heuristic(candidate)
        parsed = _safe_json_load(candidate_closed)
        if parsed is not None:
            return parsed

    # Nothing worked — return structured failure payload for downstream code to handle
    return {"error": "Invalid JSON", "raw": content}
