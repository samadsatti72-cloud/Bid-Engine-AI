import os
import re
import json
import requests
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from flashrank import RerankRequest
from dotenv import load_dotenv

import models

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

DEFAULT_SECTIONS = [
    {
        "section_code": "EXEC_SUM",
        "section_title": "Executive Summary",
        "prompt_instruction": "Write a persuasive Executive Summary detailing our core value proposition, project understanding, and alignment with client goals."
    },
    {
        "section_code": "TECH_RESP",
        "section_title": "Technical Response & Methodology",
        "prompt_instruction": "Detail our technical response, architecture, system design, implementation methodology, and execution plan."
    },
    {
        "section_code": "EXPERIENCE",
        "section_title": "Past Performance & Experience",
        "prompt_instruction": "Summarize key case studies, past projects, similar experience, and qualifications of key team members."
    },
    {
        "section_code": "COMPLIANCE",
        "section_title": "Compliance & Credentials Matrix",
        "prompt_instruction": "Discuss our compliance with ISO and SOC2 standards, quality controls, and active certifications."
    }
]

def initialize_default_proposal_sections(db: Session, workspace_id: Any) -> int:
    """Pre-populates a workspace with standard default proposal sections if empty."""
    existing_count = db.query(models.ProposalSection).filter(
        models.ProposalSection.workspace_id == workspace_id
    ).count()
    
    if existing_count > 0:
        return 0
        
    inserted = 0
    for sec in DEFAULT_SECTIONS:
        record = models.ProposalSection(
            workspace_id=workspace_id,
            section_code=sec["section_code"],
            section_title=sec["section_title"],
            prompt_instruction=sec["prompt_instruction"],
            draft_content=None,
            status="DRAFT"
        )
        db.add(record)
        inserted += 1
        
    # Also initialize the main draft placeholder if it doesn't exist
    main_draft_count = db.query(models.ProposalSection).filter(
        models.ProposalSection.workspace_id == workspace_id,
        models.ProposalSection.section_code == "MAIN_DRAFT"
    ).count()
    if main_draft_count == 0:
        main_record = models.ProposalSection(
            workspace_id=workspace_id,
            section_code="MAIN_DRAFT",
            section_title="Main Proposal Response",
            prompt_instruction="Consolidated RAG Proposal Draft",
            draft_content=None,
            status="DRAFT"
        )
        db.add(main_record)
        inserted += 1
        
    db.commit()
    return inserted

