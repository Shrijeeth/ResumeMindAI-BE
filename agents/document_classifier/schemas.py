"""Schemas for document classifier agent."""

from pydantic import BaseModel, Field

from models.document import DocumentType


class DocumentClassification(BaseModel):
    """Structured output model for document classification."""

    document_type: DocumentType = Field(
        description=(
            "Type of document: 'resume', 'job_description', 'cover_letter', or 'other'"
        )
    )
    confidence: float = Field(
        ge=0.0, le=1.0, description="Confidence score between 0 and 1"
    )
    reasoning: str = Field(
        description="Brief explanation of why this classification was chosen"
    )
