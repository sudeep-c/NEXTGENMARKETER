# utils/llm_utils.py
import ollama, json

OLLAMA_OPTIONS = {
    "keep_alive": "30m",  # keep model hot in VRAM/RAM
    "num_ctx": 2048,      # enough for our prompts; smaller = faster
    "num_predict": 400,   # cap response length (fast + JSON friendly)
    "temperature": 0.2,   # low → more deterministic JSON
    "top_p": 0.9,
    # Optional (usually helps on Windows CPU):
    "num_thread": 0,      # 0 = auto (use all cores)
}

def ask_ollama(prompt: str, model: str, json_mode: bool = True):
    resp = ollama.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        options=OLLAMA_OPTIONS,
        stream=False,
    )
    content = resp["message"]["content"]
    if not json_mode:
        return content
    try:
        return json.loads(content)
    except Exception:
        start, end = content.find("{"), content.rfind("}")
        if start != -1 and end != -1:
            try:
                return json.loads(content[start:end+1])
            except Exception:
                pass
        return {"error": "Invalid JSON", "raw": content}
