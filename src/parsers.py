"""
Crossref and OSF API response parsers

Ported from fun.R:183-233
"""

from typing import Optional, Dict, Any, List
from datetime import datetime


def extract_title(item: Dict[str, Any]) -> Optional[str]:
    """
    Extract title from Crossref item

    Ported from fun.R:219-222

    Args:
        item: Crossref API item

    Returns:
        Article title or None
    """
    title = item.get("title")
    if not title:
        return None

    if isinstance(title, list):
        return title[0] if title else None

    return str(title)


def extract_author_name(author: Dict[str, Any]) -> str:
    """
    Extract author name from Crossref author object

    Ported from fun.R:210-212

    Args:
        author: Author object with 'given' and 'family' fields

    Returns:
        Full author name
    """
    given = author.get("given", "")
    family = author.get("family", "")
    return f"{given} {family}".strip()


def extract_authors(item: Dict[str, Any]) -> Optional[str]:
    """
    Extract comma-separated author list from Crossref item

    Ported from fun.R:205-208

    Args:
        item: Crossref API item

    Returns:
        Comma-separated author names or None
    """
    if item.get("author") is None:
        return None

    authors = item["author"]
    if not isinstance(authors, list) or len(authors) == 0:
        return None

    author_names = [extract_author_name(author) for author in authors]
    return ", ".join(author_names)


def extract_date(item: Dict[str, Any], date_field: str) -> Optional[str]:
    """
    Extract date from Crossref item

    Ported from fun.R:214-217

    Args:
        item: Crossref API item
        date_field: Field name (e.g., 'created', 'published')

    Returns:
        Date string in YYYY-MM-DD format or None
    """
    if item.get(date_field) is None:
        return None

    date_obj = item[date_field]
    if "date-parts" not in date_obj:
        return None

    date_parts = date_obj["date-parts"]
    if not isinstance(date_parts, list) or len(date_parts) == 0:
        return None

    parts = date_parts[0]
    if not isinstance(parts, list) or len(parts) == 0:
        return None

    # Join date parts with hyphens (handles year-only, year-month, or full dates)
    return "-".join(str(p) for p in parts)


def extract_abstract(item: Dict[str, Any]) -> Optional[str]:
    """
    Extract abstract from Crossref item

    Ported from fun.R:200-203

    Args:
        item: Crossref API item

    Returns:
        Article abstract or None
    """
    abstract = item.get("abstract")
    return abstract if abstract else None


def extract_url(item: Dict[str, Any]) -> Optional[str]:
    """
    Extract URL from Crossref item

    Ported from fun.R:229-232

    Args:
        item: Crossref API item

    Returns:
        Article URL or None
    """
    url = item.get("URL")
    return url if url else None


def parse_crossref_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse a single Crossref API item into article dictionary

    Ported from fun.R:189-198

    Args:
        item: Crossref API item

    Returns:
        Article dictionary with standardized fields
    """
    article = {
        "title": extract_title(item),
        "authors": extract_authors(item),
        "created": extract_date(item, "created"),
        "abstract": extract_abstract(item),
        "url": extract_url(item),
        "issn": item.get("_issn") or item.get("ISSN"),  # _issn from single query, ISSN from bulk
    }

    return article


def parse_crossref_response(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Parse list of Crossref API items

    Ported from fun.R:183-187

    Args:
        items: List of Crossref API items

    Returns:
        List of article dictionaries
    """
    return [parse_crossref_item(item) for item in items]


# OSF Parsing Functions
# Ported from picnic_preprints/fun.R:95-163

def get_osf_title(item: Dict[str, Any]) -> Optional[str]:
    """
    Extract title from OSF preprint item

    Args:
        item: OSF API preprint item

    Returns:
        Preprint title or None
    """
    try:
        return item["attributes"]["title"]
    except (KeyError, TypeError):
        return None


