# Search Engine Tool

A Python-based search engine tool that crawls [quotes.toscrape.com](https://quotes.toscrape.com/), builds an inverted index, and allows users to search for pages containing specific terms.

## Project Overview

This tool was developed as part of COMP3011 (Web Services and Web Data) Coursework 2. It provides:

- **Web Crawling**: Crawls all pages of the target website with a polite 6-second delay between requests
- **Inverted Indexing**: Builds an inverted index storing word statistics (frequency, positions) for each page
- **Search**: Allows users to find pages containing specific search terms (case-insensitive)

## Installation

```bash
# Clone the repository
git clone https://github.com/your-username/search-engine-tool.git
cd search-engine-tool

# Install dependencies
pip install -r requirements.txt
```

## Usage

Run the tool:

```bash
python -m src.main
```

### Commands

#### `build` - Crawl and build the index
```
> build
```
Crawls the website, builds the inverted index, and saves it to the file system.

#### `load` - Load index from file
```
> load
```
Loads a previously built index from the file system.

#### `print <word>` - Print inverted index for a word
```
> print nonsense
```
Displays the inverted index entry for the specified word.

#### `find <words>` - Find pages containing words
```
> find indifference
> find good friends
```
Returns a list of all pages containing all specified words.

## Testing

```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=src --cov-report=html
```

## Dependencies

- `requests` - HTTP library for web crawling
- `beautifulsoup4` - HTML parsing library
- `pytest` - Testing framework
- `pytest-cov` - Test coverage reporting
