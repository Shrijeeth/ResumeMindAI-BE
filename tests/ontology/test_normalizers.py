"""Unit tests for ontology normalizers."""

import pytest

from ontology.normalizers.company import (
    get_company_aliases,
    is_known_company,
    normalize_company,
)
from ontology.normalizers.education import (
    get_degree_level,
    get_university_aliases,
    normalize_degree,
    normalize_university,
)
from ontology.normalizers.skill import (
    get_skill_aliases,
    get_skill_category,
    is_known_skill,
    normalize_skill,
)


class TestSkillNormalizer:
    """Tests for skill normalization."""

    @pytest.mark.parametrize(
        "input_skill,expected_canonical",
        [
            # Python variations
            ("python", "Python"),
            ("Python", "Python"),
            ("python3", "Python"),
            ("Python 3", "Python"),
            ("py", "Python"),
            # JavaScript variations
            ("javascript", "JavaScript"),
            ("JavaScript", "JavaScript"),
            ("js", "JavaScript"),
            ("JS", "JavaScript"),
            ("es6", "JavaScript"),
            # TypeScript
            ("typescript", "TypeScript"),
            ("ts", "TypeScript"),
            # React variations
            ("react", "React"),
            ("ReactJS", "React"),
            ("react.js", "React"),
            # Node.js variations
            ("node", "Node.js"),
            ("nodejs", "Node.js"),
            ("Node.js", "Node.js"),
            # AWS variations
            ("aws", "AWS"),
            ("AWS", "AWS"),
            ("amazon web services", "AWS"),
            # Database variations
            ("postgresql", "PostgreSQL"),
            ("postgres", "PostgreSQL"),
            ("mysql", "MySQL"),
            ("mongodb", "MongoDB"),
            ("mongo", "MongoDB"),
            # Docker/K8s
            ("docker", "Docker"),
            ("kubernetes", "Kubernetes"),
            ("k8s", "Kubernetes"),
            # Unknown skill (should title case)
            ("some unknown skill", "Some Unknown Skill"),
        ],
    )
    def test_normalize_skill(self, input_skill, expected_canonical):
        """Test skill normalization produces canonical names."""
        canonical, _ = normalize_skill(input_skill)
        assert canonical == expected_canonical

    @pytest.mark.parametrize(
        "canonical,expected_category",
        [
            ("Python", "programming_languages"),
            ("JavaScript", "programming_languages"),
            ("React", "frameworks"),
            ("Django", "frameworks"),
            ("PostgreSQL", "databases"),
            ("AWS", "cloud"),
            ("Leadership", "soft_skills"),
        ],
    )
    def test_get_skill_category(self, canonical, expected_category):
        """Test skill categorization."""
        category = get_skill_category(canonical)
        assert category == expected_category

    def test_get_skill_category_unknown(self):
        """Test unknown skills return None category."""
        category = get_skill_category("Unknown Skill")
        assert category is None

    def test_normalize_skill_with_category(self):
        """Test normalize_skill returns both canonical and category."""
        canonical, category = normalize_skill("python")
        assert canonical == "Python"
        assert category == "programming_languages"

    def test_get_skill_aliases(self):
        """Test getting aliases for canonical skill."""
        aliases = get_skill_aliases("Python")
        assert "python3" in aliases
        assert "py" in aliases

    def test_is_known_skill(self):
        """Test checking if skill is known."""
        assert is_known_skill("python") is True
        assert is_known_skill("Python") is True
        assert is_known_skill("unknown_xyz_skill") is False

    def test_normalize_skill_empty(self):
        """Test normalizing empty skill."""
        canonical, category = normalize_skill("")
        assert canonical == ""
        assert category is None

    def test_normalize_skill_special_chars(self):
        """Test normalizing skills with special characters."""
        canonical, _ = normalize_skill("C++")
        assert canonical == "C++"

        canonical, _ = normalize_skill("c#")
        assert canonical == "C#"


class TestCompanyNormalizer:
    """Tests for company name normalization."""

    @pytest.mark.parametrize(
        "input_company,expected_canonical",
        [
            # Tech giants with suffixes
            ("Google Inc.", "Google"),
            ("Google, Inc.", "Google"),
            ("Google", "Google"),
            ("Meta Platforms, Inc.", "Meta"),
            ("Facebook", "Meta"),
            ("Microsoft Corporation", "Microsoft"),
            ("Amazon.com, Inc.", "Amazon"),
            ("Apple Inc.", "Apple"),
            # AWS
            ("Amazon Web Services", "AWS"),
            ("aws", "AWS"),
            # Social media
            ("Twitter", "X"),
            ("X Corp", "X"),
            ("LinkedIn Corporation", "LinkedIn"),
            # Fintech
            ("Stripe, Inc.", "Stripe"),
            ("PayPal Holdings, Inc.", "PayPal"),
            # Consulting
            ("Deloitte", "Deloitte"),
            ("PwC", "PwC"),
            ("PricewaterhouseCoopers", "PwC"),
            # Unknown company (should just strip suffix)
            ("Unknown Company, LLC", "Unknown Company"),
            ("Some Startup Inc.", "Some Startup"),
        ],
    )
    def test_normalize_company(self, input_company, expected_canonical):
        """Test company normalization produces canonical names."""
        canonical = normalize_company(input_company)
        assert canonical == expected_canonical

    def test_normalize_company_empty(self):
        """Test normalizing empty company name."""
        canonical = normalize_company("")
        assert canonical == ""

    def test_get_company_aliases(self):
        """Test getting aliases for canonical company."""
        aliases = get_company_aliases("Google")
        assert "google" in aliases or "google inc" in aliases

    def test_is_known_company(self):
        """Test checking if company is known."""
        assert is_known_company("google") is True
        assert is_known_company("Google Inc.") is True
        assert is_known_company("unknown_xyz_company") is False

    def test_normalize_company_case_insensitive_suffix(self):
        """Suffix removal should be case-insensitive."""
        canonical = normalize_company("Example llc")
        assert canonical == "Example"


