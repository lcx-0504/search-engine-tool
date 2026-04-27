"""Tests for the web crawler module."""

import time
from unittest.mock import MagicMock, patch

import pytest
from bs4 import BeautifulSoup

from src.crawler import Crawler
from tests.conftest import (
    SAMPLE_AUTHOR_HTML,
    SAMPLE_EMPTY_PAGE_HTML,
    SAMPLE_LAST_PAGE_HTML,
    SAMPLE_QUOTE_HTML,
)


@pytest.fixture
def crawler():
    """Create a crawler with a minimal delay for testing."""
    return Crawler(delay=0.0)


class TestFetchPage:
    """Tests for fetching and parsing pages."""

    @patch("src.crawler.requests.Session.get")
    def test_fetch_page_success(self, mock_get, crawler):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = SAMPLE_QUOTE_HTML
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = crawler.fetch_page("https://quotes.toscrape.com/")
        assert result is not None
        assert isinstance(result, BeautifulSoup)

    @patch("src.crawler.requests.Session.get")
    def test_fetch_page_http_error(self, mock_get, crawler):
        from requests.exceptions import HTTPError
        mock_get.return_value.raise_for_status.side_effect = HTTPError("404")
        result = crawler.fetch_page("https://quotes.toscrape.com/bad", retries=1)
        assert result is None

    @patch("src.crawler.requests.Session.get")
    def test_fetch_page_network_error(self, mock_get, crawler):
        from requests.exceptions import ConnectionError
        mock_get.side_effect = ConnectionError("Connection refused")
        result = crawler.fetch_page("https://quotes.toscrape.com/", retries=1)
        assert result is None


class TestPolitenessWindow:
    """Tests for the politeness delay mechanism."""

    def test_wait_enforces_delay(self):
        crawler = Crawler(delay=0.2)
        crawler._last_request_time = time.monotonic()
        start = time.monotonic()
        crawler._wait()
        elapsed = time.monotonic() - start
        assert elapsed >= 0.15

    def test_wait_no_delay_on_first_request(self):
        crawler = Crawler(delay=6.0)
        start = time.monotonic()
        crawler._wait()
        elapsed = time.monotonic() - start
        assert elapsed < 0.1


class TestParseQuotesPage:
    """Tests for parsing quote pages."""

    def test_parse_quotes_basic(self, crawler):
        soup = BeautifulSoup(SAMPLE_QUOTE_HTML, "html.parser")
        result = crawler.parse_quotes_page(soup, "https://quotes.toscrape.com/page/1/")

        assert len(result["quotes"]) == 2
        assert result["quotes"][0]["author"] == "Albert Einstein"
        assert result["quotes"][1]["author"] == "J.K. Rowling"

    def test_parse_quotes_text(self, crawler):
        soup = BeautifulSoup(SAMPLE_QUOTE_HTML, "html.parser")
        result = crawler.parse_quotes_page(soup, "https://quotes.toscrape.com/page/1/")

        assert "world" in result["quotes"][0]["text"].lower()
        assert "choices" in result["quotes"][1]["text"].lower()

    def test_parse_quotes_tags(self, crawler):
        soup = BeautifulSoup(SAMPLE_QUOTE_HTML, "html.parser")
        result = crawler.parse_quotes_page(soup, "https://quotes.toscrape.com/page/1/")

        assert "change" in result["quotes"][0]["tags"]
        assert "thinking" in result["quotes"][0]["tags"]
        assert "choices" in result["quotes"][1]["tags"]

    def test_parse_quotes_author_url(self, crawler):
        soup = BeautifulSoup(SAMPLE_QUOTE_HTML, "html.parser")
        result = crawler.parse_quotes_page(soup, "https://quotes.toscrape.com/page/1/")

        assert "/author/Albert-Einstein" in result["quotes"][0]["author_url"]

    def test_parse_empty_page(self, crawler):
        soup = BeautifulSoup(SAMPLE_EMPTY_PAGE_HTML, "html.parser")
        result = crawler.parse_quotes_page(soup, "https://quotes.toscrape.com/page/11/")
        assert len(result["quotes"]) == 0


