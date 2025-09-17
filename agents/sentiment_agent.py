from typing import Dict, Any, List
import json
import chromadb
import ollama
from utils.llm_utils import ask_ollama


class SentimentAgent:
    """
    SentimentAgent — returns:
      - structured 'insights' list (new schema)
      - 'recommendations' list of campaign-style ideas (new schema)
      - legacy fields: summary, key_metrics (for backward compatibility)

    New 'insights' schema (each item):
    {
      "audience_segment": "<string>",
      "product_focus": "<string>",
      "region": "<string>",
      "signal": "<string>",
      "confidence": 0.0
    }

    New 'recommendations' schema (each item):
    {
      "idea": "<string>",
      "confidence": 0.0
    }
    """
    def __init__(self, chroma_dir: str = "./chroma_db", ollama_model: str = "mistral:7b", top_k: int = 10):
        self.ollama_model = ollama_model
        self.top_k = top_k

        # Try to connect to ChromaDB; if not available, keep None and continue (graceful degrade)
        try:
            self.client = chromadb.PersistentClient(path=chroma_dir)
            # collection name used in your project; fallback if not present
            try:
                self.collection = self.client.get_collection("sentiments_maruti")
            except Exception:
                collections = self.client.list_collections()
                if collections:
                    self.collection = self.client.get_collection(collections[0].name)
                else:
                    self.collection = None
        except Exception:
            self.client = None
            self.collection = None

    def retrieve_sentiment_data(self, query: str) -> str:
        """
        Retrieve text blobs from Chroma that match the query.
        Returns a concatenated string suitable for passing into the LLM prompt.
        """
        if not self.collection:
            return "(no sentiment docs available)"

        try:
            # Prefer generating an embedding via ollama if available
            try:
                emb = ollama.embeddings(model="nomic-embed-text", prompt=query).embedding
            except Exception:
                emb = None

            if emb is not None:
                results = self.collection.query(query_embeddings=[emb], n_results=self.top_k)
                docs = results.get("documents", [[]])[0]
            else:
                # Fallback to text query if embeddings are unavailable
                results = self.collection.query(query_texts=[query], n_results=self.top_k)
                docs = results.get("documents", [[]])[0]

            return "\n\n".join([d for d in docs if isinstance(d, str)])
        except Exception:
            return "(error retrieving sentiment docs)"

    def analyze_sentiment(self, user_prompt: str = "") -> Dict[str, Any]:
        """
        Analyze sentiment and return structured insights + recommendations + legacy outputs.
        """
        sentiment_docs = self.retrieve_sentiment_data(user_prompt or "customer sentiment for brand")

        # Example schema for guidance to LLM
        schema_example = {
            "insights": [
                {
                    "audience_segment": "Young families in Tier-2 cities",
                    "product_focus": "Ertiga",
                    "region": "South India",
                    "signal": "High EMI adoption; positive mentions about cabin space",
                    "confidence": 0.82
                }
            ],
            "summary": "Short 1-2 sentence summary of the most important sentiment signals.",
            "recommendations": [
                {
                    "idea": "Run regional EMI-focused offers for Ertiga",
                    "confidence": 0.8
                }
            ]
        }

        system_prompt = f"""
You are a Sentiment Analysis specialist. Based ONLY on the customer feedback and social signals provided,
extract up to 3 actionable, compact insights AND propose 1–3 short campaign-style recommendations.

Requirements (STRICT JSON output):
Top-level object with keys:
- "insights": list of up to 3 objects, each with:
    - audience_segment (string)
    - product_focus (string)
    - region (string)
    - signal (string)     # 1-2 sentence rationale
    - confidence (float between 0.0 and 1.0)
- "summary": short 1-2 sentence string
- "recommendations": list of up to 3 objects, each with:
    - idea (short string describing a campaign or product action)
    - confidence (float between 0.0 and 1.0)

Return ONLY valid JSON following this schema. Do NOT include any markdown or explanatory text.

Example:
{json.dumps(schema_example, ensure_ascii=False, indent=2)}
"""

        prompt = f"{system_prompt}\n\nCustomer Sentiment Data:\n{sentiment_docs}\n\nUser question: {user_prompt}"

        # Ask the LLM and expect JSON back (ask_ollama handles json_mode=True)
        resp = ask_ollama(prompt, model=self.ollama_model, json_mode=True)

        # Initialize outputs
        insights: List[Dict[str, Any]] = []
        summary: str = ""
        recommendations: List[Dict[str, Any]] = []
        legacy_key_metrics = {}

        # Parse LLM response if it's a dict
        if isinstance(resp, dict):
            # Parse summary
            summary = str(resp.get("summary", "") or resp.get("executive_summary", ""))[:1000]

            # Parse structured insights
            if "insights" in resp and isinstance(resp["insights"], list):
                raw_insights = resp["insights"]
                for it in raw_insights[:3]:
                    if not isinstance(it, dict):
                        continue
                    audience = str(it.get("audience_segment", "")).strip()
                    product = str(it.get("product_focus", "")).strip()
                    region = it.get("region", "")
                    # coerce region to string if list
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

            # Parse recommendations if present
            if "recommendations" in resp and isinstance(resp["recommendations"], list):
                for rec in resp["recommendations"][:3]:
                    if not isinstance(rec, dict):
                        # try to salvage if it's a string
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

            # Keep any legacy key_metrics if present for export/debug
            legacy_key_metrics = resp.get("key_metrics", {}) if isinstance(resp.get("key_metrics", {}), dict) else {}

        else:
            # Non-dict response - fallback: put the raw text into summary and create low-confidence fallback
            raw_text = str(resp)
            summary = raw_text[:1000]
            recommendations = [{"idea": "No structured recommendation parsed from model output", "confidence": 0.0}]
            insights = [{
                "audience_segment": "General",
                "product_focus": "",
                "region": "All",
                "signal": summary.split("\n")[0][:300],
                "confidence": 0.0
            }]

        # If LLM didn't return recommendations, attempt light heuristic suggestions based on insights
        if not recommendations:
            # create up to 2 lightweight campaign-style recs from top insights
            for it in insights[:2]:
                pf = it.get("product_focus") or "product"
                aud = it.get("audience_segment") or "target audience"
                idea = f"Target {aud} with a short campaign focused on {pf} benefits"
                conf = float(it.get("confidence", 0.0))
                # boost a bit if signal mentions explicit purchase triggers
                if "emi" in (it.get("signal", "").lower()):
                    conf = min(1.0, conf + 0.1)
                    idea = f"Promote EMI offers to {aud} for {pf}"
                recommendations.append({"idea": idea, "confidence": round(conf, 2)})

        # Final result contains the new schema + legacy fields for compatibility
        result: Dict[str, Any] = {
            "summary": summary,
            "key_metrics": legacy_key_metrics,
            "insights": insights,
            "recommendations": recommendations
        }

        return result


if __name__ == "__main__":
    agent = SentimentAgent()
    out = agent.analyze_sentiment("What do customers say about Ertiga and Fronx?")
    print(json.dumps(out, indent=2, ensure_ascii=False))
