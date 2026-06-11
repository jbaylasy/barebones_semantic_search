import os
import re

ALLOWED_EXTENSIONS = (
    ".py", ".js", ".jsx", ".ts", ".tsx", ".rs", ".go", ".java",
    ".c", ".cpp", ".cc", ".cxx", ".h", ".hpp", ".hxx",
    ".md", ".txt", ".json", ".sql",
)

PY_FUNC_RE = re.compile(
    r"^((?:async\s+)?(?:def|class)\s+\w+)", re.MULTILINE
)
JS_FUNC_RE = re.compile(
    r"^((?:export\s+)?(?:async\s+)?(?:function|class)\s+\w+"
    r"|const\s+\w+\s*=\s*(?:async\s+)?\(?[^)]*\)?\s*=>)",
    re.MULTILINE,
)
MIN_LINES = 3
MAX_FILE_SIZE = 10 * 1024 * 1024


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


def _split_by_pattern(content, pattern):
    matches = list(pattern.finditer(content))
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
        chunk_lines = end_line - start_line + 1
        if chunk_lines < MIN_LINES:
            continue
        chunk_text = "\n".join(lines[start_line - 1:end_line])
        name = sig.split("(")[0].split()[-1] if "(" in sig else sig.split()[-1]
        chunks.append({
            "text": f"File: {sig}\n{chunk_text}",
            "metadata": {
                "file": "",
                "start_line": start_line,
                "type": "function" if "def " in sig or "function " in sig or "=>" in sig else "class",
                "name": name,
            },
        })
    return chunks


def _chunk_file(file_path):
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except (OSError, UnicodeDecodeError):
        return []

    ext = os.path.splitext(file_path)[1].lower()
    basename = os.path.basename(file_path)

    if ext == ".py":
        chunks = _split_by_pattern(content, PY_FUNC_RE)
    elif ext in (".js", ".jsx", ".ts", ".tsx"):
        chunks = _split_by_pattern(content, JS_FUNC_RE)
    else:
        chunks = []

    if not chunks:
        if len(content.strip()) < MIN_LINES:
            return []
        chunks = [{
            "text": f"File: {basename}\n{content}",
            "metadata": {
                "file": file_path,
                "start_line": 1,
                "type": "file",
                "name": basename,
            },
        }]

    for c in chunks:
        c["metadata"]["file"] = file_path

    return chunks


def chunk_codebase(root_dir):
    files = _collect_files(root_dir)
    all_chunks = []
    for fp in files:
        all_chunks.extend(_chunk_file(fp))
    return all_chunks
