from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional, List, Any

# Base Schema Config
class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

# User Schemas
class UserBase(BaseSchema):
    email: str
    full_name: str

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: UUID
    created_at: datetime

# Workspace Schemas
class WorkspaceBase(BaseSchema):
    name: str
    description: Optional[str] = None

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
    section_title: str
    section_code: Optional[str] = None
    prompt_instruction: Optional[str] = None

class ProposalSectionCreate(ProposalSectionBase):
    pass

class ProposalSectionUpdate(BaseSchema):
    section_title: Optional[str] = None
    section_code: Optional[str] = None
    prompt_instruction: Optional[str] = None
    draft_content: Optional[str] = None
    status: Optional[str] = None

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



