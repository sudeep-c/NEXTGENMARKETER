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

        # Extract meaningful content from agent outputs
        def extract_summary(output):
            if isinstance(output, dict):
                return output.get("summary", "No data available")
            return str(output) if output else "No data available"
        
        def extract_insights(output):
            if isinstance(output, dict):
                insights = output.get("insights", [])
                if isinstance(insights, list):
                    return [str(item) for item in insights if item]
                return [str(insights)] if insights else []
            return []
        
        def extract_recommendations(output):
            if isinstance(output, dict):
                recs = output.get("recommendations", [])
                if isinstance(recs, list):
                    return [str(item) for item in recs if item]
                return [str(recs)] if recs else []
            return []
        
        campaign_summary = extract_summary(campaign_output)
        purchase_summary = extract_summary(purchase_output)
        sentiment_summary = extract_summary(sentiment_output)
        
        campaign_insights = extract_insights(campaign_output)
        purchase_insights = extract_insights(purchase_output)
        sentiment_insights = extract_insights(sentiment_output)
        
        campaign_recs = extract_recommendations(campaign_output)
        purchase_recs = extract_recommendations(purchase_output)
        sentiment_recs = extract_recommendations(sentiment_output)
        
        # Convert any dictionaries to strings
        def safe_join(items):
            if not items:
                return 'None'
            safe_items = []
            for item in items:
                if isinstance(item, dict):
                    safe_items.append(str(item))
                else:
                    safe_items.append(str(item))
            return ', '.join(safe_items)

        context = f"""
Campaign Agent Summary: {campaign_summary}
Campaign Insights: {safe_join(campaign_insights)}
Campaign Recommendations: {safe_join(campaign_recs)}

Purchase Agent Summary: {purchase_summary}
Purchase Insights: {safe_join(purchase_insights)}
Purchase Recommendations: {safe_join(purchase_recs)}

Sentiment Agent Summary: {sentiment_summary}
Sentiment Insights: {safe_join(sentiment_insights)}
Sentiment Recommendations: {safe_join(sentiment_recs)}
"""

        prompt = f"{system_prompt}\n\nAgent Insights:\n{context}\n"

        response = ollama.chat(model=self.ollama_model, messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ])

        try:
            result = json.loads(response["message"]["content"])
            # Ensure all required fields exist
            if "key_findings" not in result:
                result["key_findings"] = {
                    "campaign_insights": campaign_summary,
                    "purchase_insights": purchase_summary,
                    "sentiment_insights": sentiment_summary
                }
            if "strategic_recommendations" not in result:
                result["strategic_recommendations"] = [
                    "Review individual agent outputs for detailed insights",
                    "Consider cross-agent data alignment",
                    "Implement targeted improvements based on agent recommendations"
                ]
        except Exception:
            # fallback if not JSON - create structured content from raw response
            raw_content = response["message"]["content"]
            result = {
                "executive_summary": raw_content[:200] + "..." if len(raw_content) > 200 else raw_content,
                "key_findings": {
                    "campaign_insights": campaign_summary,
                    "purchase_insights": purchase_summary,
                    "sentiment_insights": sentiment_summary
                },
                "conflicts": ["Data integration requires manual review"],
                "strategic_recommendations": [
                    "Review individual agent outputs for detailed insights",
                    "Consider cross-agent data alignment",
                    "Implement targeted improvements based on agent recommendations"
                ]
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
