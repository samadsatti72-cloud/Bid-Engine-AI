from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List

from database import get_db
import models
import schemas

router = APIRouter(prefix="/api/workspaces", tags=["Workspaces"])

@router.post("", response_model=schemas.WorkspaceResponse, status_code=status.HTTP_201_CREATED)
def create_workspace(workspace: schemas.WorkspaceCreate, db: Session = Depends(get_db)):
    # Retrieve a default user to set as creator for referential integrity
    default_user = db.query(models.User).first()
    if not default_user:
        # Create a default user on the fly if none exists
        default_user = models.User(
            email="admin@example.com",
            password_hash="pbkdf2_sha256_dummy_hash",
            full_name="Default Bid Manager"
        )
        db.add(default_user)
        db.commit()
        db.refresh(default_user)
        
    db_workspace = models.Workspace(
        name=workspace.name,
        description=workspace.description,
        created_by=default_user.id
    )
    db.add(db_workspace)
    db.commit()
    db.refresh(db_workspace)
    return db_workspace

@router.get("", response_model=List[schemas.WorkspaceResponse])
def list_workspaces(db: Session = Depends(get_db)):
    return db.query(models.Workspace).order_by(models.Workspace.created_at.desc()).all()

@router.get("/{workspace_id}", response_model=schemas.WorkspaceResponse)
def get_workspace(workspace_id: UUID, db: Session = Depends(get_db)):
    workspace = db.query(models.Workspace).filter(models.Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace with ID {workspace_id} not found."
        )
    return workspace

@router.get("/{workspace_id}/documents", response_model=List[schemas.DocumentResponse])
def list_workspace_documents(workspace_id: UUID, db: Session = Depends(get_db)):
    # Check if workspace exists
    workspace = db.query(models.Workspace).filter(models.Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace with ID {workspace_id} not found."
        )
    return db.query(models.UploadedDocument).filter(models.UploadedDocument.workspace_id == workspace_id).all()
