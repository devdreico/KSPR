"""Artifact triage: type detection, hashes, entropy and strings.

Pure Python, no mandatory third-party dependency. This is the first thing that
runs on any artifact and never executes it.
"""

from __future__ import annotations

import hashlib
import math
from collections import Counter
from pathlib import Path

MAX_READ_BYTES = 64 * 1024 * 1024

# (offset, magic bytes, kind, description, extension)
MAGIC_SIGNATURES: tuple[tuple[int, bytes, str, str, str], ...] = (
    (0, b"\x7fELF", "elf", "ELF executable/object", ".elf"),
    (0, b"MZ", "pe", "DOS/PE executable", ".exe"),
    (0, b"\xca\xfe\xba\xbe", "macho", "Mach-O / Java class", ".bin"),
    (0, b"\xfe\xed\xfa\xce", "macho", "Mach-O 32-bit", ".macho"),
    (0, b"\xfe\xed\xfa\xcf", "macho", "Mach-O 64-bit", ".macho"),
    (0, b"\xcf\xfa\xed\xfe", "macho", "Mach-O 64-bit LE", ".macho"),
    (0, b"PK\x03\x04", "zip", "ZIP archive (jar/apk/docx/...) ", ".zip"),
    (0, b"PK\x05\x06", "zip", "ZIP archive (empty)", ".zip"),
    (0, b"\x1f\x8b", "gzip", "gzip compressed", ".gz"),
    (0, b"BZh", "bzip2", "bzip2 compressed", ".bz2"),
    (0, b"\xfd7zXZ\x00", "xz", "XZ compressed", ".xz"),
    (0, b"7z\xbc\xaf\x27\x1c", "7z", "7-Zip archive", ".7z"),
    (0, b"Rar!\x1a\x07", "rar", "RAR archive", ".rar"),
    (0, b"%PDF", "pdf", "PDF document", ".pdf"),
    (0, b"\x89PNG\r\n\x1a\n", "png", "PNG image", ".png"),
    (0, b"\xff\xd8\xff", "jpeg", "JPEG image", ".jpg"),
    (0, b"GIF8", "gif", "GIF image", ".gif"),
    (0, b"RIFF", "riff", "RIFF container (wav/avi/webp)", ".riff"),
    (0, b"\x00asm", "wasm", "WebAssembly module", ".wasm"),
    (0, b"dex\n", "dex", "Android DEX", ".dex"),
    (0, b"SQLite format 3\x00", "sqlite", "SQLite database", ".sqlite"),
    (0, b"hsqs", "squashfs", "SquashFS filesystem (LE)", ".squashfs"),
    (0, b"sqsh", "squashfs", "SquashFS filesystem (BE)", ".squashfs"),
    (0, b"UBI#", "ubi", "UBI image", ".ubi"),
    (0, b"\xd0\x0d\xfe\xed", "ole", "OLE/Office document", ".ole"),
    (0, b"!<arch>\n", "ar", "Unix ar archive", ".a"),
    (257, b"ustar", "tar", "tar archive", ".tar"),
)

EXTENSION_HINTS = {
    ".exe": "pe", ".dll": "pe", ".sys": "pe", ".scr": "pe",
    ".so": "elf", ".elf": "elf", ".o": "elf",
    ".apk": "zip", ".jar": "zip", ".war": "zip", ".docx": "zip", ".xlsx": "zip",
    ".pyc": "pyc", ".class": "class", ".wasm": "wasm",
}


def read_artifact(path: str | Path, max_bytes: int = MAX_READ_BYTES) -> bytes:
    """Read an artifact from disk without ever executing it."""
    target = Path(path)
    if not target.is_file():
        raise FileNotFoundError(f"Artefacto no encontrado: {path}")
    return target.read_bytes()[:max_bytes]


def detect_type(data: bytes, path: str | Path | None = None) -> tuple[str, str, str]:
    """Return (kind, description, mime) for a byte buffer."""
    if not data:
        return "empty", "Archivo vacío", "application/x-empty"
    for offset, magic, kind, description, _ext in MAGIC_SIGNATURES:
        if data[offset : offset + len(magic)] == magic:
            return kind, description, _mime_for(kind)
    if path:
        hint = EXTENSION_HINTS.get(Path(path).suffix.lower())
        if hint:
            return hint, f"Detectado por extensión ({Path(path).suffix})", _mime_for(hint)
    # Printable heuristic
    sample = data[:4096]
    printable = sum(1 for byte in sample if 32 <= byte < 127 or byte in (9, 10, 13))
    if printable / max(len(sample), 1) > 0.9:
        return "text", "Texto plano", "text/plain"
    return "binary", "Datos binarios", "application/octet-stream"


