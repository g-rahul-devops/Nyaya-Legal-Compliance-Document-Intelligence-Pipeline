"""
loaders.py

Nyaya — Legal & Compliance Document Loaders
==============================================
Each function below takes a file path and returns a list of plain Python
dicts: {"text": <string>, "metadata": {"source": <filename>, ...}}.

Multi-format loaders for:
  - TXT   -> Plain text reading        — structured legal documents (MSA, circulars)
  - HTML  -> BeautifulSoup            — FAQ portals with heading-based sections
  - CSV   -> built-in csv module      — audit logs, incident reports (one row = one doc)
  - JSON  -> built-in json module     — regulatory filing trackers (one record = one doc)
"""
import csv
import json
from bs4 import BeautifulSoup


def load_txt(filepath: str) -> list[dict]:
    """One 'document' for the whole file — Plain text legal documents."""
    with open(filepath, "r", encoding="utf-8") as f:
        full_text = f.read().strip()
    
    return [{
        "text": full_text,
        "metadata": {"source": filepath.split("/")[-1]},
    }]


def load_html(filepath: str) -> list[dict]:
    """One 'document' per <h2> section — HTML FAQs naturally structured
    with heading-based Q&A pairs."""
    with open(filepath, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    docs = []
    filename = filepath.split("/")[-1]

    # Grab the intro paragraph (document id/version line) as its own chunk.
    intro = soup.find("p")
    if intro:
        docs.append({"text": intro.get_text(strip=True),
                      "metadata": {"source": filename, "section": "header"}})

    for heading in soup.find_all("h2"):
        section_title = heading.get_text(strip=True)
        paragraph = heading.find_next_sibling("p")
        section_text = paragraph.get_text(strip=True) if paragraph else ""
        docs.append({
            "text": f"{section_title}\n{section_text}",
            "metadata": {"source": filename, "section": section_title},
        })
    return docs


def load_csv(filepath: str) -> list[dict]:
    """One 'document' per row — natural for audit logs and compliance data."""
    docs = []
    filename = filepath.split("/")[-1]
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            text = ", ".join(f"{key}: {value}" for key, value in row.items())
            # Try to get audit_id first, fallback to incident_id, or use empty string
            row_id = row.get("audit_id", row.get("incident_id", ""))
            docs.append({
                "text": text,
                "metadata": {"source": filename, "row_id": row_id},
            })
    return docs


def load_json(filepath: str) -> list[dict]:
    """One 'document' per record in the top-level list this file contains."""
    filename = filepath.split("/")[-1]
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    docs = []
    
    # Try various top-level list keys based on document type
    records = data.get("filings", data.get("equipment", [])) 
    
    for record in records:
        text = ", ".join(f"{key}: {value}" for key, value in record.items())
        # Extract a meaningful identifier from the record
        identifier = record.get("filing_id", record.get("vendor", ""))
        docs.append({
            "text": text,
            "metadata": {"source": filename, "record_id": identifier},
        })
    return docs


# Dispatch table: pick the right loader based on file extension.
LOADERS = {
    ".txt": load_txt,
    ".html": load_html,
    ".csv": load_csv,
    ".json": load_json,
}


def load_document(filepath: str) -> list[dict]:
    """Single entry point — figures out which loader to use from the extension."""
    ext = "." + filepath.rsplit(".", 1)[-1].lower()
    if ext not in LOADERS:
        raise ValueError(f"No loader registered for file type: {ext}")
    return LOADERS[ext](filepath)
