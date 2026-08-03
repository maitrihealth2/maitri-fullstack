"""
Multi-Format RAG Retriever
Given a user message, retrieves the most relevant therapy knowledge chunks
from ChromaDB and returns them as context for the LLM.
"""

import os

CHROMA_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")
COLLECTION_NAME = "therapy_knowledge"

_client = None
_collection = None


def get_collection():
    """Lazy-load ChromaDB collection (singleton)."""
    global _client, _collection
    if _collection is None:
        try:
            import chromadb
            from chromadb.config import Settings
            from chromadb.utils import embedding_functions

            _client = chromadb.PersistentClient(
                path=CHROMA_DIR,
                settings=Settings(anonymized_telemetry=False)
            )
            embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="all-MiniLM-L6-v2"
            )
            _collection = _client.get_collection(
                name=COLLECTION_NAME,
                embedding_function=embedding_fn,
            )
        except Exception as e:
            print(f"[RAG] ChromaDB collection initialization failed: {e}")
            return None
    return _collection


def retrieve_context(query: str, n_results: int = 3) -> str:
    """
    Retrieve the top-n most relevant therapy knowledge chunks for a query.
    Returns a formatted string ready to inject into the LLM prompt.
    """
    try:
        if not is_knowledge_base_ready():
            print("[RAG] retrieve_context called but knowledge base is not ready.")
            return ""

        collection = get_collection()
        if collection is None:
            return ""

        results = collection.query(
            query_texts=[query],
            n_results=n_results,
        )
        documents = results.get("documents")
        metadatas = results.get("metadatas")
        if not documents or not documents[0]:
            return ""

        chunks = documents[0]
        metadata_items = metadatas[0] if metadatas and metadatas[0] else []
        sources = [m.get("source", "unknown") for m in metadata_items]
        concepts = [m.get("concept", "clinical_knowledge") for m in metadata_items]

        if not chunks:
            return ""

        context_parts = []
        for chunk, source, concept in zip(chunks, sources, concepts):
            context_parts.append(f"[SOURCE: {source.upper()} | TOPIC: {concept.upper()}]\n{chunk}")

        return "\n\n".join(context_parts)

    except Exception as e:
        print(f"Multi-format RAG retrieval error: {e}")
        return ""


def is_knowledge_base_ready() -> bool:
    """Check if ChromaDB has been populated by inspecting the database file."""
    try:
        sqlite_file = os.path.join(CHROMA_DIR, "chroma.sqlite3")
        return os.path.exists(sqlite_file) and os.path.getsize(sqlite_file) > 1024
    except Exception:
        return False


def ensure_knowledge_base_ready(build_if_missing: bool = False) -> bool:
    """Verify whether the RAG knowledge base is ready, optionally building it if missing."""
    ready = is_knowledge_base_ready()
    if ready:
        return True

    if build_if_missing:
        print("[RAG] Knowledge base missing. Starting auto-build...")
        try:
            from .builder import build_knowledge_base
            build_knowledge_base()
            if is_knowledge_base_ready():
                print("[RAG] Knowledge base auto-build completed successfully.")
                return True
            print("[RAG] Knowledge base auto-build completed, but the database is still missing.")
        except Exception as e:
            print(f"[RAG] Auto-build failed: {e}")
    return False
