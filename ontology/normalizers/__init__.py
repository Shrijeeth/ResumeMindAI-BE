"""Normalizers for entity canonicalization.

These normalizers ensure consistent entity names across documents
to prevent duplicates in the knowledge graph.
"""

from ontology.normalizers.company import normalize_company
from ontology.normalizers.education import normalize_degree, normalize_university
from ontology.normalizers.skill import normalize_skill

__all__ = [
    "normalize_skill",
    "normalize_company",
    "normalize_university",
    "normalize_degree",
]
