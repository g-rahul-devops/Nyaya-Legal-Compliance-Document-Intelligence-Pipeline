"""
chunking.py

Nyaya — Legal & Compliance Chunking Strategies
===============================================
Every strategy below takes one document's text and returns a list of
smaller text chunks. All are called the same way from build_vectorstore.py:

    chunks = chunk_text(text, strategy="fixed")

Legal documents benefit from different strategies:
  - fixed          -> Equal-size pieces (simple, loses context at boundaries)
  - heading_aware  -> Split at clause/section headings (preserves legal structure)
  - semantic       -> Split at paragraph boundaries (good for narratives)
"""
import re


def fixed_chunk(text: str, chunk_size: int = 500) -> list[str]:
    """Split into equal-size pieces, no overlap. Simplest possible strategy —
    and the one most likely to cut a clause in half."""
    chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]
    return [c.strip() for c in chunks if c.strip()]


def overlap_chunk(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Same as fixed, but each chunk shares `overlap` characters with the
    next one, so an idea that falls on a boundary isn't lost entirely."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return [c.strip() for c in chunks if c.strip()]


def sentence_chunk(text: str, max_sentences: int = 4) -> list[str]:
    """Split into sentences first, then group every `max_sentences`
    together — never cuts a sentence in half."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    sentences = [s for s in sentences if s]
    chunks = []
    for i in range(0, len(sentences), max_sentences):
        chunk = " ".join(sentences[i:i + max_sentences])
        if chunk.strip():
            chunks.append(chunk.strip())
    return chunks


def heading_aware_chunk(text: str) -> list[str]:
    """Split at lines that look like legal headings — numbered sections
    ('1. Limitation of Liability', '2.1 Indemnification') OR labelled clauses
    ('Section 3: Governing Law') — so each chunk stays a complete legal clause
    rather than an arbitrary slice."""
    heading_pattern = re.compile(
        r"^\s*(\d+(?:\.\d+)?\s+[A-Z].{0,100}|(?:Clause|Section|Article)\s+\d+.*?:?.{0,80}|={5,}.{0,100}={5,})\s*$",
        re.MULTILINE,
    )
    matches = list(heading_pattern.finditer(text))

    if not matches:
        # No numbered headings found — fall back to semantic chunking.
        return semantic_chunk(text)

    chunks = []
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        section = text[start:end].strip()
        if section:
            chunks.append(section)
    return chunks


def semantic_chunk(text: str) -> list[str]:
    """Semantic chunking by splitting at paragraph (blank-line)
    boundaries. Works well for narratives and compliance descriptions."""
    paragraphs = re.split(r"\n\s*\n", text.strip())
    return [p.strip() for p in paragraphs if p.strip()]


STRATEGIES = {
    "fixed": fixed_chunk,
    "overlap": overlap_chunk,
    "sentence": sentence_chunk,
    "heading_aware": heading_aware_chunk,
    "semantic": semantic_chunk,
}


def chunk_text(text: str, strategy: str = "heading_aware", **kwargs) -> list[str]:
    """Single entry point — dispatches to whichever strategy you name.
    Default now is heading_aware since we're working with legal documents."""
    if strategy not in STRATEGIES:
        raise ValueError(f"Unknown chunking strategy: {strategy}. "
                          f"Choose from: {list(STRATEGIES.keys())}")
    return STRATEGIES[strategy](text, **kwargs)
