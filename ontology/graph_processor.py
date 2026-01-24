"""Document graph processing for extracting entities to FalkorDB.

This module provides the main integration with GraphRAG-SDK for
processing documents and storing entities in knowledge graphs.
"""

import logging
import time
from datetime import datetime
from typing import Optional
from uuid import UUID

from graphrag_sdk import KnowledgeGraph
from graphrag_sdk.source import Source_FromRawText

from configs.postgres import use_db_session
from configs.settings import get_settings
from models.document import DocumentType
from models.llm_provider import LLMProvider
from ontology.exceptions import (
    GraphConnectionError,
    GraphProcessingError,
    LLMProviderNotConfiguredError,
    OntologyExtractionError,
    UnsupportedDocumentTypeError,
)
from ontology.schemas import build_ontology
from ontology.schemas.constants import MAX_CONTENT_LENGTH, ONTOLOGY_VERSION
from services.graph_provider import (
    create_kg_model_config,
    validate_provider_for_graphrag,
)
from services.llm_provider import get_user_llm_provider

logger = logging.getLogger(__name__)

# Supported document types for graph processing
SUPPORTED_DOCUMENT_TYPES = {
    DocumentType.RESUME,
    DocumentType.JOB_DESCRIPTION,
    DocumentType.COVER_LETTER,
}

# Extraction instructions per document type
EXTRACTION_INSTRUCTIONS = {
    DocumentType.RESUME: """
Extract entities from this resume document. Guidelines:
- Person: Extract the person's name, email, phone, location, and professional summary
- Skills: Normalize to standard names (e.g., "Python" not "python3")
- Experience: Extract each job with company, position, dates, and achievements
- Education: Extract university, degree, field of study, and dates
- Certifications: Extract certification names and issuing organizations
- Projects: Extract project names, descriptions, and technologies used
- Use ISO date format (YYYY-MM or YYYY-MM-DD) when possible
- Mark current positions with is_current: true
""",
    DocumentType.JOB_DESCRIPTION: """
Extract entities from this job posting. Guidelines:
- JobPosting: Extract job title, description, location, salary range, employment type
- Skills: Normalize required skills to standard names (e.g., "Python" not "python3")
- Requirements: Extract must-have and nice-to-have requirements with years of experience
- Responsibilities: Extract key job duties and responsibilities
- Company: Extract company name and normalize it
- Position: Extract the job title/position
""",
    DocumentType.COVER_LETTER: """
Extract entities from this cover letter. Guidelines:
- CoverLetter: Extract target company and position mentioned
- Person: Extract the author's name if mentioned
- Skills: Extract skills the author highlights, normalized to standard names
- Company: Extract the target company name, normalized
- Position: Extract the target position
""",
}


