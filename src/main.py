"""CLI entry point for the search engine tool."""

import logging
import sys
import time

from src.crawler import Crawler
from src.indexer import Indexer
from src.search import SearchEngine

INDEX_PATH = "data/index.json"


def setup_logging() -> None:
    """Configure logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def handle_build(indexer: Indexer) -> None:
    """Execute the build command: crawl, index, and save."""
    print("Crawling https://quotes.toscrape.com/ ...")
    crawler = Crawler()
    crawl_data = crawler.crawl_all()

    print("\nBuilding index...")
    indexer.build_index(crawl_data)

    print(f"\nSaving index to {INDEX_PATH} ...")
    indexer.save_index(INDEX_PATH)
    print("Done!")


def handle_load(indexer: Indexer) -> None:
    """Execute the load command: load index from file."""
    print(f"Loading index from {INDEX_PATH} ...")
    try:
        indexer.load_index(INDEX_PATH)
        print("Ready for queries.")
    except FileNotFoundError:
        print("Error: Index file not found. Run 'build' first.")
    except ValueError as e:
        print(f"Error: {e}")


def handle_print(engine: SearchEngine, word: str) -> None:
    """Execute the print command: show index entry for a word."""
    if not engine.indexer.documents:
        print("No index loaded. Run 'build' or 'load' first.")
        return
    engine.print_index(word)


def handle_find(engine: SearchEngine, raw_args: str) -> None:
    """Execute the find command: search for pages containing all words.

    Supports phrase search with quotes: find "deep thoughts"
    When no results are found, automatically suggests similar terms
    based on prefix matching to help the user refine their query.
    """
    if not engine.indexer.documents:
        print("No index loaded. Run 'build' or 'load' first.")
        return

    query = raw_args.strip()

    # Detect search mode: quotes = phrase, | = OR, default = AND
    is_phrase = (query.startswith('"') and query.endswith('"')) or \
                (query.startswith("'") and query.endswith("'"))
    is_or = "|" in query

    start_time = time.monotonic()

    if is_phrase:
        phrase = query[1:-1]
        results = engine.find_phrase(phrase)
        elapsed = time.monotonic() - start_time
        if results:
            print(engine.format_results(results, phrase))
            print(f"\n  ({len(results)} result(s) in {elapsed:.4f}s)")
        else:
            print(f'No pages contain the exact phrase: "{phrase}"')
    elif is_or:
        or_query = query.replace("|", " ")
        results = engine.find_or(or_query)
        elapsed = time.monotonic() - start_time
        if results:
            terms = engine.indexer.tokenize(or_query)
            lines = [f'Searching for: {" OR ".join(terms)}']
            lines.append(f"Found {len(results)} result(s):")
            lines.append("")
            for i, r in enumerate(results, 1):
                lines.append(f"  {i}. [Score: {r.score:.4f}] {r.url}")
                if r.snippet:
                    lines.append(f"     {r.snippet}")
            print("\n".join(lines))
            print(f"\n  ({len(results)} result(s) in {elapsed:.4f}s)")
        else:
            print("No results found.")
    else:
        words = query.split()
        results = engine.find(query)
        elapsed = time.monotonic() - start_time
        if results:
            print(engine.format_results(results, query))
            print(f"\n  ({len(results)} result(s) in {elapsed:.4f}s)")
        else:
            # Auto-suggest when find returns no results
            for word in words:
                suggestions = engine.suggest(word.lower())
                if suggestions:
                    print(f"  Did you mean: {', '.join(suggestions)}?")


def handle_stats(engine: SearchEngine) -> None:
    """Display index statistics: documents, terms, and top words."""
    if not engine.indexer.documents:
        print("No index loaded. Run 'build' or 'load' first.")
        return

    total_docs = engine.indexer.get_document_count()
    total_terms = engine.indexer.get_term_count()

    print(f"Index statistics:")
    print(f"  Documents: {total_docs}")
    print(f"  Unique terms: {total_terms}")
    print()

    # Top 10 most frequent terms (by number of documents they appear in)
    term_df = [(term, len(postings))
               for term, postings in engine.indexer.index.items()]
    term_df.sort(key=lambda x: x[1], reverse=True)

    print("  Top 10 terms by document frequency:")
    for term, df in term_df[:10]:
        print(f"    {term:20s}  appears in {df} document(s)")


def main() -> None:
    """Main interactive loop."""
    setup_logging()
    indexer = Indexer()
    engine = SearchEngine(indexer)

    print("Search Engine Tool - COMP3011 CW2")
    print('Commands: build, load, print <word>, find <words>, stats, quit')
    print()

    while True:
        try:
            user_input = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        parts = user_input.split()
        command = parts[0].lower()
        args = parts[1:]

        if command == "build":
            handle_build(indexer)
            engine = SearchEngine(indexer)

        elif command == "load":
            handle_load(indexer)
            engine = SearchEngine(indexer)

        elif command == "print":
            if not args:
                print("Usage: print <word>")
            else:
                handle_print(engine, args[0])

        elif command == "find":
            if not args:
                print("Usage: find <word1> [word2 ...] or find \"phrase\"")
            else:
                handle_find(engine, " ".join(args))

        elif command == "stats":
            handle_stats(engine)

        elif command in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        else:
            print(f"Unknown command: '{command}'")
            print('Commands: build, load, print <word>, find <words>, stats, quit')

        print()


if __name__ == "__main__":
    main()
