"""Education entity normalization for entity deduplication.

This module provides functions to normalize university names and
degree types to their canonical forms.
"""

import re
from typing import Optional

# University name variations (lowercase key -> canonical name)
UNIVERSITY_CANONICAL_MAP: dict[str, str] = {
    # Ivy League
    "harvard": "Harvard University",
    "harvard university": "Harvard University",
    "yale": "Yale University",
    "yale university": "Yale University",
    "princeton": "Princeton University",
    "princeton university": "Princeton University",
    "columbia": "Columbia University",
    "columbia university": "Columbia University",
    "upenn": "University of Pennsylvania",
    "penn": "University of Pennsylvania",
    "university of pennsylvania": "University of Pennsylvania",
    "brown": "Brown University",
    "brown university": "Brown University",
    "dartmouth": "Dartmouth College",
    "dartmouth college": "Dartmouth College",
    "cornell": "Cornell University",
    "cornell university": "Cornell University",
    # Top Tech Schools
    "mit": "Massachusetts Institute of Technology",
    "massachusetts institute of technology": "Massachusetts Institute of Technology",
    "stanford": "Stanford University",
    "stanford university": "Stanford University",
    "caltech": "California Institute of Technology",
    "california institute of technology": "California Institute of Technology",
    "cmu": "Carnegie Mellon University",
    "carnegie mellon": "Carnegie Mellon University",
    "carnegie mellon university": "Carnegie Mellon University",
    "georgia tech": "Georgia Institute of Technology",
    "georgia institute of technology": "Georgia Institute of Technology",
    # UC System
    "berkeley": "University of California, Berkeley",
    "uc berkeley": "University of California, Berkeley",
    "ucb": "University of California, Berkeley",
    "university of california berkeley": "University of California, Berkeley",
    "university of california, berkeley": "University of California, Berkeley",
    "ucla": "University of California, Los Angeles",
    "uc los angeles": "University of California, Los Angeles",
    "university of california los angeles": "University of California, Los Angeles",
    "university of california, los angeles": "University of California, Los Angeles",
    "ucsd": "University of California, San Diego",
    "uc san diego": "University of California, San Diego",
    "uci": "University of California, Irvine",
    "uc irvine": "University of California, Irvine",
    "ucdavis": "University of California, Davis",
    "uc davis": "University of California, Davis",
    # Big Ten
    "umich": "University of Michigan",
    "university of michigan": "University of Michigan",
    "michigan": "University of Michigan",
    "uiuc": "University of Illinois Urbana-Champaign",
    "university of illinois": "University of Illinois Urbana-Champaign",
    "illinois": "University of Illinois Urbana-Champaign",
    "purdue": "Purdue University",
    "purdue university": "Purdue University",
    "wisconsin": "University of Wisconsin-Madison",
    "uw madison": "University of Wisconsin-Madison",
    "university of wisconsin": "University of Wisconsin-Madison",
    # Other Top Schools
    "nyu": "New York University",
    "new york university": "New York University",
    "duke": "Duke University",
    "duke university": "Duke University",
    "northwestern": "Northwestern University",
    "northwestern university": "Northwestern University",
    "uw": "University of Washington",
    "university of washington": "University of Washington",
    "ut austin": "University of Texas at Austin",
    "university of texas": "University of Texas at Austin",
    "university of texas at austin": "University of Texas at Austin",
    "usc": "University of Southern California",
    "university of southern california": "University of Southern California",
    # International
    "oxford": "University of Oxford",
    "university of oxford": "University of Oxford",
    "cambridge": "University of Cambridge",
    "university of cambridge": "University of Cambridge",
    "imperial": "Imperial College London",
    "imperial college": "Imperial College London",
    "imperial college london": "Imperial College London",
    "eth zurich": "ETH Zurich",
    "eth": "ETH Zurich",
    "iit": "Indian Institute of Technology",
    "indian institute of technology": "Indian Institute of Technology",
    "nus": "National University of Singapore",
    "national university of singapore": "National University of Singapore",
    "tsinghua": "Tsinghua University",
    "tsinghua university": "Tsinghua University",
    "peking": "Peking University",
    "peking university": "Peking University",
    "tokyo": "University of Tokyo",
    "university of tokyo": "University of Tokyo",
}

