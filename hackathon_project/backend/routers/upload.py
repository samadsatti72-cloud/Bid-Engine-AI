import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from uuid import UUID

from database import get_db
import models
import schemas
from services.parser import parse_document

router = APIRouter(prefix="/api/workspaces", tags=["Upload"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")

@router.post("/{workspace_id}/upload", response_model=schemas.DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    workspace_id: UUID, 
    file: UploadFile = File(...), 
    db: Session = Depends(get_db)
):
    # 1. Validate workspace
    workspace = db.query(models.Workspace).filter(models.Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace with ID {workspace_id} not found."
        )
        
    # 2. Read file bytes
    try:
        contents = await file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not read upload file: {str(e)}"
        )
        
    file_size = len(contents)
    filename = file.filename
    
    # 3. Parse raw text
    try:
        raw_text = parse_document(filename, contents)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error parsing document: {str(e)}"
        )
        
    # 4. Save file to disk
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    unique_filename = f"{uuid.uuid4()}_{filename}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    try:
        with open(file_path, "wb") as f:
            f.write(contents)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not save file to disk: {str(e)}"
        )
        
    # 5. Save document metadata & raw text to database
    db_document = models.UploadedDocument(
        workspace_id=workspace_id,
        filename=filename,
        file_path=file_path,
        file_type=file.content_type or os.path.splitext(filename)[1][1:],
        file_size=file_size,
        raw_text=raw_text
    )
    db.add(db_document)
    db.commit()
    db.refresh(db_document)
    
    return db_document
