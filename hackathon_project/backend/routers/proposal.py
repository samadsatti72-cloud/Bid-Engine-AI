from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List

from database import get_db
import models
import schemas
from services.proposal_service import (
    initialize_default_proposal_sections,
    generate_proposal_section_draft,
    generate_full_workspace_proposal
)

router = APIRouter(prefix="/api/workspaces", tags=["Proposal Drafting"])

@router.get("/{workspace_id}/proposal/sections", response_model=List[schemas.ProposalSectionResponse])
def get_proposal_sections(workspace_id: UUID, db: Session = Depends(get_db)):
    # 1. Validate workspace
    workspace = db.query(models.Workspace).filter(models.Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace with ID {workspace_id} not found."
        )
        
    # 2. Auto-initialize default sections if none exist
    initialize_default_proposal_sections(db, workspace_id)
    
    # 3. Retrieve all sections
    return db.query(models.ProposalSection).filter(
        models.ProposalSection.workspace_id == workspace_id
    ).order_by(models.ProposalSection.section_code, models.ProposalSection.created_at).all()

@router.post("/{workspace_id}/proposal/sections", response_model=schemas.ProposalSectionResponse, status_code=status.HTTP_201_CREATED)
def create_proposal_section(workspace_id: UUID, section: schemas.ProposalSectionCreate, db: Session = Depends(get_db)):
    # 1. Validate workspace
    workspace = db.query(models.Workspace).filter(models.Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace with ID {workspace_id} not found."
        )
        
    # 2. Create record
    db_section = models.ProposalSection(
        workspace_id=workspace_id,
        section_title=section.section_title,
        section_code=section.section_code,
        prompt_instruction=section.prompt_instruction,
        status="DRAFT"
    )
    db.add(db_section)
    db.commit()
    db.refresh(db_section)
    return db_section

@router.put("/{workspace_id}/proposal/sections/{section_id}", response_model=schemas.ProposalSectionResponse)
def update_proposal_section(workspace_id: UUID, section_id: UUID, update_data: schemas.ProposalSectionUpdate, db: Session = Depends(get_db)):
    # 1. Validate workspace
    workspace = db.query(models.Workspace).filter(models.Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace with ID {workspace_id} not found."
        )
        
    # 2. Fetch section
    db_section = db.query(models.ProposalSection).filter(
        models.ProposalSection.id == section_id,
        models.ProposalSection.workspace_id == workspace_id
    ).first()
    
    if not db_section:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Proposal section with ID {section_id} not found in this workspace."
        )
        
    # 3. Update fields
    if update_data.section_title is not None:
        db_section.section_title = update_data.section_title
    if update_data.section_code is not None:
        db_section.section_code = update_data.section_code
    if update_data.prompt_instruction is not None:
        db_section.prompt_instruction = update_data.prompt_instruction
    if update_data.draft_content is not None:
        db_section.draft_content = update_data.draft_content
    if update_data.status is not None:
        db_section.status = update_data.status
        
    db.commit()
    db.refresh(db_section)
    return db_section

@router.post("/{workspace_id}/proposal/generate_full", status_code=status.HTTP_200_OK)
def trigger_full_proposal_generation(workspace_id: UUID, db: Session = Depends(get_db)):
    # 1. Validate workspace
    workspace = db.query(models.Workspace).filter(models.Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace with ID {workspace_id} not found."
        )
        
    # 2. Get requirements count
    req_count = db.query(models.ExtractedRequirement).filter(
        models.ExtractedRequirement.workspace_id == workspace_id
    ).count()
    
    if req_count == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No requirements extracted for this workspace. Please extract requirements first."
        )
        
    try:
        compiled_draft = generate_full_workspace_proposal(db, workspace_id)
        return {
            "status": "success",
            "message": "Full proposal response compiled successfully!",
            "draft": compiled_draft
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Full proposal generation failed: {str(e)}"
        )
