"""
Vector Store module using ChromaDB with persistent disk storage
and sentence-transformers (all-MiniLM-L6-v2) for local semantic retrieval.
"""

import re
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from app.backend.config import CHROMA_PERSIST_DIR, EMBEDDING_MODEL

# Initialize persistent Chroma client
_chroma_client = None
_embedding_fn = None


def get_embedding_function():
    """Initializes and caches local embedding function."""
    global _embedding_fn
    if _embedding_fn is None:
        try:
            _embedding_fn = embedding_functions.DefaultEmbeddingFunction()
        except Exception as e:
            print(f"[VectorStore] DefaultEmbeddingFunction init fallback: {e}")
            _embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=EMBEDDING_MODEL
            )
    return _embedding_fn


def get_chroma_client() -> chromadb.PersistentClient:
    """Returns persistent ChromaDB client instance."""
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(
            path=str(CHROMA_PERSIST_DIR),
            settings=Settings(anonymized_telemetry=False, allow_reset=True)
        )
    return _chroma_client


def _sanitize_collection_name(doc_id: str) -> str:
    """Chroma collection names must be 3-63 chars and contain alphanumeric or underscores."""
    clean = re.sub(r'[^a-zA-Z0-9_-]', '_', doc_id)
    name = f"doc_{clean}"[:60]
    if len(name) < 3:
        name = f"doc_{name}_coll"
    return name


def index_chunks(doc_id: str, chunks: List[Dict[str, Any]]) -> int:
    """
    Stores and indexes a list of document chunks into a scoped ChromaDB collection.
    """
    client = get_chroma_client()
    embedding_fn = get_embedding_function()
    collection_name = _sanitize_collection_name(doc_id)

    # Delete existing collection if re-indexing
    try:
        client.delete_collection(name=collection_name)
    except Exception:
        pass

    collection = client.create_collection(
        name=collection_name,
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"}
    )

    if not chunks:
        return 0

    ids = [c["chunk_id"] for c in chunks]
    documents = [c["text"] for c in chunks]
    metadatas = [
        {
            "doc_id": c.get("doc_id", doc_id),
            "page_number": int(c.get("page_number", 1)),
            "section_title": str(c.get("section_title", "")),
            "word_count": int(c.get("word_count", 0)),
            "chunk_id": str(c.get("chunk_id", ""))
        }
        for c in chunks
    ]

    collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas
    )

    return len(chunks)


def query_relevant_chunks(
    doc_id: str,
    query_text: str,
    top_k: int = 4
) -> List[Dict[str, Any]]:
    """
    Retrieves the top-k most relevant chunks for a question from the document's collection.
    """
    client = get_chroma_client()
    embedding_fn = get_embedding_function()
    collection_name = _sanitize_collection_name(doc_id)

    try:
        collection = client.get_collection(
            name=collection_name,
            embedding_function=embedding_fn
        )
    except Exception as e:
        print(f"[VectorStore] Collection {collection_name} not found: {e}")
        return []

    results = collection.query(
        query_texts=[query_text],
        n_results=min(top_k, max(1, collection.count()))
    )

    retrieved = []
    if results and "documents" in results and results["documents"]:
        docs = results["documents"][0]
        metas = results["metadatas"][0] if "metadatas" in results else [{}] * len(docs)
        distances = results["distances"][0] if "distances" in results and results["distances"] else [0.0] * len(docs)
        ids = results["ids"][0] if "ids" in results and results["ids"] else [""] * len(docs)

        for i, text in enumerate(docs):
            meta = metas[i] if i < len(metas) else {}
            dist = distances[i] if i < len(distances) else 0.0
            chunk_id = ids[i] if i < len(ids) else f"{doc_id}_chunk_{i}"
            retrieved.append({
                "chunk_id": chunk_id,
                "text": text,
                "page_number": meta.get("page_number", 1),
                "section_title": meta.get("section_title", "General"),
                "similarity_score": round(1.0 - float(dist), 4),
                "doc_id": doc_id
            })

    return retrieved
