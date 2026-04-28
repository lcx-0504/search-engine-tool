"""Search engine with TF-IDF ranking and query suggestions."""

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

            results.append(SearchResult(
                url=url,
                score=total_score,
                matched_terms=matched,
            ))

        results.sort(key=lambda r: r.score, reverse=True)
        return results

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
        result: rank, TF-IDF score, URL, and per-term match details.
        """
        terms = self.indexer.tokenize(query)
        lines = [f'Searching for: {" AND ".join(terms)}']
        lines.append(f"Found {len(results)} result(s):")
        lines.append("")

        for i, result in enumerate(results, 1):
            lines.append(f"  {i}. [Score: {result.score:.4f}] {result.url}")
            for term, stats in result.matched_terms.items():
                lines.append(f"     '{term}': frequency={stats.frequency}, "
                             f"positions={stats.positions}")
        return "\n".join(lines)
