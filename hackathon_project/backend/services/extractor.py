import os
import re
import json
import requests
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

def chunk_text(text: str, chunk_size: int = 15000, overlap: int = 500) -> List[str]:
    """Splits a long text string into overlapping chunks."""
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += (chunk_size - overlap)
    return chunks

def extract_string_from_item(item: Any) -> str:
    """Defensively extracts a text string from various item types returned by LLM (strings, dicts, lists)."""
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        # Check standard dictionary keys Llama 3.2 might generate
        for key in ["requirement", "description", "name", "text", "value", "date", "document"]:
            if key in item and isinstance(item[key], str):
                return item[key]
        # Fallback to the first string value in the dict
        for val in item.values():
            if isinstance(val, str):
                return val
        return json.dumps(item)
    return str(item)

def extract_from_chunk(text_chunk: str) -> Dict[str, List[str]]:
    """Calls local Ollama to extract requirements from a single chunk of text."""
    prompt = f"""You are a professional bid manager analyzing a Request for Proposal (RFP) document.
Analyze the following RFP text chunk and extract:
1. Mandatory requirements (e.g., compliance statements, must-have features, experience years, certifications like ISO)
2. Submission deadlines (e.g., submission dates, Q&A dates, times)
3. Evaluation criteria (e.g., technical weights, financial weights, evaluation percentages)
4. Required/mandatory documents (e.g., certificates, resumes, financial sheets, case studies, references)
5. Budget values (e.g., project budget, funding limits, max pricing values)
6. Eligibility criteria (e.g., company eligibility, background checks, registration requirements)
7. Q&A sections (e.g., Q&A timelines, query address details, standard Q&A questions if any)

RFP Text Chunk:
\"\"\"
{text_chunk}
\"\"\"

Return ONLY a valid JSON object with this exact structure (no extra text before or after):
{{
  "requirements": [],
  "deadlines": [],
  "evaluation_criteria": [],
  "mandatory_documents": [],
  "budget_values": [],
  "eligibility_criteria": [],
  "qa_sections": []
}}

Rules:
- Do NOT hallucinate. Only extract items explicitly mentioned in the text.
- If a category has no items in this chunk, return an empty array for it.
- Keep the extracted items concise but include context (e.g., instead of just "ISO certification", write "Must possess ISO 9001 certification").
- Return ONLY the JSON object, no other text.
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
        response = requests.post(url, json=payload, timeout=60)
        if response.status_code == 200:
            result = response.json()
            response_text = result.get("response", "{}").strip()
            
            # Try to extract JSON from the response (in case there's extra text)
            data = None
            
            # Try 1: Direct JSON parse
            try:
                data = json.loads(response_text)
            except json.JSONDecodeError:
                pass
            
            # Try 2: Find JSON in markdown code blocks
            if not data:
                markdown_match = re.search(r'```(?:json)?\s*\n(.*?)\n```', response_text, re.DOTALL)
                if markdown_match:
                    try:
                        data = json.loads(markdown_match.group(1))
                    except json.JSONDecodeError:
                        pass
            
            # Try 3: Find JSON with regex
            if not data:
                json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text, re.DOTALL)
                if json_match:
                    try:
                        data = json.loads(json_match.group(0))
                    except json.JSONDecodeError:
                        pass
            
            if not data:
                print(f"Failed to parse Ollama response as JSON")
                print(f"Response text: {response_text[:300]}")
                data = {}
            
            # Standardize and defensively extract strings
            return {
                "requirements": [extract_string_from_item(x) for x in data.get("requirements", [])],
                "deadlines": [extract_string_from_item(x) for x in data.get("deadlines", [])],
                "evaluation_criteria": [extract_string_from_item(x) for x in data.get("evaluation_criteria", [])],
                "mandatory_documents": [extract_string_from_item(x) for x in data.get("mandatory_documents", [])],
                "budget_values": [extract_string_from_item(x) for x in data.get("budget_values", [])],
                "eligibility_criteria": [extract_string_from_item(x) for x in data.get("eligibility_criteria", [])],
                "qa_sections": [extract_string_from_item(x) for x in data.get("qa_sections", [])]
            }
        else:
            print(f"Ollama extraction failed with status {response.status_code}: {response.text}")
            return {
                "requirements": [], "deadlines": [], "evaluation_criteria": [], "mandatory_documents": [],
                "budget_values": [], "eligibility_criteria": [], "qa_sections": []
            }
    except Exception as e:
        print(f"Error calling Ollama API: {e}")
        import traceback
        traceback.print_exc()
        return {
            "requirements": [], "deadlines": [], "evaluation_criteria": [], "mandatory_documents": [],
            "budget_values": [], "eligibility_criteria": [], "qa_sections": []
        }

def deduplicate_items(items: List[str]) -> List[str]:
    """Cleans and deduplicates a list of extracted text items."""
    seen = set()
    unique_items = []
    for item in items:
        cleaned = item.strip()
        if not cleaned:
            continue
        # Deduplicate based on lowercased representation
        lower_item = cleaned.lower()
        if lower_item not in seen:
            seen.add(lower_item)
            unique_items.append(cleaned)
    return unique_items

def extract_requirements_fallback(text: str) -> Dict[str, List[str]]:
    """Fallback regex-based extraction for requirements when Ollama is unavailable."""
    results = {
        "requirements": [],
        "deadlines": [],
        "evaluation_criteria": [],
        "mandatory_documents": [],
        "budget_values": [],
        "eligibility_criteria": [],
        "qa_sections": []
    }
    
    # Extract requirements with keywords
    requirement_keywords = [
        (r'(?:must|shall|required|mandatory|should)\s+(?:have|provide|include|support|ensure|implement|maintain)[^\n.]*(?:\.|$)', "requirements"),
        (r'(?:certification|experience|years?)\s+(?:in|with|of)\s+[^\n.]*(?:\.|$)', "eligibility_criteria"),
        (r'(?:budget|cost|price|funding|allocation)\s*(?:limit|maximum|not exceed|up to)[^\n.]*(?:\.|$)', "budget_values"),
        (r'(?:deadline|due|submission|closing)\s+(?:date|time)[^\n.]*(?:\.|$)', "deadlines"),
        (r'(?:evaluation|scoring|weight|percentage|criteria)[^\n.]*(?:\.|$)', "evaluation_criteria"),
        (r'(?:document|attach|submit|provide)\s+(?:proof|evidence|certificate|copy)[^\n.]*(?:\.|$)', "mandatory_documents"),
    ]
    
    for pattern, category in requirement_keywords:
        matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
        if matches:
            for match in matches:
                cleaned = match.strip()
                if len(cleaned) > 10:  # Only include non-trivial matches
                    results[category].append(cleaned)
    
    # Deduplicate all categories
    for key in results:
        results[key] = deduplicate_items(results[key])
    
    return results

def extract_workspace_requirements(documents_text: List[str]) -> Dict[str, List[str]]:
    """Analyzes a list of document texts, chunks them, and returns consolidated requirements."""
    consolidated = {
        "requirements": [],
        "deadlines": [],
        "evaluation_criteria": [],
        "mandatory_documents": [],
        "budget_values": [],
        "eligibility_criteria": [],
        "qa_sections": []
    }

    for text in documents_text:
        chunks = chunk_text(text)
        for chunk in chunks:
            chunk_data = extract_from_chunk(chunk)
            for key in consolidated:
                consolidated[key].extend(chunk_data.get(key, []))

    # Deduplicate all keys
    for key in consolidated:
        consolidated[key] = deduplicate_items(consolidated[key])
    
    # If we got very few results, try fallback extraction
    total_extracted = sum(len(v) for v in consolidated.values())
    if total_extracted < 3:  # If we got less than 3 items total, use fallback
        print(f"Ollama extraction returned only {total_extracted} items, using fallback regex extraction...")
        for text in documents_text:
            fallback_data = extract_requirements_fallback(text)
            for key in consolidated:
                consolidated[key].extend(fallback_data.get(key, []))
        
        # Deduplicate again after fallback
        for key in consolidated:
            consolidated[key] = deduplicate_items(consolidated[key])

    return consolidated

def extract_entities_regex(text: str) -> Dict[str, List[str]]:
    """Quick regex pattern matching for dates, budgets, and percentages as baseline."""
    entities = {
        "dates": [],
        "deadlines": [],
        "money_budget": [],
        "percentages": [],
        "organizations": [],
        "certifications": [],
        "locations": []
    }
    
    # Percentages (e.g. 40%, 12.5%, etc.)
    pct_matches = re.findall(r'\b\d+(?:\.\d+)?\s*%\b', text)
    entities["percentages"] = list(set(pct_matches))
    
    # Money/Budget (e.g. $150,000, $2.5 million, €10K)
    money_matches = re.findall(r'\$\s*\d{1,3}(?:,\d{3})*(?:\.\d+)?(?:\s*(?:million|billion|k|m|b))?\b|\b\d+(?:\.\d+)?\s*(?:USD|EUR|dollars)\b', text, re.IGNORECASE)
    entities["money_budget"] = list(set(money_matches))
    
    # Dates (e.g. MM/DD/YYYY, YYYY-MM-DD, Month DD, YYYY)
    date_matches1 = re.findall(r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b', text)
    date_matches2 = re.findall(r'\b\d{4}-\d{1,2}-\d{1,2}\b', text)
    date_matches3 = re.findall(r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}\b', text, re.IGNORECASE)
    all_dates = list(set(date_matches1 + date_matches2 + date_matches3))
    entities["dates"] = all_dates

    return entities

def extract_entities_from_chunk(text_chunk: str) -> Dict[str, List[str]]:
    """Calls local Ollama to extract named entities from a single chunk of text."""
    prompt = f"""You are a professional bid manager analyzing a Request for Proposal (RFP) document.
