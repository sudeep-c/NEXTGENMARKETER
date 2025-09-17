# marketer_agent.py
from typing import Dict, Any, List
import json
import ollama
from utils.llm_utils import ask_ollama


class MarketerAgent:
    def __init__(self, ollama_model: str = "mistral:7b"):
        self.ollama_model = ollama_model

    def _ensure_list_of_str(self, v):
        if v is None:
            return []
        if isinstance(v, list):
            return [str(x) for x in v]
        return [str(v)]

    def _safe_float(self, v, default=0.0):
        try:
            return float(v)
        except Exception:
            return default

    def _normalize_key_findings(self, maybe_kf: Dict[str, Any], sources_present: List[str]):
        """Return a key_findings dict with sensible defaults for missing agents."""
        norm = {}
        # expected keys: sentiment, purchase, campaign
        for k in ("sentiment", "purchase", "campaign"):
            val = maybe_kf.get(k) if isinstance(maybe_kf, dict) else None
            if val:
                # If it's a string or list, keep as-list of strings
                if isinstance(val, list):
                    norm[k] = [str(x) for x in val]
                elif isinstance(val, dict):
                    # flatten small dict -> list of "k: v"
                    parts = []
                    for kk, vv in val.items():
                        parts.append(f"{kk}: {vv}")
                    norm[k] = parts
                else:
                    norm[k] = [str(val)]
            else:
                # mark as not available if agent was not run
                if k.capitalize() in sources_present:
                    norm[k] = ["No key findings produced by agent"]
                else:
                    norm[k] = [f"No data available (agent not run)"]
        return norm

    def _ensure_final_campaign_shape(self, raw: Dict[str, Any], sources_present: List[str], campaign_refs: Dict[str, Any]):
        """Guarantee final_campaign has the required keys and safe defaults."""
        # required structure
        keys = [
            "campaign_name",
            "product",
            "region",
            "audience_segment",
            "concept",
            "channels",        # list[str]
            "content_brief",
            "kpis",            # list[str]
            "rationale"
        ]

        fc = raw.get("final_campaign") if isinstance(raw, dict) else None
        if not isinstance(fc, dict):
            fc = {}

        # Helper: try to pick a product from campaign_refs (purchase -> product_focus, sentiment -> most mentioned models, campaign -> product)
        def pick_product():
            if campaign_refs.get("purchase"):
                p = campaign_refs["purchase"].get("product_focus") or campaign_refs["purchase"].get("product") or campaign_refs["purchase"].get("top_products")
                if isinstance(p, list) and p:
                    return ", ".join([str(x) for x in p])
                if p:
                    return str(p)
            if campaign_refs.get("sentiment"):
                mm = campaign_refs["sentiment"].get("most_mentioned_models") or campaign_refs["sentiment"].get("most_mentioned") or campaign_refs["sentiment"].get("top_models")
                if isinstance(mm, list) and mm:
                    return ", ".join([str(x) for x in mm])
                if mm:
                    return str(mm)
            if campaign_refs.get("campaign"):
                name = campaign_refs["campaign"].get("product") or campaign_refs["campaign"].get("products") or campaign_refs["campaign"].get("top_products")
                if isinstance(name, list) and name:
                    return ", ".join([str(x) for x in name])
                if name:
                    return str(name)
            return ""

        defaults = {
            "campaign_name": fc.get("campaign_name") or fc.get("name") or "New Campaign Idea",
            "product": fc.get("product") or pick_product() or "Generic Product",
            "region": fc.get("region") or fc.get("geo") or "National",
            "audience_segment": fc.get("audience_segment") or fc.get("segment") or "General Audience",
            "concept": fc.get("concept") or fc.get("idea") or "Short concise campaign concept generated from agent outputs",
            "channels": self._ensure_list_of_str(fc.get("channels")) or ["Email", "Push", "SMS"],
            "content_brief": fc.get("content_brief") or fc.get("brief") or "Short content brief describing main messaging and CTAs.",
            "kpis": self._ensure_list_of_str(fc.get("kpis")) or ["CTR", "Conversion Rate"],
            "rationale": fc.get("rationale") or fc.get("why") or "Derived from provided specialist agent outputs."
        }

        # Clean channel values to be strings and limited to known channels where possible
        cleaned_channels = []
        for ch in defaults["channels"]:
            chs = str(ch).strip()
            if chs:
                cleaned_channels.append(chs)
        if not cleaned_channels:
            cleaned_channels = ["Email", "Push", "SMS"]
        defaults["channels"] = cleaned_channels

        # Ensure kpis are strings
        defaults["kpis"] = [str(x) for x in defaults["kpis"]]

        return defaults

    def combine_insights(
        self,
        campaign_output: Dict[str, Any],
        purchase_output: Dict[str, Any],
        sentiment_output: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Takes outputs from Campaign, Purchase, and Sentiment agents
        and produces a unified marketing strategy recommendation.

        Guarantees:
        - final returned dict contains 'executive_summary', 'key_findings', 'final_campaign',
          and 'source_agents' keys.
        - 'final_campaign' follows a strict shape with safe defaults.
        - Marketer will NOT hallucinate unrelated products or industries (system prompt enforces).
        """

        # Build a compact context used for the prompt and also to attempt to extract
        # fields if the LLM response is incomplete.
        def extract_summary(out):
            if isinstance(out, dict):
                return out.get("summary", "")
            return str(out) if out else ""

        def extract_key_insights(out):
            if isinstance(out, dict):
                insights = out.get("insights", [])
                # keep as list of dicts or strings
                if isinstance(insights, list):
                    return insights
                if isinstance(insights, dict):
                    return [insights]
                if insights:
                    return [insights]
            return []

        campaign_summary = extract_summary(campaign_output)
        purchase_summary = extract_summary(purchase_output)
        sentiment_summary = extract_summary(sentiment_output)

        # Collect small reference blob for fallback extraction
        campaign_refs = {
            "campaign": campaign_output or {},
            "purchase": purchase_output or {},
            "sentiment": sentiment_output or {},
        }

        # Track which agents produced outputs
        sources = []
        if campaign_output:
            sources.append("Campaign")
        if purchase_output:
            sources.append("Purchase")
        if sentiment_output:
            sources.append("Sentiment")

        # System prompt — tightened to avoid hallucinations and force strict JSON
        system_prompt = """
You are Marketer Agent — a strict, conservative marketing strategist assistant.
You MUST only use the information present in the provided "Agent Insights" section below.
Do NOT invent facts, products, regions, or metrics that are not present in the provided agent outputs.
If an agent's output is missing, explicitly mark its findings as "No data available (agent not run)".
Your primary task is to produce ONE concise new campaign idea (not copy-paste of existing campaigns),
and a short executive summary + structured key findings. The final output MUST be valid JSON.

Output JSON MUST contain these top-level keys:
- executive_summary (string)
- key_findings (object with keys 'sentiment', 'purchase', 'campaign' each containing a list of strings)
- final_campaign (object with exact keys: campaign_name, product, region, audience_segment, concept, channels, content_brief, kpis, rationale)
- source_agents (list of strings)

Do not add additional top-level keys beyond these (you may include 'conflicts' if necessary).
Keep the executive_summary <= 5 sentences and keep campaign fields concise.
If you cannot produce a confident answer, still return valid JSON, and set sensible defaults.
"""

        # Compose the agent insights compactly (JSON) to feed to LLM
        insights_blob = {
            "campaign_summary": campaign_summary,
            "purchase_summary": purchase_summary,
            "sentiment_summary": sentiment_summary,
            "campaign_insights": campaign_output.get("insights") if isinstance(campaign_output, dict) else None,
            "purchase_insights": purchase_output.get("insights") if isinstance(purchase_output, dict) else None,
            "sentiment_insights": sentiment_output.get("insights") if isinstance(sentiment_output, dict) else None,
        }

        prompt = f"""
{system_prompt}

Agent Insights (JSON):
{json.dumps(insights_blob, default=str, indent=2)}

Task:
- Using ONLY the Agent Insights above, generate the required JSON structure.
- Produce ONE NEW campaign idea (new concept).
- Keep the executive summary concise and do not hallucinate.
"""

        # Ask the LLM via helper
        resp = ask_ollama(prompt, model=self.ollama_model, json_mode=True)

        # If response is already a dict, use it; else attempt to parse JSON; else fallback to structured content
        result: Dict[str, Any]
        if isinstance(resp, dict):
            result = resp
        else:
            # try to parse JSON string
            try:
                result = json.loads(str(resp))
            except Exception:
                # fallback: produce a structured result using compact synthesis
                exec_sum = (
                    campaign_summary or purchase_summary or sentiment_summary or
                    "No substantive agent outputs available."
                )
                result = {
                    "executive_summary": exec_sum[:500],
                    "key_findings": {},
                    "final_campaign": {},
                    "source_agents": sources,
                }

        # normalize key_findings
        maybe_kf = result.get("key_findings", {})
        normalized_kf = self._normalize_key_findings(maybe_kf, sources)
        result["key_findings"] = normalized_kf

        # ensure executive summary exists and is concise
        exec_summary = result.get("executive_summary") or ""
        if not exec_summary:
            # create short executive summary from available summaries
            pieces = []
            if sentiment_summary:
                pieces.append(sentiment_summary)
            if purchase_summary:
                pieces.append(purchase_summary)
            if campaign_summary:
                pieces.append(campaign_summary)
            exec_summary = " ".join(pieces)[:800] if pieces else "No executive summary available."
        result["executive_summary"] = exec_summary.strip()

        # ensure source_agents present
        if "source_agents" not in result or not isinstance(result["source_agents"], list):
            result["source_agents"] = sources

        # ensure final_campaign shape
        final_campaign = self._ensure_final_campaign_shape(result, sources, campaign_refs)
        result["final_campaign"] = final_campaign

        # final safety: ensure keys exist
        for k in ("executive_summary", "key_findings", "final_campaign", "source_agents"):
            if k not in result:
                result[k] = {} if k == "key_findings" else ([] if k == "source_agents" else "")

        return result


if __name__ == "__main__":
    # Quick local test
    campaign_output = {
        "summary": "Campaign performance mixed; email works best",
        "insights": [{"audience_segment": "Tech-savvy", "product_focus": "Alpha", "confidence": 0.8}],
    }
    purchase_output = {
        "summary": "Purchases concentrated in South region for Alpha",
        "insights": [{"audience_segment": "Families", "product_focus": "Alpha", "confidence": 0.75}],
    }
    sentiment_output = {
        "summary": "Mostly positive mentions for Alpha among urban users",
        "insights": [{"audience_segment": "Urban", "product_focus": "Alpha", "confidence": 0.9}],
    }
    agent = MarketerAgent()
    out = agent.combine_insights(campaign_output, purchase_output, sentiment_output)
    print(json.dumps(out, indent=2))