# Degree type variations (lowercase key -> (canonical name, level))
DEGREE_CANONICAL_MAP: dict[str, tuple[str, str]] = {
    # Bachelor's degrees
    "bs": ("Bachelor of Science", "bachelor"),
    "b.s.": ("Bachelor of Science", "bachelor"),
    "b.s": ("Bachelor of Science", "bachelor"),
    "bsc": ("Bachelor of Science", "bachelor"),
    "b.sc.": ("Bachelor of Science", "bachelor"),
    "b.sc": ("Bachelor of Science", "bachelor"),
    "bachelor of science": ("Bachelor of Science", "bachelor"),
    "ba": ("Bachelor of Arts", "bachelor"),
    "b.a.": ("Bachelor of Arts", "bachelor"),
    "b.a": ("Bachelor of Arts", "bachelor"),
    "bachelor of arts": ("Bachelor of Arts", "bachelor"),
    "bba": ("Bachelor of Business Administration", "bachelor"),
    "b.b.a.": ("Bachelor of Business Administration", "bachelor"),
    "bachelor of business administration": (
        "Bachelor of Business Administration",
        "bachelor",
    ),
    "beng": ("Bachelor of Engineering", "bachelor"),
    "b.eng.": ("Bachelor of Engineering", "bachelor"),
    "b.eng": ("Bachelor of Engineering", "bachelor"),
    "bachelor of engineering": ("Bachelor of Engineering", "bachelor"),
    "btech": ("Bachelor of Technology", "bachelor"),
    "b.tech.": ("Bachelor of Technology", "bachelor"),
    "b.tech": ("Bachelor of Technology", "bachelor"),
    "bachelor of technology": ("Bachelor of Technology", "bachelor"),
    "bfa": ("Bachelor of Fine Arts", "bachelor"),
    "b.f.a.": ("Bachelor of Fine Arts", "bachelor"),
    "bachelor of fine arts": ("Bachelor of Fine Arts", "bachelor"),
    "bachelor's": ("Bachelor's Degree", "bachelor"),
    "bachelors": ("Bachelor's Degree", "bachelor"),
    "bachelor": ("Bachelor's Degree", "bachelor"),
    "undergraduate": ("Bachelor's Degree", "bachelor"),
    # Master's degrees
    "ms": ("Master of Science", "master"),
    "m.s.": ("Master of Science", "master"),
    "m.s": ("Master of Science", "master"),
    "msc": ("Master of Science", "master"),
    "m.sc.": ("Master of Science", "master"),
    "m.sc": ("Master of Science", "master"),
    "master of science": ("Master of Science", "master"),
    "ma": ("Master of Arts", "master"),
    "m.a.": ("Master of Arts", "master"),
    "m.a": ("Master of Arts", "master"),
    "master of arts": ("Master of Arts", "master"),
    "mba": ("Master of Business Administration", "master"),
    "m.b.a.": ("Master of Business Administration", "master"),
    "master of business administration": (
        "Master of Business Administration",
        "master",
    ),
    "meng": ("Master of Engineering", "master"),
    "m.eng.": ("Master of Engineering", "master"),
    "m.eng": ("Master of Engineering", "master"),
    "master of engineering": ("Master of Engineering", "master"),
    "mtech": ("Master of Technology", "master"),
    "m.tech.": ("Master of Technology", "master"),
    "m.tech": ("Master of Technology", "master"),
    "master of technology": ("Master of Technology", "master"),
    "mfa": ("Master of Fine Arts", "master"),
    "m.f.a.": ("Master of Fine Arts", "master"),
    "master of fine arts": ("Master of Fine Arts", "master"),
    "mcs": ("Master of Computer Science", "master"),
    "master of computer science": ("Master of Computer Science", "master"),
    "master's": ("Master's Degree", "master"),
    "masters": ("Master's Degree", "master"),
    "master": ("Master's Degree", "master"),
    "graduate": ("Master's Degree", "master"),
    # Doctoral degrees
    "phd": ("Doctor of Philosophy", "phd"),
    "ph.d.": ("Doctor of Philosophy", "phd"),
    "ph.d": ("Doctor of Philosophy", "phd"),
    "doctorate": ("Doctor of Philosophy", "phd"),
    "doctoral": ("Doctor of Philosophy", "phd"),
    "doctor of philosophy": ("Doctor of Philosophy", "phd"),
    "dba": ("Doctor of Business Administration", "phd"),
    "d.b.a.": ("Doctor of Business Administration", "phd"),
    "doctor of business administration": (
        "Doctor of Business Administration",
        "phd",
    ),
    "md": ("Doctor of Medicine", "phd"),
    "m.d.": ("Doctor of Medicine", "phd"),
    "doctor of medicine": ("Doctor of Medicine", "phd"),
    "jd": ("Juris Doctor", "phd"),
    "j.d.": ("Juris Doctor", "phd"),
    "juris doctor": ("Juris Doctor", "phd"),
    # Associate degrees
    "aa": ("Associate of Arts", "associate"),
    "a.a.": ("Associate of Arts", "associate"),
    "associate of arts": ("Associate of Arts", "associate"),
    "as": ("Associate of Science", "associate"),
    "a.s.": ("Associate of Science", "associate"),
    "associate of science": ("Associate of Science", "associate"),
    "associate": ("Associate's Degree", "associate"),
    "associate's": ("Associate's Degree", "associate"),
    "associates": ("Associate's Degree", "associate"),
}


