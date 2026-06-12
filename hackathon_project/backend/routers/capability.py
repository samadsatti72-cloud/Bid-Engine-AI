from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, cast, String
from uuid import UUID
from typing import List, Optional
import os
import re
import uuid

from database import get_db
import models
import schemas
from services.capability_service import chunk_text, extract_metadata_from_chunk
from services.parser import parse_document

# ── Security constants ────────────────────────────────────────────────────────
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt"}
MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB

router = APIRouter(prefix="/api/capabilities", tags=["Capability Library"])

# The 50 preloaded project and certification records provided by the user
CAPABILITY_SEED_DATA = """CAP-001	Cybersecurity	Project 1: Cybersecurity deployment for client	ISO 27001	2023	PKR 15M	34	International
CAP-002	ERP Implementation	Project 2: ERP Implementation deployment for client	N/A	2021	PKR 159M	14	Federal Govt
CAP-003	Road Construction	Project 3: Road Construction deployment for client	ISO 27001	2020	PKR 177M	32	Federal Govt
CAP-004	Bridge Engineering	Project 4: Bridge Engineering deployment for client	N/A	2025	PKR 73M	24	Federal Govt
CAP-005	Fleet Management	Project 5: Fleet Management deployment for client	PMP	2022	PKR 137M	26	International
CAP-006	Hospital IT	Project 6: Hospital IT deployment for client	CMMI L3	2020	PKR 154M	19	International
CAP-007	Medical Equipment	Project 7: Medical Equipment deployment for client	ISO 27001	2022	PKR 94M	19	Private Sector
CAP-008	Solar Energy	Project 8: Solar Energy deployment for client	CMMI L3	2024	PKR 31M	33	Provincial Govt
CAP-009	Network Design	Project 9: Network Design deployment for client	CMMI L3	2022	PKR 182M	21	Private Sector
CAP-010	LMS Development	Project 10: LMS Development deployment for client	N/A	2022	PKR 199M	23	Federal Govt
CAP-011	Mobile Banking	Project 11: Mobile Banking deployment for client	CE Mark	2019	PKR 85M	14	Private Sector
CAP-012	Cloud Infrastructure	Project 12: Cloud Infrastructure deployment for client	ISO 27001	2025	PKR 108M	33	Federal Govt
CAP-013	Cybersecurity	Project 13: Cybersecurity deployment for client	N/A	2025	PKR 143M	20	International
CAP-014	ERP Implementation	Project 14: ERP Implementation deployment for client	ISO 27001	2020	PKR 137M	17	International
CAP-015	Road Construction	Project 15: Road Construction deployment for client	N/A	2022	PKR 199M	7	Provincial Govt
CAP-016	Bridge Engineering	Project 16: Bridge Engineering deployment for client	CMMI L3	2023	PKR 38M	35	Private Sector
CAP-017	Fleet Management	Project 17: Fleet Management deployment for client	CE Mark	2024	PKR 129M	9	Federal Govt
CAP-018	Hospital IT	Project 18: Hospital IT deployment for client	N/A	2023	PKR 66M	28	Provincial Govt
CAP-019	Medical Equipment	Project 19: Medical Equipment deployment for client	CMMI L3	2023	PKR 8M	23	International
CAP-020	Solar Energy	Project 20: Solar Energy deployment for client	ISO 27001	2020	PKR 34M	20	Federal Govt
CAP-021	Network Design	Project 21: Network Design deployment for client	N/A	2025	PKR 44M	21	Private Sector
CAP-022	LMS Development	Project 22: LMS Development deployment for client	ISO 9001	2024	PKR 74M	19	International
CAP-023	Mobile Banking	Project 23: Mobile Banking deployment for client	CE Mark	2020	PKR 121M	23	Provincial Govt
CAP-024	Cloud Infrastructure	Project 24: Cloud Infrastructure deployment for client	CE Mark	2020	PKR 158M	22	Provincial Govt
CAP-025	Cybersecurity	Project 25: Cybersecurity deployment for client	ISO 27001	2021	PKR 111M	16	Private Sector
CAP-026	ERP Implementation	Project 26: ERP Implementation deployment for client	ISO 27001	2021	PKR 190M	15	International
CAP-027	Road Construction	Project 27: Road Construction deployment for client	PMP	2022	PKR 142M	21	Private Sector
CAP-028	Bridge Engineering	Project 28: Bridge Engineering deployment for client	CMMI L3	2023	PKR 200M	23	International
CAP-029	Fleet Management	Project 29: Fleet Management deployment for client	CE Mark	2021	PKR 53M	28	Provincial Govt
CAP-030	Hospital IT	Project 30: Hospital IT deployment for client	ISO 9001	2022	PKR 64M	33	International
CAP-031	Medical Equipment	Project 31: Medical Equipment deployment for client	ISO 27001	2021	PKR 195M	21	International
CAP-032	Solar Energy	Project 32: Solar Energy deployment for client	CE Mark	2024	PKR 171M	10	International
CAP-033	Network Design	Project 33: Network Design deployment for client	ISO 27001	2020	PKR 133M	36	Private Sector
CAP-034	LMS Development	Project 34: LMS Development deployment for client	ISO 27001	2025	PKR 117M	9	International
CAP-035	Mobile Banking	Project 35: Mobile Banking deployment for client	ISO 27001	2024	PKR 41M	19	Provincial Govt
CAP-036	Cloud Infrastructure	Project 36: Cloud Infrastructure deployment for client	ISO 27001	2022	PKR 72M	16	International
CAP-037	Cybersecurity	Project 37: Cybersecurity deployment for client	N/A	2019	PKR 89M	33	International
CAP-038	ERP Implementation	Project 38: ERP Implementation deployment for client	CMMI L3	2024	PKR 188M	34	International
CAP-039	Road Construction	Project 39: Road Construction deployment for client	ISO 9001	2019	PKR 163M	8	Provincial Govt
CAP-040	Bridge Engineering	Project 40: Bridge Engineering deployment for client	N/A	2024	PKR 78M	13	Federal Govt
CAP-041	Fleet Management	Project 41: Fleet Management deployment for client	CE Mark	2019	PKR 199M	26	Federal Govt
CAP-042	Hospital IT	Project 42: Hospital IT deployment for client	CE Mark	2020	PKR 182M	15	Federal Govt
CAP-043	Medical Equipment	Project 43: Medical Equipment deployment for client	ISO 27001	2021	PKR 19M	15	Private Sector
CAP-044	Solar Energy	Project 44: Solar Energy deployment for client	CMMI L3	2022	PKR 42M	13	International
CAP-045	Network Design	Project 45: Network Design deployment for client	ISO 9001	2024	PKR 51M	11	Provincial Govt
CAP-046	LMS Development	Project 46: LMS Development deployment for client	ISO 27001	2023	PKR 102M	25	Provincial Govt
CAP-047	Mobile Banking	Project 47: Mobile Banking deployment for client	CE Mark	2023	PKR 41M	13	International
CAP-048	Cloud Infrastructure	Project 48: Cloud Infrastructure deployment for client	N/A	2021	PKR 122M	14	Federal Govt
CAP-049	Cybersecurity	Project 49: Cybersecurity deployment for client	CE Mark	2021	PKR 178M	23	Provincial Govt
CAP-050	ERP Implementation	Project 50: ERP Implementation deployment for client	ISO 27001	2022	PKR 93M	24	Private Sector"""

