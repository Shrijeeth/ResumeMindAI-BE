"""Ontology schema definitions for document processing.

This module combines all entity and relation definitions from
resume, job description, and cover letter schemas into a unified ontology.
"""

from graphrag_sdk import Ontology

from ontology.schemas.common import get_common_entities, get_common_relations
from ontology.schemas.constants import ONTOLOGY_VERSION
from ontology.schemas.cover_letter import (
    get_cover_letter_entities,
    get_cover_letter_relations,
)
from ontology.schemas.job_description import (
    get_job_description_entities,
    get_job_description_relations,
)
from ontology.schemas.resume import get_resume_entities, get_resume_relations


def build_ontology() -> Ontology:
    """Build the complete ontology with all entities and relations.

    Returns:
        Ontology: Complete ontology for document processing
    """
    entities = [
        *get_common_entities(),
        *get_resume_entities(),
        *get_job_description_entities(),
        *get_cover_letter_entities(),
    ]

    relations = [
        *get_common_relations(),
        *get_resume_relations(),
        *get_job_description_relations(),
        *get_cover_letter_relations(),
    ]

    return Ontology(entities=entities, relations=relations)


__all__ = [
    "build_ontology",
    "ONTOLOGY_VERSION",
]
