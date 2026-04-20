import re
import json
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DRUG_NAMES, STAKEHOLDER_KEYWORDS

# PII patterns
PII_PATTERNS = [
    (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]'),
    (r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b', '[PHONE]'),
    (r'\b\d{1,5}\s\w+\s(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd)\b', '[ADDRESS]'),
    (r'\b(?:SSN|Social Security)[:\s]*\d{3}-\d{2}-\d{4}\b', '[SSN]'),
]

def remove_pii(text: str) -> str:
    for pattern, replacement in PII_PATTERNS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text

def normalize_text(text: str) -> str:
    text = re.sub(r'http\S+|www\S+', '', text)          # remove URLs
    text = re.sub(r'\s+', ' ', text).strip()             # collapse whitespace
    text = re.sub(r'[^\x00-\x7F]+', '', text)            # remove non-ASCII
    return text

def detect_drugs(text: str) -> list:
    found = []
    text_lower = text.lower()
    for drug in DRUG_NAMES:
        if drug.lower() in text_lower:
            found.append(drug)
    return found

def classify_stakeholder(text: str) -> str:
    text_lower = text.lower()
    scores = {stakeholder: 0 for stakeholder in STAKEHOLDER_KEYWORDS}
    for stakeholder, keywords in STAKEHOLDER_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text_lower:
                scores[stakeholder] += 1
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "Patients"  # default to Patients

def chunk_text(text: str, chunk_size: int = 400, overlap: int = 50) -> list:
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
        i += chunk_size - overlap
    return chunks

def preprocess_post(post: dict) -> dict:
    full_text = f"{post.get('title', '')} {post.get('text', '')}"
    for comment in post.get("comments", []):
        full_text += f" {comment.get('text', '')}"

    full_text = normalize_text(full_text)
    full_text = remove_pii(full_text)

    return {
        "id": post["id"],
        "subreddit": post.get("subreddit", ""),
        "keyword": post.get("keyword", ""),
        "url": post.get("url", ""),
        "created_utc": post.get("created_utc", ""),
        "score": post.get("score", 0),
        "raw_text": full_text,
        "drugs_detected": detect_drugs(full_text),
        "stakeholder": classify_stakeholder(full_text),
        "chunks": chunk_text(full_text),
    }

def run_preprocessor(
    input_path: str = "data/raw_posts.json",
    output_path: str = "data/processed_posts.json"
):
    with open(input_path, "r", encoding="utf-8") as f:
        raw_posts = json.load(f)

    processed = [preprocess_post(p) for p in raw_posts]

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(processed, f, indent=2, ensure_ascii=False)

    print(f"Preprocessed {len(processed)} posts -> {output_path}")
    return processed

if __name__ == "__main__":
    run_preprocessor()
