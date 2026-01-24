"""Common entities shared across all document types.

These entities are reused between resumes, job descriptions, and cover letters
to enable cross-document deduplication and matching.
"""

from graphrag_sdk import Entity, Relation
from graphrag_sdk.attribute import Attribute, AttributeType


def get_common_entities() -> list[Entity]:
    """Get entities shared across all document types.

    Returns:
        list[Entity]: List of common entity definitions
    """
    return [
        Entity(
            label="Skill",
            attributes=[
                Attribute(
                    "canonical_name", AttributeType.STRING, unique=True, required=True
                ),
                Attribute(
                    "category",
                    AttributeType.STRING,
                    unique=False,
                    required=False,
                ),
                Attribute("aliases", AttributeType.LIST, unique=False, required=False),
            ],
            description="A technical or soft skill",
        ),
        Entity(
            label="Company",
            attributes=[
                Attribute(
                    "canonical_name", AttributeType.STRING, unique=True, required=True
                ),
                Attribute(
                    "industry", AttributeType.STRING, unique=False, required=False
                ),
                Attribute(
                    "location", AttributeType.STRING, unique=False, required=False
                ),
                Attribute("aliases", AttributeType.LIST, unique=False, required=False),
            ],
            description="A company or organization",
        ),
        Entity(
            label="Position",
            attributes=[
                Attribute("title", AttributeType.STRING, unique=True, required=True),
                Attribute("level", AttributeType.STRING, unique=False, required=False),
            ],
            description="A job title or role",
        ),
        Entity(
            label="Document",
            attributes=[
                Attribute(
                    "document_id", AttributeType.STRING, unique=True, required=True
                ),
                Attribute("user_id", AttributeType.STRING, unique=False, required=True),
                Attribute(
                    "document_type", AttributeType.STRING, unique=False, required=False
                ),
                Attribute(
                    "processed_at", AttributeType.STRING, unique=False, required=False
                ),
                Attribute(
                    "ontology_version",
                    AttributeType.STRING,
                    unique=False,
                    required=False,
                ),
            ],
            description="Reference to the source document",
        ),
    ]


def get_common_relations() -> list[Relation]:
    """Get relations used across document types.

    These relations link primary entities (Person, JobPosting, CoverLetter)
    to their source Document.

    Returns:
        list[Relation]: List of common relation definitions
    """
    return [
        # Document tracking relations are defined in each specific schema
        # to link Person -> Document, JobPosting -> Document, etc.
    ]
