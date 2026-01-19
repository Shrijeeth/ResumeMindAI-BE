"""Document parsing task for TaskIQ.

Orchestrates the full document processing workflow:
1. Upload to S3
2. Classify document type using Agno AI
3. Parse to markdown using MarkItDown
4. Store results in database
5. (Placeholder) Convert to graph/ontology
"""

import logging
import tempfile
from datetime import datetime
from pathlib import Path
from uuid import UUID

from markitdown import MarkItDown
from sqlalchemy import select

from agents.document_classifier import classify_document
from configs import get_settings
from configs.lifecycle import worker_context
from configs.postgres import use_db_session
from configs.s3 import get_s3_client
from models.document import Document, DocumentStatus, DocumentType
from tasks import broker

logger = logging.getLogger(__name__)


async def update_document_status(
    document_id: UUID,
    status: DocumentStatus,
    error_message: str | None = None,
    **kwargs,
) -> None:
    """Update document status in database."""
    async with use_db_session() as session:
        result = await session.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()
        if document:
            document.status = status.value
            if error_message:
                document.error_message = error_message
            for key, value in kwargs.items():
                if hasattr(document, key):
                    setattr(document, key, value)
            if status == DocumentStatus.COMPLETED:
                document.processed_at = datetime.utcnow()


async def upload_to_s3(
    file_content: bytes,
    user_id: str,
    document_id: str,
    filename: str,
    file_type: str,
) -> str:
    """Upload file to S3 and return the S3 key."""
    settings = get_settings()
    s3_client = await get_s3_client()

    # Generate S3 key: users/{user_id}/documents/{document_id}/{filename}
    s3_key = f"users/{user_id}/documents/{document_id}/{filename}"

    content_type_map = {
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # noqa: E501
        "txt": "text/plain",
        "md": "text/markdown",
    }
    content_type = content_type_map.get(file_type, "application/octet-stream")

    async with s3_client as client:
        await client.put_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=s3_key,
            Body=file_content,
            ContentType=content_type,
        )

    logger.info(f"Uploaded file to S3: {s3_key}")
    return s3_key


def parse_document_to_markdown(
    file_content: bytes, filename: str, file_type: str
) -> str:
    """Parse document to markdown using MarkItDown."""
    md = MarkItDown()

    # MarkItDown requires a file path, so we use a temp file
    suffix = f".{file_type}"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp_file:
        tmp_file.write(file_content)
        tmp_path = tmp_file.name

    try:
        result = md.convert(tmp_path)
        markdown_content = result.markdown
        logger.info(f"Parsed document to markdown: {len(markdown_content)} chars")
        return markdown_content
    finally:
        # Clean up temp file
        Path(tmp_path).unlink(missing_ok=True)


async def convert_to_graph_ontology(
    document_id: UUID,
    markdown_content: str,
    document_type: DocumentType,
) -> tuple[str | None, str | None]:
    """
    PLACEHOLDER: Convert parsed markdown to graph/ontology using graphsdk.

    This function will be implemented to:
    1. Create nodes in FalkorDB graph
    2. Extract entities from resume (skills, experience, education)
    3. Build relationships between entities
    4. Store ontology metadata

    Returns:
        tuple: (graph_node_id, ontology_version)
    """
    # TODO: Implement graph conversion using graphrag-sdk
    # from graphrag_sdk import KnowledgeGraph
    #
    # Example implementation outline:
    # kg = KnowledgeGraph(...)
    # entities = extract_entities(markdown_content, document_type)
    # node_id = await kg.add_document_node(document_id, entities)
    # relationships = build_relationships(entities)
    # await kg.add_relationships(relationships)

    logger.info(f"PLACEHOLDER: Graph conversion for document {document_id}")
    return None, None