def generate_proposal_section_draft(db: Session, workspace_id: Any, section_code: str, instruction: str = None) -> str:
    """Generates draft content for a specific proposal section using RAG evidence."""
    # 1. Fetch requirements and compliance results for context
    requirements = db.query(models.ExtractedRequirement).filter(
        models.ExtractedRequirement.workspace_id == workspace_id
    ).all()
    
    compliance_results = db.query(models.ComplianceResult).join(
        models.ExtractedRequirement,
        models.ComplianceResult.requirement_id == models.ExtractedRequirement.id
    ).filter(
        models.ExtractedRequirement.workspace_id == workspace_id
    ).all()
    
    req_text = ""
    for r in requirements:
        req_text += f"- [{r.category}] {r.req_number}: {r.description} (Priority: {r.priority})\n"
        
    comp_text = ""
    for cr in compliance_results:
        # Find description
        desc = db.query(models.ExtractedRequirement).filter(models.ExtractedRequirement.id == cr.requirement_id).first().description
        comp_text += f"- Requirement: {desc} | Status: {cr.status} | Evidence: {cr.evidence} | Reasoning: {cr.reasoning}\n"

    # 2. Retrieve & Rerank capabilities for evidence
    capabilities = db.query(models.CapabilityLibrary).all()
    evidence_text = ""
    if capabilities:
        section_queries = {
            "EXEC_SUM": "executive summary overview value proposition bid proposal introduction",
            "TECH_RESP": "technical architecture methodology execution framework system engineering implementation",
            "EXPERIENCE": "past performance case study resumes project history experience client references",
            "COMPLIANCE": "security certification ISO 27001 SOC2 quality compliance standards credentials"
        }
        query = section_queries.get(section_code, "company profile capabilities credentials")
        
        passages = []
        for cap in capabilities:
            passages.append({
                "id": str(cap.id),
                "text": f"Title: {cap.title}\nCategory: {cap.category}\nContent: {cap.content}",
                "meta": cap
            })
            
        from services.ranker_service import _ranker
        rerank_request = RerankRequest(query=query, passages=passages)
        ranked = _ranker.rerank(rerank_request)
        
        for item in ranked[:3]:
            cap = item["meta"]
            evidence_text += f"Document: {cap.title} ({cap.category})\nContent: {cap.content}\n\n"
    else:
        evidence_text = "No capability library items available."

    # 3. Prompt selection
    prompts_templates = {
        "EXEC_SUM": """You are an enterprise bid proposal writer.
Write the Executive Summary section for a bid proposal response.
Retrieved Evidence:
{evidence}

RFP requirements & checklist info:
{requirements}

Instructions:
- Write a professional, enterprise-level, persuasive overview of our bid.
- Maintain compliance with the requirements.
- Never invent fake achievements, awards, client names, or certifications.
- If key evidence is missing to back up a claim, explicitly insert a warning placeholder: [FLAG: Missing evidence for <claim>].
- Format the response in clear Markdown. Do not include introductory or concluding conversational chat. Start directly with the section content.
""",
        "TECH_RESP": """You are an enterprise bid proposal writer.
Write the Technical Response & Methodology section for a bid proposal response.
Retrieved Evidence:
{evidence}

RFP requirements & checklist info:
{requirements}

Instructions:
- Write a detailed execution approach, architecture overview, and deployment methodology.
- Make it sound professional, technical, and persuasive.
- Ground all details in the retrieved company evidence.
- Never invent fake achievements or capabilities.
- If there is no evidence for a specific technical requirement requested in the RFP, explicitly insert a warning placeholder: [FLAG: Missing evidence for technical requirement: <requirement>].
- Format the response in clear Markdown. Do not include conversational text. Start directly with the section content.
""",
        "EXPERIENCE": """You are an enterprise bid proposal writer.
Write the Past Performance & Experience section for a bid proposal response.
Retrieved Evidence:
{evidence}

RFP requirements & checklist info:
{requirements}

Instructions:
- Summarize our key experience, past case studies, and corporate achievements.
- Ground everything strictly in the retrieved case studies and resumes.
- Never invent fake client names, project numbers, budgets, or years of experience.
- If we do not have case studies matching a specific required area, explicitly insert: [FLAG: Missing evidence for case study / experience in <area>].
- Format the response in clear Markdown. Start directly with the section content.
""",
        "COMPLIANCE": """You are an enterprise bid proposal writer.
Write the Compliance & Credentials section for a bid proposal response.
Retrieved Evidence:
{evidence}

RFP requirements & checklist info:
{requirements}

Instructions:
- Summarize the company's compliance credentials, security frameworks, and certifications.
- Discuss how we satisfy the compliance requirements.
- Ground details strictly in the retrieved certifications and compliance matrix results.
- Never invent certifications.
- If a certification or compliance standard is required but missing, insert: [FLAG: Missing credential / certificate: <certificate>].
- Format the response in clear Markdown. Start directly with the section content.
"""
    }
    
    template = prompts_templates.get(section_code, """You are an enterprise bid proposal writer.
Write the section "{section_code}" for a bid proposal response.
Retrieved Evidence:
{evidence}

RFP requirements:
{requirements}

Instructions:
- Write a professional, enterprise-level response.
- Ground all details in the retrieved company evidence.
- If key evidence is missing, explicitly insert a warning placeholder: [FLAG: Missing evidence for <claim>].
- Format the response in clear Markdown. Start directly with the section content.
""")
    
    prompt = template.format(
        evidence=evidence_text,
        requirements=req_text + "\nCompliance Check:\n" + comp_text,
        section_code=section_code
    )
    
    if instruction:
        prompt += f"\nAdditional User Custom Instruction: {instruction}\n"
        
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.2,
            "num_predict": 800
        }
    }
    
    try:
        url = f"{OLLAMA_BASE_URL}/api/generate"
        response = requests.post(url, json=payload, timeout=60)
        if response.status_code == 200:
            result = response.json()
            return result.get("response", "").strip()
        else:
            return f"[FLAG: Ollama generation failed with code {response.status_code}]"
    except Exception as e:
        return f"[FLAG: System exception calling Ollama: {str(e)}]"

def generate_full_workspace_proposal(db: Session, workspace_id: Any) -> str:
    """Generates drafts for all sections and compiles them into the MAIN_DRAFT."""
    # Ensure sections are initialized
    initialize_default_proposal_sections(db, workspace_id)
    
    # Fetch all sections except MAIN_DRAFT
    sections = db.query(models.ProposalSection).filter(
        models.ProposalSection.workspace_id == workspace_id,
        models.ProposalSection.section_code != "MAIN_DRAFT"
    ).order_by(models.ProposalSection.section_code).all()
    
    drafts = {}
    for sec in sections:
        # Generate draft
        content = generate_proposal_section_draft(db, workspace_id, sec.section_code, sec.prompt_instruction)
        sec.draft_content = content
        sec.status = "UNDER-REVIEW"
        drafts[sec.section_code] = content
        
    # Compile
    full_compiled = ""
    # Ordering manually for clean layout
    order = ["EXEC_SUM", "TECH_RESP", "EXPERIENCE", "COMPLIANCE"]
    for code in order:
        sec = next((s for s in sections if s.section_code == code), None)
        if sec:
            full_compiled += f"# {sec.section_title}\n\n{sec.draft_content}\n\n---\n\n"
            
    # Save back to MAIN_DRAFT
    main_sec = db.query(models.ProposalSection).filter(
        models.ProposalSection.workspace_id == workspace_id,
        models.ProposalSection.section_code == "MAIN_DRAFT"
    ).first()
    
    if not main_sec:
        main_sec = models.ProposalSection(
            workspace_id=workspace_id,
            section_code="MAIN_DRAFT",
            section_title="Main Proposal Response",
            prompt_instruction="Consolidated RAG Proposal Draft",
            draft_content=full_compiled,
            status="UNDER-REVIEW"
        )
        db.add(main_sec)
    else:
        main_sec.draft_content = full_compiled
        main_sec.status = "UNDER-REVIEW"
        
    db.commit()
    return full_compiled
