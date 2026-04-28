"""Tests for the CLI main module."""

from unittest.mock import MagicMock, patch

import pytest

from src.main import handle_build, handle_find, handle_load, handle_print, handle_stats, main


class TestHandleBuild:
    """Tests for the build command handler."""

    @patch("src.main.Crawler")
    def test_build_success(self, mock_crawler_cls, built_indexer, tmp_path):
        mock_crawler = MagicMock()
        mock_crawler.crawl_all.return_value = {
            "pages": [],
            "authors": {},
            "pages_crawled": 0,
        }
        mock_crawler_cls.return_value = mock_crawler

        from src.indexer import Indexer
        indexer = Indexer()
        with patch("src.main.INDEX_PATH", str(tmp_path / "idx.json")):
            handle_build(indexer)

        mock_crawler.crawl_all.assert_called_once()


class TestHandleLoad:
    """Tests for the load command handler."""

    def test_load_success(self, built_indexer, tmp_path):
        filepath = str(tmp_path / "idx.json")
        built_indexer.save_index(filepath)

        from src.indexer import Indexer
        indexer = Indexer()
        with patch("src.main.INDEX_PATH", filepath):
            handle_load(indexer)

        assert indexer.get_term_count() > 0

    def test_load_file_not_found(self):
        from src.indexer import Indexer
        indexer = Indexer()
        with patch("src.main.INDEX_PATH", "/nonexistent/file.json"):
            handle_load(indexer)
        assert indexer.get_term_count() == 0


class TestHandlePrint:
    """Tests for the print command handler."""

    def test_print_existing_word(self, search_engine):
        handle_print(search_engine, "world")

    def test_print_missing_word(self, search_engine):
        handle_print(search_engine, "xyzzy")

    def test_print_without_index(self, capsys):
        from src.indexer import Indexer
        from src.search import SearchEngine
        engine = SearchEngine(Indexer())
        handle_print(engine, "world")
        output = capsys.readouterr().out
        assert "No index loaded" in output


class TestHandleFind:
    """Tests for the find command handler."""

    def test_find_single_word(self, search_engine):
        handle_find(search_engine, "world")

    def test_find_multi_word(self, search_engine):
        handle_find(search_engine, "world thinking")

    def test_find_no_results(self, search_engine):
        handle_find(search_engine, "xyzzy")

    def test_find_without_index(self, capsys):
        from src.indexer import Indexer
        from src.search import SearchEngine
        engine = SearchEngine(Indexer())
        handle_find(engine, "world")
        output = capsys.readouterr().out
        assert "No index loaded" in output

    def test_find_auto_suggest(self, search_engine, capsys):
        """When a term is not found, suggestions are shown automatically."""
        handle_find(search_engine, "wor")
        output = capsys.readouterr().out
        assert "Did you mean" in output

    def test_find_phrase_search(self, search_engine, capsys):
        """Quoted query triggers phrase search."""
        handle_find(search_engine, '"our thinking"')
        output = capsys.readouterr().out
        assert "Score" in output


class TestHandleStats:
    """Tests for the stats command handler."""

    def test_stats_with_index(self, search_engine, capsys):
        handle_stats(search_engine)
        output = capsys.readouterr().out
        assert "Documents:" in output
        assert "Unique terms:" in output
        assert "Top 10" in output

    def test_stats_without_index(self, capsys):
        from src.indexer import Indexer
        from src.search import SearchEngine
        engine = SearchEngine(Indexer())
        handle_stats(engine)
        output = capsys.readouterr().out
        assert "No index loaded" in output


class TestMainLoop:
    """Tests for the interactive main loop."""

    @patch("builtins.input", side_effect=["quit"])
    def test_quit(self, mock_input):
        main()

    @patch("builtins.input", side_effect=["exit"])
    def test_exit(self, mock_input):
        main()

    @patch("builtins.input", side_effect=["", "q"])
    def test_empty_input_then_quit(self, mock_input):
        main()

    @patch("builtins.input", side_effect=["badcommand", "quit"])
    def test_unknown_command(self, mock_input):
        main()

    @patch("builtins.input", side_effect=["print", "quit"])
    def test_print_no_args(self, mock_input):
        main()

    @patch("builtins.input", side_effect=["find", "quit"])
    def test_find_no_args(self, mock_input):
        main()

    @patch("builtins.input", side_effect=EOFError)
    def test_eof(self, mock_input):
        main()

    @patch("builtins.input", side_effect=KeyboardInterrupt)
    def test_keyboard_interrupt(self, mock_input):
        main()

    @patch("builtins.input", side_effect=["print world", "quit"])
    def test_print_word_without_index(self, mock_input):
        main()

    @patch("builtins.input", side_effect=["find world", "quit"])
    def test_find_word_without_index(self, mock_input):
        main()
