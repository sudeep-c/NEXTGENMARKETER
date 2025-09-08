#!/usr/bin/env python3
"""
Ingest CSVs and a PDF into ChromaDB using Ollama embeddings.

Example:
python ingest.py \
  --campaign ./maruti_campaigns_2000.csv \
  --purchase ./maruti_purchases_2000.csv \
  --sentiment ./maruti_sentiment_2000.csv \
  --pdf ./Trends_India_Vehicle_Market.pdf \
  --ollama-model nomic-embed-text \
  --persist-dir ./chroma_db \
  --batch-size 128
"""

import os
import argparse
import time
import json
from typing import List, Dict, Any, Optional
from pathlib import Path

import pandas as pd
from tqdm import tqdm

# Chroma
import chromadb

# PDF reading
import PyPDF2

# Embeddings: try ollama python client first, fallback to requests
try:
    import ollama
    OLLAMA_PY_AVAILABLE = True
except Exception:
    OLLAMA_PY_AVAILABLE = False

import requests
import math
import uuid
import itertools

# ----------------- Helpers -----------------

def read_csv_safe(path: Optional[str]) -> pd.DataFrame:
    if not path:
        return pd.DataFrame()
    if not os.path.exists(path):
        print(f"[warn] {path} does not exist. Skipping.")
        return pd.DataFrame()
    df = pd.read_csv(path, dtype=str).fillna("")
    return df

