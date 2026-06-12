from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List

from database import get_db
import models
import schemas
from services.compliance_service import run_workspace_compliance_validation

router = APIRouter(prefix="/api/workspaces", tags=["Compliance"])

@router.post("/{workspace_id}/compliance/validate", status_code=status.HTTP_200_OK)
def trigger_compliance_validation(workspace_id: UUID, db: Session = Depends(get_db)):
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
        num_validated = run_workspace_compliance_validation(db, workspace_id)
        return {
            "status": "success",
            "message": f"Successfully completed compliance audit for {num_validated} requirements.",
            "count": num_validated
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Compliance validation failed: {str(e)}"
        )

@router.get("/{workspace_id}/compliance/results", response_model=List[schemas.ComplianceResultResponse])
def get_compliance_results(workspace_id: UUID, db: Session = Depends(get_db)):
    # 1. Validate workspace
    workspace = db.query(models.Workspace).filter(models.Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace with ID {workspace_id} not found."
        )
        
    # 2. Query results joined with requirements to filter by workspace
    results = db.query(models.ComplianceResult).join(
        models.ExtractedRequirement,
        models.ComplianceResult.requirement_id == models.ExtractedRequirement.id
    ).filter(
        models.ExtractedRequirement.workspace_id == workspace_id
    ).all()
    
    return results
