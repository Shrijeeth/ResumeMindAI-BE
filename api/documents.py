"""Document upload and processing API endpoints."""

import logging
import time
from typing import Optional
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.document import (
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE_BYTES,
    DocumentListItem,
    DocumentOut,
    DocumentStatusResponse,
    DocumentUploadResponse,
)
from api.schemas.errors import ErrorCode, create_error_response
from api.schemas.graph import (
    GraphData,
    NodeType,
)
from configs import get_settings
from configs.postgres import get_db
from configs.s3 import get_s3_client
from middlewares.auth import get_current_user
from middlewares.idempotency import idempotent
from models.document import Document, DocumentStatus
from services.document import (
    create_document_record,
    delete_s3_file,
    get_document_by_id,
)
from services.graph_service import get_graph_data
from services.metrics import metrics
from tasks.document_parser import parse_document_task

logger = logging.getLogger(__name__)
router = APIRouter(tags=["documents"])


def validate_file_extension(filename: str) -> str:
    """Validate and return file extension."""
    if not filename or "." not in filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename - must have an extension",
        )
    extension = filename.rsplit(".", 1)[-1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "File type '{extension}' not supported. Allowed: "
                + ", ".join(ALLOWED_EXTENSIONS)
            ),
        )
    return extension


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
@idempotent()
async def upload_document(
    file: UploadFile = File(..., description="Resume or job-related document"),
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Upload a document for parsing.

    Accepts PDF, DOCX, TXT, or MD files. Returns immediately with a task_id
    for polling. Processing happens asynchronously via TaskIQ.
    """
    user_id = current_user.id

    # Validate file extension
    file_extension = validate_file_extension(file.filename)

    # Read file content
    file_content = await file.read()
    file_size = len(file_content)

    # Validate file size
    if file_size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                "File too large. Maximum size is "
                + f"{MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB"
            ),
        )

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file uploaded",
        )

    try:
        # Create document record in DB
        document = await create_document_record(
            session=session,
            user_id=user_id,
            filename=file.filename,
            file_type=file_extension,
            file_size=file_size,
        )

        # Upload to S3 first (before queueing task)
        settings = get_settings()
        s3_client = await get_s3_client()
        s3_key = f"users/{user_id}/documents/{document.id}/{file.filename}"

        content_type_map = {
            "pdf": "application/pdf",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # noqa: E501
            "txt": "text/plain",
            "md": "text/markdown",
        }
        content_type = content_type_map.get(file_extension, "application/octet-stream")

        async with s3_client as client:
            await client.put_object(
                Bucket=settings.S3_BUCKET_NAME,
                Key=s3_key,
                Body=file_content,
                ContentType=content_type,
            )

        logger.info(f"Uploaded file to S3: {s3_key}")

        # Update document with S3 info
        document.s3_key = s3_key
        document.s3_bucket = settings.S3_BUCKET_NAME
        await session.commit()

        logger.info("Queueing background task...")
        # Queue background task with S3 key instead of raw bytes
        task = await parse_document_task.kiq(
            document_id=str(document.id),
            user_id=user_id,
        )

        # Update document with task_id
        document.task_id = task.task_id
        await session.commit()

        logger.info(f"Document upload initiated: {document.id}, task: {task.task_id}")

        return DocumentUploadResponse(
            document_id=document.id,
            task_id=task.task_id,
            status=DocumentStatus.PENDING,
            message=(
                "Document upload initiated. Use the status endpoint to track progress."
            ),
        )

    except Exception as e:
        await session.rollback()
        logger.error(f"Error initiating document upload: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate document upload: {str(e)}",
        )


@router.get("/{document_id}/status", response_model=DocumentStatusResponse)
async def get_document_status(
    document_id: UUID,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Poll for document processing status.

    Returns current processing state, progress indicator, and any errors.
    """
    user_id = current_user.id

    document = await get_document_by_id(session, document_id, user_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    return DocumentStatusResponse.from_orm_model(document)


@router.get("/", response_model=list[DocumentListItem])
async def list_documents(
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """
    List user's documents with pagination and optional status filter.
    """
    user_id = current_user.id

    query = select(Document).where(Document.user_id == user_id)

    if status_filter:
        try:
            status_enum = DocumentStatus(status_filter)
            query = query.where(Document.status == status_enum.value)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Invalid status filter. Allowed: "
                    + ", ".join([s.value for s in DocumentStatus])
                ),
            )

    query = query.order_by(Document.created_at.desc()).offset(offset).limit(limit)

    result = await session.execute(query)
    documents = result.scalars().all()

    return [DocumentListItem.from_orm_model(doc) for doc in documents]


@router.get("/{document_id}", response_model=DocumentOut)
async def get_document(
    document_id: UUID,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Get full document details including parsed markdown content.
    """
    user_id = current_user.id

    document = await get_document_by_id(session, document_id, user_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    return DocumentOut.from_orm_model(document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Delete a document and its S3 file.
    """
    user_id = current_user.id

    document = await get_document_by_id(session, document_id, user_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    try:
        # Delete from S3 if s3_key exists
        if document.s3_key:
            await delete_s3_file(document.s3_key)

        await session.delete(document)
        await session.commit()
        logger.info(f"Document deleted: {document_id}")
    except Exception as e:
        await session.rollback()
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document",
        )


@router.get("/{document_id}/graph", response_model=GraphData)
async def get_document_graph(
    document_id: UUID,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    types: Optional[str] = Query(None, description="Filter by node types (CSV)"),
    max_nodes: int = Query(100, ge=1, le=100, description="Maximum nodes to return"),
    max_depth: Optional[int] = Query(
        None, ge=1, le=5, description="Maximum traversal depth"
    ),
):
    """
    Get knowledge graph data for a document.

    Returns nodes and links for the document's knowledge graph.
    Enforces a maximum of 100 nodes per response with deterministic downsampling.
    """
    user_id = current_user.id
    start_time = time.time()

    # Verify document exists and belongs to user
    document = await get_document_by_id(session, document_id, user_id)
    if not document:
        logger.warning(
            "Document not found or access denied",
            extra={
                "user_id": user_id,
                "document_id": str(document_id),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=create_error_response(
                code=ErrorCode.NOT_FOUND,
                message="Document not found",
            ).model_dump(),
        )

    # Validate node types if provided
    node_types = None
    if types:
        type_list = [t.strip() for t in types.split(",")]
        # Validate each type is a valid NodeType
        for node_type in type_list:
            try:
                NodeType(node_type)
            except ValueError:
                logger.warning(
                    "Invalid node type provided",
                    extra={
                        "user_id": user_id,
                        "document_id": str(document_id),
                        "invalid_type": node_type,
                    },
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=create_error_response(
                        code=ErrorCode.BAD_REQUEST,
                        message=f"Invalid node type: {node_type}",
                    ).model_dump(),
                )
        node_types = type_list

    try:
        # Get graph data
        graph_data = await get_graph_data(
            user_id=user_id,
            document_id=str(document_id),
            node_types=node_types,
            max_nodes=max_nodes,
            max_depth=max_depth,
        )

        duration_ms = int((time.time() - start_time) * 1000)

        # Log observability data
        logger.info(
            "Graph data retrieved successfully",
            extra={
                "user_id": user_id,
                "document_id": str(document_id),
                "node_count": len(graph_data.nodes),
                "link_count": len(graph_data.links),
                "duration_ms": duration_ms,
                "max_nodes": max_nodes,
                "node_types": node_types,
                "max_depth": max_depth,
                "downsampled": len(graph_data.nodes) == max_nodes,
            },
        )

        # Record metrics
        metrics.record_request(
            user_id=user_id,
            document_id=str(document_id),
            node_count=len(graph_data.nodes),
            link_count=len(graph_data.links),
            duration_ms=duration_ms,
            downsampled=len(graph_data.nodes) == max_nodes,
        )

        return graph_data

    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        logger.error(
            "Error retrieving graph data",
            extra={
                "user_id": user_id,
                "document_id": str(document_id),
                "duration_ms": duration_ms,
                "error": str(e),
            },
        )
        metrics.record_error(
            error_code="INTERNAL",
            user_id=user_id,
            document_id=str(document_id),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_error_response(
                code=ErrorCode.INTERNAL,
                message="Failed to retrieve graph data",
            ).model_dump(),
        )
