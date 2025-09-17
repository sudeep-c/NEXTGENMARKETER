# purchase_agent.py
from typing import Dict, Any
import json
from utils.llm_utils import ask_ollama


class PurchaseAgent:
    def __init__(self, ollama_model="mistral:7b"):
        self.ollama_model = ollama_model

    def analyze_purchases(self, user_prompt: str) -> Dict[str, Any]:
        """
        Analyze purchase-related queries and return structured insights.
        Output is normalized to include both insights and campaign-style recommendations.
        """
        system_prompt = """
        You are the Purchase Agent. Your job is to analyze purchase data
        (transactions, payment methods, regions, products).

        Return STRICT JSON with this structure:
        {
          "summary": "<short overview>",
          "key_metrics": {},   // optional key metrics, can be empty
          "insights": [
            {
              "audience_segment": "<string>",
              "product_focus": "<string>",
              "region": "<string>",
              "signal": "<string>",
              "confidence": <float>
            }
          ],
          "recommendations": [
            {
              "idea": "<campaign-style recommendation derived from purchase signals>",
              "confidence": <float>
            }
          ]
        }

        Rules:
        - Insights = audience/product/region-level patterns from purchases
        - Recommendations = campaign-style ideas derived from purchase signals
        - Confidence between 0.0–1.0
        - Be concise and actionable
        """

        # Call LLM
        resp = ask_ollama(
            f"{system_prompt}\n\nUser question:\n{user_prompt}",
            model=self.ollama_model,
            json_mode=True
        )

        # Normalize output
        if not isinstance(resp, dict):
            return {
                "summary": str(resp),
                "key_metrics": {},
                "insights": [],
                "recommendations": []
            }

        result = {
            "summary": resp.get("summary", "No summary available"),
            "key_metrics": resp.get("key_metrics", {}),
            "insights": resp.get("insights", []),
            "recommendations": resp.get("recommendations", [])
        }

        # Ensure recommendations are campaign-style (fallback if empty)
        if not result["recommendations"] and result["insights"]:
            result["recommendations"] = [
                {
                    "idea": f"Target {ins.get('audience_segment', 'customers')} with a campaign highlighting {ins.get('product_focus', 'products')}",
                    "confidence": ins.get("confidence", 0.6)
                }
                for ins in result["insights"][:2]
            ]

        return result


if __name__ == "__main__":
    agent = PurchaseAgent()
    output = agent.analyze_purchases("Analyze Ertiga purchase patterns across states")
    print(json.dumps(output, indent=2))
