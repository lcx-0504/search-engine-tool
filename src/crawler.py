"""Web crawler for quotes.toscrape.com with politeness control."""

import logging
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class Crawler:
    """Crawls quotes.toscrape.com respecting a politeness window."""

    BASE_URL = "https://quotes.toscrape.com/"

    def __init__(self, base_url: str = BASE_URL, delay: float = 6.0) -> None:
        self.base_url = base_url
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "COMP3011-SearchEngine/1.0"
        })
        self._last_request_time: float = 0.0
        self.failed_urls: List[str] = []

    def _wait(self) -> None:
        """Enforce minimum delay between consecutive requests."""
        elapsed = time.monotonic() - self._last_request_time
        if self._last_request_time > 0 and elapsed < self.delay:
            wait_time = self.delay - elapsed
            logger.info(f"Waiting {wait_time:.1f}s (politeness window)")
            time.sleep(wait_time)

    def fetch_page(self, url: str, retries: int = 3) -> Optional[BeautifulSoup]:
        """Fetch and parse a single page with retry logic."""
        for attempt in range(1, retries + 1):
            try:
                self._wait()
                self._last_request_time = time.monotonic()
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                return BeautifulSoup(response.text, "html.parser")
            except requests.RequestException as e:
                logger.warning(f"Attempt {attempt}/{retries} failed for {url}: {e}")
                if attempt < retries:
                    time.sleep(2 ** attempt)
        logger.error(f"Failed to fetch {url} after {retries} attempts")
        return None

    def parse_quotes_page(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Extract all quotes and metadata from a quotes page."""
        quotes: List[Dict[str, Any]] = []
        for quote_div in soup.select("div.quote"):
            text_el = quote_div.select_one("span.text")
            author_el = quote_div.select_one("small.author")
            tags = [tag.get_text() for tag in quote_div.select("a.tag")]
            author_link_el = quote_div.select_one("a[href*='/author/']")

            if text_el and author_el:
                quotes.append({
                    "text": text_el.get_text(strip=True),
                    "author": author_el.get_text(strip=True),
                    "tags": tags,
                    "author_url": urljoin(
                        self.base_url,
                        author_link_el["href"]
                    ) if author_link_el else None,
                })

        next_page = self._get_next_page_url(soup)
        return {"url": url, "quotes": quotes, "next_page": next_page}

    def _get_next_page_url(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract the next page URL, or None if on the last page."""
        next_li = soup.select_one("li.next > a")
        if next_li and next_li.get("href"):
            return urljoin(self.base_url, next_li["href"])
        return None

    def parse_author_page(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract author information from an author detail page."""
        name_el = soup.select_one("h3.author-title")
        born_date_el = soup.select_one("span.author-born-date")
        born_location_el = soup.select_one("span.author-born-location")
        description_el = soup.select_one("div.author-description")

        return {
            "name": name_el.get_text(strip=True) if name_el else "",
            "born_date": born_date_el.get_text(strip=True) if born_date_el else "",
            "born_location": born_location_el.get_text(strip=True) if born_location_el else "",
            "description": description_el.get_text(strip=True) if description_el else "",
        }

    def _retry_failed(self, pages: List[Dict[str, Any]],
                      authors: Dict[str, Dict[str, str]]) -> None:
        """Retry all URLs that failed during the initial crawl."""
        if not self.failed_urls:
            return

        retry_urls = self.failed_urls.copy()
        self.failed_urls.clear()
        print(f"\nRetrying {len(retry_urls)} failed URL(s)...")

        for url in retry_urls:
            soup = self.fetch_page(url)
            if soup is None:
                self.failed_urls.append(url)
                print(f"  Retry failed: {url}")
                continue

            if "/author/" in url:
                author_info = self.parse_author_page(soup)
                authors[url] = author_info
                print(f"  Retry succeeded (author): {url}")
            else:
                page_data = self.parse_quotes_page(soup, url)
                pages.append(page_data)
                print(f"  Retry succeeded (page): {url}")

    def crawl_all(self) -> Dict[str, Any]:
        """
        Crawl the entire website: all quote pages and author detail pages.
        Failed URLs are collected and retried in a final pass.

        Returns a dict with 'pages', 'authors', 'pages_crawled',
        and 'failed_urls' keys.
        """
        pages: List[Dict[str, Any]] = []
        authors: Dict[str, Dict[str, str]] = {}
        author_urls_seen: set = set()
        self.failed_urls.clear()
        url: Optional[str] = self.base_url
        page_num = 0

        # Phase 1: crawl all quote pages
        while url:
            page_num += 1
            logger.info(f"Crawling page {page_num}: {url}")
            soup = self.fetch_page(url)
            if soup is None:
                self.failed_urls.append(url)
                break

            page_data = self.parse_quotes_page(soup, url)
            pages.append(page_data)
            print(f"  Page {page_num}: {len(page_data['quotes'])} quotes found")

            for quote in page_data["quotes"]:
                author_url = quote.get("author_url")
                if author_url and author_url not in author_urls_seen:
                    author_urls_seen.add(author_url)

            url = page_data["next_page"]

        # Phase 2: crawl all author detail pages
        print(f"Crawling author pages: {len(author_urls_seen)} authors")
        for i, author_url in enumerate(author_urls_seen, 1):
            logger.info(f"Crawling author {i}/{len(author_urls_seen)}: {author_url}")
            soup = self.fetch_page(author_url)
            if soup:
                author_info = self.parse_author_page(soup)
                authors[author_url] = author_info
            else:
                self.failed_urls.append(author_url)

        # Phase 3: retry failed URLs
        self._retry_failed(pages, authors)

        if self.failed_urls:
            print(f"\nWarning: {len(self.failed_urls)} URL(s) still failed after retry:")
            for failed_url in self.failed_urls:
                print(f"  - {failed_url}")

        return {
            "pages": pages,
            "authors": authors,
            "pages_crawled": page_num,
            "failed_urls": self.failed_urls,
        }
