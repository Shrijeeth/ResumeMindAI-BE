"""Skill name normalization for entity deduplication.

This module provides functions to normalize skill names to their
canonical forms, preventing duplicates like "Python" vs "python3".
"""

import re
from typing import Optional

from ontology.schemas.constants import SKILL_CATEGORIES

# Canonical skill mappings (lowercase key -> canonical name)
SKILL_CANONICAL_MAP: dict[str, str] = {
    # Python variations
    "python": "Python",
    "python3": "Python",
    "python 3": "Python",
    "python2": "Python",
    "python 2": "Python",
    "py": "Python",
    # JavaScript variations
    "javascript": "JavaScript",
    "js": "JavaScript",
    "ecmascript": "JavaScript",
    "es6": "JavaScript",
    "es2015": "JavaScript",
    "es2020": "JavaScript",
    "es2021": "JavaScript",
    # TypeScript variations
    "typescript": "TypeScript",
    "ts": "TypeScript",
    # React variations
    "react": "React",
    "reactjs": "React",
    "react.js": "React",
    "react js": "React",
    # Angular variations
    "angular": "Angular",
    "angularjs": "Angular",
    "angular.js": "Angular",
    "angular 2": "Angular",
    # Vue variations
    "vue": "Vue.js",
    "vuejs": "Vue.js",
    "vue.js": "Vue.js",
    "vue js": "Vue.js",
    "vue 3": "Vue.js",
    # Node.js variations
    "node": "Node.js",
    "nodejs": "Node.js",
    "node.js": "Node.js",
    "node js": "Node.js",
    # Express variations
    "express": "Express.js",
    "expressjs": "Express.js",
    "express.js": "Express.js",
    # Next.js variations
    "next": "Next.js",
    "nextjs": "Next.js",
    "next.js": "Next.js",
    # Django variations
    "django": "Django",
    "django rest framework": "Django",
    "drf": "Django REST Framework",
    # FastAPI variations
    "fastapi": "FastAPI",
    "fast api": "FastAPI",
    # Flask variations
    "flask": "Flask",
    # Spring variations
    "spring": "Spring",
    "spring boot": "Spring Boot",
    "springboot": "Spring Boot",
    # AWS variations
    "aws": "AWS",
    "amazon web services": "AWS",
    "amazon aws": "AWS",
    # GCP variations
    "gcp": "GCP",
    "google cloud": "GCP",
    "google cloud platform": "GCP",
    # Azure variations
    "azure": "Azure",
    "microsoft azure": "Azure",
    "ms azure": "Azure",
    # Docker variations
    "docker": "Docker",
    "docker compose": "Docker Compose",
    "docker-compose": "Docker Compose",
    # Kubernetes variations
    "kubernetes": "Kubernetes",
    "k8s": "Kubernetes",
    "kube": "Kubernetes",
    # Database variations
    "postgresql": "PostgreSQL",
    "postgres": "PostgreSQL",
    "psql": "PostgreSQL",
    "pg": "PostgreSQL",
    "mysql": "MySQL",
    "my sql": "MySQL",
    "mongodb": "MongoDB",
    "mongo": "MongoDB",
    "mongo db": "MongoDB",
    "redis": "Redis",
    "elasticsearch": "Elasticsearch",
    "elastic search": "Elasticsearch",
    "elastic": "Elasticsearch",
    "dynamodb": "DynamoDB",
    "dynamo db": "DynamoDB",
    "dynamo": "DynamoDB",
    "cassandra": "Cassandra",
    "sqlite": "SQLite",
    "sql lite": "SQLite",
    # Java variations
    "java": "Java",
    "java 8": "Java",
    "java 11": "Java",
    "java 17": "Java",
    # Go variations
    "go": "Go",
    "golang": "Go",
    # Rust variations
    "rust": "Rust",
    "rustlang": "Rust",
    # C++ variations
    "c++": "C++",
    "cpp": "C++",
    "cplusplus": "C++",
    # C# variations
    "c#": "C#",
    "csharp": "C#",
    "c sharp": "C#",
    # .NET variations
    ".net": ".NET",
    "dotnet": ".NET",
    "dot net": ".NET",
    ".net core": ".NET Core",
    "dotnet core": ".NET Core",
    # Ruby variations
    "ruby": "Ruby",
    "ruby on rails": "Ruby on Rails",
    "rails": "Ruby on Rails",
    "ror": "Ruby on Rails",
    # PHP variations
    "php": "PHP",
    "laravel": "Laravel",
    # Git variations
    "git": "Git",
    "github": "GitHub",
    "gitlab": "GitLab",
    "bitbucket": "Bitbucket",
    # CI/CD variations
    "jenkins": "Jenkins",
    "circleci": "CircleCI",
    "circle ci": "CircleCI",
    "travis ci": "Travis CI",
    "travisci": "Travis CI",
    "github actions": "GitHub Actions",
    # Terraform variations
    "terraform": "Terraform",
    "tf": "Terraform",
    # Machine Learning variations
    "machine learning": "Machine Learning",
    "ml": "Machine Learning",
    "deep learning": "Deep Learning",
    "dl": "Deep Learning",
    "tensorflow": "TensorFlow",
    "pytorch": "PyTorch",
    "torch": "PyTorch",
    "keras": "Keras",
    "scikit-learn": "Scikit-learn",
    "sklearn": "Scikit-learn",
    # Data Science variations
    "data science": "Data Science",
    "data analysis": "Data Analysis",
    "pandas": "Pandas",
    "numpy": "NumPy",
    "matplotlib": "Matplotlib",
    # Soft skills
    "leadership": "Leadership",
    "communication": "Communication",
    "problem solving": "Problem Solving",
    "problem-solving": "Problem Solving",
    "teamwork": "Team Collaboration",
    "team work": "Team Collaboration",
    "collaboration": "Team Collaboration",
    "team collaboration": "Team Collaboration",
    "project management": "Project Management",
    "pm": "Project Management",
    "agile": "Agile",
    "scrum": "Scrum",
    "kanban": "Kanban",
}


