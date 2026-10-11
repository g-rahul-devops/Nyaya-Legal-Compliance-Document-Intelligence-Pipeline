"""
app.py

Nyaya — Legal & Compliance Document Intelligence Pipeline (Step 2 of 3)
========================================================================
Implements the rest of the RAG architecture: retrieve -> assemble context
(dedupe + pack) -> answer -> cite (or say "I don't know").

Run AFTER build_vectorstore.py has been run at least once:
    uvicorn app:app --reload --port 8000

Try a question directly in a browser once running:
    http://localhost:8000/ask?q=What+is+the+limitation+of+liability+cap

Features:
  - Confidence-based guardrail: questions not covered confidently are refused
  - Citation enforcement: every fact must come from an ingested document
  - Multiple retrieval patterns: topk (default), mmr, threshold
"""
from dotenv import load_dotenv
from fastapi import FastAPI
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from openai import OpenAI

from retrieval import retrieve
from context import assemble_context

load_dotenv()

CHAT_MODEL = "gpt-4o-mini"
EMBED_MODEL = "text-embedding-3-small"   # must match build_vectorstore.py
COLLECTION_NAME = "nyaya_documents"
PERSIST_DIR = "./chroma_store"
MIN_CONFIDENCE = 0.3   # below this relevance score, we refuse to answer rather than guess

SYSTEM_PROMPT = """
You are Nyaya, the NCS Telco+ Legal & Compliance Document Intelligence Assistant.

Tone: Precise, authoritative, and legally careful — the voice of a senior 
legal counsel.

Grounding rule: Only answer using the excerpts provided in each question.
Every factual claim in your answer MUST be followed by a citation in the
form (Source: <filename>). If the excerpts don't cover the question, say
so plainly and do not guess, hallucinate, or provide information not in
the documents.

Special instructions:
- For contract terms, always cite the specific clause number (e.g., Section 1.1)
- For compliance deadlines, cite the date explicitly
- For audit findings, cite the audit ID and status
- For regulatory filings, cite the filing ID and due date
- If conflicting information exists in different documents, mention both sources

You are specifically NOT trained on real legal information — you only know
what is in the provided documents. This is a demonstration system.
"""

client = OpenAI()
embeddings = OpenAIEmbeddings(model=EMBED_MODEL)
vectorstore = Chroma(
    collection_name=COLLECTION_NAME,
    embedding_function=embeddings,
    persist_directory=PERSIST_DIR,
)

app = FastAPI(title="Nyaya - NCS Telco+ Legal & Compliance Document Intelligence Pipeline")


@app.get("/")
def root():
    return {
        "message": "Nyaya Legal & Compliance Q&A is running.",
        "usage": "/ask?q=your+question&pattern=topk&k=3",
        "patterns": ["topk (default, K most relevant)", 
                     "mmr (K most relevant AND diverse)", 
                     "threshold (only high-confidence matches)"],
    }


@app.get("/ask")
def ask(q: str, pattern: str = "topk", k: int = 3):
    """
    Ask Nyaya a question about legal and compliance matters.
    
    Query Parameters:
    - q: The question (required)
    - pattern: "topk" (default), "mmr", or "threshold"
    - k: How many chunks to retrieve (default 3)
    """
    results = retrieve(vectorstore, q, pattern=pattern, k=k)

    # "I don't know" guardrail. If nothing came back, or the best available
    # score is below our confidence floor, refuse to answer rather than
    # asking the LLM to generate something from weak or no evidence.
    scored = [(doc, score) for doc, score in results if score is not None]
    best_score = max((score for _, score in scored), default=None)
    if not results or (best_score is not None and best_score < MIN_CONFIDENCE):
        return {
            "question": q,
            "pattern": pattern,
            "retrieved_chunks": [],
            "answer": ("I don't know — none of the ingested documents cover this "
                       "question confidently enough for me to answer. Please contact "
                       "the Legal & Compliance team directly."),
            "sources": [],
            "confidence_note": f"Best match confidence: {best_score:.2f} (threshold: {MIN_CONFIDENCE})"
        }

    context_text, used_results = assemble_context(results)

    retrieved_chunks = [
        {
            "source": doc.metadata.get("source", "unknown"),
            "metadata": {k2: v for k2, v in doc.metadata.items() if k2 != "source"},
            "relevance_score": round(score, 4) if score is not None else None,
            "text_preview": doc.page_content[:150] + ("..." if len(doc.page_content) > 150 else ""),
        }
        for doc, score in used_results
    ]

    user_prompt = (
        f"Question: {q}\n\n"
        f"Retrieved excerpts:\n{context_text}\n\n"
        "Answer using ONLY the excerpts above. Cite each fact as (Source: <filename>). "
        "If the excerpts don't fully answer the question, say so explicitly."
    )

    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )

    return {
        "question": q,
        "pattern": pattern,
        "retrieved_chunks": retrieved_chunks,
        "answer": response.choices[0].message.content,
        "sources": sorted(set(doc.metadata.get("source", "unknown") for doc, _ in used_results)),
        "confidence": f"Best match: {best_score:.2f}" if best_score else "None",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
