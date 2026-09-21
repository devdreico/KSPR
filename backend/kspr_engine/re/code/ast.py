"""Multi-language AST extraction via tree-sitter (with a Python fallback)."""

from __future__ import annotations

from pathlib import Path

LANGUAGES = {
    ".py": "python",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".hpp": "cpp",
    ".cc": "cpp",
    ".cs": "c_sharp",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".kt": "kotlin",
    ".scala": "scala",
    ".lua": "lua",
    ".sh": "bash",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
}

FUNCTION_TYPES = {
    "function_definition", "function_declaration", "function_item", "function_signature",
    "method_definition", "method_declaration", "constructor_declaration", "constructor",
    "arrow_function", "generator_function_declaration", "local_function", "def",
}
CLASS_TYPES = {
    "class_definition", "class_declaration", "class_specifier", "struct_item", "impl_item",
    "struct_specifier", "interface_declaration", "object_declaration", "enum_declaration",
}
IMPORT_TYPES = {
    "import_statement", "import_from_statement", "import_declaration", "use_declaration",
    "preproc_include", "using_directive", "package_clause", "require",
}


def supported_languages() -> list[str]:
    return sorted(set(LANGUAGES.values()))


def analyze_code(path: str | Path, source: str | None = None) -> dict:
    """Parse a source file and return functions, classes and imports."""
    target = Path(path)
    language = LANGUAGES.get(target.suffix.lower())
    if source is None:
        source = target.read_text(encoding="utf-8", errors="replace")
    if language is None:
        return _python_fallback(target, source, "Lenguaje no soportado por tree-sitter")
    try:
        from tree_sitter_language_pack import get_parser  # type: ignore

        parser = get_parser(language)
        tree = parser.parse(source.encode("utf-8", "replace"))
    except Exception as exc:
        return _python_fallback(target, source, str(exc))

    functions: list[dict] = []
    classes: list[dict] = []
    imports: list[str] = []

    def walk(node) -> None:
        node_type = node.type
        name_node = node.child_by_field_name("name")
        if node_type in FUNCTION_TYPES:
            name = name_node.text.decode("utf-8", "replace") if name_node else _first_identifier(node)
            if name:
                functions.append({"name": name, "line": node.start_point[0] + 1})
        elif node_type in CLASS_TYPES:
            name = name_node.text.decode("utf-8", "replace") if name_node else _first_identifier(node)
            if name:
                classes.append({"name": name, "line": node.start_point[0] + 1})
        elif node_type in IMPORT_TYPES:
            text = node.text.decode("utf-8", "replace").strip().splitlines()[0]
            if text:
                imports.append(text[:160])
        for child in node.children:
            walk(child)

    walk(tree.root_node)
    return {
        "file": str(target),
        "language": language,
        "functions": functions,
        "classes": classes,
        "imports": imports,
    }


def _first_identifier(node) -> str:
    for child in node.children:
        if child.type in {"identifier", "type_identifier", "field_identifier", "property_identifier"}:
            return child.text.decode("utf-8", "replace")
    return ""


def _python_fallback(target: Path, source: str, reason: str) -> dict:
    try:
        import ast

        tree = ast.parse(source)
        functions = [{"name": n.name, "line": n.lineno} for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
        classes = [{"name": n.name, "line": n.lineno} for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        return {"file": str(target), "language": "python", "functions": functions, "classes": classes, "imports": imports}
    except SyntaxError:
        return {"file": str(target), "language": "unknown", "functions": [], "classes": [], "imports": [], "error": reason}