class TestEducationNormalizer:
    """Tests for education normalization (universities and degrees)."""

    @pytest.mark.parametrize(
        "input_university,expected_canonical",
        [
            # Ivy League
            ("harvard", "Harvard University"),
            ("Harvard University", "Harvard University"),
            ("yale", "Yale University"),
            ("princeton", "Princeton University"),
            ("columbia", "Columbia University"),
            # Tech schools
            ("mit", "Massachusetts Institute of Technology"),
            ("MIT", "Massachusetts Institute of Technology"),
            ("stanford", "Stanford University"),
            ("Stanford University", "Stanford University"),
            ("cmu", "Carnegie Mellon University"),
            ("Carnegie Mellon", "Carnegie Mellon University"),
            # UC System
            ("berkeley", "University of California, Berkeley"),
            ("uc berkeley", "University of California, Berkeley"),
            ("UCLA", "University of California, Los Angeles"),
            # International
            ("oxford", "University of Oxford"),
            ("cambridge", "University of Cambridge"),
            # Unknown university
            ("Some Local University", "Some Local University"),
        ],
    )
    def test_normalize_university(self, input_university, expected_canonical):
        """Test university normalization produces canonical names."""
        canonical = normalize_university(input_university)
        assert canonical == expected_canonical

    @pytest.mark.parametrize(
        "input_degree,expected_canonical,expected_level",
        [
            # Bachelor's degrees
            ("bs", "Bachelor of Science", "bachelor"),
            ("B.S.", "Bachelor of Science", "bachelor"),
            ("BSc", "Bachelor of Science", "bachelor"),
            ("ba", "Bachelor of Arts", "bachelor"),
            ("B.A.", "Bachelor of Arts", "bachelor"),
            ("beng", "Bachelor of Engineering", "bachelor"),
            ("btech", "Bachelor of Technology", "bachelor"),
            # Master's degrees
            ("ms", "Master of Science", "master"),
            ("M.S.", "Master of Science", "master"),
            ("msc", "Master of Science", "master"),
            ("ma", "Master of Arts", "master"),
            ("mba", "Master of Business Administration", "master"),
            ("MBA", "Master of Business Administration", "master"),
            # Doctoral degrees
            ("phd", "Doctor of Philosophy", "phd"),
            ("Ph.D.", "Doctor of Philosophy", "phd"),
            ("doctorate", "Doctor of Philosophy", "phd"),
            ("md", "Doctor of Medicine", "phd"),
            ("jd", "Juris Doctor", "phd"),
            # Associate degrees
            ("aa", "Associate of Arts", "associate"),
            ("as", "Associate of Science", "associate"),
            # Unknown degree
            ("Some Certification", "Some Certification", "unknown"),
        ],
    )
    def test_normalize_degree(self, input_degree, expected_canonical, expected_level):
        """Test degree normalization produces canonical names and levels."""
        canonical, level = normalize_degree(input_degree)
        assert canonical == expected_canonical
        assert level == expected_level

    @pytest.mark.parametrize(
        "input_degree,expected_level",
        [
            ("Bachelor of Fine Arts", "bachelor"),
            ("undergraduate research program", "bachelor"),
            ("Masters in Computer Science", "master"),
            ("Ph.D in Physics", "phd"),
            ("Associate of Arts", "associate"),
            ("graduate studies program", "master"),
            ("associate degree program", "associate"),
        ],
    )
    def test_normalize_degree_infers_level_from_keywords(
        self,
        input_degree,
        expected_level,
    ):
        """Infer degree level when not in canonical map."""
        _, level = normalize_degree(input_degree)
        assert level == expected_level

    def test_normalize_university_empty(self):
        """Test normalizing empty university name."""
        canonical = normalize_university("")
        assert canonical == ""

    def test_normalize_degree_empty(self):
        """Test normalizing empty degree name."""
        canonical, level = normalize_degree("")
        assert canonical == ""
        assert level == "unknown"

    def test_get_university_aliases(self):
        """Test getting aliases for canonical university."""
        aliases = get_university_aliases("Harvard University")
        assert "harvard" in aliases

    def test_get_degree_level(self):
        """Test getting degree level from canonical name."""
        assert get_degree_level("Bachelor of Science") == "bachelor"
        assert get_degree_level("Doctor of Philosophy") == "phd"

    def test_get_degree_level_unknown(self):
        """Unknown canonical degree should return None."""
        assert get_degree_level("Unknown Degree") is None