@router.post("/seed", status_code=status.HTTP_201_CREATED)
def seed_capability_library(
    confirm: bool = Query(False, description="Must be true to execute this destructive operation."),
    db: Session = Depends(get_db)
):
    """Wipes active library items and seeds the 50 past projects & certifications."""
    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This operation will wipe all existing capability records. Pass ?confirm=true to proceed."
        )
    try:
        # 1. Clear previous records
        db.query(models.CapabilityLibrary).delete()
        
        # 2. Parse TSV records
        lines = CAPABILITY_SEED_DATA.strip().split("\n")
        records_to_insert = []
        
        for line in lines:
            parts = line.split("\t")
            if len(parts) < 8:
                continue
            
            cap_id, domain, summary, certification, year_completed, val, dur, client_type = parts
            
            # Skip header row if present
            if cap_id.lower() == "cap id":
                continue
                
            try:
                year = int(year_completed)
            except ValueError:
                year = 2026
                
            # Double-indexing Strategy:
            # 1. Store the Case Study/Project Summary
            metadata = {
                "cap_id": cap_id,
                "document_type": "case_study",
                "domain": domain.lower(),
                "year": year,
                "contract_value": val,
                "duration_months": int(dur) if dur.isdigit() else None,
                "client_type": client_type
            }
            
            project_record = models.CapabilityLibrary(
                title=f"Project Summary: {cap_id} ({domain})",
                category="Case Study",
                content=f"Project Summary: {summary}\nClient Type: {client_type}\nContract Value: {val}\nDuration: {dur} months\nYear Completed: {year_completed}",
                additional_metadata=metadata,
                vector_id=f"vec-{cap_id}-summary"
            )
            records_to_insert.append(project_record)
            
            # 2. Store the Certification separately if it is not N/A
            if certification.upper() != "N/A" and certification.strip() != "":
                cert_metadata = {
                    "cap_id": cap_id,
                    "document_type": "certification",
                    "domain": domain.lower(),
                    "year": year,
                    "certification": certification
                }
                
                cert_record = models.CapabilityLibrary(
                    title=f"Certification: {certification} ({cap_id})",
                    category="Certification",
                    content=f"Company Certification: The company successfully possessed and maintained the '{certification}' certification in {year_completed} for the '{domain}' domain under project '{cap_id}'.",
                    additional_metadata=cert_metadata,
                    vector_id=f"vec-{cap_id}-cert"
                )
                records_to_insert.append(cert_record)

        if records_to_insert:
            db.add_all(records_to_insert)
            db.commit()
            
        return {
            "status": "success",
            "message": f"Successfully seeded {len(records_to_insert)} capability library items (from 50 source records).",
            "count": len(records_to_insert)
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to seed capability database: {str(e)}"
        )

