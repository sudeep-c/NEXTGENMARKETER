from typing import Dict, Any
import json
import chromadb
import ollama

class PurchaseAgent:
    def __init__(self, chroma_dir="./chroma_db", ollama_model="gpt-oss:20b", top_k=10):
        # Connect to ChromaDB
        self.client = chromadb.PersistentClient(path=chroma_dir)
        self.collection = self.client.get_collection("purchases_maruti")
        self.ollama_model = ollama_model
        self.top_k = top_k

    def retrieve_purchase_data(self, query: str) -> str:
        """
        Retrieves top_k purchase docs from Chroma relevant to query.
        """
        emb = ollama.embeddings(model="nomic-embed-text", prompt=query).embedding
        results = self.collection.query(query_embeddings=[emb], n_results=self.top_k)
        docs = results["documents"][0] if results and "documents" in results else []
        return "\n\n".join(docs)

    def analyze_purchases(self, query: str = "Analyze Maruti purchase data") -> Dict[str, Any]:
        """
        Calls Ollama to analyze purchase data and return structured insights.
        """
        purchase_docs = self.retrieve_purchase_data(query)

        system_prompt = """
        You are the Purchase Analysis Agent for Maruti vehicles.
        Analyze purchase records and return JSON with:
        - summary (1–2 lines),
        - key_metrics (top models, avg transaction value, popular payment methods, regions with highest sales),
        - insights (demand shifts, underperforming models, seasonal effects, dealer patterns),
        - recommendations (actionable sales/marketing steps).
        
        Only return valid JSON.
        """

        prompt = f"{system_prompt}\n\nPurchase Data:\n{purchase_docs}\n"

        response = ollama.chat(model=self.ollama_model, messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ])

        try:
            result = json.loads(response["message"]["content"])
        except Exception:
            result = {
                "summary": response["message"]["content"],
                "key_metrics": {},
                "insights": [],
                "recommendations": []
            }

        return result


if __name__ == "__main__":
    agent = PurchaseAgent()
    output = agent.analyze_purchases()
    print(json.dumps(output, indent=2))
