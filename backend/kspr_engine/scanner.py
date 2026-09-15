"""Extracción estática conservadora de señales de repositorios legados."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from .models import SourceFile

UI_PATTERNS: list[tuple[str, str, str]] = [
    (r"(?:id|name|data-testid)=?[\"']([^\"']+)", "element", "HTML/UI identifier"),
    (r"getElementById\s*\(\s*[\"']([^\"']+)", "element", "DOM UI identifier"),
    (r"\b(btn|button|submit|confirm|save|delete|edit|cancel)[A-Za-z0-9_ -]*", "button", "button/action"),
    (r"\b(txt|input|textarea|field|search|codigo|code)[A-Za-z0-9_ -]*", "input", "input/form field"),
    (r"\b(form|formulario)[A-Za-z0-9_ -]*", "form", "form"),
    (r"\b(link|anchor|href|navigate|router\.push|navigate\()[^\n]*", "link", "navigation"),
]

EVENT_PATTERNS = [
    r"onClick\s*=\s*\{?([^}\n]+)",
    r"onSubmit\s*=\s*\{?([^}\n]+)",
    r"(?:KeyDown|KeyPress|Change|Click)\s*\([^)]*\)",
    r"addEventListener\s*\(\s*[\"']([^\"']+)",
    r"@[A-Za-z]+",
]

ROUTE_PATTERNS = [
    r"(?:app|router|api)\.(get|post|put|patch|delete)\s*\(\s*[\"']([^\"']+)",
    r"@(get|post|put|patch|delete)\s*\(\s*[\"']?([^\"') ]+)",
    r"path\s*[:=]\s*[\"']([^\"']+)",
]

DB_PATTERNS = [
    r"\bSELECT\b[\s\S]{0,180}?\bFROM\b\s+([\w.\[\]]+)",
    r"\b(?:INSERT\s+INTO|UPDATE|DELETE\s+FROM)\s+([\w.\[\]]+)",
    r"(?:stored procedure|procedure|sp_[A-Za-z0-9_]+)",
]


@dataclass
class ScanResult:
    files: list[dict]
    ui_elements: list[dict]
    events: list[dict]
    routes: list[dict]
    data_operations: list[dict]
    dependencies: list[dict]
    stats: dict


def _line_number(content: str, position: int) -> int:
    return content.count("\n", 0, position) + 1


def _language(path: str) -> str:
    ext = path.rsplit(".", 1)[-1].lower() if "." in path else "text"
    return {
        "py": "python", "js": "javascript", "jsx": "javascript-react", "ts": "typescript",
        "tsx": "typescript-react", "cs": "csharp", "java": "java", "sql": "sql",
        "html": "html", "vue": "vue", "php": "php", "rb": "ruby", "go": "go",
    }.get(ext, ext)


def scan_files(source_files: list[SourceFile]) -> ScanResult:
    ui_elements: list[dict] = []
    events: list[dict] = []
    routes: list[dict] = []
    data_operations: list[dict] = []
    dependencies: list[dict] = []
    scanned_files: list[dict] = []
    line_count = 0

    for source in source_files:
        content = source.content
        language = _language(source.path)
        lines = content.count("\n") + (1 if content else 0)
        line_count += lines
        scanned_files.append({"path": source.path, "language": language, "lines": lines, "bytes": len(content.encode())})

        for pattern, kind, description in UI_PATTERNS:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                value = (match.group(1) if match.lastindex else match.group(0)).strip()
                if len(value) > 120:
                    value = value[:120]
                ui_elements.append({
                    "name": value, "kind": kind, "description": description,
                    "file": source.path, "line": _line_number(content, match.start()),
                })

        for pattern in EVENT_PATTERNS:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                value = match.group(1).strip() if match.lastindex else match.group(0).strip()
                events.append({"handler": value[:160], "file": source.path, "line": _line_number(content, match.start())})

        for pattern in ROUTE_PATTERNS:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                groups = match.groups()
                method, path = (groups[-2], groups[-1]) if len(groups) > 1 else ("UNKNOWN", groups[0])
                routes.append({"method": method.upper(), "path": path, "file": source.path, "line": _line_number(content, match.start())})

        for pattern in DB_PATTERNS:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                value = match.group(0)
                data_operations.append({"operation": value.strip()[:180], "file": source.path, "line": _line_number(content, match.start())})

        import_patterns = [
            r"(?:from|import)\s+[\"']([^\"']+)",
            r"using\s+([A-Za-z0-9_.]+)",
            r"require\s*\(\s*[\"']([^\"']+)",
        ]
        for pattern in import_patterns:
            for match in re.finditer(pattern, content):
                dependencies.append({"name": match.group(1), "file": source.path, "line": _line_number(content, match.start())})

    unique_ui = list({(x["name"], x["kind"], x["file"], x["line"]): x for x in ui_elements}.values())
    unique_events = list({(x["handler"], x["file"], x["line"]): x for x in events}.values())
    unique_routes = list({(x["method"], x["path"], x["file"]): x for x in routes}.values())
    unique_ops = list({(x["operation"], x["file"], x["line"]): x for x in data_operations}.values())
    unique_deps = list({(x["name"], x["file"]): x for x in dependencies}.values())

    return ScanResult(
        files=scanned_files,
        ui_elements=unique_ui,
        events=unique_events,
        routes=unique_routes,
        data_operations=unique_ops,
        dependencies=unique_deps,
        stats={
            "files": len(scanned_files), "lines": line_count,
            "languages": dict(Counter(item["language"] for item in scanned_files)),
        },
    )
