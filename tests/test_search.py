"""Tests for the search engine module."""

import pytest

from src.search import SearchEngine


class TestPrintIndex:
    """Tests for the print command."""

    def test_print_existing_word(self, search_engine):
        entry = search_engine.print_index("world")
        assert entry is not None
        assert len(entry) >= 1

    def test_print_nonexistent_word(self, search_engine):
        entry = search_engine.print_index("xyzzyspoon")
        assert entry is None

    def test_print_case_insensitive(self, search_engine):
        entry1 = search_engine.print_index("world")
        entry2 = search_engine.print_index("World")
        assert entry1 == entry2


class TestFind:
    """Tests for the find command."""

    def test_find_single_word(self, search_engine):
        results = search_engine.find("world")
        assert len(results) >= 1
        assert all(r.url for r in results)

    def test_find_multi_word_and(self, search_engine):
        results = search_engine.find("world thinking")
        assert len(results) >= 1
        for r in results:
            assert "world" in r.matched_terms
            assert "thinking" in r.matched_terms

    def test_find_no_results(self, search_engine):
        results = search_engine.find("xyzzyspoon")
        assert results == []

    def test_find_empty_query(self, search_engine):
        results = search_engine.find("")
        assert results == []

    def test_find_results_sorted_by_score(self, search_engine):
        results = search_engine.find("world")
        if len(results) > 1:
            for i in range(len(results) - 1):
                assert results[i].score >= results[i + 1].score

    def test_find_case_insensitive(self, search_engine):
        results_lower = search_engine.find("world")
        results_upper = search_engine.find("World")
        assert len(results_lower) == len(results_upper)

    def test_find_partial_match_fails_and(self, search_engine):
        """If one term doesn't exist, AND logic returns no results."""
        results = search_engine.find("world xyzzyspoon")
        assert results == []

    def test_find_score_is_positive(self, search_engine):
        results = search_engine.find("world")
        for r in results:
            assert r.score >= 0.0


class TestFindOr:
    """Tests for OR search logic."""

    def test_or_single_word(self, search_engine):
        results = search_engine.find_or("world")
        assert len(results) >= 1

    def test_or_returns_more_than_and(self, search_engine):
        """OR should return at least as many results as AND."""
        and_results = search_engine.find("world change")
        or_results = search_engine.find_or("world change")
        assert len(or_results) >= len(and_results)

    def test_or_no_results(self, search_engine):
        results = search_engine.find_or("xyzzyspoon")
        assert results == []

    def test_or_empty_query(self, search_engine):
        results = search_engine.find_or("")
        assert results == []

    def test_or_partial_terms_exist(self, search_engine):
        """OR still returns results even if only some terms exist."""
        results = search_engine.find_or("world xyzzyspoon")
        assert len(results) >= 1


class TestSuggest:
    """Tests for query suggestions."""

    def test_suggest_basic(self, search_engine):
        suggestions = search_engine.suggest("wor")
        assert "world" in suggestions

    def test_suggest_empty_prefix(self, search_engine):
        suggestions = search_engine.suggest("")
        assert suggestions == []

    def test_suggest_no_match(self, search_engine):
        suggestions = search_engine.suggest("zzz")
        assert suggestions == []

    def test_suggest_max_results(self, search_engine):
        suggestions = search_engine.suggest("t", max_results=3)
        assert len(suggestions) <= 3


class TestPhraseSearch:
    """Tests for phrase (adjacent terms) search."""

    def test_phrase_found(self, search_engine):
        results = search_engine.find_phrase("our thinking")
        assert len(results) >= 1

    def test_phrase_not_adjacent(self, search_engine):
        """Terms exist in same doc but not adjacent — should not match."""
        results = search_engine.find_phrase("world choices")
        assert results == []

    def test_phrase_single_word_fallback(self, search_engine):
        results = search_engine.find_phrase("world")
        assert len(results) >= 1

    def test_phrase_nonexistent_term(self, search_engine):
        results = search_engine.find_phrase("xyzzy spoon")
        assert results == []

    def test_phrase_empty(self, search_engine):
        results = search_engine.find_phrase("")
        assert results == []


class TestSnippet:
    """Tests for snippet generation."""

    def test_snippet_in_results(self, search_engine):
        results = search_engine.find("world")
        assert any(r.snippet for r in results)

    def test_snippet_contains_term(self, search_engine):
        results = search_engine.find("world")
        for r in results:
            if r.snippet:
                assert "world" in r.snippet.lower()

    def test_snippet_highlights_term(self, search_engine):
        """Matched terms should be highlighted with *UPPERCASE*."""
        results = search_engine.find("world")
        for r in results:
            if r.snippet:
                assert "*WORLD*" in r.snippet

    def test_snippet_empty_for_missing_text(self, search_engine):
        snippet = search_engine._generate_snippet(
            "https://nonexistent.url/", ["world"])
        assert snippet == ""


class TestFormatResults:
    """Tests for result formatting."""

    def test_format_results_basic(self, search_engine):
        results = search_engine.find("world")
        output = search_engine.format_results(results, "world")
        assert "world" in output.lower()
        assert "Score" in output

    def test_format_results_empty(self, search_engine):
        output = search_engine.format_results([], "nothing")
        assert "0 result" in output
