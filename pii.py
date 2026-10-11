"""
pii.py

Nyaya — PII-Safe Ingestion Basics
===================================
Before any chunk gets embedded and stored, it passes through this
redaction step. For legal & compliance documents, PII typically includes:
  - Email addresses
  - Phone numbers  
  - Personal identification numbers (PAN, Aadhar patterns)
  - Names (business names are OK, personal names redacted)

Try it yourself: the HTML FAQ document in this assignment contains a real
example — multiple legal contacts' names, emails, and phone numbers — placed
there specifically so you can watch this function redact it during ingestion.
"""
import re

PATTERNS = {
    "EMAIL": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    "PHONE_INDIA": re.compile(r"(?:\+91[-\s]?)?[6-9]\d{9}\b"),
    "PAN_LIKE_ID": re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"),
}


def redact_pii(text: str) -> tuple[str, dict]:
    """Replace any matched PII with a labelled placeholder.
    Returns the redacted text AND a count of what was redacted, so the
    build script can report what it found without ever printing the
    actual PII to a terminal or log file.
    
    This is used to demonstrate PII-safe ingestion on the Legal FAQ document
    which contains realistic (but fictional) legal contact information."""
    redaction_counts = {}
    redacted_text = text
    for label, pattern in PATTERNS.items():
        matches = pattern.findall(redacted_text)
        if matches:
            redaction_counts[label] = len(matches)
            redacted_text = pattern.sub(f"[REDACTED_{label}]", redacted_text)
    return redacted_text, redaction_counts
