from typing import List, Dict, Any
from pathlib import Path
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import pandas as pd
import uuid

PERSIST_DIR = str(Path(".chroma").absolute())
_EMBEDDER = None  # Lazy-initialized

def _get_embedder() -> SentenceTransformer:
    global _EMBEDDER
    if _EMBEDDER is None:
        _EMBEDDER = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    return _EMBEDDER

def _embed(texts: List[str]) -> List[List[float]]:
    embedder = _get_embedder()
    return embedder.encode(texts, normalize_embeddings=True).tolist()

def get_client():
    return chromadb.PersistentClient(path=PERSIST_DIR, settings=Settings(allow_reset=False))

def get_collection(namespace: str):
    client = get_client()
    return client.get_or_create_collection(name=namespace, metadata={"hnsw:space": "cosine"})

def upsert_dataframe_as_docs(df: pd.DataFrame, namespace: str, text_cols: List[str], meta_cols: List[str] = None, id_prefix: str = ""):
    meta_cols = meta_cols or []
    coll = get_collection(namespace)
    docs, ids, metas = [], [], []
    for i, row in df.iterrows():
        text = " | ".join(str(row[c]) for c in text_cols if pd.notna(row[c]))
        doc_id = f"{id_prefix}{i}-{uuid.uuid4().hex[:8]}"
        meta = {k: (None if pd.isna(row[k]) else row[k]) for k in meta_cols}
        ids.append(doc_id)
        docs.append(text)
        metas.append(meta)

    coll.add(documents=docs, metadatas=metas, ids=ids, embeddings=_embed(docs))

def query_namespace(namespace: str, query: str, k: int = 5) -> List[Dict[str, Any]]:
    coll = get_collection(namespace)
    res = coll.query(
        query_embeddings=_embed([query]),
        n_results=k
    )
    out = []
    for i in range(len(res["ids"][0])):
        out.append({
            "id": res["ids"][0][i],
            "text": res["documents"][0][i],
            "metadata": res["metadatas"][0][i],
            "distance": res["distances"][0][i] if "distances" in res else None
        })
    return out