def normalize_university(name: str) -> str:
    """Normalize a university name to its canonical form.

    Args:
        name: The raw university name from the document

    Returns:
        str: The canonical university name
    """
    if not name:
        return name

    key = name.strip().lower()

    # Direct mapping lookup
    if key in UNIVERSITY_CANONICAL_MAP:
        return UNIVERSITY_CANONICAL_MAP[key]

    # Clean up and return original with proper capitalization
    cleaned = re.sub(r"\s+", " ", name).strip()
    return cleaned


def normalize_degree(name: str) -> tuple[str, str]:
    """Normalize a degree name and extract its level.

    Args:
        name: The raw degree name from the document

    Returns:
        tuple: (canonical_name, level) where level is one of:
               'associate', 'bachelor', 'master', 'phd', 'unknown'
    """
    if not name:
        return name, "unknown"

    key = name.strip().lower()

    # Direct mapping lookup
    if key in DEGREE_CANONICAL_MAP:
        return DEGREE_CANONICAL_MAP[key]

    # Try to infer level from keywords
    level = "unknown"
    if any(word in key for word in ["bachelor", "undergraduate", "bs", "ba"]):
        level = "bachelor"
    elif any(word in key for word in ["master", "graduate", "ms", "ma", "mba"]):
        level = "master"
    elif any(word in key for word in ["doctor", "phd", "ph.d", "doctoral"]):
        level = "phd"
    elif any(word in key for word in ["associate"]):
        level = "associate"

    # Clean up and return original
    cleaned = re.sub(r"\s+", " ", name).strip()
    return cleaned, level


def get_university_aliases(canonical_name: str) -> list[str]:
    """Get all known aliases for a canonical university name.

    Args:
        canonical_name: The canonical university name

    Returns:
        list[str]: List of known aliases
    """
    aliases = []
    for alias, canonical in UNIVERSITY_CANONICAL_MAP.items():
        if canonical == canonical_name and alias != canonical_name.lower():
            aliases.append(alias)
    return aliases


def get_degree_level(canonical_name: str) -> Optional[str]:
    """Get the level for a canonical degree name.

    Args:
        canonical_name: The canonical degree name

    Returns:
        str: The degree level or None if not found
    """
    for _, (canonical, level) in DEGREE_CANONICAL_MAP.items():
        if canonical == canonical_name:
            return level
    return None
