import os
import sys

from search_engine.chunker import chunk_codebase
from search_engine.embedder import init_embedder, embed_texts
from search_engine.database import init_db, index_chunks
from search_engine.search import search_code, format_results


def _table_name(path):
    return os.path.basename(os.path.abspath(path)) + "_index"


def cmd_index(path):
    init_embedder()
    db = init_db()
    name = _table_name(path)
    print(f"Indexing {path} ...")
    chunks = chunk_codebase(path)
    if not chunks:
        print("No chunks produced.")
        return
    count = index_chunks(db, name, chunks, embed_texts)
    print(f"Indexed {count} chunks into '{name}'.")


def cmd_search(path, query, n=3):
    init_embedder()
    db = init_db()
    name = _table_name(path)
    result = search_code(db, name, query, n)
    print(format_results(result))


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python main.py index <directory>")
        print("  python main.py search <directory> <query>")
        sys.exit(1)

    command = sys.argv[1]

    if command == "index":
        if len(sys.argv) < 3:
            print("Usage: python main.py index <directory>")
            sys.exit(1)
        cmd_index(sys.argv[2])

    elif command == "search":
        if len(sys.argv) < 4:
            print("Usage: python main.py search <directory> <query>")
            sys.exit(1)
        cmd_search(sys.argv[2], " ".join(sys.argv[3:]))

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
