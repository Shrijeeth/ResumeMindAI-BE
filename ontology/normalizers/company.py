"""Company name normalization for entity deduplication.

This module provides functions to normalize company names to their
canonical forms, preventing duplicates like "Google Inc." vs "Google".
"""

import re

# Common suffixes to strip for matching
COMPANY_SUFFIXES = [
    ", Inc.",
    " Inc.",
    " Inc",
    ", LLC",
    " LLC",
    ", Ltd.",
    " Ltd.",
    " Ltd",
    ", Corp.",
    " Corp.",
    " Corp",
    " Corporation",
    " Company",
    " Co.",
    " Co",
    ", L.P.",
    " L.P.",
    " LP",
    " PLC",
    " plc",
    " AG",
    " GmbH",
    " S.A.",
    " SA",
    " N.V.",
    " NV",
    " Pty Ltd",
    " Pvt Ltd",
    " Private Limited",
    " Limited",
]

# Known company name variations (lowercase key -> canonical name)
COMPANY_CANONICAL_MAP: dict[str, str] = {
    # Tech Giants
    "google": "Google",
    "google inc": "Google",
    "alphabet": "Alphabet",
    "alphabet inc": "Alphabet",
    "meta": "Meta",
    "meta platforms": "Meta",
    "facebook": "Meta",
    "facebook inc": "Meta",
    "microsoft": "Microsoft",
    "microsoft corp": "Microsoft",
    "microsoft corporation": "Microsoft",
    "amazon": "Amazon",
    "amazon.com": "Amazon",
    "amazon web services": "AWS",
    "aws": "AWS",
    "apple": "Apple",
    "apple inc": "Apple",
    "netflix": "Netflix",
    "netflix inc": "Netflix",
    # Cloud Providers
    "salesforce": "Salesforce",
    "salesforce.com": "Salesforce",
    "oracle": "Oracle",
    "oracle corporation": "Oracle",
    "ibm": "IBM",
    "international business machines": "IBM",
    "vmware": "VMware",
    "vmware inc": "VMware",
    # Social Media
    "twitter": "X",
    "x corp": "X",
    "linkedin": "LinkedIn",
    "linkedin corporation": "LinkedIn",
    "snap": "Snap",
    "snap inc": "Snap",
    "snapchat": "Snap",
    "tiktok": "TikTok",
    "bytedance": "ByteDance",
    # Fintech
    "stripe": "Stripe",
    "stripe inc": "Stripe",
    "paypal": "PayPal",
    "paypal holdings": "PayPal",
    "square": "Block",
    "block inc": "Block",
    # Rideshare
    "uber": "Uber",
    "uber technologies": "Uber",
    "lyft": "Lyft",
    "lyft inc": "Lyft",
    # E-commerce
    "shopify": "Shopify",
    "shopify inc": "Shopify",
    "ebay": "eBay",
    "ebay inc": "eBay",
    # Hardware
    "nvidia": "NVIDIA",
    "nvidia corporation": "NVIDIA",
    "intel": "Intel",
    "intel corporation": "Intel",
    "amd": "AMD",
    "advanced micro devices": "AMD",
    "qualcomm": "Qualcomm",
    # Consulting
    "deloitte": "Deloitte",
    "pwc": "PwC",
    "pricewaterhousecoopers": "PwC",
    "kpmg": "KPMG",
    "ernst & young": "EY",
    "ey": "EY",
    "accenture": "Accenture",
    "mckinsey": "McKinsey",
    "mckinsey & company": "McKinsey",
    "boston consulting group": "BCG",
    "bcg": "BCG",
    "bain": "Bain & Company",
    "bain & company": "Bain & Company",
}


def normalize_company(company_name: str) -> str:
    """Normalize a company name to its canonical form.

    Args:
        company_name: The raw company name from the document

    Returns:
        str: The canonical company name
    """
    if not company_name:
        return company_name

    normalized = company_name.strip()

    # Remove common suffixes
    for suffix in COMPANY_SUFFIXES:
        if normalized.endswith(suffix):
            normalized = normalized[: -len(suffix)].strip()
            break
        # Also check case-insensitive
        if normalized.lower().endswith(suffix.lower()):
            normalized = normalized[: -len(suffix)].strip()
            break

    # Check canonical mapping
    key = normalized.lower().strip()
    if key in COMPANY_CANONICAL_MAP:
        return COMPANY_CANONICAL_MAP[key]

    # Clean up any extra whitespace
    normalized = re.sub(r"\s+", " ", normalized).strip()

    return normalized


def get_company_aliases(canonical_name: str) -> list[str]:
    """Get all known aliases for a canonical company name.

    Args:
        canonical_name: The canonical company name

    Returns:
        list[str]: List of known aliases
    """
    aliases = []
    for alias, canonical in COMPANY_CANONICAL_MAP.items():
        if canonical == canonical_name and alias != canonical_name.lower():
            aliases.append(alias)
    return aliases


def is_known_company(company_name: str) -> bool:
    """Check if a company name is in the known mappings.

    Args:
        company_name: The company name to check

    Returns:
        bool: True if the company is known, False otherwise
    """
    # First strip suffixes
    normalized = company_name.strip()
    for suffix in COMPANY_SUFFIXES:
        if normalized.lower().endswith(suffix.lower()):
            normalized = normalized[: -len(suffix)].strip()
            break

    cleaned = normalized.lower().strip()
    return cleaned in COMPANY_CANONICAL_MAP
