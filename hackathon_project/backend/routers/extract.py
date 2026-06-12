from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List, Dict

from database import get_db
import models
import schemas
from services.extractor import extract_workspace_requirements, extract_entities_from_text
from services.ranker_service import rank_requirements



router = APIRouter(prefix="/api/workspaces", tags=["Extraction"])

@router.post("/{workspace_id}/extract", status_code=status.HTTP_200_OK)
def trigger_extraction(workspace_id: UUID, db: Session = Depends(get_db)):
    # 1. Validate workspace
    workspace = db.query(models.Workspace).filter(models.Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace with ID {workspace_id} not found."
        )

    # 2. Get all uploaded documents for the workspace
    documents = db.query(models.UploadedDocument).filter(
        models.UploadedDocument.workspace_id == workspace_id
    ).all()
    
    if not documents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No documents found in this workspace. Please upload a document first."
        )

    # 3. Collect texts from all documents
    docs_text = [doc.raw_text for doc in documents if doc.raw_text]
    if not docs_text or all(not text.strip() for text in docs_text):
         raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded documents contain no readable text."
        )

    # 4. Trigger Ollama requirements extraction
    try:
        extracted_data = extract_workspace_requirements(docs_text)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ollama requirements extraction failed: {str(e)}"
        )

    # 4.5 Trigger Named Entity Extraction
    try:
        entities_data = extract_entities_from_text(docs_text)
    except Exception as e:
        print(f"Ollama entity extraction failed: {e}")
        entities_data = {}

    # 5. Clear previous requirements & entities for this workspace
    db.query(models.ExtractedRequirement).filter(
        models.ExtractedRequirement.workspace_id == workspace_id
    ).delete()
    
    db.query(models.ExtractedEntity).filter(
        models.ExtractedEntity.workspace_id == workspace_id
    ).delete()
    
    # 6. Insert new requirements
    new_records = []
    
    # Mapping lists to category & priority
    categories_mapping = {
        "requirements": ("Mandatory", "MUST"),
        "deadlines": ("Deadline", "MUST"),
        "evaluation_criteria": ("Evaluation Criteria", "SHOULD"),
        "mandatory_documents": ("Required Document", "MUST"),
        "budget_values": ("Budget", "INFO"),
        "eligibility_criteria": ("Eligibility", "MUST"),
        "qa_sections": ("Q&A", "INFO")
    }

    # Retrieve first document ID for reference
    default_doc_id = documents[0].id

    for key, (category, priority) in categories_mapping.items():
        items = extracted_data.get(key, [])
        for item in items:
            record = models.ExtractedRequirement(
                workspace_id=workspace_id,
                document_id=default_doc_id,
                category=category,
                priority=priority,
                description=item,
                req_number=f"EXT-{len(new_records)+1:02d}"
            )
            new_records.append(record)

    if new_records:
        db.add_all(new_records)

    # 7. Insert new entities
    new_entities = []
    for entity_type, values in entities_data.items():
        for val in values:
            record = models.ExtractedEntity(
                workspace_id=workspace_id,
                document_id=default_doc_id,
                entity_type=entity_type,
                value=val
            )
            new_entities.append(record)

    if new_entities:
        db.add_all(new_entities)

    db.commit()

    return {
        "status": "success",
        "message": f"Successfully extracted {len(new_records)} checklist items and {len(new_entities)} entities.",
        "counts": {
            "requirements": len(extracted_data.get("requirements", [])),
            "deadlines": len(extracted_data.get("deadlines", [])),
            "evaluation_criteria": len(extracted_data.get("evaluation_criteria", [])),
            "mandatory_documents": len(extracted_data.get("mandatory_documents", [])),
            "budget_values": len(extracted_data.get("budget_values", [])),
            "eligibility_criteria": len(extracted_data.get("eligibility_criteria", [])),
            "qa_sections": len(extracted_data.get("qa_sections", []))
        }
    }

