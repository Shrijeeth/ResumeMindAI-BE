"""Unit tests for ontology schema definitions."""

from ontology.schemas import build_ontology
from ontology.schemas.common import get_common_entities
from ontology.schemas.constants import ONTOLOGY_VERSION, SKILL_CATEGORIES
from ontology.schemas.cover_letter import (
    get_cover_letter_entities,
    get_cover_letter_relations,
)
from ontology.schemas.job_description import (
    get_job_description_entities,
    get_job_description_relations,
)
from ontology.schemas.resume import get_resume_entities, get_resume_relations


class TestOntologyVersion:
    """Tests for ontology versioning."""

    def test_version_format(self):
        """Test ontology version follows semantic versioning."""
        parts = ONTOLOGY_VERSION.split(".")
        assert len(parts) == 3
        # All parts should be numeric
        for part in parts:
            assert part.isdigit()

    def test_skill_categories_not_empty(self):
        """Test skill categories are defined."""
        assert len(SKILL_CATEGORIES) > 0
        for category, skills in SKILL_CATEGORIES.items():
            assert len(skills) > 0


class TestCommonEntities:
    """Tests for common entity definitions."""

    def test_common_entities_not_empty(self):
        """Test common entities are defined."""
        entities = get_common_entities()
        assert len(entities) > 0

    def test_skill_entity_exists(self):
        """Test Skill entity is defined with required attributes."""
        entities = get_common_entities()
        skill = next((e for e in entities if e.label == "Skill"), None)
        assert skill is not None
        # Check unique attribute
        unique_attrs = [a for a in skill.attributes if a.unique]
        assert len(unique_attrs) > 0
        assert unique_attrs[0].name == "canonical_name"

    def test_company_entity_exists(self):
        """Test Company entity is defined with required attributes."""
        entities = get_common_entities()
        company = next((e for e in entities if e.label == "Company"), None)
        assert company is not None
        unique_attrs = [a for a in company.attributes if a.unique]
        assert len(unique_attrs) > 0
        assert unique_attrs[0].name == "canonical_name"

    def test_position_entity_exists(self):
        """Test Position entity is defined."""
        entities = get_common_entities()
        position = next((e for e in entities if e.label == "Position"), None)
        assert position is not None

    def test_document_entity_exists(self):
        """Test Document entity is defined for tracking."""
        entities = get_common_entities()
        document = next((e for e in entities if e.label == "Document"), None)
        assert document is not None
        # Check document_id is unique
        unique_attrs = [a for a in document.attributes if a.unique]
        assert len(unique_attrs) > 0
        assert unique_attrs[0].name == "document_id"


class TestResumeEntities:
    """Tests for resume entity definitions."""

    def test_resume_entities_not_empty(self):
        """Test resume entities are defined."""
        entities = get_resume_entities()
        assert len(entities) > 0

    def test_person_entity_exists(self):
        """Test Person entity is defined."""
        entities = get_resume_entities()
        person = next((e for e in entities if e.label == "Person"), None)
        assert person is not None
        # Check name is unique
        unique_attrs = [a for a in person.attributes if a.unique]
        assert len(unique_attrs) > 0
        assert unique_attrs[0].name == "name"

    def test_experience_entity_exists(self):
        """Test Experience entity is defined."""
        entities = get_resume_entities()
        experience = next((e for e in entities if e.label == "Experience"), None)
        assert experience is not None

    def test_education_entity_exists(self):
        """Test Education entity is defined."""
        entities = get_resume_entities()
        education = next((e for e in entities if e.label == "Education"), None)
        assert education is not None

    def test_resume_relations_not_empty(self):
        """Test resume relations are defined."""
        relations = get_resume_relations()
        assert len(relations) > 0

    def test_has_skill_relation_exists(self):
        """Test HAS_SKILL relation is defined."""
        relations = get_resume_relations()
        has_skill = next((r for r in relations if r.label == "HAS_SKILL"), None)
        assert has_skill is not None
        assert has_skill.source.label == "Person"
        assert has_skill.target.label == "Skill"


