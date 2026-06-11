import lancedb
import pyarrow as pa

_db = None


def init_db(db_path="./search_db"):
    global _db
    if _db is None:
        _db = lancedb.connect(db_path)
    return _db


def _get_or_create_table(db, name):
    try:
        return db.open_table(name)
    except Exception:
        schema = pa.schema([
            pa.field("vector", pa.list_(pa.float32(), 384)),
            pa.field("text", pa.string()),
            pa.field("file", pa.string()),
            pa.field("start_line", pa.int32()),
            pa.field("type", pa.string()),
            pa.field("name", pa.string()),
        ])
        empty = pa.table({
            "vector": pa.array([], type=pa.list_(pa.float32(), 384)),
            "text": pa.array([], type=pa.string()),
            "file": pa.array([], type=pa.string()),
            "start_line": pa.array([], type=pa.int32()),
            "type": pa.array([], type=pa.string()),
            "name": pa.array([], type=pa.string()),
        }, schema=schema)
        return db.create_table(name, empty)


def index_chunks(db, table_name, chunks, embed_fn):
    if not chunks:
        return
    table = _get_or_create_table(db, table_name)
    texts = [c["text"] for c in chunks]
    vectors = embed_fn(texts).tolist()
    records = []
    for i, c in enumerate(chunks):
        meta = c["metadata"]
        records.append({
            "vector": vectors[i],
            "text": texts[i],
            "file": meta["file"],
            "start_line": meta["start_line"],
            "type": meta["type"],
            "name": meta["name"],
        })
    table.add(records)
    return len(records)


def search_db(db, table_name, query_vector, n_results=3):
    table = _get_or_create_table(db, table_name)
    raw = table.search(query_vector.tolist()).limit(n_results).to_list()
    results = []
    for r in raw:
        results.append({
            "file": r.get("file", ""),
            "start_line": r.get("start_line", 0),
            "name": r.get("name", ""),
            "type": r.get("type", ""),
            "distance": r.get("_distance", 0.0),
            "code": r.get("text", ""),
        })
    return results