@router.post("/ingest", response_model=List[schemas.CapabilityResponse], status_code=status.HTTP_201_CREATED)
async def ingest_capability_document(
    category: str,  # "Case Study", "Certification", "CV", "Company Profile", etc.
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Ingests custom corporate files, chunks them, extracts metadata using LLM, and stores them."""
    # 1. Read file bytes
    try:
        contents = await file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not read uploaded file: {str(e)}"
        )

    filename = os.path.basename(file.filename or "upload")
    filename = re.sub(r"[^\w.\-]", "_", filename) or "upload"

    # Validate extension
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"File type '{ext}' is not supported. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Enforce file size limit
    if len(contents) > MAX_FILE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the {MAX_FILE_BYTES // (1024*1024)} MB limit."
        )
    
    # 2. Parse raw text
    try:
        raw_text = parse_document(filename, contents)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error parsing document content: {str(e)}"
        )

    if not raw_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document contains no readable text."
        )

    # 3. Chunk text intelligently
    chunks = chunk_text(raw_text, chunk_size=1000, overlap=200)
    records_to_insert = []
    
    # 4. Process each chunk and extract metadata via local Ollama LLM
    for idx, chunk in enumerate(chunks):
        title = f"{os.path.splitext(filename)[0]} - Chunk {idx + 1}"
        
        # Extract metadata
        meta = extract_metadata_from_chunk(chunk)
        # Force document type overwrite if categorizing manually
        if category:
            meta["document_type"] = category.lower().replace(" ", "_")

        db_item = models.CapabilityLibrary(
            title=title,
            category=category or "Other",
            content=chunk,
            additional_metadata=meta,
            vector_id=f"vec-{uuid.uuid4()}"
        )
        records_to_insert.append(db_item)

    if records_to_insert:
        db.add_all(records_to_insert)
        db.commit()
        for record in records_to_insert:
            db.refresh(record)

    return records_to_insert

@router.get("", response_model=List[schemas.CapabilityResponse])
def get_capabilities(
    category: Optional[str] = None,
    domain: Optional[str] = None,
    year: Optional[int] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Retrieves capability library records with keyword search and metadata filters."""
    query = db.query(models.CapabilityLibrary)
    
    # Category filter
    if category and category != "ALL":
        query = query.filter(models.CapabilityLibrary.category == category)
        
    # Metadata filters
    if domain and domain != "ALL":
        query = query.filter(
            cast(models.CapabilityLibrary.additional_metadata['domain'], String).ilike(f"%{domain}%")
        )
        
    if year:
        # Cast JSONB year to integer string check or equivalent
        query = query.filter(
            cast(models.CapabilityLibrary.additional_metadata['year'], String) == str(year)
        )
        
    # Keyword search across title, content, or metadata
    if search:
        search_filter = or_(
            models.CapabilityLibrary.title.ilike(f"%{search}%"),
            models.CapabilityLibrary.content.ilike(f"%{search}%"),
            cast(models.CapabilityLibrary.additional_metadata, String).ilike(f"%{search}%")
        )
        query = query.filter(search_filter)

    return query.order_by(models.CapabilityLibrary.created_at.desc()).all()

@router.delete("/reset")
def clear_capability_library(
    confirm: bool = Query(False, description="Must be true to execute this destructive operation."),
    db: Session = Depends(get_db)
):
    """Clears all records in the capability library."""
    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This operation will permanently delete all capability records. Pass ?confirm=true to proceed."
        )
    try:
        num_deleted = db.query(models.CapabilityLibrary).delete()
        db.commit()
        return {
            "status": "success",
            "message": f"Successfully cleared {num_deleted} capability library items."
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear capability database: {str(e)}"
        )