def read_pdf_text(pdf_path: str) -> str:
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(pdf_path)
    text_parts = []
    with open(pdf_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for p in range(len(reader.pages)):
            try:
                page = reader.pages[p]
                text = page.extract_text() or ""
                text_parts.append(text)
            except Exception:
                continue
    return "\n".join(text_parts)

def chunk_text(text: str, max_len: int = 1000, overlap: int = 200) -> List[str]:
    """
    Simple char-based chunker with overlap.
    max_len and overlap measured in characters.
    """
    if not text:
        return []
    text = text.strip()
    if len(text) <= max_len:
        return [text]
    chunks = []
    start = 0
    L = len(text)
    while start < L:
        end = start + max_len
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap
        if start < 0:
            start = 0
        if start >= L:
            break
    return chunks

# ----------------- Embedding via Ollama -----------------

class OllamaEmbedder:
    def __init__(self, model: str, host: Optional[str] = None, timeout: int = 60):
        self.model = model
        self.host = host or "http://localhost:11434"
        self.timeout = timeout

        if OLLAMA_PY_AVAILABLE:
            # If the ollama package is present, use it (it exposes embeddings or embeddings function)
            try:
                # The package may expose as `ollama.Client()` or module-level functions.
                # We'll attempt to use ollama.embeddings(...) like common examples.
                self.client = ollama
                # quick test is avoided here to keep startup light
                self.mode = "python"
                print("[info] using ollama python client for embeddings.")
            except Exception:
                self.mode = "http"
        else:
            self.mode = "http"
            print("[info] ollama python package not available — using HTTP fallback to local Ollama server.")

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a list of texts. This function tries python client first; falls back to HTTP.
        """
        if self.mode == "python":
            try:
                # Process texts one by one since Ollama Python client expects single strings
                embs = []
                for text in texts:
                    resp = self.client.embeddings(model=self.model, prompt=text)
                    # The response is an EmbeddingsResponse object with an embedding attribute
                    if hasattr(resp, 'embedding'):
                        embs.append(resp.embedding)
                    elif isinstance(resp, list):
                        embs.append(resp)
                    elif isinstance(resp, dict) and "embedding" in resp:
                        embs.append(resp["embedding"])
                    else:
                        raise RuntimeError(f"Unexpected ollama response shape for text: {text[:50]}...")
                return embs
            except Exception as e:
                print("[warn] ollama python client failed, falling back to HTTP. Error:", e)
                self.mode = "http"

        # HTTP fallback: POST to /api/embed or /embed (depending on Ollama version)
        # Ollama provides /api/embed?model=<model> or /embed endpoints; many installations accept:
        # POST http://localhost:11434/embed with json {"model": "...", "text": ["..."]}
        url = f"{self.host}/embed"  # older versions
        # try alternative url if needed:
        try_urls = [f"{self.host}/embed", f"{self.host}/api/embed", f"{self.host}/v1/embeddings"]
        last_err = None
        for url in try_urls:
            try:
                payload = {"model": self.model, "text": texts}
                r = requests.post(url, json=payload, timeout=self.timeout)
                if r.status_code == 200:
                    body = r.json()
                    # expected either {'data': [...]} or list
                    if isinstance(body, dict) and "data" in body:
                        # data may contain objects with "embedding"
                        embs = []
                        for item in body["data"]:
                            if isinstance(item, dict) and "embedding" in item:
                                embs.append(item["embedding"])
                            elif isinstance(item, (list, tuple)):
                                embs.append(list(item))
                            else:
                                # if raw numeric list
                                embs.append(item)
                        return embs
                    elif isinstance(body, list):
                        # assume list of embeddings or dicts
                        embs = []
                        for item in body:
                            if isinstance(item, dict) and "embedding" in item:
                                embs.append(item["embedding"])
                            else:
                                embs.append(item)
                        return embs
                else:
                    last_err = f"{url} => {r.status_code}: {r.text[:200]}"
            except Exception as e:
                last_err = str(e)
        raise RuntimeError(f"Ollama embed HTTP fallback failed. Last error: {last_err}")

# ----------------- Chroma ingestion -----------------

class ChromaIngestor:
    def __init__(self, persist_dir: str):
        self.client = chromadb.PersistentClient(path=persist_dir)

    def get_or_create(self, name: str):
        try:
            return self.client.get_collection(name=name)
        except Exception:
            return self.client.create_collection(name=name)

    def add_documents(self, collection_name: str, ids: List[str], embeddings: List[List[float]], 
                      documents: List[str], metadatas: List[Dict[str, Any]]):
        coll = self.get_or_create(collection_name)
        coll.add(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)
        # PersistentClient automatically persists data, no need to call persist()

# ----------------- Builders for each dataset -----------------

def build_campaign_doc(row: Dict[str, Any]) -> (str, Dict[str, Any]):
    # row is a pandas record or dict
    # Create a human-friendly document string and metadata
    doc = (
        f"Campaign {row.get('campaign_id')}: {row.get('campaign_name')}\n"
        f"Brand: {row.get('brand')}\n"
        f"Model: {row.get('target_model')}\n"
        f"Audience: {row.get('audience_segment')}\n"
        f"Channel: {row.get('channel')}\n"
        f"Dates: {row.get('start_date')} to {row.get('end_date')}\n"
        f"Subject: {row.get('message_subject')}\n"
        f"Body: {row.get('message_body')}\n"
        f"Impressions: {row.get('impressions')} Clicks: {row.get('clicks')} CTR: {row.get('ctr')} ConvRate: {row.get('conversion_rate')}"
    )
    metadata = {
        "campaign_id": row.get("campaign_id"),
        "brand": row.get("brand"),
        "target_model": row.get("target_model"),
        "audience_segment": row.get("audience_segment"),
        "channel": row.get("channel"),
        "start_date": row.get("start_date"),
        "end_date": row.get("end_date"),
        "impressions": row.get("impressions"),
        "clicks": row.get("clicks"),
        "ctr": row.get("ctr"),
        "conversion_rate": row.get("conversion_rate")
    }
    return doc, metadata

def build_purchase_doc(row: Dict[str, Any]) -> (str, Dict[str, Any]):
    doc = (
        f"Order {row.get('order_id')}: Brand {row.get('brand')} Model {row.get('model')}\n"
        f"Customer: {row.get('customer_id')} Dealer: {row.get('dealer_id')}\n"
        f"Date: {row.get('purchase_date')} Qty: {row.get('quantity')} UnitPrice: {row.get('unit_price')}\n"
        f"Payment: {row.get('payment_method')} Region: {row.get('region')} City: {row.get('city')}"
    )
    metadata = {
        "order_id": row.get("order_id"),
        "brand": row.get("brand"),
        "customer_id": row.get("customer_id"),
        "dealer_id": row.get("dealer_id"),
        "purchase_date": row.get("purchase_date"),
        "model": row.get("model"),
        "quantity": row.get("quantity"),
        "unit_price": row.get("unit_price"),
        "payment_method": row.get("payment_method"),
        "region": row.get("region"),
        "city": row.get("city")
    }
    return doc, metadata

def build_sentiment_doc(row: Dict[str, Any]) -> (str, Dict[str, Any]):
    # engagement_metrics might be stored as string or dict
    eng = row.get("engagement_metrics")
    try:
        if isinstance(eng, str):
            eng2 = json.loads(eng)
        else:
            eng2 = eng
    except Exception:
        eng2 = eng
    doc = (
        f"Feedback {row.get('feedback_id')} (source: {row.get('source')})\n"
        f"Brand: {row.get('brand')} Date: {row.get('timestamp')} Location: {row.get('geo_location')}\n"
        f"Text: {row.get('text')}\n"
        f"Engagement: {eng2}"
    )
    metadata = {
        "feedback_id": row.get("feedback_id"),
        "brand": row.get("brand"),
        "source": row.get("source"),
        "timestamp": row.get("timestamp"),
        "geo_location": row.get("geo_location"),
        "engagement_metrics": json.dumps(eng2) if isinstance(eng2, dict) else str(eng2)
    }
    return doc, metadata

# ----------------- Main ingestion flow -----------------

def batch(iterable, n=1):
    it = iter(iterable)
    while True:
        chunk = list(itertools.islice(it, n))
        if not chunk:
            break
        yield chunk

def ingest_file_to_chroma(ingestor: ChromaIngestor, embedder: OllamaEmbedder,
                          rows: List[Dict[str, Any]], collection_name: str,
                          builder_fn, batch_size: int = 128, chunk_long_texts: bool = True):
    """
    rows: list of dicts
    builder_fn: returns (doc_text, metadata)
    """
    if not rows:
        print(f"[info] no rows for {collection_name}. skipping.")
        return

    # Build docs and metadata
    docs = []
    metas = []
    ids = []
    for i, r in enumerate(rows):
        doc, meta = builder_fn(r)
        # Optionally chunk very long docs (especially PDF pages or message_body)
        if chunk_long_texts and len(doc) > 2000:
            pieces = chunk_text(doc, max_len=1000, overlap=200)
            for j, p in enumerate(pieces):
                docs.append(p)
                metas.append({**meta, "__chunk_index": j, "__orig_id": meta.get(list(meta.keys())[0])})
                ids.append(str(uuid.uuid4()))
        else:
            docs.append(doc)
            metas.append(meta)
            ids.append(str(uuid.uuid4()))

    print(f"[info] prepared {len(docs)} documents for collection '{collection_name}'.")

    # embed in batches
    for doc_batch in tqdm(list(batch(list(zip(ids, docs, metas)), batch_size)), desc=f"Embedding {collection_name}"):
        ids_b, docs_b, metas_b = zip(*doc_batch)
        texts = list(docs_b)
        # retry logic for embeddings
        attempts = 0
        while True:
            try:
                embs = embedder.embed_batch(texts)
                break
            except Exception as e:
                attempts += 1
                print(f"[warn] embed_batch failed attempt {attempts}: {e}")
                if attempts >= 3:
                    raise
                time.sleep(2 * attempts)

        ingestor.add_documents(collection_name=collection_name,
                               ids=list(ids_b),
                               embeddings=embs,
                               documents=texts,
                               metadatas=list(metas_b))
        print(f"[info] added {len(ids_b)} docs to {collection_name} (batch).")

# ----------------- CLI & runner -----------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign", default="./data/maruti_campaigns_2000.csv")
    parser.add_argument("--purchase", default="./data/maruti_purchases_2000.csv")
    parser.add_argument("--sentiment", default="./data/maruti_sentiment_2000.csv")
    parser.add_argument("--pdf", default="./data/Trends_India_Vehicle_Market.pdf")
    parser.add_argument("--ollama-model", default="nomic-embed-text")
    parser.add_argument("--ollama-host", default="http://localhost:11434")
    parser.add_argument("--persist-dir", default="./chroma_db")
    parser.add_argument("--batch-size", type=int, default=128)
    args = parser.parse_args()


    # prepare embedder and chroma
    embedder = OllamaEmbedder(model=args.ollama_model, host=args.ollama_host)
    ingestor = ChromaIngestor(persist_dir=args.persist_dir)

    # Read CSVs
    df_campaign = read_csv_safe(args.campaign)
    df_purchase = read_csv_safe(args.purchase)
    df_sentiment = read_csv_safe(args.sentiment)

    # Convert rows to dict list
    campaign_rows = df_campaign.to_dict(orient="records") if not df_campaign.empty else []
    purchase_rows = df_purchase.to_dict(orient="records") if not df_purchase.empty else []
    sentiment_rows = df_sentiment.to_dict(orient="records") if not df_sentiment.empty else []

    # Ingest campaign/purchase/sentiment
    ingest_file_to_chroma(ingestor, embedder, campaign_rows, "campaigns_maruti", build_campaign_doc, batch_size=args.batch_size)
    ingest_file_to_chroma(ingestor, embedder, purchase_rows, "purchases_maruti", build_purchase_doc, batch_size=args.batch_size)
    ingest_file_to_chroma(ingestor, embedder, sentiment_rows, "sentiments_maruti", build_sentiment_doc, batch_size=args.batch_size)

    # Ingest PDF (chunk into pages/blocks)
    if os.path.exists(args.pdf):
        print("[info] reading PDF:", args.pdf)
        txt = read_pdf_text(args.pdf)
        if txt.strip():
            chunks = chunk_text(txt, max_len=1200, overlap=250)
            pdf_rows = []
            for i, c in enumerate(chunks):
                pdf_rows.append({
                    "feedback_id": f"PDF-TRND-{i}",
                    "brand": "Maruti-Research",
                    "source": "PDF",
                    "timestamp": "",
                    "text": c,
                    "engagement_metrics": {},
                    "geo_location": ""
                })
            ingest_file_to_chroma(ingestor, embedder, pdf_rows, "trends_india_vehicle_market_pdf", build_sentiment_doc, batch_size=args.batch_size, chunk_long_texts=False)
        else:
            print("[warn] PDF had no extractable text; skipping PDF ingestion.")
    else:
        print(f"[warn] PDF file {args.pdf} not found; skipping PDF ingestion.")

    print("[done] ingestion complete. Chroma persisted at:", args.persist_dir)

if __name__ == "__main__":
    main()
