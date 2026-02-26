"""Document domain model. Document identifier is user-scoped filename."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class DocumentFormat(str, Enum):
    PDF = "pdf"
    MARKDOWN = "markdown"


class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class Document(BaseModel):
    """Domain model for a user document. document_id = filename (user-scoped)."""

    filename: str = Field(..., description="User-scoped document identifier")
    owner_id: str = Field(..., description="OAuth subject / user identifier")
    format: DocumentFormat = Field(..., description="pdf | markdown")
    size_bytes: int = Field(..., ge=0, description="File size; max 25 MB")
    uploaded_at: datetime = Field(..., description="When the document was uploaded")
    processing_status: ProcessingStatus = Field(
        default=ProcessingStatus.PENDING,
        description="pending | processing | processed | failed",
    )
    processing_error: Optional[str] = Field(
        default=None,
        description="Present when status is failed",
    )
    processed_at: Optional[datetime] = Field(
        default=None,
        description="When embedding completed (status processed)",
    )

    class Config:
        use_enum_values = True
