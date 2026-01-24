"""Custom exceptions for graph processing operations."""


class GraphProcessingError(Exception):
    """Base exception for graph processing failures.

    This exception is raised when there's a general error during
    graph processing that doesn't fit into more specific categories.
    """

    pass


class LLMProviderNotConfiguredError(GraphProcessingError):
    """Raised when user has no LLM provider configured.

    Graph processing requires an LLM provider to extract entities
    from documents. This exception indicates the user needs to
    configure a provider before processing can continue.
    """

    def __init__(self, user_id: str):
        self.user_id = user_id
        super().__init__(
            f"No LLM provider configured for user {user_id}. "
            "Please configure an LLM provider to enable graph processing."
        )


class OntologyExtractionError(GraphProcessingError):
    """Raised when LLM fails to extract entities from document.

    This can happen due to:
    - Invalid document content
    - LLM rate limiting
    - Network errors during extraction
    - Parsing errors in LLM response
    """

    def __init__(self, document_id: str, reason: str):
        self.document_id = document_id
        self.reason = reason
        super().__init__(
            f"Failed to extract entities from document {document_id}: {reason}"
        )


class GraphConnectionError(GraphProcessingError):
    """Raised when connection to FalkorDB fails.

    This can happen due to:
    - FalkorDB server is down
    - Network connectivity issues
    - Invalid credentials
    - Connection timeout
    """

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Failed to connect to FalkorDB: {reason}")


class OntologyValidationError(GraphProcessingError):
    """Raised when ontology validation fails.

    This can happen when:
    - Entity definitions have invalid attributes
    - Relations reference non-existent entities
    - Schema constraints are violated
    """

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Ontology validation failed: {reason}")


class UnsupportedDocumentTypeError(GraphProcessingError):
    """Raised when document type is not supported for graph processing.

    Currently supported types:
    - resume
    - job_description
    - cover_letter
    """

    def __init__(self, document_type: str):
        self.document_type = document_type
        super().__init__(
            f"Document type '{document_type}' is not supported for graph processing. "
            "Supported types: resume, job_description, cover_letter"
        )
