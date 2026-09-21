"""High-level artifact analysis orchestrating triage, formats and detection."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .detect import detect_crypto, detect_packer, scan_yara
from .formats import list_archive, parse_elf, parse_pe
from .models import ArtifactReport, Evidence, Finding
from .traits import detect_type, entropy, extract_strings, hashes, read_artifact

MAX_STRINGS = 800


def analyze_artifact(path: str | Path, yara_rules: str | None = None, string_min: int = 5) -> ArtifactReport:
    """Produce a normalized report for one artifact without executing it."""
    target = Path(path)
    data = read_artifact(target)
    kind, description, mime = detect_type(data, target)
    report = ArtifactReport(
        path=str(target),
        size=len(data),
        kind=kind,
        description=description,
        mime=mime,
        hashes=hashes(data),
        entropy=round(entropy(data), 3),
        strings=extract_strings(data, min_length=string_min)[:MAX_STRINGS],
    )

    parsed: dict[str, Any] | None = None
    if kind == "elf":
        parsed = _safe(parse_elf, target)
    elif kind == "pe":
        parsed = _safe(parse_pe, target)
    elif kind == "zip":
        archive = _safe(list_archive, target)
        if archive:
            report.metadata["archive"] = {"format": archive.get("format"), "count": archive.get("count"), "members": archive.get("members", [])[:200]}

    if parsed:
        report.sections = parsed.get("sections", [])
        raw_imports = parsed.get("imports", [])
        if raw_imports and isinstance(raw_imports[0], dict):
            report.imports = sorted({f"{entry.get('dll')}!{fn}" for entry in raw_imports for fn in entry.get("functions", [])})
            report.metadata["libraries"] = [entry.get("dll") for entry in raw_imports]
        else:
            report.imports = list(raw_imports)
        report.exports = parsed.get("exports", [])
        report.symbols = parsed.get("symbols", [])
        report.metadata["format"] = parsed
        report.findings.extend(_format_findings(parsed, kind))

    report.findings.extend(detect_packer(data, report.sections))
    report.findings.extend(detect_crypto(data))
    report.findings.extend(scan_yara(data, rules_path=yara_rules))
    return report


def _safe(function, argument):
    try:
        return function(str(argument))
    except Exception as exc:
        return {"error": str(exc)}


def _format_findings(parsed: dict[str, Any], kind: str) -> list[Finding]:
    findings: list[Finding] = []
    suspicious = parsed.get("suspicious_imports") or []
    if suspicious:
        findings.append(Finding(
            title="Imports potencialmente peligrosos",
            category="behavior",
            severity="high",
            description="El binario importa funciones asociadas a inyección, descarga o ejecución.",
            evidence=[Evidence("import", name) for name in suspicious],
        ))
    if parsed.get("error"):
        findings.append(Finding(
            title="Parser de formato con error",
            category="format",
            severity="info",
            description=str(parsed["error"]),
        ))
    if kind == "pe" and parsed.get("imphash"):
        findings.append(Finding(
            title="Imphash",
            category="format",
            severity="info",
            description="Huella de imports útil para comparar familias de malware.",
            evidence=[Evidence("imphash", str(parsed["imphash"]))],
            metadata={"imphash": parsed["imphash"]},
        ))
    return findings