Analyze the following RFP text chunk and extract named entities.
Extract these exact entity types:
1. dates (specific calendar dates, e.g., "October 12, 2026", "2026-06-15")
2. deadlines (explicit project/submission deadlines or due dates, e.g., "Submission due October 12, 2026 at 5:00 PM")
3. money_budget (monetary values, funding, budget limits, pricing constraints, e.g., "$150,000", "budget not exceeding $2.5 Million")
4. percentages (percentages, evaluation weights, margins, e.g., "40%", "15% weight")
5. organizations (companies, government agencies, partnerships, institutions, e.g., "Department of Education", "Acme Corporation")
6. certifications (certifications, standards, compliance certifications, e.g., "ISO 9001", "SOC 2 Type II", "PMP")
7. locations (geographic places, cities, states, addresses, delivery sites, e.g., "New York, NY", "Washington DC")

RFP Text Chunk:
\"\"\"
{text_chunk}
\"\"\"

Return ONLY a valid JSON object with this exact structure (no extra text before or after):
{{
  "dates": [],
  "deadlines": [],
  "money_budget": [],
  "percentages": [],
  "organizations": [],
  "certifications": [],
  "locations": []
}}

Rules:
- Do NOT hallucinate. Only extract items explicitly mentioned in the text.
- If a category has no items in this chunk, return an empty array for it.
- Keep the extracted values concise and precise.
- Return ONLY the JSON object, no other text.
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
        response = requests.post(url, json=payload, timeout=60)
        if response.status_code == 200:
            result = response.json()
            response_text = result.get("response", "{}").strip()
            
            # Try to extract JSON from the response (in case there's extra text)
            data = None
            
            # Try 1: Direct JSON parse
            try:
                data = json.loads(response_text)
            except json.JSONDecodeError:
                pass
            
            # Try 2: Find JSON in markdown code blocks
            if not data:
                markdown_match = re.search(r'```(?:json)?\s*\n(.*?)\n```', response_text, re.DOTALL)
                if markdown_match:
                    try:
                        data = json.loads(markdown_match.group(1))
                    except json.JSONDecodeError:
                        pass
            
            # Try 3: Find JSON with regex
            if not data:
                json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text, re.DOTALL)
                if json_match:
                    try:
                        data = json.loads(json_match.group(0))
                    except json.JSONDecodeError:
                        pass
            
            if not data:
                print(f"Failed to parse Ollama entity response as JSON")
                print(f"Response text: {response_text[:300]}")
                data = {}
            
            return {
                "dates": [extract_string_from_item(x) for x in data.get("dates", [])],
                "deadlines": [extract_string_from_item(x) for x in data.get("deadlines", [])],
                "money_budget": [extract_string_from_item(x) for x in data.get("money_budget", [])],
                "percentages": [extract_string_from_item(x) for x in data.get("percentages", [])],
                "organizations": [extract_string_from_item(x) for x in data.get("organizations", [])],
                "certifications": [extract_string_from_item(x) for x in data.get("certifications", [])],
                "locations": [extract_string_from_item(x) for x in data.get("locations", [])]
            }
        else:
            print(f"Ollama entity extraction failed with status {response.status_code}: {response.text}")
            return {
                "dates": [], "deadlines": [], "money_budget": [], "percentages": [],
                "organizations": [], "certifications": [], "locations": []
            }
    except Exception as e:
        print(f"Error calling Ollama API for entities: {e}")
        import traceback
        traceback.print_exc()
        return {
            "dates": [], "deadlines": [], "money_budget": [], "percentages": [],
            "organizations": [], "certifications": [], "locations": []
        }

def extract_entities_from_text(documents_text: List[str]) -> Dict[str, List[str]]:
    """Analyzes document texts, chunks them, extracts entities using regex and LLM, and consolidates them."""
    consolidated = {
        "dates": [],
        "deadlines": [],
        "money_budget": [],
        "percentages": [],
        "organizations": [],
        "certifications": [],
        "locations": []
    }

    for text in documents_text:
        # 1. Quick regex run on whole text first
        regex_data = extract_entities_regex(text)
        for key in regex_data:
            consolidated[key].extend(regex_data[key])
        
        # 2. Chunk text and run LLM
        chunks = chunk_text(text)
        for chunk in chunks:
            chunk_data = extract_entities_from_chunk(chunk)
            for key in consolidated:
                consolidated[key].extend(chunk_data.get(key, []))

    # Deduplicate all keys
    for key in consolidated:
        consolidated[key] = deduplicate_items(consolidated[key])

    return consolidated