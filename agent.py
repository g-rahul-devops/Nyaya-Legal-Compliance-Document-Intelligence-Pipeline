"""
agent.py

Nyaya — Ask the Pipeline (Step 3 of 3)
=========================================
5 hardcoded questions covering all 5 documents and formats, so a single run
proves Nyaya is grounded across ALL FIVE formats (TXT, HTML, CSV, JSON) — 
not just whichever one happened to be easiest to parse.

IMPORTANT: app.py must already be running in a separate terminal
(uvicorn app:app --reload --port 8000) before you run this file.

Run:
    python agent.py

The 5 questions map to the 5 documents:
Q1 -> MSA: limitation of liability cap
Q2 -> Regulatory Circular: compliance deadline
Q3 -> Legal FAQ (HTML): urgent contract review contact (PII redaction test)
Q4 -> Audit Log (CSV): open audit findings
Q5 -> Filing Tracker (JSON): overdue or upcoming filings
"""
import requests
import json

BASE_URL = "http://localhost:8000/ask"

# One question per document, in the same order as documents/.
QUESTIONS = [
    # Q1 - MSA (TXT) - Section 1.1 liability cap is "twelve (12) months of fees"
    "What is the limitation of liability cap in our standard MSA?",
    
    # Q2 - Regulatory Circular (TXT) - Q3 deadline is October 15, 2024
    "What is the deadline for submitting the quarterly compliance report for Q3?",
    
    # Q3 - Legal FAQ (HTML) - should redact Priya Sharma's contact info
    "Who do I contact to request an urgent contract review?",
    
    # Q4 - Audit Log (CSV) - should find Open audits: AUD-2024-001, 002, 003, 007, 009, 012, 014, 015
    "Which compliance audit findings are still open?",
    
    # Q5 - Filing Tracker (JSON) - should find overdue or within 30 days
    "Which regulatory filings are overdue or due within the next 30 days?",
]

# Bonus question designed to trigger the 'I don't know' guardrail
BONUS_QUESTIONS = [
    "What is the company's policy on international arbitration seat selection?",
    "Who is the VP of Marketing for NCS Telco+?",
]


def ask_nyaya(question: str, pattern: str = "topk", k: int = 3) -> dict:
    """Call the Nyaya backend with a question."""
    response = requests.get(BASE_URL, params={"q": question, "pattern": pattern, "k": k}, timeout=60)
    response.raise_for_status()
    return response.json()


def main():
    print("\n" + "=" * 80)
    print("Nyaya — NCS Telco+ Legal & Compliance Document Intelligence Pipeline")
    print("=" * 80)
    
    print("\n[SECTION 1] Testing 5 core questions (one per document)")
    print("-" * 80)

    for i, question in enumerate(QUESTIONS, start=1):
        print(f"\n{'='*80}")
        print(f"Q{i}: {question}")
        print(f"{'='*80}")
        
        try:
            result = ask_nyaya(question)
        except requests.exceptions.ConnectionError:
            print("ERROR: Could not reach Nyaya. Is app.py running in another terminal?")
            print("       Terminal 1: uvicorn app:app --reload --port 8000")
            return

        # Display retrieved chunks
        if result["retrieved_chunks"]:
            print(f"\nRetrieved {len(result['retrieved_chunks'])} chunk(s):")
            for j, chunk in enumerate(result["retrieved_chunks"], 1):
                print(f"\n  [{j}] Source: {chunk['source']}")
                print(f"      Score: {chunk['relevance_score']}")
                if chunk["metadata"]:
                    print(f"      Metadata: {chunk['metadata']}")
                print(f"      Preview: {chunk['text_preview']}")
        else:
            print("\n(No chunks above confidence threshold)")

        # Display answer
        print(f"\nA{i}: {result['answer']}")
        if result["sources"]:
            print(f"     Sources: {', '.join(result['sources'])}")
        print(f"     Confidence: {result.get('confidence', 'N/A')}")

    # Chunk comparison: same question with different retrieval patterns
    print(f"\n\n{'='*80}")
    print("[SECTION 2] Comparing retrieval patterns on ONE question")
    print(f"{'='*80}")
    
    test_question = QUESTIONS[0]  # Use the MSA question
    print(f"\nQuestion: {test_question}\n")
    
    for pattern in ["topk", "threshold", "mmr"]:
        print(f"--- Retrieval Pattern: {pattern} ---")
        result = ask_nyaya(test_question, pattern=pattern, k=5)
        print(f"Chunks retrieved: {len(result['retrieved_chunks'])}")
        for chunk in result["retrieved_chunks"]:
            print(f"  - {chunk['source']} (score={chunk['relevance_score']})")
        if result["retrieved_chunks"]:
            print(f"Answer preview: {result['answer'][:120]}...")
        else:
            print(f"Pattern filtered out all results (confidence threshold too high)")
        print()

    # Bonus: 'I don't know' guardrail test
    print(f"\n{'='*80}")
    print("[SECTION 3] Testing 'I don't know' guardrail (out-of-scope questions)")
    print(f"{'='*80}")
    
    for bonus_q in BONUS_QUESTIONS:
        print(f"\nBonus Q: {bonus_q}")
        result = ask_nyaya(bonus_q)
        if result["retrieved_chunks"]:
            print(f"  ⚠ Chunks retrieved (guardrail failed): {len(result['retrieved_chunks'])}")
            for chunk in result["retrieved_chunks"]:
                print(f"    - {chunk['source']} (score={chunk['relevance_score']})")
        else:
            print(f"  ✓ Guardrail working: no chunks above confidence threshold")
            print(f"  Answer: {result['answer'][:150]}...")

    print(f"\n\n{'='*80}")
    print("✓ End-to-end test complete!")
    print(f"{'='*80}")
    print("\nNext steps:")
    print("  1. Review which chunking strategy gave better results")
    print("  2. Review which retrieval pattern worked best for your questions")
    print("  3. Check that PII was redacted in the Legal FAQ document")
    print("  4. Update README with findings")
    print()


if __name__ == "__main__":
    main()
