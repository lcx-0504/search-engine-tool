"""Data models for the search engine tool."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class WordStats:
    """Statistics for a word occurrence in a specific document."""
    frequency: int = 0
    positions: List[int] = field(default_factory=list)
    tf: float = 0.0


@dataclass
class DocumentMeta:
    """Metadata for a crawled document (page)."""
    url: str = ""
    title: str = ""
    total_words: int = 0
    crawled_at: str = ""


@dataclass
class SearchResult:
    """A single search result with relevance scoring."""
    url: str
    score: float
    matched_terms: Dict[str, WordStats] = field(default_factory=dict)
    snippet: str = ""
