import chromadb
import json
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rag.embedder import embed_texts

CHROMA_PATH = "data/chroma_db"
COLLECTION_NAME = "sml_posts"

def get_collection():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

def build_vector_store(analyzed_posts_path: str = "data/analyzed_posts.json"):
    with open(analyzed_posts_path, "r", encoding="utf-8") as f:
        posts = json.load(f)

    collection = get_collection()

    # Clear existing
    existing = collection.count()
    if existing > 0:
        collection.delete(where={"source": "reddit"})

    documents, metadatas, ids = [], [], []

    for post in posts:
        for i, chunk in enumerate(post.get("chunks", [post["raw_text"]])):
            chunk_id = f"{post['id']}_chunk_{i}"
            documents.append(chunk)
            metadatas.append({
                "source": "reddit",
                "post_id": post["id"],
                "subreddit": post.get("subreddit", ""),
                "stakeholder": post.get("stakeholder", "Patients"),
                "sentiment": post.get("sentiment", "Neutral"),
                "emotion": post.get("emotion", "Neutral"),
                "themes": ", ".join(post.get("themes", [])),
                "drugs": ", ".join(post.get("drugs_mentioned", [])),
                "url": post.get("url", ""),
                "created_utc": post.get("created_utc", ""),
            })
            ids.append(chunk_id)

    # Batch upsert
    batch_size = 100
    for i in range(0, len(documents), batch_size):
        batch_docs = documents[i:i+batch_size]
        batch_embeddings = embed_texts(batch_docs).tolist()
        collection.upsert(
            ids=ids[i:i+batch_size],
            documents=batch_docs,
            embeddings=batch_embeddings,
            metadatas=metadatas[i:i+batch_size],
        )
        print(f"  Upserted {min(i+batch_size, len(documents))}/{len(documents)} chunks")

    print(f"Vector store built: {collection.count()} chunks total")

if __name__ == "__main__":
    build_vector_store()
