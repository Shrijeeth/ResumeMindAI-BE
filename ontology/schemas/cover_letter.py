"""Cover letter-specific entity and relation definitions.

Defines entities for representing cover letter content.
"""

from graphrag_sdk import Entity, Relation
from graphrag_sdk.attribute import Attribute, AttributeType


def get_cover_letter_entities() -> list[Entity]:
    """Get cover letter-specific entity definitions.

    Returns:
        list[Entity]: List of cover letter entity definitions
    """
    return [
        Entity(
            label="CoverLetter",
            attributes=[
                Attribute("id", AttributeType.STRING, unique=True, required=True),
                Attribute(
                    "target_company", AttributeType.STRING, unique=False, required=False
                ),
                Attribute(
                    "target_position",
                    AttributeType.STRING,
                    unique=False,
                    required=False,
                ),
                Attribute(
                    "salutation", AttributeType.STRING, unique=False, required=False
                ),
                Attribute(
                    "opening", AttributeType.STRING, unique=False, required=False
                ),
                Attribute(
                    "closing", AttributeType.STRING, unique=False, required=False
                ),
            ],
            description="A cover letter document",
        ),
    ]


def get_cover_letter_relations() -> list[Relation]:
    """Get cover letter-specific relation definitions.

    Note: CoverLetter reuses Person, Company, Position, and Skill entities
    from other schemas to enable cross-document linking.

    Returns:
        list[Relation]: List of cover letter relation definitions
    """
    return [
        # CoverLetter relations - link to shared entities
        Relation("WRITTEN_BY", "CoverLetter", "Person"),
        Relation("TARGETS_COMPANY", "CoverLetter", "Company"),
        Relation("TARGETS_POSITION", "CoverLetter", "Position"),
        Relation("MENTIONS_SKILL", "CoverLetter", "Skill"),
        Relation("FROM_DOCUMENT", "CoverLetter", "Document"),
    ]
