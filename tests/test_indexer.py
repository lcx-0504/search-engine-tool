"""Tests for the indexer module."""

import json

import pytest

from src.indexer import Indexer


class TestTokenize:
    """Tests for text tokenization."""

    def test_basic_tokenization(self):
        indexer = Indexer()
        tokens = indexer.tokenize("Hello World")
        assert tokens == ["hello", "world"]

    def test_case_insensitive(self):
        indexer = Indexer()
        tokens = indexer.tokenize("Good GOOD gOoD")
        assert all(t == "good" for t in tokens)

    def test_punctuation_removal(self):
        indexer = Indexer()
        tokens = indexer.tokenize("Hello, world! How are you?")
        assert "hello" in tokens
        assert "world" in tokens
        assert "," not in tokens

    def test_apostrophe_preserved(self):
        indexer = Indexer()
        tokens = indexer.tokenize("don't it's won't")
        assert "don't" in tokens
        assert "it's" in tokens

    def test_empty_string(self):
        indexer = Indexer()
        tokens = indexer.tokenize("")
        assert tokens == []

    def test_special_characters_only(self):
        indexer = Indexer()
        tokens = indexer.tokenize("!@#$%^&*()")
        assert tokens == []

    def test_unicode_quotes(self):
        indexer = Indexer()
        tokens = indexer.tokenize("“The world is beautiful.”")
        assert "the" in tokens
        assert "world" in tokens


class TestBuildIndex:
    """Tests for index construction."""

    def test_build_index_basic(self, built_indexer):
        assert built_indexer.get_term_count() > 0
        assert built_indexer.get_document_count() > 0

    def test_word_in_index(self, built_indexer):
        entry = built_indexer.get_entry("world")
        assert entry is not None
        assert len(entry) >= 1

    def test_case_insensitive_lookup(self, built_indexer):
        entry_lower = built_indexer.get_entry("world")
        entry_upper = built_indexer.get_entry("World")
        assert entry_lower == entry_upper

    def test_word_frequency(self, built_indexer):
        entry = built_indexer.get_entry("world")
        assert entry is not None
        for url, stats in entry.items():
            assert stats.frequency > 0

    def test_word_positions(self, built_indexer):
        entry = built_indexer.get_entry("world")
        assert entry is not None
        for url, stats in entry.items():
            assert len(stats.positions) == stats.frequency

    def test_tf_computed(self, built_indexer):
        entry = built_indexer.get_entry("world")
        assert entry is not None
        for url, stats in entry.items():
            assert stats.tf > 0.0

    def test_idf_computed(self, built_indexer):
        assert len(built_indexer.idf_scores) > 0
        assert "world" in built_indexer.idf_scores

    def test_nonexistent_word(self, built_indexer):
        entry = built_indexer.get_entry("xyzzyspoon")
        assert entry is None

    def test_author_indexed(self, built_indexer):
        entry = built_indexer.get_entry("einstein")
        assert entry is not None

    def test_tag_indexed(self, built_indexer):
        entry = built_indexer.get_entry("change")
        assert entry is not None

    def test_empty_crawl_data(self):
        indexer = Indexer()
        indexer.build_index({"pages": [], "authors": {}})
        assert indexer.get_term_count() == 0
        assert indexer.get_document_count() == 0

    def test_author_description_indexed(self, built_indexer):
        entry = built_indexer.get_entry("physicist")
        assert entry is not None

    def test_author_born_date_indexed(self, built_indexer):
        entry = built_indexer.get_entry("march")
        assert entry is not None

    def test_author_born_location_indexed(self, built_indexer):
        entry = built_indexer.get_entry("ulm")
        assert entry is not None


class TestSaveLoad:
    """Tests for index serialization and deserialization."""

    def test_save_creates_file(self, built_indexer, tmp_path):
        filepath = str(tmp_path / "test_index.json")
        built_indexer.save_index(filepath)
        assert (tmp_path / "test_index.json").exists()

    def test_save_valid_json(self, built_indexer, tmp_path):
        filepath = str(tmp_path / "test_index.json")
        built_indexer.save_index(filepath)
        with open(filepath) as f:
            data = json.load(f)
        assert "metadata" in data
        assert "index" in data
        assert "documents" in data

    def test_save_load_roundtrip(self, built_indexer, tmp_path):
        filepath = str(tmp_path / "test_index.json")
        built_indexer.save_index(filepath)

        new_indexer = Indexer()
        new_indexer.load_index(filepath)

        assert new_indexer.get_term_count() == built_indexer.get_term_count()
        assert new_indexer.get_document_count() == built_indexer.get_document_count()

        for term in built_indexer.index:
            assert term in new_indexer.index
            for url in built_indexer.index[term]:
                orig = built_indexer.index[term][url]
                loaded = new_indexer.index[term][url]
                assert orig.frequency == loaded.frequency
                assert orig.positions == loaded.positions

    def test_load_nonexistent_file(self):
        indexer = Indexer()
        with pytest.raises(FileNotFoundError):
            indexer.load_index("/nonexistent/path/index.json")

    def test_load_corrupted_file(self, tmp_path):
        filepath = str(tmp_path / "bad.json")
        with open(filepath, "w") as f:
            f.write("not valid json {{{")

        indexer = Indexer()
        with pytest.raises(ValueError):
            indexer.load_index(filepath)

    def test_load_empty_file(self, tmp_path):
        filepath = str(tmp_path / "empty.json")
        with open(filepath, "w") as f:
            f.write("")

        indexer = Indexer()
        with pytest.raises(ValueError):
            indexer.load_index(filepath)

    def test_save_overwrite(self, built_indexer, tmp_path):
        filepath = str(tmp_path / "test_index.json")
        built_indexer.save_index(filepath)
        size1 = (tmp_path / "test_index.json").stat().st_size
        built_indexer.save_index(filepath)
        size2 = (tmp_path / "test_index.json").stat().st_size
        assert size1 == size2
