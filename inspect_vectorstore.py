"""
inspect_vectorstore.py

Nyaya — Debug Utility: Peek into the Vector Store
==================================================
Before running app.py + agent.py, it's helpful to verify that:
  1. Documents were loaded correctly
  2. PII was redacted as expected
  3. Chunks have the right metadata
  4. Collection exists in ChromaDB

Run this AFTER build_vectorstore.py to debug what got stored.

Usage:
    python inspect_vectorstore.py
"""
import os
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv

load_dotenv()

EMBED_MODEL = "text-embedding-3-small"
COLLECTION_NAME = "nyaya_documents"
PERSIST_DIR = "./chroma_store"


def inspect():
    print("\n" + "=" * 70)
    print("Inspecting Nyaya Vector Store")
    print("=" * 70)

    # Check if store exists
    if not os.path.exists(PERSIST_DIR):
        print(f"\n✗ Store not found at {PERSIST_DIR}")
        print(f"  Run 'python build_vectorstore.py' first.")
        return

    print(f"\n✓ Found vector store at {PERSIST_DIR}")

    try:
        embeddings = OpenAIEmbeddings(model=EMBED_MODEL)
        vectorstore = Chroma(
            collection_name=COLLECTION_NAME,
            embedding_function=embeddings,
            persist_directory=PERSIST_DIR,
        )
    except Exception as e:
        print(f"✗ Error loading vector store: {e}")
        return

    # Get collection info
    try:
        collection_info = vectorstore.get()
        print(f"\nCollection: {COLLECTION_NAME}")
        print(f"Total documents stored: {len(collection_info['ids'])}")
    except Exception as e:
        print(f"✗ Error querying collection: {e}")
        return

    # Summarize by source
    print("\n--- Documents by Source ---")
    sources = {}
    for metadata_dict in collection_info.get("metadatas", []):
        source = metadata_dict.get("source", "unknown")
        sources[source] = sources.get(source, 0) + 1

    for source in sorted(sources.keys()):
        print(f"  {source}: {sources[source]} chunk(s)")

    # Show sample chunks
    print("\n--- Sample Chunks (first 3) ---")
    ids = collection_info["ids"][:3]
    documents = collection_info["documents"][:3]
    metadatas = collection_info.get("metadatas", [{}]*3)[:3]
    
    for i, (doc_id, doc_text, metadata) in enumerate(zip(ids, documents, metadatas), 1):
        print(f"\n[Chunk {i}]")
        print(f"  ID: {doc_id}")
        print(f"  Source: {metadata.get('source', 'unknown')}")
        print(f"  Metadata: {metadata}")
        print(f"  Text (first 200 chars): {doc_text[:200]}...")

    # Test a simple query
    print("\n--- Testing a Simple Query ---")
    test_query = "What is the liability cap?"
    results = vectorstore.similarity_search_with_relevance_scores(test_query, k=2)
    
    print(f"Query: '{test_query}'")
    print(f"Results: {len(results)} matches")
    for i, (doc, score) in enumerate(results, 1):
        print(f"\n  [{i}] Score: {score:.4f}")
        print(f"      Source: {doc.metadata.get('source', 'unknown')}")
        print(f"      Text: {doc.page_content[:150]}...")

    print(f"\n{'='*70}")
    print("✓ Inspection complete!")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    inspect()