def _mime_for(kind: str) -> str:
    return {
        "elf": "application/x-elf",
        "pe": "application/vnd.microsoft.portable-executable",
        "macho": "application/x-mach-binary",
        "zip": "application/zip",
        "gzip": "application/gzip",
        "pdf": "application/pdf",
        "png": "image/png",
        "jpeg": "image/jpeg",
        "wasm": "application/wasm",
        "sqlite": "application/vnd.sqlite3",
        "text": "text/plain",
    }.get(kind, "application/octet-stream")


def hashes(data: bytes) -> dict[str, str]:
    """Return common digests for an artifact."""
    result = {
        "md5": hashlib.md5(data).hexdigest(),
        "sha1": hashlib.sha1(data).hexdigest(),
        "sha256": hashlib.sha256(data).hexdigest(),
    }
    try:
        import tlsh  # optional

        if len(data) >= 256:
            result["tlsh"] = tlsh.hash(data)
    except Exception:
        pass
    return result


def entropy(data: bytes) -> float:
    """Shannon entropy in bits per byte (0..8)."""
    if not data:
        return 0.0
    counts = Counter(data)
    length = len(data)
    return -sum((count / length) * math.log2(count / length) for count in counts.values())


def entropy_blocks(data: bytes, block_size: int = 1024) -> list[float]:
    """Entropy per block; high values indicate packing/compression/encryption."""
    if block_size <= 0:
        raise ValueError("block_size debe ser positivo")
    return [round(entropy(data[i : i + block_size]), 3) for i in range(0, len(data), block_size)]


def extract_strings(data: bytes, min_length: int = 4) -> list[tuple[int, str]]:
    """Extract ASCII and UTF-16LE strings with their file offsets."""
    results: list[tuple[int, str]] = []
    ascii_run: list[str] = []
    ascii_start = 0
    for index, byte in enumerate(data):
        if 32 <= byte < 127 or byte in (9,):
            if not ascii_run:
                ascii_start = index
            ascii_run.append(chr(byte))
        else:
            if len(ascii_run) >= min_length:
                results.append((ascii_start, "".join(ascii_run)))
            ascii_run = []
    if len(ascii_run) >= min_length:
        results.append((ascii_start, "".join(ascii_run)))

    # UTF-16LE: printable followed by NUL
    index = 0
    while index + 1 < len(data):
        char = data[index]
        if 32 <= char < 127 and data[index + 1] == 0:
            start = index
            chars: list[str] = []
            while index + 1 < len(data) and 32 <= data[index] < 127 and data[index + 1] == 0:
                chars.append(chr(data[index]))
                index += 2
            if len(chars) >= min_length:
                results.append((start, "".join(chars)))
        else:
            index += 1
    results.sort(key=lambda item: item[0])
    return results


def hexdump(data: bytes, offset: int = 0, length: int = 256) -> list[str]:
    """Classic hex+ASCII dump lines for a range."""
    chunk = data[offset : offset + length]
    lines: list[str] = []
    for line_start in range(0, len(chunk), 16):
        block = chunk[line_start : line_start + 16]
        hex_part = " ".join(f"{byte:02x}" for byte in block)
        ascii_part = "".join(chr(byte) if 32 <= byte < 127 else "." for byte in block)
        lines.append(f"{offset + line_start:08x}  {hex_part:<47}  {ascii_part}")
    return lines


def find_embedded(data: bytes, min_size: int = 16) -> list[dict[str, object]]:
    """Locate embedded artifacts by magic-signature scanning (for carving)."""
    found: list[dict[str, object]] = []
    seen: set[int] = set()
    for _anchor, magic, kind, description, ext in MAGIC_SIGNATURES:
        start = 0
        while True:
            index = data.find(magic, start)
            if index < 0:
                break
            start = index + 1
            if index in seen:
                continue
            seen.add(index)
            found.append({"offset": index, "kind": kind, "description": description, "extension": ext, "size_hint": len(data) - index})
    found.sort(key=lambda item: int(item["offset"]))
    return [item for item in found if int(item["size_hint"]) >= min_size]
