"""Search engine with TF-IDF ranking, phrase search, and query suggestions."""

from typing import Dict, List, Optional, Set

from src.indexer import Indexer
from src.models import SearchResult, WordStats


class SearchEngine:
    """Provides search capabilities over an inverted index."""

    def __init__(self, indexer: Indexer) -> None:
        self.indexer = indexer

    def print_index(self, word: str) -> Optional[Dict[str, WordStats]]:
        """Print the inverted index entry for a given word.

        Shows document count, IDF score, and per-document stats
        including frequency, positions, TF, and TF-IDF.
        """
        entry = self.indexer.get_entry(word)
        if entry is None:
            print(f"Word '{word}' not found in the index.")
            return None

        idf = self.indexer.idf_scores.get(word.lower(), 0.0)
        print(f'Index entry for "{word}":')
        print(f"  Found in {len(entry)} document(s) (IDF: {idf:.3f})")
        print()

        for i, (url, stats) in enumerate(entry.items(), 1):
            tf_idf = stats.tf * idf
            print(f"  {i}. {url}")
            print(f"     Frequency: {stats.frequency}, "
                  f"Positions: {stats.positions}")
            print(f"     TF: {stats.tf:.4f}, TF-IDF: {tf_idf:.4f}")

        return entry

    def find(self, query: str) -> List[SearchResult]:
        """Find pages containing ALL query terms (AND logic).

        Tokenizes the query, intersects document sets for each term,
        and ranks results by total TF-IDF score across all terms.
        Returns an empty list if any term is missing from the index.
        """
        terms = self.indexer.tokenize(query)
        if not terms:
            print("Empty query. Please enter at least one search term.")
            return []

        # Look up each term and collect its document set
        doc_sets: List[Set[str]] = []
        for term in terms:
            entry = self.indexer.get_entry(term)
            if entry is None:
                print(f"No results found: term '{term}' does not exist in the index.")
                return []
            doc_sets.append(set(entry.keys()))

        # AND logic: intersect all document sets
        matching_urls = doc_sets[0]
        for s in doc_sets[1:]:
            matching_urls &= s

        if not matching_urls:
            print(f"No pages contain all the terms: {', '.join(terms)}")
            return []

        # Score each matching document by summing TF-IDF across query terms
        results: List[SearchResult] = []
        for url in matching_urls:
            total_score = 0.0
            matched: Dict[str, WordStats] = {}
            for term in terms:
                stats = self.indexer.index[term][url]
                idf = self.indexer.idf_scores.get(term, 0.0)
                total_score += stats.tf * idf
                matched[term] = stats

            snippet = self._generate_snippet(url, terms)
            results.append(SearchResult(
                url=url,
                score=total_score,
                matched_terms=matched,
                snippet=snippet,
            ))

        results.sort(key=lambda r: r.score, reverse=True)
        return results

    def find_or(self, query: str) -> List[SearchResult]:
        """Find pages containing ANY query term (OR logic).

        Unlike find(), returns documents matching at least one term.
        Documents matching more terms and with higher TF-IDF rank higher.
        """
        terms = self.indexer.tokenize(query)
        if not terms:
            print("Empty query. Please enter at least one search term.")
            return []

        # Collect all documents matching any term
        doc_scores: Dict[str, Dict[str, WordStats]] = {}
        valid_terms = []
        for term in terms:
            entry = self.indexer.get_entry(term)
            if entry is None:
                continue
            valid_terms.append(term)
            for url, stats in entry.items():
                if url not in doc_scores:
                    doc_scores[url] = {}
                doc_scores[url][term] = stats

        if not doc_scores:
            print(f"No results found for any of: {', '.join(terms)}")
            return []

        results: List[SearchResult] = []
        for url, matched in doc_scores.items():
            total_score = 0.0
            for term, stats in matched.items():
                idf = self.indexer.idf_scores.get(term, 0.0)
                total_score += stats.tf * idf

            snippet = self._generate_snippet(url, valid_terms)
            results.append(SearchResult(
                url=url,
                score=total_score,
                matched_terms=matched,
                snippet=snippet,
            ))

        results.sort(key=lambda r: r.score, reverse=True)
        return results

    def find_phrase(self, phrase: str) -> List[SearchResult]:
        """Find pages where query terms appear as an adjacent phrase.

        Uses stored token positions to verify that terms appear
        consecutively in the document, not just anywhere on the page.
        """
        terms = self.indexer.tokenize(phrase)
        if not terms:
            print("Empty query. Please enter at least one search term.")
            return []

        if len(terms) == 1:
            return self.find(phrase)

        # All terms must exist in the index
        for term in terms:
            if self.indexer.get_entry(term) is None:
                print(f"No results found: term '{term}' does not exist in the index.")
                return []

        # Find documents containing all terms
        doc_sets = [set(self.indexer.index[t].keys()) for t in terms]
        candidates = doc_sets[0]
        for s in doc_sets[1:]:
            candidates &= s

        results: List[SearchResult] = []
        for url in candidates:
            # Check if terms appear as consecutive positions
            first_positions = self.indexer.index[terms[0]][url].positions
            for start_pos in first_positions:
                match = True
                for offset, term in enumerate(terms[1:], 1):
                    if (start_pos + offset) not in self.indexer.index[term][url].positions:
                        match = False
                        break
                if match:
                    # Phrase found in this document
                    total_score = 0.0
                    matched: Dict[str, WordStats] = {}
                    for term in terms:
                        stats = self.indexer.index[term][url]
                        idf = self.indexer.idf_scores.get(term, 0.0)
                        total_score += stats.tf * idf
                        matched[term] = stats

                    snippet = self._generate_snippet(url, terms)
                    results.append(SearchResult(
                        url=url,
                        score=total_score,
                        matched_terms=matched,
                        snippet=snippet,
                    ))
                    break

        results.sort(key=lambda r: r.score, reverse=True)
        return results

    def _generate_snippet(self, url: str, terms: List[str],
                          context_chars: int = 80) -> str:
        """Generate a text snippet around the first matched term.

        Extracts a window of context_chars characters around the first
        occurrence of any query term in the document's full text.
        """
        doc = self.indexer.documents.get(url)
        if not doc or not doc.full_text:
            return ""

        text = doc.full_text
        text_lower = text.lower()

        # Find the earliest occurrence of any query term
        best_pos = len(text)
        for term in terms:
            pos = text_lower.find(term)
            if pos != -1 and pos < best_pos:
                best_pos = pos

        if best_pos == len(text):
            return ""

        start = max(0, best_pos - context_chars // 2)
        end = min(len(text), best_pos + context_chars // 2)

        snippet = text[start:end].strip()
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."

        return snippet

    def suggest(self, prefix: str, max_results: int = 5) -> List[str]:
        """Suggest words from the index matching a prefix.

        Returns up to max_results terms, sorted by document frequency
        (most common first) to surface the most useful suggestions.
        """
        prefix = prefix.lower().strip()
        if not prefix:
            return []

        suggestions: List[tuple] = []
        for term in self.indexer.index:
            if term.startswith(prefix):
                df = len(self.indexer.index[term])
                suggestions.append((term, df))

        suggestions.sort(key=lambda x: x[1], reverse=True)
        return [s[0] for s in suggestions[:max_results]]

    def format_results(self, results: List[SearchResult], query: str) -> str:
        """Format search results for display.

        Shows query terms (joined with AND), result count, and for each
        result: rank, TF-IDF score, URL, snippet, and per-term match details.
        """
        terms = self.indexer.tokenize(query)
        lines = [f'Searching for: {" AND ".join(terms)}']
        lines.append(f"Found {len(results)} result(s):")
        lines.append("")

        for i, result in enumerate(results, 1):
            lines.append(f"  {i}. [Score: {result.score:.4f}] {result.url}")
            if result.snippet:
                lines.append(f"     {result.snippet}")
            for term, stats in result.matched_terms.items():
                lines.append(f"     '{term}': frequency={stats.frequency}, "
                             f"positions={stats.positions}")
        return "\n".join(lines)