class DocumentGraphProcessor:
    """Processes documents and extracts entities to FalkorDB knowledge graph.

    This class handles the complete workflow of:
    1. Connecting to FalkorDB with user-specific graph
    2. Configuring the LLM model for extraction
    3. Processing document content through GraphRAG-SDK
    4. Tracking processing results and errors

    Attributes:
        user_id: The user who owns the documents
        provider: The user's configured LLM provider
        settings: Application settings
    """

    def __init__(
        self,
        user_id: str,
        provider: LLMProvider,
    ):
        """Initialize the document graph processor.

        Args:
            user_id: User ID for graph namespacing
            provider: User's LLM provider configuration
        """
        self.user_id = user_id
        self.provider = provider
        self.settings = get_settings()
        self._kg: Optional[KnowledgeGraph] = None
        self._initialized = False

    @property
    def graph_name(self) -> str:
        """Generate user-specific graph name."""
        return f"resume_kg_{self.user_id}"

    def initialize(self) -> None:
        """Initialize the knowledge graph connection and ontology.

        This method:
        1. Validates the LLM provider configuration
        2. Creates the model configuration for GraphRAG
        3. Builds the ontology schema
        4. Connects to FalkorDB and creates/loads the graph

        Raises:
            GraphProcessingError: If provider validation fails
            GraphConnectionError: If FalkorDB connection fails
        """
        if self._initialized:
            return

        # Validate provider
        is_valid, error = validate_provider_for_graphrag(self.provider)
        if not is_valid:
            raise GraphProcessingError(f"Invalid LLM provider: {error}")

        try:
            # Create model config from user's provider
            model_config = create_kg_model_config(self.provider)

            # Build ontology
            ontology = build_ontology()

            # Initialize KnowledgeGraph
            # GraphRAG-SDK uses synchronous FalkorDB client
            self._kg = KnowledgeGraph(
                name=self.graph_name,
                model_config=model_config,
                ontology=ontology,
                host=self.settings.FALKORDB_HOST,
                port=self.settings.FALKORDB_PORT,
                username=self.settings.FALKORDB_USERNAME or None,
                password=self.settings.FALKORDB_PASSWORD or None,
            )

            self._initialized = True
            logger.info(f"Initialized KnowledgeGraph: {self.graph_name}")

        except Exception as e:
            logger.error(f"Failed to initialize KnowledgeGraph: {e}")
            raise GraphConnectionError(str(e))

    def process_document(
        self,
        document_id: UUID,
        markdown_content: str,
        document_type: DocumentType,
    ) -> tuple[str, str]:
        """Process a document and extract entities to the graph.

        This method:
        1. Creates a source from markdown content
        2. Gets extraction instructions for the document type
        3. Processes through GraphRAG-SDK
        4. Adds a Document node to track the source
        5. Returns the graph node ID and ontology version

        Args:
            document_id: UUID of the document being processed
            markdown_content: Parsed markdown content from the document
            document_type: Type of document (resume, job_description, cover_letter)

        Returns:
            tuple: (graph_node_id, ontology_version)

        Raises:
            RuntimeError: If processor not initialized
            UnsupportedDocumentTypeError: If document type not supported
            OntologyExtractionError: If extraction fails
        """
        if not self._kg:
            raise RuntimeError(
                "KnowledgeGraph not initialized. Call initialize() first."
            )

        if document_type not in SUPPORTED_DOCUMENT_TYPES:
            raise UnsupportedDocumentTypeError(document_type.value)

        start_time = time.time()

        # Truncate content if needed
        content = markdown_content[:MAX_CONTENT_LENGTH]

        # Get extraction instructions for this document type
        instructions = EXTRACTION_INSTRUCTIONS.get(document_type, "")

        try:
            # Create source from markdown content
            source = Source_FromRawText(text=content, instruction=instructions)

            # Process through GraphRAG-SDK
            # This is synchronous - OK in TaskIQ worker
            self._kg.process_sources(
                sources=[source],
                instructions=instructions,
                hide_progress=True,  # Don't show progress bar in background task
            )

            # Check for failed documents
            if self._kg.failed_documents:
                logger.warning(
                    f"Some content failed to process for document {document_id}: "
                    f"{self._kg.failed_documents}"
                )

            # Add Document node to track source
            self._add_document_node(document_id, document_type)

            # Generate node ID
            graph_node_id = f"{self.graph_name}:{document_id}"

            duration_ms = int((time.time() - start_time) * 1000)
            logger.info(
                "Graph processing completed",
                extra={
                    "document_id": str(document_id),
                    "user_id": self.user_id,
                    "document_type": document_type.value,
                    "duration_ms": duration_ms,
                    "ontology_version": ONTOLOGY_VERSION,
                    "content_length": len(content),
                },
            )

            return graph_node_id, ONTOLOGY_VERSION

        except Exception as e:
            logger.error(
                f"Error processing document {document_id} to graph: {e}",
                extra={
                    "document_id": str(document_id),
                    "user_id": self.user_id,
                    "document_type": document_type.value,
                    "error": str(e),
                },
            )
            raise OntologyExtractionError(str(document_id), str(e))

    def _add_document_node(
        self,
        document_id: UUID,
        document_type: DocumentType,
    ) -> None:
        """Add a Document node to track the source document.

        Args:
            document_id: UUID of the source document
            document_type: Type of the document
        """
        try:
            self._kg.add_node(
                entity="Document",
                attributes={
                    "document_id": str(document_id),
                    "user_id": self.user_id,
                    "document_type": document_type.value,
                    "processed_at": datetime.utcnow().isoformat(),
                    "ontology_version": ONTOLOGY_VERSION,
                },
            )
        except Exception as e:
            # Don't fail the whole process if Document node fails
            logger.warning(f"Failed to add Document node for {document_id}: {e}")


async def convert_to_graph_ontology(
    document_id: UUID,
    markdown_content: str,
    document_type: DocumentType,
    user_id: str,
) -> tuple[Optional[str], Optional[str]]:
    """Convert parsed markdown to graph/ontology using GraphRAG-SDK.

    This is the main entry point for graph processing, called from
    the document parser task.

    Args:
        document_id: UUID of the document being processed
        markdown_content: Parsed markdown content from the document
        document_type: Type of document (should be resume, or etc)
        user_id: User ID for fetching LLM provider settings

    Returns:
        tuple: (graph_node_id, ontology_version) or (None, None) on failure
    """
    settings = get_settings()

    # Check if GraphRAG is enabled
    if not getattr(settings, "GRAPHRAG_ENABLED", True):
        logger.info("GraphRAG processing is disabled")
        return None, None

    # Skip non-supported document types
    if document_type not in SUPPORTED_DOCUMENT_TYPES:
        logger.info(
            f"Skipping graph conversion for unsupported document type: "
            f"{document_type.value}"
        )
        return None, None

    try:
        # Get user's LLM provider
        async with use_db_session() as session:
            provider = await get_user_llm_provider(session, user_id)

        if not provider:
            logger.warning(
                f"No LLM provider configured for user {user_id}, "
                "skipping graph processing"
            )
            return None, None

        # Create processor
        processor = DocumentGraphProcessor(
            user_id=user_id,
            provider=provider,
        )

        # Initialize (connects to FalkorDB, sets up ontology)
        # This is synchronous but fast
        processor.initialize()

        # Process document (synchronous operation)
        # GraphRAG-SDK is synchronous - OK in TaskIQ worker
        graph_node_id, ontology_version = processor.process_document(
            document_id=document_id,
            markdown_content=markdown_content,
            document_type=document_type,
        )

        logger.info(
            f"Successfully processed document {document_id} to graph. "
            f"Node ID: {graph_node_id}, Ontology: {ontology_version}"
        )

        return graph_node_id, ontology_version

    except LLMProviderNotConfiguredError as e:
        logger.warning(str(e))
        return None, None

    except (GraphConnectionError, OntologyExtractionError) as e:
        logger.error(f"Graph processing error for document {document_id}: {e}")
        return None, None

    except Exception as e:
        logger.error(
            f"Unexpected error converting document {document_id} to graph: {e}"
        )
        return None, None
