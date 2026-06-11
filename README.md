# Barebones Semantic Search

Minimal semantic code search using sentence-transformers + LanceDB.

## Setup

```bash
uv sync
```

## Usage

```bash
# Index a directory
python main.py index /path/to/codebase

# Search
python main.py search /path/to/codebase "auth logic"
```
