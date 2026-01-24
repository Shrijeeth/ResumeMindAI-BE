"""Job description-specific entity and relation definitions.

Defines entities for representing job posting content including
JobPosting, Requirement, and Responsibility.
"""

from graphrag_sdk import Entity, Relation
from graphrag_sdk.attribute import Attribute, AttributeType


def get_job_description_entities() -> list[Entity]:
    """Get job description-specific entity definitions.

    Returns:
        list[Entity]: List of job description entity definitions
    """
    return [
        Entity(
            label="JobPosting",
            attributes=[
                Attribute("id", AttributeType.STRING, unique=True, required=True),
                Attribute("title", AttributeType.STRING, unique=False, required=True),
                Attribute(
                    "description", AttributeType.STRING, unique=False, required=False
                ),
                Attribute(
                    "location", AttributeType.STRING, unique=False, required=False
                ),
                Attribute(
                    "salary_range", AttributeType.STRING, unique=False, required=False
                ),
                Attribute(
                    "employment_type",
                    AttributeType.STRING,
                    unique=False,
                    required=False,
                ),
                Attribute(
                    "remote_policy", AttributeType.STRING, unique=False, required=False
                ),
            ],
            description="A job posting or listing",
        ),
        Entity(
            label="Requirement",
            attributes=[
                Attribute(
                    "canonical_name", AttributeType.STRING, unique=True, required=True
                ),
                Attribute(
                    "requirement_type",
                    AttributeType.STRING,
                    unique=False,
                    required=False,
                ),
                Attribute(
                    "years_experience",
                    AttributeType.NUMBER,
                    unique=False,
                    required=False,
                ),
            ],
            description="A job requirement (must-have or nice-to-have)",
        ),
        Entity(
            label="Responsibility",
            attributes=[
                Attribute(
                    "description", AttributeType.STRING, unique=True, required=True
                ),
                Attribute(
                    "category",
                    AttributeType.STRING,
                    unique=False,
                    required=False,
                ),
            ],
            description="A job responsibility or duty",
        ),
    ]


def get_job_description_relations() -> list[Relation]:
    """Get job description-specific relation definitions.

    Note: JobPosting reuses Skill, Company, and Position entities
    from the common schema to enable cross-document matching.

    Returns:
        list[Relation]: List of job description relation definitions
    """
    return [
        # JobPosting relations - reuse common entities!
        Relation("REQUIRES_SKILL", "JobPosting", "Skill"),
        Relation("HAS_REQUIREMENT", "JobPosting", "Requirement"),
        Relation("HAS_RESPONSIBILITY", "JobPosting", "Responsibility"),
        Relation("AT_COMPANY", "JobPosting", "Company"),
        Relation("FOR_POSITION", "JobPosting", "Position"),
        Relation("FROM_DOCUMENT", "JobPosting", "Document"),
        # Requirement can also link to skills
        Relation("REQUIRES", "Requirement", "Skill"),
    ]