@router.get("/{workspace_id}/requirements", response_model=List[schemas.RequirementResponse])
def get_extracted_requirements(workspace_id: UUID, db: Session = Depends(get_db)):
    # Validate workspace
    workspace = db.query(models.Workspace).filter(models.Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace with ID {workspace_id} not found."
        )
    return db.query(models.ExtractedRequirement).filter(
        models.ExtractedRequirement.workspace_id == workspace_id
    ).order_by(models.ExtractedRequirement.category, models.ExtractedRequirement.req_number).all()

@router.get("/{workspace_id}/entities", response_model=List[schemas.EntityResponse])
def get_extracted_entities(workspace_id: UUID, db: Session = Depends(get_db)):
    # Validate workspace
    workspace = db.query(models.Workspace).filter(models.Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace with ID {workspace_id} not found."
        )
    return db.query(models.ExtractedEntity).filter(
        models.ExtractedEntity.workspace_id == workspace_id
    ).order_by(models.ExtractedEntity.entity_type, models.ExtractedEntity.value).all()

@router.post("/{workspace_id}/entities", status_code=status.HTTP_200_OK)
def trigger_entity_extraction(workspace_id: UUID, db: Session = Depends(get_db)):
    # 1. Validate workspace
    workspace = db.query(models.Workspace).filter(models.Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace with ID {workspace_id} not found."
        )

    # 2. Get all uploaded documents
    documents = db.query(models.UploadedDocument).filter(
        models.UploadedDocument.workspace_id == workspace_id
    ).all()
    if not documents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No documents found in this workspace."
        )

    # 3. Collect texts
    docs_text = [doc.raw_text for doc in documents if doc.raw_text]
    if not docs_text or all(not text.strip() for text in docs_text):
         raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded documents contain no readable text."
        )

    # 4. Trigger Named Entity Extraction
    try:
        entities_data = extract_entities_from_text(docs_text)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Entity extraction failed: {str(e)}"
        )

    # 5. Clear previous entities
    db.query(models.ExtractedEntity).filter(
        models.ExtractedEntity.workspace_id == workspace_id
    ).delete()

    # 6. Insert new entities
    new_records = []
    default_doc_id = documents[0].id
    for entity_type, values in entities_data.items():
        for val in values:
            record = models.ExtractedEntity(
                workspace_id=workspace_id,
                document_id=default_doc_id,
                entity_type=entity_type,
                value=val
            )
            new_records.append(record)

    if new_records:
        db.add_all(new_records)
        db.commit()

    return {
        "status": "success",
        "message": f"Successfully extracted {len(new_records)} entities.",
        "counts": {k: len(v) for k, v in entities_data.items()}
    }


@router.post("/{workspace_id}/requirements/rank", response_model=List[schemas.RankedRequirementResponse])
def get_ranked_requirements(workspace_id: UUID, request: schemas.RerankRequest, db: Session = Depends(get_db)):
    # 1. Validate workspace
    workspace = db.query(models.Workspace).filter(models.Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace with ID {workspace_id} not found."
        )
        
    # 2. Query all requirements for the workspace
    requirements = db.query(models.ExtractedRequirement).filter(
        models.ExtractedRequirement.workspace_id == workspace_id
    ).all()
    
    if not requirements:
        return []
        
    # 3. Convert to list of dicts for the ranker
    req_dicts = []
    for r in requirements:
        req_dicts.append({
            "id": r.id,
            "workspace_id": r.workspace_id,
            "document_id": r.document_id,
            "req_number": r.req_number,
            "category": r.category,
            "description": r.description,
            "priority": r.priority,
            "page_number": r.page_number,
            "created_at": r.created_at
        })
        
    # 4. Rerank using BGE reranker
    try:
        ranked_results = rank_requirements(request.query, req_dicts)
        return ranked_results
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"BGE reranking failed: {str(e)}"
        )


