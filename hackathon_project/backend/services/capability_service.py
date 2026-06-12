import os
import json
import requests
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """Splits a long text string into overlapping chunks."""
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        # Move forward by chunk_size - overlap
        start += (chunk_size - overlap)
    return chunks

def extract_metadata_from_chunk(chunk_text: str) -> Dict[str, Any]:
    """Calls local Ollama to analyze and extract metadata categories from a chunk of text."""
    prompt = f"""You are an AI data engineer. Analyze the following document text chunk and extract metadata for categorizing it in a corporate Capability Library.

Chunk Text:
\"\"\"
{chunk_text}
\"\"\"

Return a JSON object with this exact structure:
{{
  "document_type": "project_summary" | "certification" | "cv" | "company_profile" | "case_study" | "prior_proposal" | "other",
  "domain": "e.g., cybersecurity, cloud, finance, erp, network, construction, education, energy, etc.",
  "year": 2026 (or null if not mentioned),
  "tags": ["tag1", "tag2", "tag3"]
}}

Rules:
- Categorize the document type and domain accurately based on the text.
- If year is not mentioned, return null.
- Keep tags concise and relevant to the domain.
- Do NOT include any explanations, return ONLY valid JSON.
"""

    url = f"{OLLAMA_BASE_URL}/api/generate"
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.0
        }
    }

    try:
        response = requests.post(url, json=payload, timeout=30)
        if response.status_code == 200:
            result = response.json()
            response_text = result.get("response", "{}")
            data = json.loads(response_text)
            
            # Standardize returned keys
            return {
                "document_type": data.get("document_type", "other"),
                "domain": data.get("domain", "unknown"),
                "year": data.get("year"),
                "tags": data.get("tags", [])
            }
        else:
            print(f"Ollama metadata extraction failed with status {response.status_code}")
            return {"document_type": "other", "domain": "unknown", "year": None, "tags": []}
    except Exception as e:
        print(f"Error calling Ollama API for metadata extraction: {e}")
        return {"document_type": "other", "domain": "unknown", "year": None, "tags": []}