def normalize_skill(skill_name: str) -> tuple[str, Optional[str]]:
    """Normalize a skill name to its canonical form.

    Args:
        skill_name: The raw skill name from the document

    Returns:
        tuple: (canonical_name, category) where category may be None
    """
    if not skill_name:
        return skill_name, None

    # Clean input
    cleaned = skill_name.strip().lower()
    cleaned = re.sub(r"[^\w\s\.\+\#\-]", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    # Direct mapping lookup
    if cleaned in SKILL_CANONICAL_MAP:
        canonical = SKILL_CANONICAL_MAP[cleaned]
    else:
        # Title case fallback for unknown skills
        canonical = skill_name.strip().title()

    # Determine category
    category = get_skill_category(canonical)

    return canonical, category


def get_skill_category(canonical_name: str) -> Optional[str]:
    """Get the category for a canonical skill name.

    Args:
        canonical_name: The canonical skill name

    Returns:
        str: The category name or None if not categorized
    """
    for cat, skills in SKILL_CATEGORIES.items():
        if canonical_name in skills:
            return cat
    return None


def get_skill_aliases(canonical_name: str) -> list[str]:
    """Get all known aliases for a canonical skill name.

    Args:
        canonical_name: The canonical skill name

    Returns:
        list[str]: List of known aliases (excluding the canonical name itself)
    """
    aliases = []
    for alias, canonical in SKILL_CANONICAL_MAP.items():
        if canonical == canonical_name and alias != canonical_name.lower():
            aliases.append(alias)
    return aliases


def is_known_skill(skill_name: str) -> bool:
    """Check if a skill name is in the known mappings.

    Args:
        skill_name: The skill name to check

    Returns:
        bool: True if the skill is known, False otherwise
    """
    cleaned = skill_name.strip().lower()
    return cleaned in SKILL_CANONICAL_MAP