@broker.task(
    task_name="parse_document",
    retry_on_error=True,
    max_retries=3,
)
async def parse_document_task(
    document_id: str,
    user_id: str,
) -> dict:
    """
    Main document processing task.

    Workflow:
    1. Fetch document metadata from DB
    2. Download file from S3
    3. Classify document type using Agno AI
    4. If valid (resume/job doc), parse with MarkItDown
    5. Store results in database
    6. (Placeholder) Convert to graph/ontology

    Args:
        document_id: UUID of the document record
        user_id: Owner's user ID

    Returns:
        Processing result with status and details
    """
    doc_uuid = UUID(document_id)

    async with worker_context(postgres=True, redis=True, s3=True, falkordb=False):
        try:
            logger.info(f"Starting document processing: {document_id}")
            await update_document_status(doc_uuid, DocumentStatus.VALIDATING)

            # Fetch document metadata from DB
            async with use_db_session() as session:
                result = await session.execute(
                    select(Document).where(Document.id == doc_uuid)
                )
                document = result.scalar_one_or_none()
                if not document:
                    raise ValueError(f"Document {document_id} not found")

                s3_key = document.s3_key
                s3_bucket = document.s3_bucket
                filename = document.original_filename
                file_type = document.file_type

            # Download file from S3
            s3_client = await get_s3_client()
            async with s3_client as client:
                response = await client.get_object(
                    Bucket=s3_bucket,
                    Key=s3_key,
                )
                file_content = await response["Body"].read()

            logger.info(f"Downloaded file from S3: {s3_key}")

            # Classify document type using Agno

            # For text-based classification, we need to parse first for MD/TXT
            # For PDF/DOCX, we do a preliminary parse for classification
            preliminary_text = ""
            if file_type in ("txt", "md"):
                preliminary_text = file_content.decode("utf-8", errors="ignore")[:5000]
            else:
                # Parse to get text for classification
                preliminary_text = parse_document_to_markdown(
                    file_content, filename, file_type
                )[:5000]  # First 5000 chars for classification

            classification_result = await classify_document(
                text_content=preliminary_text,
                filename=filename,
                user_id=user_id,
            )

            document_type = classification_result["document_type"]
            confidence = classification_result.get("confidence", 0.0)

            logger.info(
                f"Document classified as: {document_type} (confidence: {confidence})"
            )

            # Step 3: Validate document type
            valid_types = {
                DocumentType.RESUME.value,
                DocumentType.JOB_DESCRIPTION.value,
                DocumentType.COVER_LETTER.value,
            }

            if document_type not in valid_types:
                await update_document_status(
                    doc_uuid,
                    DocumentStatus.INVALID,
                    error_message=f"Document type '{document_type}' is not supported. "
                    "Only resumes, job descriptions, and cover letters are accepted.",
                    document_type=document_type,
                    classification_confidence=confidence,
                )
                return {
                    "status": "invalid",
                    "document_id": document_id,
                    "document_type": document_type,
                    "message": "Document is not a resume or job-related file",
                }

            # Step 4: Parse full document to markdown
            await update_document_status(
                doc_uuid,
                DocumentStatus.PARSING,
                document_type=document_type,
                classification_confidence=confidence,
            )

            # Full parsing (reuse preliminary if already done for txt/md)
            if file_type in ("txt", "md"):
                markdown_content = file_content.decode("utf-8", errors="ignore")
            else:
                markdown_content = parse_document_to_markdown(
                    file_content, filename, file_type
                )

            # Step 5: Placeholder for graph/ontology conversion
            graph_node_id, ontology_version = await convert_to_graph_ontology(
                document_id=doc_uuid,
                markdown_content=markdown_content,
                document_type=DocumentType(document_type),
            )

            # Step 6: Mark as completed
            await update_document_status(
                doc_uuid,
                DocumentStatus.COMPLETED,
                markdown_content=markdown_content,
                graph_node_id=graph_node_id,
                ontology_version=ontology_version,
            )

            logger.info(f"Document processing completed: {document_id}")

            return {
                "status": "completed",
                "document_id": document_id,
                "document_type": document_type,
                "markdown_length": len(markdown_content),
                "s3_key": s3_key,
            }

        except Exception as e:
            logger.error(f"Error processing document {document_id}: {e}")
            await update_document_status(
                doc_uuid,
                DocumentStatus.FAILED,
                error_message=str(e)[:1000],  # Truncate error message
            )
            raise  # Re-raise for TaskIQ retry handling
