import json
import os
import sys
from rank_bm25 import BM25Okapi
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rag.embedder import embed_query
from rag.vector_store import get_collection
from openai import OpenAI
from dotenv import load_dotenv
from config import OPENROUTER_MODEL, OPENROUTER_BASE_URL

load_dotenv()

def _get_api_key():
    try:
        import streamlit as st
        return st.secrets["OPENROUTER_API_KEY"]
    except Exception:
        return os.getenv("OPENROUTER_API_KEY")

def _get_client():
    return OpenAI(
        api_key=_get_api_key(),
        base_url=OPENROUTER_BASE_URL,
    )

RAG_SYSTEM_PROMPT = """You are an expert pharmaceutical analyst specializing in asthma biologics, particularly Mepolizumab (Nucala).
You answer questions based on real patient and healthcare professional discussions from Reddit.
Always ground your answers in the provided context. Be specific, cite themes and stakeholder perspectives.
If the context doesn't contain enough information, say so clearly."""

def semantic_search(query: str, n_results: int = 10, filters: dict = None) -> list:
    collection = get_collection()
    query_embedding = embed_query(query).tolist()
    where = filters if filters else None
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where=where,
        include=["documents", "metadatas", "distances"],
    )
    docs = results["documents"][0]
    metas = results["metadatas"][0]
    scores = results["distances"][0]
    return [{"text": d, "metadata": m, "score": 1 - s} for d, m, s in zip(docs, metas, scores)]

def bm25_search(query: str, all_docs: list, n_results: int = 10) -> list:
    tokenized = [doc["text"].lower().split() for doc in all_docs]
    bm25 = BM25Okapi(tokenized)
    scores = bm25.get_scores(query.lower().split())
    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:n_results]
    return [{"text": all_docs[i]["text"], "metadata": all_docs[i]["metadata"], "score": float(scores[i])} for i in top_indices]

def hybrid_retrieve(query: str, n_results: int = 8, filters: dict = None) -> list:
    # Semantic retrieval
    semantic_results = semantic_search(query, n_results=n_results * 2, filters=filters)

    # BM25 on semantic candidates
    if len(semantic_results) > 0:
        bm25_results = bm25_search(query, semantic_results, n_results=n_results)
    else:
        bm25_results = []

    # Merge and deduplicate by text, prefer higher combined score
    seen = set()
    merged = []
    for r in bm25_results + semantic_results:
        key = r["text"][:100]
        if key not in seen:
            seen.add(key)
            merged.append(r)

    return merged[:n_results]

def rag_query(query: str, filters: dict = None) -> str:
    results = hybrid_retrieve(query, n_results=8, filters=filters)

    if not results:
        return "No relevant posts found in the database. Please run the scraper and analysis pipeline first."

    context_parts = []
    for i, r in enumerate(results):
        meta = r["metadata"]
        context_parts.append(
            f"[{i+1}] Subreddit: r/{meta.get('subreddit','')} | "
            f"Stakeholder: {meta.get('stakeholder','')} | "
            f"Sentiment: {meta.get('sentiment','')} | "
            f"Themes: {meta.get('themes','')}\n"
            f"{r['text']}"
        )

    context = "\n\n---\n\n".join(context_parts)

    messages = [
        {"role": "system", "content": RAG_SYSTEM_PROMPT},
        {"role": "user", "content": f"Context from Reddit discussions:\n\n{context}\n\nQuestion: {query}"}
    ]

    response = _get_client().chat.completions.create(
        model=OPENROUTER_MODEL,
        messages=messages,
        temperature=0.3,
    )
    return response.choices[0].message.content
