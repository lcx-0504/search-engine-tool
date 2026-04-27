"""Shared test fixtures for the search engine test suite."""

import pytest

SAMPLE_QUOTE_HTML = """
<html>
<body>
<div class="quote" itemscope itemtype="http://schema.org/CreativeWork">
    <span class="text" itemprop="text">"The world as we have created it is a process of our thinking. It cannot be changed without changing our thinking."</span>
    <span>by <small class="author" itemprop="author">Albert Einstein</small>
    <a href="/author/Albert-Einstein">(about)</a>
    </span>
    <div class="tags">
        Tags:
        <a class="tag" href="/tag/change/page/1/">change</a>
        <a class="tag" href="/tag/deep-thoughts/page/1/">deep-thoughts</a>
        <a class="tag" href="/tag/thinking/page/1/">thinking</a>
        <a class="tag" href="/tag/world/page/1/">world</a>
    </div>
</div>
<div class="quote" itemscope itemtype="http://schema.org/CreativeWork">
    <span class="text" itemprop="text">"It is our choices, Harry, that show what we truly are, far more than our abilities."</span>
    <span>by <small class="author" itemprop="author">J.K. Rowling</small>
    <a href="/author/J-K-Rowling">(about)</a>
    </span>
    <div class="tags">
        Tags:
        <a class="tag" href="/tag/abilities/page/1/">abilities</a>
        <a class="tag" href="/tag/choices/page/1/">choices</a>
    </div>
</div>
<nav>
    <ul class="pager">
        <li class="next">
            <a href="/page/2/">Next <span aria-hidden="true">&rarr;</span></a>
        </li>
    </ul>
</nav>
</body>
</html>
"""

SAMPLE_LAST_PAGE_HTML = """
<html>
<body>
<div class="quote" itemscope itemtype="http://schema.org/CreativeWork">
    <span class="text" itemprop="text">"A day without sunshine is like, you know, night."</span>
    <span>by <small class="author" itemprop="author">Steve Martin</small>
    <a href="/author/Steve-Martin">(about)</a>
    </span>
    <div class="tags">
        Tags:
        <a class="tag" href="/tag/humor/page/1/">humor</a>
    </div>
</div>
<nav>
    <ul class="pager">
        <li class="previous">
            <a href="/page/9/">Previous <span aria-hidden="true">&larr;</span></a>
        </li>
    </ul>
</nav>
</body>
</html>
"""

SAMPLE_AUTHOR_HTML = """
<html>
<body>
<div class="author-details">
    <h3 class="author-title">Albert Einstein</h3>
    <p>
        <span class="author-born-date">March 14, 1879</span>,
        <span class="author-born-location">in Ulm, Germany</span>
    </p>
    <div class="author-description">
        Albert Einstein was a German-born theoretical physicist who developed
        the theory of relativity. He received the Nobel Prize in Physics in 1921.
    </div>
</div>
</body>
</html>
"""

SAMPLE_EMPTY_PAGE_HTML = """
<html>
<body>
<div class="container">
    <div class="row">
        <div class="col-md-8">
            <h3 class="text-center">No quotes found!</h3>
        </div>
    </div>
</div>
</body>
</html>
"""


@pytest.fixture
def sample_crawl_data():
    """Minimal crawl data for testing indexer and search."""
    return {
        "pages": [
            {
                "url": "https://quotes.toscrape.com/page/1/",
                "quotes": [
                    {
                        "text": "“The world as we have created it is a process of our thinking.”",
                        "author": "Albert Einstein",
                        "tags": ["change", "thinking", "world"],
                        "author_url": "https://quotes.toscrape.com/author/Albert-Einstein",
                    },
                    {
                        "text": "“It is our choices that show what we truly are.”",
                        "author": "J.K. Rowling",
                        "tags": ["abilities", "choices"],
                        "author_url": "https://quotes.toscrape.com/author/J-K-Rowling",
                    },
                ],
                "next_page": "https://quotes.toscrape.com/page/2/",
            },
            {
                "url": "https://quotes.toscrape.com/page/2/",
                "quotes": [
                    {
                        "text": "“The world is a beautiful place and worth the fighting for.”",
                        "author": "Ernest Hemingway",
                        "tags": ["world"],
                        "author_url": "https://quotes.toscrape.com/author/Ernest-Hemingway",
                    },
                ],
                "next_page": None,
            },
        ],
        "authors": {
            "https://quotes.toscrape.com/author/Albert-Einstein": {
                "name": "Albert Einstein",
                "born_date": "March 14, 1879",
                "born_location": "in Ulm, Germany",
                "description": "Albert Einstein was a German-born theoretical physicist.",
            }
        },
        "pages_crawled": 2,
    }


@pytest.fixture
def built_indexer(sample_crawl_data):
    """An Indexer with a pre-built index from sample data."""
    from src.indexer import Indexer
    indexer = Indexer()
    indexer.build_index(sample_crawl_data)
    return indexer


@pytest.fixture
def search_engine(built_indexer):
    """A SearchEngine backed by the sample index."""
    from src.search import SearchEngine
    return SearchEngine(built_indexer)
