"""
build_vectorstore.py

Nyaya — Legal & Compliance Document Intelligence Pipeline (Step 1 of 3)
==========================================================================
The "ingest -> chunk -> embed -> index" half of the RAG architecture.

Loads all 5 source documents (TXT/MSA, TXT/Circular, HTML/FAQ, CSV/Audit, JSON/Filings) 
from documents/, redacts obvious PII, chunks each document using a configurable 
strategy, embeds every chunk with OpenAI's embedding model, and stores everything 
in a persistent ChromaDB vector store via LangChain.

Run:
    python build_vectorstore.py                     # default strategy: heading_aware
    python build_vectorstore.py --strategy fixed
    python build_vectorstore.py --strategy semantic
    python build_vectorstore.py --strategy sentence

Re-run any time you edit a document, or to compare how a different chunking 
strategy changes retrieval quality — this always rebuilds the whole store 
from scratch.
"""
import argparse
import glob
import os
import shutil

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

from loaders import load_document
from chunking import chunk_text, STRATEGIES
from pii import redact_pii

load_dotenv()

EMBED_MODEL = "text-embedding-3-small"
COLLECTION_NAME = "nyaya_documents"
PERSIST_DIR = "./chroma_store"


def build(strategy: str):
    print("=" * 70)
    print(f"Nyaya — Building the Knowledge Base (chunking strategy: {strategy})")
    print("=" * 70)

    filepaths = sorted(glob.glob("documents/*"))
    if not filepaths:
        print("No documents found in documents/ — nothing to build.")
        return

    print(f"\nFound {len(filepaths)} source document(s):")
    for f in filepaths:
        print(f"  - {os.path.basename(f)}")

    all_documents = []
    total_pii_redactions = {}

    for filepath in filepaths:
        filename = os.path.basename(filepath)
        print(f"\n[Processing] {filename} ...")

        raw_units = load_document(filepath)
        print(f"  Loaded as {len(raw_units)} source unit(s) (section / row / record)")

        file_chunk_count = 0
        file_pii_counts = {}
        
        for unit in raw_units:
            redacted_text, pii_counts = redact_pii(unit["text"])
            for label, count in pii_counts.items():
                total_pii_redactions[label] = total_pii_redactions.get(label, 0) + count
                file_pii_counts[label] = file_pii_counts.get(label, 0) + count

            chunks = chunk_text(redacted_text, strategy=strategy)
            for i, chunk in enumerate(chunks):
                metadata = dict(unit["metadata"])
                metadata["chunk_index"] = i
                metadata["chunking_strategy"] = strategy
                all_documents.append(Document(page_content=chunk, metadata=metadata))
                file_chunk_count += 1

        print(f"  -> {file_chunk_count} chunk(s) created")
        if file_pii_counts:
            print(f"     PII redacted in this file: {file_pii_counts}")

    print(f"\n{'='*70}")
    print(f"SUMMARY")
    print(f"{'='*70}")
    print(f"Total chunks to embed: {len(all_documents)}")
    if total_pii_redactions:
        print(f"PII redacted during ingestion:")
        for label, count in total_pii_redactions.items():
            print(f"  - {label}: {count} instance(s)")
    else:
        print("No PII patterns matched during ingestion.")

    print(f"\nEmbedding and storing in ChromaDB (this calls the OpenAI API)...")
    print(f"Embedding model: {EMBED_MODEL}")
    print(f"Collection name: {COLLECTION_NAME}")
    print(f"Storage directory: {PERSIST_DIR}")
    
    embeddings = OpenAIEmbeddings(model=EMBED_MODEL)

    # Fresh start every run, so re-running after an edit doesn't duplicate data.
    if os.path.exists(PERSIST_DIR):
        shutil.rmtree(PERSIST_DIR)
        print(f"Cleared existing store.")

    Chroma.from_documents(
        documents=all_documents,
        embedding=embeddings,
        collection_name=COLLECTION_NAME,
        persist_directory=PERSIST_DIR,
    )
    
    print(f"\n✓ Build complete! Vector store ready at: {PERSIST_DIR}/")
    print(f"  Run 'python app.py' in one terminal, then 'python agent.py' in another.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build the Nyaya vector store with a chunking strategy.")
    parser.add_argument("--strategy", default="heading_aware", choices=STRATEGIES.keys(),
                        help=f"Chunking strategy. Options: {list(STRATEGIES.keys())}")
    args = parser.parse_args()
    build(args.strategy)
