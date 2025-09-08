from typing import Dict, Any
import json
import chromadb
import ollama

class CampaignAgent:
    def __init__(self, chroma_dir="./chroma_db", ollama_model="gpt-oss:20b", top_k=10):
        # Connect to ChromaDB
        self.client = chromadb.PersistentClient(path=chroma_dir)
        self.collection = self.client.get_collection("campaigns_maruti")
        self.ollama_model = ollama_model
        self.top_k = top_k

    def retrieve_campaign_data(self, query: str) -> str:
        """
        Retrieves top_k campaign docs from Chroma relevant to query.
        """
        # Get embedding for query
        emb = ollama.embeddings(model="nomic-embed-text", prompt=query).embedding
        results = self.collection.query(query_embeddings=[emb], n_results=self.top_k)
        docs = results["documents"][0] if results and "documents" in results else []
        return "\n\n".join(docs)

    def analyze_campaigns(self, query: str = "Analyze Maruti campaign performance") -> Dict[str, Any]:
        """
        Calls Ollama to analyze campaign performance and return structured insights.
        """
        campaign_docs = self.retrieve_campaign_data(query)

        system_prompt = f"""
        You are the Campaign Analysis Agent for Maruti campaigns.
        Analyze the campaign data and return JSON with:
        - summary (1–2 lines),
        - key_metrics (avg CTR, conversion_rate, best/worst channel),
        - insights (specific issues or opportunities),
        - recommendations (actionable next steps).
        
        Only return valid JSON.
        """

        prompt = f"{system_prompt}\n\nCampaign Data:\n{campaign_docs}\n"

        response = ollama.chat(model=self.ollama_model, messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ])

        # Parse JSON safely
        try:
            result = json.loads(response["message"]["content"])
        except Exception:
            # fallback: wrap content into JSON
            result = {"summary": response["message"]["content"], "insights": [], "recommendations": []}

        return result


if __name__ == "__main__":
    agent = CampaignAgent()
    output = agent.analyze_campaigns()
    print(json.dumps(output, indent=2))