def get_osf_abstract(item: Dict[str, Any]) -> Optional[str]:
    """
    Extract abstract from OSF preprint item

    Args:
        item: OSF API preprint item

    Returns:
        Preprint abstract (description) or None
    """
    try:
        return item["attributes"]["description"]
    except (KeyError, TypeError):
        return None


def get_osf_url(item: Dict[str, Any]) -> Optional[str]:
    """
    Extract DOI URL from OSF preprint item

    Args:
        item: OSF API preprint item

    Returns:
        DOI URL or None
    """
    try:
        return item["links"]["preprint_doi"]
    except (KeyError, TypeError):
        return None


def get_osf_date(item: Dict[str, Any], name: str) -> Optional[str]:
    """
    Extract date from OSF preprint item

    Args:
        item: OSF API preprint item
        name: Date field name (e.g., 'date_created')

    Returns:
        Date string in YYYY-MM-DD format or None
    """
    try:
        date_str = item["attributes"][name]
        # Parse ISO 8601 datetime and convert to date
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d")
    except (KeyError, TypeError, ValueError):
        return None


def get_osf_author(item: Dict[str, Any]) -> Optional[str]:
    """
    Extract author name from OSF contributor item

    Args:
        item: OSF contributor item

    Returns:
        Author full name or None
    """
    try:
        return item["embeds"]["users"]["data"]["attributes"]["full_name"]
    except (KeyError, TypeError):
        return None


def get_osf_authors(item: Dict[str, Any]) -> Optional[str]:
    """
    Extract comma-separated author list from OSF preprint item

    Args:
        item: OSF API preprint item

    Returns:
        Comma-separated author names or None
    """
    try:
        contributors = item["embeds"]["contributors"]["data"]
        author_names = []
        for contributor in contributors:
            name = get_osf_author(contributor)
            if name:
                author_names.append(name)
        return ", ".join(author_names) if author_names else None
    except (KeyError, TypeError):
        return None


def get_osf_subject(subject_item: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """
    Extract subject id and text from OSF subject item (level 2)

    Args:
        subject_item: OSF subject hierarchy item

    Returns:
        Dictionary with 'id' and 'name' or None
    """
    try:
        # Subject is a nested list - get level 2 (specific discipline)
        if len(subject_item) < 2:
            return None
        level2 = subject_item[1]
        return {
            "id": level2.get("id", ""),
            "name": level2.get("text", "")
        }
    except (KeyError, TypeError, IndexError):
        return None


def get_osf_subjects(item: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Extract all subjects from OSF preprint item

    Args:
        item: OSF API preprint item

    Returns:
        List of subject dictionaries with 'id' and 'name' (level 2 disciplines)
    """
    try:
        subjects_data = item["attributes"]["subjects"]
        subjects = []
        for subject_item in subjects_data:
            subject = get_osf_subject(subject_item)
            if subject:
                subjects.append(subject)
        # Remove duplicates by id while preserving order
        seen = set()
        unique_subjects = []
        for s in subjects:
            if s["id"] not in seen:
                seen.add(s["id"])
                unique_subjects.append(s)
        return unique_subjects if unique_subjects else []
    except (KeyError, TypeError):
        return []


def parse_osf_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse a single OSF API item into article dictionary

    Ported from picnic_preprints/fun.R:95-105

    Args:
        item: OSF API preprint item

    Returns:
        Article dictionary with standardized fields
    """
    subjects = get_osf_subjects(item)

    article = {
        "title": get_osf_title(item),
        "authors": get_osf_authors(item),
        "created": get_osf_date(item, "date_created"),
        "abstract": get_osf_abstract(item),
        "url": get_osf_url(item),
        "subjects": subjects  # List of subjects
    }

    return article


def parse_osf_response(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Parse list of OSF API items

    Ported from picnic_preprints/fun.R:89-93

    Args:
        items: List of OSF API preprint items

    Returns:
        List of article dictionaries
    """
    articles = []
    for item in items:
        article = parse_osf_item(item)
        # Keep subjects as list (no expansion into separate rows)
        articles.append(article)

    return articles