class TestJobDescriptionEntities:
    """Tests for job description entity definitions."""

    def test_job_description_entities_not_empty(self):
        """Test job description entities are defined."""
        entities = get_job_description_entities()
        assert len(entities) > 0

    def test_job_posting_entity_exists(self):
        """Test JobPosting entity is defined."""
        entities = get_job_description_entities()
        job_posting = next((e for e in entities if e.label == "JobPosting"), None)
        assert job_posting is not None

    def test_requirement_entity_exists(self):
        """Test Requirement entity is defined."""
        entities = get_job_description_entities()
        requirement = next((e for e in entities if e.label == "Requirement"), None)
        assert requirement is not None

    def test_job_description_relations_not_empty(self):
        """Test job description relations are defined."""
        relations = get_job_description_relations()
        assert len(relations) > 0

    def test_requires_skill_relation_exists(self):
        """Test REQUIRES_SKILL relation is defined (links to common Skill)."""
        relations = get_job_description_relations()
        requires_skill = next(
            (r for r in relations if r.label == "REQUIRES_SKILL"), None
        )
        assert requires_skill is not None
        assert requires_skill.source.label == "JobPosting"
        assert requires_skill.target.label == "Skill"


class TestCoverLetterEntities:
    """Tests for cover letter entity definitions."""

    def test_cover_letter_entities_not_empty(self):
        """Test cover letter entities are defined."""
        entities = get_cover_letter_entities()
        assert len(entities) > 0

    def test_cover_letter_entity_exists(self):
        """Test CoverLetter entity is defined."""
        entities = get_cover_letter_entities()
        cover_letter = next((e for e in entities if e.label == "CoverLetter"), None)
        assert cover_letter is not None

    def test_cover_letter_relations_not_empty(self):
        """Test cover letter relations are defined."""
        relations = get_cover_letter_relations()
        assert len(relations) > 0


class TestBuildOntology:
    """Tests for complete ontology building."""

    def test_build_ontology_returns_ontology(self):
        """Test build_ontology returns an Ontology object."""
        ontology = build_ontology()
        assert ontology is not None
        assert hasattr(ontology, "entities")
        assert hasattr(ontology, "relations")

    def test_build_ontology_has_all_entities(self):
        """Test built ontology contains entities from all schemas."""
        ontology = build_ontology()
        entity_labels = [e.label for e in ontology.entities]

        # Common entities
        assert "Skill" in entity_labels
        assert "Company" in entity_labels
        assert "Position" in entity_labels
        assert "Document" in entity_labels

        # Resume entities
        assert "Person" in entity_labels
        assert "Experience" in entity_labels
        assert "Education" in entity_labels

        # Job description entities
        assert "JobPosting" in entity_labels
        assert "Requirement" in entity_labels

        # Cover letter entities
        assert "CoverLetter" in entity_labels

    def test_build_ontology_has_all_relations(self):
        """Test built ontology contains relations from all schemas."""
        ontology = build_ontology()
        relation_labels = [r.label for r in ontology.relations]

        # Resume relations
        assert "HAS_SKILL" in relation_labels
        assert "HAS_EXPERIENCE" in relation_labels
        assert "AT_COMPANY" in relation_labels

        # Job description relations
        assert "REQUIRES_SKILL" in relation_labels
        assert "HAS_REQUIREMENT" in relation_labels

        # Cover letter relations
        assert "WRITTEN_BY" in relation_labels
        assert "TARGETS_COMPANY" in relation_labels

    def test_no_duplicate_entities(self):
        """Test built ontology has no duplicate entity labels."""
        ontology = build_ontology()
        entity_labels = [e.label for e in ontology.entities]
        assert len(entity_labels) == len(set(entity_labels))

    def test_skill_entity_shared_across_documents(self):
        """Test Skill entity can be referenced by multiple relations.

        This verifies the deduplication design - the same Skill entity
        is used by Person (HAS_SKILL), JobPosting (REQUIRES_SKILL),
        and CoverLetter (MENTIONS_SKILL).
        """
        ontology = build_ontology()
        skill_relations = [r for r in ontology.relations if r.target.label == "Skill"]

        # Should have relations from multiple source entities
        source_entities = set(r.source.label for r in skill_relations)
        assert "Person" in source_entities  # From resume
        assert "JobPosting" in source_entities  # From job description
        assert "CoverLetter" in source_entities  # From cover letter
