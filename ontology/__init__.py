"""Ontology module for GraphRAG-SDK integration.

This module provides the ontology definitions and graph processing
capabilities for extracting structured entities from documents.
"""

from ontology.exceptions import (
    GraphProcessingError,
    LLMProviderNotConfiguredError,
    OntologyExtractionError,
)
from ontology.graph_processor import (
    DocumentGraphProcessor,
    convert_to_graph_ontology,
)
from ontology.schemas import build_ontology
from ontology.schemas.constants import ONTOLOGY_VERSION

__all__ = [
    "ONTOLOGY_VERSION",
    "build_ontology",
    "convert_to_graph_ontology",
    "DocumentGraphProcessor",
    "GraphProcessingError",
    "LLMProviderNotConfiguredError",
    "OntologyExtractionError",
]
