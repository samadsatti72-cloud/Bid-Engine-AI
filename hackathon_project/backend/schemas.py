from pydantic import BaseModel, ConfigDict, field_validator, Field
from uuid import UUID
from datetime import datetime
from typing import Optional, List, Any
import re

# Base Schema Config
class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

# User Schemas
class UserBase(BaseSchema):
    email: str = Field(..., max_length=255)
    full_name: str = Field(..., max_length=255)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        pattern = r'^[\w.+\-]+@[\w\-]+\.[a-z]{2,}$'
        if not re.match(pattern, v, re.IGNORECASE):
            raise ValueError("Invalid email address format.")
        return v.lower().strip()

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)

class UserResponse(UserBase):
    id: UUID
    created_at: datetime

# Workspace Schemas
class WorkspaceBase(BaseSchema):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)

class WorkspaceCreate(WorkspaceBase):
    pass

class WorkspaceResponse(WorkspaceBase):
    id: UUID
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

# Document Schemas
class DocumentResponse(BaseSchema):
    id: UUID
    workspace_id: UUID
    filename: str
    file_type: str
    file_size: int
    raw_text: Optional[str] = None
    created_at: datetime


# Extracted Requirement Schemas
class RequirementResponse(BaseSchema):
    id: UUID
    workspace_id: UUID
    document_id: Optional[UUID] = None
    req_number: Optional[str] = None
    category: Optional[str] = None
    description: str
    priority: str
    page_number: Optional[int] = None
    created_at: datetime

# Extracted Entity Schemas
class EntityResponse(BaseSchema):
    id: UUID
    workspace_id: UUID
    document_id: Optional[UUID] = None
    entity_type: str
    value: str
    created_at: datetime


# Bid Score Schemas
class BidScoreResponse(BaseSchema):
    id: UUID
    workspace_id: UUID
    go_no_go: str
    go_no_go_reasoning: Optional[str] = None
    win_probability: Optional[float] = None
    score_breakdown: Optional[Any] = None
    created_at: datetime

# Capability Library Schemas
class CapabilityBase(BaseSchema):
    title: str
    category: str
    content: str
    additional_metadata: Optional[Any] = None

class CapabilityCreate(CapabilityBase):
    pass

class CapabilityResponse(CapabilityBase):
    id: UUID
    vector_id: Optional[str] = None
    created_at: datetime


# Compliance Result Schemas
class ComplianceResultResponse(BaseSchema):
    id: UUID
    requirement_id: UUID
    status: str
    reasoning: Optional[str] = None
    evidence: Optional[str] = None
    gap_analysis: Optional[str] = None
    confidence_score: Optional[int] = None
    created_at: datetime


# Proposal Section Schemas
class ProposalSectionBase(BaseSchema):
    section_title: str = Field(..., min_length=1, max_length=255)
    section_code: Optional[str] = Field(None, max_length=50)
    prompt_instruction: Optional[str] = Field(None, max_length=5000)

class ProposalSectionCreate(ProposalSectionBase):
    pass

class ProposalSectionUpdate(BaseSchema):
    section_title: Optional[str] = Field(None, min_length=1, max_length=255)
    section_code: Optional[str] = Field(None, max_length=50)
    prompt_instruction: Optional[str] = Field(None, max_length=5000)
    draft_content: Optional[str] = Field(None, max_length=50000)
    status: Optional[str] = Field(None, max_length=50)

class ProposalSectionResponse(ProposalSectionBase):
    id: UUID
    workspace_id: UUID
    draft_content: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime


class RerankRequest(BaseModel):
    query: str


class RankedRequirementResponse(RequirementResponse):
    score: float



