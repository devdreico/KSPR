"""KSPR Reverse Engineering engine.

Real static analysis for binaries, firmware, archives and code: triage,
format parsing, disassembly, decompilation adapters, threat detection and
file carving/recovery. Every heavy dependency is optional and degrades to a
pure-Python or tool-backed fallback when missing.
"""

from .models import ArtifactReport, Evidence, Finding
from .traits import (
    detect_type,
    entropy,
    entropy_blocks,
    extract_strings,
    find_embedded,
    hashes,
    hexdump,
    read_artifact,
)

__all__ = [
    "ArtifactReport",
    "Evidence",
    "Finding",
    "detect_type",
    "entropy",
    "entropy_blocks",
    "extract_strings",
    "find_embedded",
    "hashes",
    "hexdump",
    "read_artifact",
]
