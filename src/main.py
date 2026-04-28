"""CLI entry point for the search engine tool."""

import logging
import sys

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

    # Detect phrase search: query wrapped in quotes
    is_phrase = (query.startswith('"') and query.endswith('"')) or \
                (query.startswith("'") and query.endswith("'"))

    if is_phrase:
        phrase = query[1:-1]
        results = engine.find_phrase(phrase)
        if results:
            display_query = f'"{phrase}" (phrase search)'
            print(engine.format_results(results, phrase))
        else:
            print(f'No pages contain the exact phrase: "{phrase}"')
    else:
        words = query.split()
        results = engine.find(query)
        if results:
            print(engine.format_results(results, query))
        else:
            # Auto-suggest when find returns no results
            for word in words:
                suggestions = engine.suggest(word.lower())
                if suggestions:
                    print(f"  Did you mean: {', '.join(suggestions)}?")


def main() -> None:
    """Main interactive loop."""
    setup_logging()
    indexer = Indexer()
    engine = SearchEngine(indexer)

    print("Search Engine Tool - COMP3011 CW2")
    print('Commands: build, load, print <word>, find <words> or find "phrase", quit')
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

        elif command in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        else:
            print(f"Unknown command: '{command}'")
            print('Commands: build, load, print <word>, find <words> or find "phrase", quit')

        print()


if __name__ == "__main__":
    main()
