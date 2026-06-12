import os
import re
import json
import requests
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from flashrank import RerankRequest
from dotenv import load_dotenv

import models

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

def check_rule_based_compliance(db: Session, req_desc: str) -> Tuple[bool, str, str, str, int]:
    """
    Performs quick rule-based checks for certifications or numeric experience years.
    Returns: (is_matched, status, reasoning, evidence, confidence)
    """
    req_lower = req_desc.lower()
    
    # 1. Certification Checks (e.g., ISO 27001, CMMI, PMP)
    cert_matches = {
        "iso 27001": "ISO 27001",
        "iso 9001": "ISO 9001",
        "cmmi": "CMMI",
        "pmp": "PMP",
        "ce mark": "CE Mark",
        "soc2": "SOC2",
        "soc 2": "SOC2"
    }
    
    for key, cert_name in cert_matches.items():
        if key in req_lower:
            # Query db for this certification
            db_cert = db.query(models.CapabilityLibrary).filter(
                models.CapabilityLibrary.category == "Certification",
                models.CapabilityLibrary.content.ilike(f"%{cert_name}%")
            ).first()
            
            if db_cert:
                return (
                    True,
                    "PASS",
                    f"Rule-based match: Company possesses the required {cert_name} certification.",
                    db_cert.title,
                    100
                )
            else:
                return (
                    True,
                    "FAIL",
                    f"Rule-based match: Required certification {cert_name} was not found in the capability library.",
                    "Missing",
                    100
                )
                
    return (False, "FAIL", "", "Missing", 0)

def evaluate_requirement_compliance(db: Session, requirement: models.ExtractedRequirement) -> Dict[str, Any]:
    """Evaluates a single requirement's compliance using rules & LLM RAG reasoning."""
    try:
        # 1. Rule-based check
        is_rule_matched, rule_status, rule_reasoning, rule_evidence, rule_confidence = check_rule_based_compliance(db, requirement.description)
        if is_rule_matched:
            return {
                "requirement_id": requirement.id,
                "status": rule_status,
                "reasoning": rule_reasoning,
                "evidence": rule_evidence,
                "gap_analysis": "None" if rule_status == "PASS" else f"Acquire certification: {requirement.description}",
                "confidence_score": rule_confidence
            }
        
        # 2. Retrieve capability library items for evidence
        capabilities = db.query(models.CapabilityLibrary).all()
        if not capabilities:
            return {
                "requirement_id": requirement.id,
                "status": "FAIL",
                "reasoning": "No internal evidence available in capability library.",
                "evidence": "Missing",
                "gap_analysis": "Populate the Capability Library with company credentials, resumes, and case studies.",
                "confidence_score": 90
            }
        
        # 3. Rerank capabilities to find the most relevant evidence
        passages = []
        for cap in capabilities:
            passages.append({
                "id": str(cap.id),
                "text": f"Title: {cap.title}\nCategory: {cap.category}\nContent: {cap.content}",
                "meta": cap
            })
        
        # Rerank using BGE
        from services.ranker_service import _ranker
        rerank_request = RerankRequest(query=requirement.description, passages=passages)
        ranked = _ranker.rerank(rerank_request)
        
        # Get top 2 items as evidence
        top_items = ranked[:2]
        evidence_text = ""
        evidence_names = []
        for item in top_items:
            cap = item["meta"]
            evidence_names.append(cap.title)
            evidence_text += f"Document: {cap.title} ({cap.category})\nContent: {cap.content}\n\n"
        
        # 4. LLM reasoning
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": f"""You are an enterprise compliance auditor checking if the company meets an RFP requirement.
RFP Requirement: "{requirement.description}"

Company Evidence:
{evidence_text}

Evaluate compliance. You must match the requirement to the company evidence.
Respond ONLY in valid JSON format with the following keys. Do NOT output any explanation, html, markdown, or text other than raw JSON.

