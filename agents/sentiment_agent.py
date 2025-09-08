from typing import Dict, Any
import json
import chromadb
import ollama


class SentimentAgent:
    def __init__(self, chroma_dir="./chroma_db", ollama_model="gpt-oss:20b", top_k=10):
        # Connect to ChromaDB
        self.client = chromadb.PersistentClient(path=chroma_dir)
        self.collection = self.client.get_collection("sentiments_maruti")
        self.ollama_model = ollama_model
        self.top_k = top_k

    def retrieve_sentiment_data(self, query: str) -> str:
        """
        Retrieves top_k sentiment docs from Chroma relevant to query.
        """
        emb = ollama.embeddings(model="nomic-embed-text", prompt=query).embedding
        results = self.collection.query(query_embeddings=[emb], n_results=self.top_k)
        docs = results["documents"][0] if results and "documents" in results else []
        return "\n\n".join(docs)

    def analyze_sentiment(self, query: str = "Analyze Maruti customer sentiment") -> Dict[str, Any]:
        """
        Calls Ollama to analyze sentiment data and return structured insights.
        """
        sentiment_docs = self.retrieve_sentiment_data(query)

        system_prompt = """
        You are the Sentiment Analysis Agent for Maruti vehicles.
        Analyze customer feedback (social posts, reviews, surveys) and return JSON with:
        - summary (1–2 lines),
        - key_metrics (positive %, negative %, neutral %, top regions, most mentioned models),
        - insights (themes like service issues, price concerns, feature praise),
        - recommendations (actions to improve brand perception or leverage positive buzz).

        Only return valid JSON.
        """

        prompt = f"{system_prompt}\n\nCustomer Sentiment Data:\n{sentiment_docs}\n"

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
    agent = SentimentAgent()
    output = agent.analyze_sentiment()
    print(json.dumps(output, indent=2))
