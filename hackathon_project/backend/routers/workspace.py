from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List
import secrets

try:
    from passlib.context import CryptContext
    _pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    def _hash_password(plain: str) -> str:
        return _pwd_context.hash(plain)
except ImportError:
    import hashlib
    def _hash_password(plain: str) -> str:  # type: ignore[misc]
        return hashlib.sha256(plain.encode()).hexdigest()

from database import get_db
import models
import schemas

router = APIRouter(prefix="/api/workspaces", tags=["Workspaces"])

@router.post("", response_model=schemas.WorkspaceResponse, status_code=status.HTTP_201_CREATED)
def create_workspace(workspace: schemas.WorkspaceCreate, db: Session = Depends(get_db)):
    # Retrieve a default user to set as creator for referential integrity
    default_user = db.query(models.User).first()
    if not default_user:
        # Create a default system user on first run with a random strong password
        _initial_password = secrets.token_urlsafe(32)  # random, not reused
        default_user = models.User(
            email="system@bid-engine.internal",
            password_hash=_hash_password(_initial_password),
            full_name="System User"
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
