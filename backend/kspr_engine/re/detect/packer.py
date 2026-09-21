"""Packer/compressor detection using signatures and entropy heuristics."""

from __future__ import annotations

from ..models import Evidence, Finding
from ..traits import entropy

PACKER_MARKERS = (
    (b"UPX!", "UPX", "high"),
    (b"UPX0", "UPX", "high"),
    (b"UPX1", "UPX", "high"),
    (b".aspack", "ASPack", "medium"),
    (b"ASPack", "ASPack", "medium"),
    (b".themida", "Themida", "high"),
    (b"MPRESS", "MPRESS", "medium"),
    (b".petite", "Petite", "medium"),
    (b"FSG!", "FSG", "medium"),
    (b"PECompact", "PECompact", "medium"),
)


def detect_packer(data: bytes, sections: list[dict] | None = None) -> list[Finding]:
    findings: list[Finding] = []
    for marker, name, severity in PACKER_MARKERS:
        offset = data.find(marker)
        if offset >= 0:
            findings.append(Finding(
                title=f"Packer detectado: {name}",
                category="packer",
                severity=severity,
                description=f"Firma '{marker.decode('latin-1')}' encontrada; el binario podría estar empaquetado.",
                evidence=[Evidence("signature", marker.decode("latin-1"), offset=offset)],
            ))
    overall = entropy(data)
    if overall > 7.2 and not findings:
        findings.append(Finding(
            title="Alta entropía global",
            category="packer",
            severity="medium",
            description=f"Entropía {overall:.2f}/8.0; posible cifrado, compresión o empaquetado.",
            evidence=[Evidence("entropy", f"{overall:.2f} bits/byte")],
        ))
    if sections:
        high = [s for s in sections if s.get("entropy", 0) > 7.0]
        if high:
            findings.append(Finding(
                title="Secciones de alta entropía",
                category="packer",
                severity="medium",
                description=f"{len(high)} secciones superan 7.0 de entropía.",
                evidence=[Evidence("section", f"{s.get('name')} = {s.get('entropy')}", offset=s.get("addr")) for s in high[:8]],
            ))
    return findings
