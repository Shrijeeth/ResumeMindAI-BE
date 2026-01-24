"""Resume-specific entity and relation definitions.

Defines entities for representing resume content including
Person, Experience, Education, Certification, and Project.
"""

from graphrag_sdk import Entity, Relation
from graphrag_sdk.attribute import Attribute, AttributeType


def get_resume_entities() -> list[Entity]:
    """Get resume-specific entity definitions.

    Returns:
        list[Entity]: List of resume entity definitions
    """
    return [
        Entity(
            label="Person",
            attributes=[
                Attribute("name", AttributeType.STRING, unique=True, required=True),
                Attribute("email", AttributeType.STRING, unique=False, required=False),
                Attribute("phone", AttributeType.STRING, unique=False, required=False),
                Attribute(
                    "location",
                    AttributeType.STRING,
                    unique=False,
                    required=False,
                ),
                Attribute(
                    "linkedin_url",
                    AttributeType.STRING,
                    unique=False,
                    required=False,
                ),
                Attribute(
                    "github_url",
                    AttributeType.STRING,
                    unique=False,
                    required=False,
                ),
                Attribute(
                    "summary",
                    AttributeType.STRING,
                    unique=False,
                    required=False,
                ),
            ],
            description="A person whose resume is being processed",
        ),
        Entity(
            label="Experience",
            attributes=[
                Attribute("id", AttributeType.STRING, unique=True, required=True),
                Attribute(
                    "start_date", AttributeType.STRING, unique=False, required=False
                ),
                Attribute(
                    "end_date",
                    AttributeType.STRING,
                    unique=False,
                    required=False,
                ),
                Attribute(
                    "is_current",
                    AttributeType.BOOLEAN,
                    unique=False,
                    required=False,
                ),
                Attribute(
                    "description",
                    AttributeType.STRING,
                    unique=False,
                    required=False,
                ),
                Attribute(
                    "achievements", AttributeType.LIST, unique=False, required=False
                ),
            ],
            description="A specific work experience entry",
        ),
        Entity(
            label="University",
            attributes=[
                Attribute(
                    "canonical_name", AttributeType.STRING, unique=True, required=True
                ),
                Attribute(
                    "location",
                    AttributeType.STRING,
                    unique=False,
                    required=False,
                ),
                Attribute(
                    "aliases",
                    AttributeType.LIST,
                    unique=False,
                    required=False,
                ),
            ],
            description="An educational institution",
        ),
        Entity(
            label="Degree",
            attributes=[
                Attribute(
                    "canonical_name", AttributeType.STRING, unique=True, required=True
                ),
                Attribute("level", AttributeType.STRING, unique=False, required=False),
                Attribute("field", AttributeType.STRING, unique=False, required=False),
            ],
            description="An academic degree type",
        ),
        Entity(
            label="Education",
            attributes=[
                Attribute("id", AttributeType.STRING, unique=True, required=True),
                Attribute(
                    "start_date", AttributeType.STRING, unique=False, required=False
                ),
                Attribute(
                    "end_date",
                    AttributeType.STRING,
                    unique=False,
                    required=False,
                ),
                Attribute("gpa", AttributeType.STRING, unique=False, required=False),
                Attribute("major", AttributeType.STRING, unique=False, required=False),
            ],
            description="A specific education entry",
        ),
        Entity(
            label="Certification",
            attributes=[
                Attribute(
                    "canonical_name", AttributeType.STRING, unique=True, required=True
                ),
                Attribute(
                    "issuing_org", AttributeType.STRING, unique=False, required=False
                ),
                Attribute("aliases", AttributeType.LIST, unique=False, required=False),
            ],
            description="A professional certification",
        ),
        Entity(
            label="Project",
            attributes=[
                Attribute("name", AttributeType.STRING, unique=True, required=True),
                Attribute(
                    "description", AttributeType.STRING, unique=False, required=False
                ),
                Attribute("url", AttributeType.STRING, unique=False, required=False),
            ],
            description="A project or portfolio item",
        ),
    ]


def get_resume_relations() -> list[Relation]:
    """Get resume-specific relation definitions.

    Returns:
        list[Relation]: List of resume relation definitions
    """
    return [
        # Person relations
        Relation("HAS_SKILL", "Person", "Skill"),
        Relation("HAS_EXPERIENCE", "Person", "Experience"),
        Relation("HAS_EDUCATION", "Person", "Education"),
        Relation("HAS_CERTIFICATION", "Person", "Certification"),
        Relation("WORKED_ON", "Person", "Project"),
        Relation("FROM_DOCUMENT", "Person", "Document"),
        # Experience relations
        Relation("AT_COMPANY", "Experience", "Company"),
        Relation("AS_POSITION", "Experience", "Position"),
        Relation("USED_SKILL", "Experience", "Skill"),
        # Education relations
        Relation("AT_UNIVERSITY", "Education", "University"),
        Relation("FOR_DEGREE", "Education", "Degree"),
        # Project relations
        Relation("USES_SKILL", "Project", "Skill"),
    ]