class TestNextPageDetection:
    """Tests for pagination link extraction."""

    def test_next_page_exists(self, crawler):
        soup = BeautifulSoup(SAMPLE_QUOTE_HTML, "html.parser")
        next_url = crawler._get_next_page_url(soup)
        assert next_url is not None
        assert "/page/2/" in next_url

    def test_last_page_no_next(self, crawler):
        soup = BeautifulSoup(SAMPLE_LAST_PAGE_HTML, "html.parser")
        next_url = crawler._get_next_page_url(soup)
        assert next_url is None


class TestParseAuthorPage:
    """Tests for parsing author detail pages."""

    def test_parse_author_basic(self, crawler):
        soup = BeautifulSoup(SAMPLE_AUTHOR_HTML, "html.parser")
        result = crawler.parse_author_page(soup)

        assert result["name"] == "Albert Einstein"
        assert result["born_date"] == "March 14, 1879"
        assert "Ulm" in result["born_location"]
        assert "physicist" in result["description"]

    def test_parse_author_missing_fields(self, crawler):
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")
        result = crawler.parse_author_page(soup)
        assert result["name"] == ""
        assert result["born_date"] == ""
        assert result["description"] == ""


class TestCrawlAll:
    """Integration tests for the full crawl process."""

    @patch.object(Crawler, "fetch_page")
    def test_crawl_all_basic(self, mock_fetch, crawler):
        page1_soup = BeautifulSoup(SAMPLE_QUOTE_HTML, "html.parser")
        last_page_soup = BeautifulSoup(SAMPLE_LAST_PAGE_HTML, "html.parser")
        author_soup = BeautifulSoup(SAMPLE_AUTHOR_HTML, "html.parser")

        # page1 -> page2(last) -> 3 author pages (Einstein, Rowling, Martin)
        mock_fetch.side_effect = [
            page1_soup, last_page_soup,
            author_soup, author_soup, author_soup,
        ]

        result = crawler.crawl_all()
        assert result["pages_crawled"] == 2
        assert len(result["pages"]) == 2

    @patch.object(Crawler, "fetch_page")
    def test_crawl_all_fetch_failure(self, mock_fetch, crawler):
        mock_fetch.return_value = None
        result = crawler.crawl_all()
        assert result["pages_crawled"] == 1
        assert len(result["pages"]) == 0


class TestFailedUrlQueue:
    """Tests for the failed URL retry mechanism."""

    @patch.object(Crawler, "fetch_page")
    def test_failed_author_gets_retried(self, mock_fetch, crawler):
        page1_soup = BeautifulSoup(SAMPLE_LAST_PAGE_HTML, "html.parser")
        author_soup = BeautifulSoup(SAMPLE_AUTHOR_HTML, "html.parser")

        # page1 ok -> author fails first time -> author succeeds on retry
        mock_fetch.side_effect = [page1_soup, None, author_soup]

        result = crawler.crawl_all()
        assert len(result["failed_urls"]) == 0
        assert len(result["authors"]) == 1

    @patch.object(Crawler, "fetch_page")
    def test_still_failed_after_retry(self, mock_fetch, crawler):
        page1_soup = BeautifulSoup(SAMPLE_LAST_PAGE_HTML, "html.parser")

        # page1 ok -> author fails -> retry also fails
        mock_fetch.side_effect = [page1_soup, None, None]

        result = crawler.crawl_all()
        assert len(result["failed_urls"]) == 1

    @patch.object(Crawler, "fetch_page")
    def test_no_retry_when_all_succeed(self, mock_fetch, crawler):
        page1_soup = BeautifulSoup(SAMPLE_LAST_PAGE_HTML, "html.parser")
        author_soup = BeautifulSoup(SAMPLE_AUTHOR_HTML, "html.parser")

        mock_fetch.side_effect = [page1_soup, author_soup]

        result = crawler.crawl_all()
        assert len(result["failed_urls"]) == 0

    @patch.object(Crawler, "fetch_page")
    def test_quote_page_failure_added_to_queue(self, mock_fetch, crawler):
        # First page fetch fails immediately
        mock_fetch.side_effect = [None, None]

        result = crawler.crawl_all()
        assert len(result["failed_urls"]) == 1
