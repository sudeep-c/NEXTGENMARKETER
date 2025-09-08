
# 📈 Next-Gen Marketer

*AI-Powered Multi-Agent Marketing Orchestration System*

---

## 🚀 Overview

Next-Gen Marketer is a **multi-agent AI system** that uses Retrieval-Augmented Generation (RAG) and local LLMs (via [Ollama](https://ollama.com)) to design **new marketing campaigns** based on customer data.

It combines **specialist agents**:

* 💬 **Sentiment Agent** → customer emotions & feedback
* 🛒 **Purchase Agent** → buying behavior & product trends
* 📊 **Campaign Agent** → past campaign performance (CTR, conversions, channels)
* 🎨 **Marketer Agent** → synthesizes insights into **fresh, creative campaign proposals**

All agents are orchestrated with **LangGraph**, ensuring the right agents are called depending on the user’s prompt.

---

## 🏗️ Architecture

```
Raw CSVs → Ingest (pandas → embeddings → ChromaDB) → Agents query their namespace
 → Orchestrator (LangGraph) → Marketer Agent (llama3.1) → Campaign Proposal (JSON + UI)
```

* **Data Sources**: `data/sentiment_data.csv`, `data/purchase_data.csv`, `data/campaign_data.csv`
* **Vector DB**: [Chroma](https://www.trychroma.com/)
* **LLMs**: Local models via Ollama (`llama3.2:3b` for fast analysis, `llama3.1:8b` for creative synthesis)
* **Orchestration**: [LangGraph](https://www.langchain.com/langgraph)
* **Frontend**: [Streamlit](https://streamlit.io/) UI

---

## 📂 Project Structure

```
Next-Gen-Marketer/
 ├── agents/              # Sentiment, Purchase, Campaign, Marketer agents
 ├── utils/               # RAG + LLM utilities
 ├── data/                # CSV datasets (sentiment, purchase, campaigns)
 ├── app.py               # Streamlit app (UI)
 ├── orchestrator.py      # LangGraph orchestrator
 ├── ingest.py            # CSV → embeddings ingestion
 ├── requirements.txt     # Python dependencies
 └── README.md
```

---

## ⚡ Quick Start

### 1️⃣ Install dependencies

```bash
git clone https://github.com/roshanpbabu/Next-Gen-Marketer.git
cd Next-Gen-Marketer
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2️⃣ Install Ollama & pull models

[Install Ollama](https://ollama.com/download), then:

```bash
ollama pull llama3.2:3b   # Sentiment, Purchase, Campaign agents
ollama pull llama3.1:8b   # Marketer agent
```

### 3️⃣ Ingest sample data

```bash
python ingest.py
```

### 4️⃣ Run the app

```bash
streamlit run app.py
```

Open your browser at: [http://localhost:8501](http://localhost:8501)

---

## 🎯 Example Prompts

* **Sentiment only** → `Give me top 5 campaign ideas based on customer sentiments`
* **Sentiment + Purchase** → `Recommend a strategy using sentiments + purchase behavior`
* **All agents** → `What's the best overall campaign strategy?`

---

## 📊 Example Output

* Agent analysis (per-agent recommendations, confidence, rationale, evidence)
* Orchestrated summary (combined insights)
* 🎨 **Final Campaign Proposal**:

  ```json
  {
    "campaign_name": "Back-to-Campus Shoe Blitz",
    "product": "Shoes",
    "region": "Tier 1 Cities",
    "segment": "Students & Young Professionals",
    "concept": "Discount + limited-edition collab sneakers",
    "channels": ["Email", "Push", "Instagram"],
    "content_brief": "Visual storytelling around style + comfort; influencer seeding."
  }
  ```

---

## 🔒 Security & Privacy

* All data and models run **locally** via Ollama — no cloud calls.
* Sensitive data should be **masked before embedding** (remove PII).
* `.gitignore` excludes `.venv/`, `.chroma/`, `__pycache__/`, and Streamlit caches.

---

## 🛠️ Tech Stack

* Python 3.11
* Streamlit (UI)
* LangGraph (agent orchestration)
* Ollama (local LLM inference)
* ChromaDB (vector store for embeddings)
* pandas (CSV loading + preprocessing)

---

## 🏆 Hackathon Notes

This project demonstrates:

* ✅ Modular agent design (each agent = independent file)
* ✅ Multi-agent orchestration with LangGraph
* ✅ RAG integration for grounded insights
* ✅ Local LLM deployment with Ollama (privacy-friendly)
* ✅ Modern UI with Streamlit

---

## 👨‍💻 Author

Built by **SA Team(Aakash, Manoj, Roshan, Sudeep and Vinay)**
🔗 [GitHub: roshanpbabu](https://github.com/roshanpbabu)

---

👉 Would you like me to also generate a **diagram (PNG/SVG)** of your multi-agent architecture (cleaner than ASCII), so you can embed it in the README?
