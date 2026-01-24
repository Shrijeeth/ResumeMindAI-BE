"""Ontology version constants and configuration."""

# Semantic versioning for ontology schema
ONTOLOGY_VERSION = "1.0.0"

# Version history for tracking changes
ONTOLOGY_VERSIONS = {
    "1.0.0": {
        "released": "2025-01-24",
        "description": (
            "Initial ontology with Person, Skill, Company, Experience, Education, "
            "Certification, Project entities for resumes; JobPosting, Requirement, "
            "Responsibility for job descriptions; CoverLetter for cover letters."
        ),
        "entities": [
            "Person",
            "Skill",
            "Company",
            "Position",
            "Experience",
            "University",
            "Degree",
            "Education",
            "Certification",
            "Project",
            "JobPosting",
            "Requirement",
            "Responsibility",
            "CoverLetter",
            "Document",
        ],
    },
}

# Maximum content length for extraction
MAX_CONTENT_LENGTH = 50000

# Skill categories for classification
SKILL_CATEGORIES = {
    "programming_languages": [
        "Python",
        "JavaScript",
        "TypeScript",
        "Java",
        "Go",
        "Rust",
        "C++",
        "C#",
        "Ruby",
        "PHP",
        "Swift",
        "Kotlin",
        "Scala",
        "R",
        "MATLAB",
    ],
    "frameworks": [
        "React",
        "Angular",
        "Vue.js",
        "Django",
        "FastAPI",
        "Flask",
        "Express.js",
        "Spring",
        "Next.js",
        "NestJS",
        "Rails",
        "Laravel",
    ],
    "databases": [
        "PostgreSQL",
        "MySQL",
        "MongoDB",
        "Redis",
        "Elasticsearch",
        "DynamoDB",
        "Cassandra",
        "SQLite",
        "Oracle",
        "SQL Server",
    ],
    "cloud": [
        "AWS",
        "GCP",
        "Azure",
        "Docker",
        "Kubernetes",
        "Terraform",
        "CloudFormation",
        "Serverless",
    ],
    "tools": [
        "Git",
        "GitHub",
        "GitLab",
        "Jenkins",
        "CircleCI",
        "Travis CI",
        "Jira",
        "Confluence",
    ],
    "soft_skills": [
        "Leadership",
        "Communication",
        "Problem Solving",
        "Team Collaboration",
        "Project Management",
        "Agile",
        "Scrum",
    ],
}
