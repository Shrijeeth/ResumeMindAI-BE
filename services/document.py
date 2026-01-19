"""Document service layer for CRUD operations and S3 interactions."""

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from configs import get_settings
from configs.s3 import get_s3_client
from models.document import Document, DocumentStatus

logger = logging.getLogger(__name__)


async def create_document_record(
    session: AsyncSession,
    user_id: str,
    filename: str,
    file_type: str,
    file_size: int,
) -> Document:
    """Create a new document record in the database."""
    document = Document(
        user_id=user_id,
        original_filename=filename,
        file_type=file_type,
        file_size_bytes=file_size,
        status=DocumentStatus.PENDING.value,
    )
    session.add(document)
    await session.flush()
    await session.refresh(document)
    return document


async def get_document_by_id(
    session: AsyncSession,
    document_id: UUID,
    user_id: str,
) -> Optional[Document]:
    """Get a document by ID, ensuring it belongs to the user."""
    result = await session.execute(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def get_documents_by_user(
    session: AsyncSession,
    user_id: str,
    status: Optional[DocumentStatus] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Document]:
    """Get all documents for a user with optional status filter."""
    query = select(Document).where(Document.user_id == user_id)

    if status:
        query = query.where(Document.status == status.value)

    query = query.order_by(Document.created_at.desc()).offset(offset).limit(limit)

    result = await session.execute(query)
    return list(result.scalars().all())


async def update_document(
    session: AsyncSession,
    document: Document,
    **kwargs,
) -> Document:
    """Update document fields."""
    for key, value in kwargs.items():
        if hasattr(document, key):
            setattr(document, key, value)
    await session.commit()
    await session.refresh(document)
    return document


async def delete_document(
    session: AsyncSession,
    document: Document,
) -> None:
    """Delete a document record."""
    await session.delete(document)
    await session.commit()


async def delete_s3_file(s3_key: str) -> bool:
    """Delete a file from S3."""
    try:
        settings = get_settings()
        s3_client = await get_s3_client()

        async with s3_client as client:
            await client.delete_object(
                Bucket=settings.S3_BUCKET_NAME,
                Key=s3_key,
            )
        logger.info(f"Deleted S3 file: {s3_key}")
        return True
    except Exception as e:
        logger.error(f"Error deleting S3 file {s3_key}: {e}")
        return False


async def get_s3_presigned_url(
    s3_key: str,
    expiration: int = 3600,
) -> Optional[str]:
    """Generate a presigned URL for downloading a file from S3."""
    try:
        settings = get_settings()
        s3_client = await get_s3_client()

        async with s3_client as client:
            url = await client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": settings.S3_BUCKET_NAME,
                    "Key": s3_key,
                },
                ExpiresIn=expiration,
            )
        return url
    except Exception as e:
        logger.error(f"Error generating presigned URL for {s3_key}: {e}")
        return None
