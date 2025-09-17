from typing import Dict, Any, List
import json
from utils.llm_utils import ask_ollama


class CampaignAgent:
    """
    CampaignAgent — analyzes campaign performance outputs and returns:
      - summary (legacy)
      - key_metrics (legacy)
      - insights: list of up to 3 structured items:
         { audience_segment, product_focus, region, signal, confidence }
      - recommendations: list of up to 3 campaign-style ideas:
         { idea, confidence }

    The agent uses ask_ollama(..., json_mode=True) and falls back to lightweight heuristics
    if the model does not return the expected schema.
    """

    def __init__(self, ollama_model: str = "mistral:7b"):
        self.ollama_model = ollama_model

    def analyze_campaigns(self, user_prompt: str = "") -> Dict[str, Any]:
        """
        Analyze campaign performance and suggest structured insights + campaign-style recommendations.
        """
        system_prompt = """
You are a Campaign Performance specialist.

Based ONLY on the campaign performance data provided, extract up to 3 actionable insights and propose 1–3 campaign-style recommendations.

Output STRICT JSON with top-level keys:
- "summary": short 1-2 sentence summary,
- "key_metrics": optional object with numeric/aggregate metrics,
- "insights": list of up to 3 objects, each with:
    - audience_segment (string),
    - product_focus (string),
    - region (string),
    - signal (string),    # 1-2 sentence reason
    - confidence (float 0.0–1.0)
- "recommendations": list of up to 3 objects, each with:
    - idea (short string describing a campaign or product action),
    - confidence (float 0.0–1.0)

Return ONLY valid JSON following the schema. No markdown or extra text.
"""

        prompt = f"{system_prompt}\n\nCampaign data / user question:\n{user_prompt}"

        resp = ask_ollama(prompt, model=self.ollama_model, json_mode=True)

        # Init
        insights: List[Dict[str, Any]] = []
        recommendations: List[Dict[str, Any]] = []
        summary = ""
        key_metrics = {}

        # If model returned structured dict, parse
        if isinstance(resp, dict):
            summary = str(resp.get("summary") or resp.get("executive_summary") or "")[:1000]
            key_metrics = resp.get("key_metrics", {}) or {}

            if "insights" in resp and isinstance(resp["insights"], list):
                for it in resp["insights"][:3]:
                    if not isinstance(it, dict):
                        continue
                    audience = str(it.get("audience_segment", "")).strip()
                    product = str(it.get("product_focus", "")).strip()
                    region = it.get("region", "")
                    if isinstance(region, list):
                        region = ", ".join([str(r) for r in region])
                    region = str(region).strip()
                    signal = str(it.get("signal", "")).strip()
                    try:
                        confidence = float(it.get("confidence", 0.0))
                        confidence = max(0.0, min(1.0, confidence))
                    except Exception:
                        confidence = 0.0

                    insights.append({
                        "audience_segment": audience or "General",
                        "product_focus": product or "",
                        "region": region or "All",
                        "signal": signal or "",
                        "confidence": confidence
                    })

            if "recommendations" in resp and isinstance(resp["recommendations"], list):
                for rec in resp["recommendations"][:3]:
                    if not isinstance(rec, dict):
                        if isinstance(rec, str) and rec.strip():
                            recommendations.append({"idea": rec.strip(), "confidence": 0.0})
                        continue
                    idea = str(rec.get("idea") or rec.get("title") or rec.get("text") or "").strip()
                    try:
                        conf = float(rec.get("confidence", 0.0))
                        conf = max(0.0, min(1.0, conf))
                    except Exception:
                        conf = 0.0
                    if idea:
                        recommendations.append({"idea": idea, "confidence": conf})

        else:
            # fallback for non-dict responses: put raw text into summary and create basic placeholders
            raw = str(resp)
            summary = raw[:1000]
            insights = [{
                "audience_segment": "General",
                "product_focus": "",
                "region": "All",
                "signal": summary.split("\n")[0][:300],
                "confidence": 0.0
            }]

        # If recommendations are missing, derive light-weight suggestions from insights
        if not recommendations and insights:
            for it in insights[:2]:
                pf = it.get("product_focus") or "product"
                aud = it.get("audience_segment") or "customers"
                idea = f"Run tailored ads for {aud} focusing on {pf} benefits"
                conf = float(it.get("confidence", 0.0))
                recommendations.append({"idea": idea, "confidence": round(conf or 0.6, 2)})

        result: Dict[str, Any] = {
            "summary": summary or "No summary available",
            "key_metrics": key_metrics,
            "insights": insights,
            "recommendations": recommendations
        }

        return result


if __name__ == "__main__":
    agent = CampaignAgent()
    out = agent.analyze_campaigns("Analyze campaign CTR drop for SUV ads and provide targeted recommendations")
    print(json.dumps(out, indent=2))