JSON keys:
- "status": "PASS" (fully met), "PARTIAL" (partially met), or "FAIL" (not met / missing evidence)
- "evidence": Title of supporting document(s), or "Missing"
- "reasoning": Clear explanation of how the evidence satisfies (or fails to satisfy) the requirement. Be professional, enterprise-level, and objective. Never invent achievements.
- "gap_analysis": If status is FAIL or PARTIAL, describe what is missing. Otherwise "None".
- "confidence_score": Integer between 0 and 100.

JSON:""",
            "stream": False,
            "options": {
                "temperature": 0.0,
                "num_predict": 250
            }
        }
        
        url = f"{OLLAMA_BASE_URL}/api/generate"
        response = requests.post(url, json=payload, timeout=20)
        if response.status_code == 200:
            res_json = response.json()
            output_text = res_json.get("response", "").strip()
            # Extract JSON block if model returned markdown
            match = re.search(r"\{.*\}", output_text, re.DOTALL)
            if match:
                parsed = json.loads(match.group(0))
                return {
                    "requirement_id": requirement.id,
                    "status": parsed.get("status", "FAIL").upper(),
                    "reasoning": parsed.get("reasoning", "Evaluated by LLM."),
                    "evidence": parsed.get("evidence", "Missing"),
                    "gap_analysis": parsed.get("gap_analysis", "None"),
                    "confidence_score": int(parsed.get("confidence_score", 70))
                }
                
        # Heuristic fallback if LLM fails
        best_score = top_items[0]["score"] if top_items else 0.0
        best_cap = top_items[0]["meta"] if top_items else None
        
        if best_score > 0.6 and best_cap:
            return {
                "requirement_id": requirement.id,
                "status": "PASS" if best_score > 0.75 else "PARTIAL",
                "reasoning": f"Matched capability '{best_cap.title}' with confidence {int(best_score*100)}%.",
                "evidence": best_cap.title,
                "gap_analysis": "None" if best_score > 0.75 else "Verify details manually.",
                "confidence_score": int(best_score * 100)
            }
            
        return {
            "requirement_id": requirement.id,
            "status": "FAIL",
            "reasoning": "No matching evidence found in the capability library.",
            "evidence": "Missing",
            "gap_analysis": f"Add evidence for: {requirement.description}",
            "confidence_score": 60
        }
    except Exception as e:
        print(f"Exception during compliance audit: {e}")
        return {
            "requirement_id": requirement.id,
            "status": "FAIL",
            "reasoning": f"Exception occurred during compliance check: {str(e)}",
            "evidence": "Missing",
            "gap_analysis": "System error",
            "confidence_score": 0
        }

def run_workspace_compliance_validation(db: Session, workspace_id: Any) -> int:
    """Orchestrates compliance validation for all requirements in a workspace."""
    # 1. Fetch requirements
    requirements = db.query(models.ExtractedRequirement).filter(
        models.ExtractedRequirement.workspace_id == workspace_id
    ).all()
    
    if not requirements:
        return 0
        
    # 2. Delete existing compliance results for these requirements
    req_ids = [r.id for r in requirements]
    db.query(models.ComplianceResult).filter(
        models.ComplianceResult.requirement_id.in_(req_ids)
    ).delete(synchronize_session=False)
    db.commit()
    
    # 3. Evaluate each requirement and insert results
    results_to_insert = []
    for req in requirements:
        eval_data = evaluate_requirement_compliance(db, req)
        res_record = models.ComplianceResult(
            requirement_id=req.id,
            status=eval_data["status"],
            reasoning=eval_data["reasoning"],
            evidence=eval_data["evidence"],
            gap_analysis=eval_data["gap_analysis"],
            confidence_score=eval_data["confidence_score"]
        )
        results_to_insert.append(res_record)
        
    if results_to_insert:
        db.add_all(results_to_insert)
        db.commit()
        
    return len(results_to_insert)
