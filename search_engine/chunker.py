import ast
import os
import re

ALLOWED_EXTENSIONS = (
    ".py", ".js", ".jsx", ".ts", ".tsx", ".rs", ".go", ".java",
    ".c", ".cpp", ".cc", ".cxx", ".h", ".hpp", ".hxx",
    ".md", ".txt", ".json", ".sql",
)

MIN_LINES = 3
MAX_FILE_SIZE = 10 * 1024 * 1024

JS_FUNC_RE = re.compile(
    r"^((?:export\s+)?(?:async\s+)?(?:function|class)\s+\w+"
    r"|const\s+\w+\s*=\s*(?:async\s+)?\(?[^)]*\)?\s*=>)",
    re.MULTILINE,
)


def _collect_files(root_dir):
    files = []
    for dirpath, dirs, filenames in os.walk(root_dir):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for fn in filenames:
            if any(fn.endswith(ext) for ext in ALLOWED_EXTENSIONS):
                fp = os.path.join(dirpath, fn)
                try:
                    if os.path.getsize(fp) <= MAX_FILE_SIZE:
                        files.append(fp)
                except OSError:
                    pass
    return files


def _extract_docstring(node):
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return None
    body = node.body
    if not body:
        return None
    first = body[0]
    if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
        return first.value.value.strip()
    return None


def _chunk_python_ast(content, file_path):
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return []

    lines = content.splitlines()
    chunks = []
    parent_map = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parent_map[id(child)] = parent

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            _add_ast_node(node, lines, file_path, chunks, parent_type="class", parent_name=None)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            parent = parent_map.get(id(node))
            if isinstance(parent, ast.ClassDef):
                _add_ast_node(node, lines, file_path, chunks, parent_type="method", parent_name=parent.name)
            else:
                _add_ast_node(node, lines, file_path, chunks, parent_type="function", parent_name=None)

    return chunks


def _add_ast_node(node, lines, file_path, chunks, parent_type, parent_name):
    start = node.lineno
    end = node.end_lineno or start
    if end - start + 1 < MIN_LINES:
        return

    docstring = _extract_docstring(node)
    name = node.name
    chunk_lines = lines[start - 1:end]
    chunk_text = "\n".join(chunk_lines)

    if docstring:
        chunk_text = f'"""\n{docstring}\n"""\n\n{chunk_text}'

    context = f"File: {file_path}"
    if parent_name:
        context += f" | class: {parent_name}, {parent_type}: {name}"
    else:
        context += f" | {parent_type}: {name}"
    enriched = f"{context}\n{chunk_text}"

    chunks.append({
        "text": enriched,
        "metadata": {
            "file": file_path,
            "start_line": start,
            "type": parent_type,
            "name": name,
        },
    })


def _chunk_js_regex(content, file_path):
    matches = list(JS_FUNC_RE.finditer(content))
    if not matches:
        return []
    lines = content.split("\n")
    chunks = []
    for i, m in enumerate(matches):
        sig = m.group(1)
        start_line = content[:m.start()].count("\n") + 1
        if i + 1 < len(matches):
            end_line = content[:matches[i + 1].start()].count("\n")
        else:
            end_line = len(lines)
        if end_line - start_line + 1 < MIN_LINES:
            continue
        chunk_text = "\n".join(lines[start_line - 1:end_line])
        name = sig.split("(")[0].split()[-1] if "(" in sig else sig.split()[-1]
        context = f"File: {file_path} | function: {name}"
        chunks.append({
            "text": f"{context}\n{chunk_text}",
            "metadata": {
                "file": file_path,
                "start_line": start_line,
                "type": "function",
                "name": name,
            },
        })
    return chunks


def _fallback_chunk(content, file_path):
    basename = os.path.basename(file_path)
    return [{
        "text": f"File: {basename}\n{content}",
        "metadata": {
            "file": file_path,
            "start_line": 1,
            "type": "file",
            "name": basename,
        },
    }]


def _chunk_file(file_path):
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except (OSError, UnicodeDecodeError):
        return []

    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".py":
        chunks = _chunk_python_ast(content, file_path)
    elif ext in (".js", ".jsx", ".ts", ".tsx"):
        chunks = _chunk_js_regex(content, file_path)
    else:
        chunks = []

    if not chunks:
        if len(content.strip()) < MIN_LINES:
            return []
        chunks = _fallback_chunk(content, file_path)

    return chunks


def chunk_codebase(root_dir):
    files = _collect_files(root_dir)
    all_chunks = []
    for fp in files:
        all_chunks.extend(_chunk_file(fp))
    return all_chunks
