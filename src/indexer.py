"""Inverted index builder with TF-IDF scoring."""

import json
import logging
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from src.models import DocumentMeta, WordStats

logger = logging.getLogger(__name__)

DEFAULT_INDEX_PATH = "data/index.json"


class Indexer:
    """Builds and manages an inverted index from crawled data."""

    def __init__(self) -> None:
        # Inverted index: word -> {document_url -> WordStats}
        self.index: Dict[str, Dict[str, WordStats]] = {}
        # Document metadata: url -> DocumentMeta
        self.documents: Dict[str, DocumentMeta] = {}
        # Pre-computed IDF scores: word -> log(N / df)
        self.idf_scores: Dict[str, float] = {}

    def tokenize(self, text: str) -> List[str]:
        """Tokenize text into lowercase words, stripping punctuation.

        Allows apostrophes within words (e.g. "don't") but removes all
        other punctuation. Case-insensitive as required by the Brief.
        """
        text = text.lower()
        # Match multi-char words (with internal apostrophes) or single letters
        tokens = re.findall(r"[a-z][a-z']*[a-z]|[a-z]", text)
        return tokens

    def build_index(self, crawl_data: Dict[str, Any]) -> None:
        """Build the full inverted index from crawl data.

        Processes quote pages and author pages separately:
        - Quote pages: indexes quote text, author names, and tags
        - Author pages: indexes name, birth info, and description
        After indexing, computes TF and IDF for all term-document pairs.
        """
        self.index.clear()
        self.documents.clear()
        self.idf_scores.clear()

        pages = crawl_data.get("pages", [])
        authors = crawl_data.get("authors", {})

        # Index quote pages: each page URL is one document, combining all
        # quote text, author names, and tags on that page
        for page in pages:
            url = page["url"]
            all_text_parts: List[str] = []

            for quote in page.get("quotes", []):
                all_text_parts.append(quote.get("text", ""))
                all_text_parts.append(quote.get("author", ""))
                all_text_parts.extend(quote.get("tags", []))

            full_text = " ".join(all_text_parts)
            tokens = self.tokenize(full_text)

            self.documents[url] = DocumentMeta(
                url=url,
                title=full_text[:80] + "..." if len(full_text) > 80 else full_text,
                total_words=len(tokens),
                crawled_at=datetime.now(timezone.utc).isoformat(),
                full_text=full_text,
            )

            self._index_tokens(url, tokens)

        # Index author pages: each author URL is one document, combining
        # name, birth date, birth location, and biography description
        for author_url, author_info in authors.items():
            all_parts: List[str] = []
            all_parts.append(author_info.get("name", ""))
            all_parts.append(author_info.get("born_date", ""))
            all_parts.append(author_info.get("born_location", ""))
            all_parts.append(author_info.get("description", ""))

            full_text = " ".join(part for part in all_parts if part)
            if full_text:
                tokens = self.tokenize(full_text)
                self.documents[author_url] = DocumentMeta(
                    url=author_url,
                    title=author_info.get("name", ""),
                    total_words=len(tokens),
                    crawled_at=datetime.now(timezone.utc).isoformat(),
                    full_text=full_text,
                )
                self._index_tokens(author_url, tokens)

        self._compute_idf()
        self._compute_all_tf()

        total_terms = len(self.index)
        total_docs = len(self.documents)
        logger.info(f"Index built: {total_terms} terms across {total_docs} documents")
        print(f"  Indexed {total_terms} unique terms across {total_docs} documents")

    def _index_tokens(self, url: str, tokens: List[str]) -> None:
        """Add token occurrences for a document to the index.

        Records frequency and position of each token. Positions are
        stored to support potential future phrase/proximity queries.
        """
        for position, token in enumerate(tokens):
            if token not in self.index:
                self.index[token] = {}
            if url not in self.index[token]:
                self.index[token][url] = WordStats()
            stats = self.index[token][url]
            stats.frequency += 1
            stats.positions.append(position)

    def _compute_idf(self) -> None:
        """Compute IDF scores for all terms: log(N / df).

        Words appearing in fewer documents get higher IDF, making rare
        terms more significant in search ranking.
        """
        n = len(self.documents)
        if n == 0:
            return
        for term, postings in self.index.items():
            df = len(postings)
            self.idf_scores[term] = math.log(n / df) if df > 0 else 0.0

    def _compute_all_tf(self) -> None:
        """Compute TF for every (term, document) pair.

        TF = frequency / total_words_in_document. Normalised by document
        length so longer documents don't get unfair advantage.
        """
        for term, postings in self.index.items():
            for url, stats in postings.items():
                doc = self.documents.get(url)
                if doc and doc.total_words > 0:
                    stats.tf = stats.frequency / doc.total_words

    def get_entry(self, word: str) -> Optional[Dict[str, WordStats]]:
        """Get the inverted index entry for a word."""
        return self.index.get(word.lower())

    def get_document_count(self) -> int:
        """Return the total number of indexed documents."""
        return len(self.documents)

    def get_term_count(self) -> int:
        """Return the total number of unique terms."""
        return len(self.index)

    def save_index(self, filepath: str = DEFAULT_INDEX_PATH) -> None:
        """Serialize and save the index to a JSON file.

        Stores metadata, document info, inverted index, and IDF scores.
        Creates parent directories if they don't exist.
        """
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "metadata": {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "total_documents": len(self.documents),
                "total_terms": len(self.index),
            },
            "documents": {
                url: {
                    "url": doc.url,
                    "title": doc.title,
                    "total_words": doc.total_words,
                    "crawled_at": doc.crawled_at,
                    "full_text": doc.full_text,
                }
                for url, doc in self.documents.items()
            },
            "index": {
                term: {
                    url: {
                        "frequency": stats.frequency,
                        "positions": stats.positions,
                        "tf": stats.tf,
                    }
                    for url, stats in postings.items()
                }
                for term, postings in self.index.items()
            },
            "idf": self.idf_scores,
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        size_kb = path.stat().st_size / 1024
        print(f"Index saved to {filepath} ({size_kb:.0f} KB)")

    def load_index(self, filepath: str = DEFAULT_INDEX_PATH) -> None:
        """Load the index from a JSON file.

        Reconstructs documents, index, and IDF scores from the saved
        JSON. Raises FileNotFoundError or ValueError on bad input.
        """
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Index file not found: {filepath}")

        with open(path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid index file format: {e}")

        self.documents.clear()
        self.index.clear()
        self.idf_scores.clear()

        for url, doc_data in data.get("documents", {}).items():
            self.documents[url] = DocumentMeta(
                url=doc_data["url"],
                title=doc_data["title"],
                total_words=doc_data["total_words"],
                crawled_at=doc_data["crawled_at"],
                full_text=doc_data.get("full_text", ""),
            )

        for term, postings in data.get("index", {}).items():
            self.index[term] = {}
            for url, stats_data in postings.items():
                self.index[term][url] = WordStats(
                    frequency=stats_data["frequency"],
                    positions=stats_data["positions"],
                    tf=stats_data["tf"],
                )

        self.idf_scores = data.get("idf", {})

        total_terms = len(self.index)
        total_docs = len(self.documents)
        print(f"Index loaded: {total_terms} terms, {total_docs} documents")
