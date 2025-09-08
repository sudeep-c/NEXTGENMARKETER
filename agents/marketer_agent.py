from typing import Dict, Any
import json
import ollama


class MarketerAgent:
    def __init__(self, ollama_model="gpt-oss:20b"):
        self.ollama_model = ollama_model

    def combine_insights(
        self,
        campaign_output: Dict[str, Any],
        purchase_output: Dict[str, Any],
        sentiment_output: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Takes outputs from Campaign, Purchase, and Sentiment agents
        and produces a unified marketing strategy recommendation.
        """
        system_prompt = """
        You are the Marketer Agent. Your job is to combine insights from
        Campaign, Purchase, and Sentiment Agents into one unified marketing strategy.
        
        Output structured JSON with:
        - executive_summary (2–3 lines),
        - key_findings (from campaigns, purchases, and sentiment),
        - conflicts (where agents disagree or data is misaligned),
        - strategic_recommendations (high-level actions for the marketing team).
        
        Only return valid JSON.
        """

        context = {
            "campaign_agent": campaign_output,
            "purchase_agent": purchase_output,
            "sentiment_agent": sentiment_output
        }

        prompt = f"{system_prompt}\n\nAgent Insights:\n{json.dumps(context, indent=2)}\n"

        response = ollama.chat(model=self.ollama_model, messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ])

        try:
            result = json.loads(response["message"]["content"])
        except Exception:
            # fallback if not JSON
            result = {
                "executive_summary": response["message"]["content"],
                "key_findings": {},
                "conflicts": [],
                "strategic_recommendations": []
            }

        return result


if __name__ == "__main__":
    # Example dummy agent outputs (in practice, import actual agent outputs here)
    campaign_output = {
        "summary": "SUV CTR declining; compact SUVs outperform luxury SUVs.",
        "recommendations": ["Shift spend from TV to Social Media"]
    }
    purchase_output = {
        "summary": "Compact SUVs lead sales; sedans declining.",
        "recommendations": ["Focus campaigns on compact SUVs"]
    }
    sentiment_output = {
        "summary": "Positive buzz around Brezza; complaints about service.",
        "recommendations": ["Improve after-sales service messaging"]
    }

    agent = MarketerAgent()
    output = agent.combine_insights(campaign_output, purchase_output, sentiment_output)
    print(json.dumps(output, indent=2))
