"""KSPR Autonomous Cognitive OS: AST Parser and Static Code Decomposition Engine."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any


class CodeASTAnalyzer:
    @staticmethod
    def analyze_python_file(filepath: Path) -> dict[str, Any]:
        if not filepath.is_file():
            return {"error": "File not found"}

        try:
            code = filepath.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(code, filename=str(filepath))
        except Exception as e:
            return {"error": f"Parse error: {e}"}

        classes = []
        functions = []
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.append({
                    "name": node.name,
                    "lineno": node.lineno,
                    "methods": [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                })
            elif isinstance(node, ast.FunctionDef):
                functions.append({
                    "name": node.name,
                    "lineno": node.lineno,
                    "args": [arg.arg for arg in node.args.args]
                })
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for alias in node.names:
                        imports.append(f"{module}.{alias.name}")

        return {
            "file": str(filepath),
            "classes": classes,
            "functions": functions,
            "imports": imports
        }
