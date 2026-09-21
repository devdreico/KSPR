"""Data models for the KSPR reverse engineering engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Evidence:
    """A single auditable fact tied to an offset or symbol."""

    kind: str
    detail: str
    offset: int | None = None
    file: str | None = None
    confidence: float = 1.0

    def label(self) -> str:
        location = f" @0x{self.offset:x}" if self.offset is not None else ""
        return f"[{self.kind}]{location} {self.detail}"


@dataclass
class Finding:
    """A conclusion with its supporting evidence."""

    title: str
    category: str
    description: str = ""
    severity: str = "info"  # info | low | medium | high | critical
    evidence: list[Evidence] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ArtifactReport:
    """Normalized result of analyzing one artifact."""

    path: str
    size: int = 0
    kind: str = "unknown"
    description: str = ""
    mime: str = ""
    hashes: dict[str, str] = field(default_factory=dict)
    entropy: float = 0.0
    sections: list[dict[str, Any]] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    exports: list[str] = field(default_factory=list)
    symbols: list[str] = field(default_factory=list)
    strings: list[tuple[int, str]] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "size": self.size,
            "kind": self.kind,
            "description": self.description,
            "mime": self.mime,
            "hashes": self.hashes,
            "entropy": self.entropy,
            "sections": self.sections,
            "imports": self.imports,
            "exports": self.exports,
            "symbols": self.symbols,
            "strings_count": len(self.strings),
            "findings": [
                {
                    "title": finding.title,
                    "category": finding.category,
                    "severity": finding.severity,
                    "description": finding.description,
                    "evidence": [e.label() for e in finding.evidence],
                }
                for finding in self.findings
            ],
            "metadata": self.metadata,
        }
