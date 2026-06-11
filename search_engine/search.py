from search_engine.embedder import embed_query
from search_engine.database import search_db


def search_code(db, table_name, query, n_results=3):
    vector = embed_query(query)
    results = search_db(db, table_name, vector, n_results)
    return {
        "query": query,
        "results": results,
    }


def format_results(output):
    lines = [f'Query: "{output["query"]}"', "=" * 60]
    for i, r in enumerate(output["results"]):
        lines.append(f"--- Result {i + 1} ---")
        lines.append(f"File:   {r['file']}")
        lines.append(f"Line:   {r['start_line']}")
        lines.append(f"Name:   {r['name']}")
        lines.append(f"Type:   {r['type']}")
        lines.append(f"Score:  {r['distance']:.4f}")
        lines.append(f"Code:\n{r['code']}")
        lines.append("-" * 60)
    return "\n".join(lines)
