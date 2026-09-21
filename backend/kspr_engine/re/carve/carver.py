"""Signature-based file carving and deleted-file recovery."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from ..traits import find_embedded

MIN_CARVE_SIZE = 8


def _end_of_file(data: bytes, start: int, kind: str, next_offset: int) -> int:
    """Best-effort end boundary for a carved artifact."""
    if kind == "zip":
        eocd = data.find(b"PK\x05\x06", start)
        if eocd >= 0:
            return min(len(data), eocd + 22)
    if kind == "png":
        iend = data.find(b"IEND", start)
        if iend >= 0:
            return min(len(data), iend + 8)
    if kind == "jpeg":
        eoi = data.find(b"\xff\xd9", start + 2)
        if eoi >= 0:
            return min(len(data), eoi + 2)
    if kind == "pdf":
        eof = data.find(b"%%EOF", start)
        if eof >= 0:
            return min(len(data), eof + 5)
    if kind == "gzip":
        return min(len(data), start + 8_000_000)
    return next_offset


def carve(data: bytes, output_dir: str | Path, min_size: int = MIN_CARVE_SIZE, max_files: int = 500) -> dict[str, object]:
    """Carve embedded artifacts from a byte buffer into `output_dir`."""
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    embedded = find_embedded(data, min_size=min_size)
    carved: list[dict[str, object]] = []
    for index, item in enumerate(embedded[:max_files]):
        start = int(item["offset"])
        following = int(embedded[index + 1]["offset"]) if index + 1 < len(embedded) else len(data)
        next_offset = following if following > start else len(data)
        end = _end_of_file(data, start, str(item["kind"]), next_offset)
        if end <= start:
            continue
        extension = str(item.get("extension", ".bin"))
        name = f"carved_{start:08x}_{item['kind']}{extension}"
        target = destination / name
        target.write_bytes(data[start:end])
        carved.append({"offset": start, "size": end - start, "kind": item["kind"], "path": str(target)})
    return {"carved": carved, "count": len(carved), "output_dir": str(destination)}


def recover(image: str | Path, output_dir: str | Path) -> dict[str, object]:
    """Recover files from a disk image: use foremost/scalpel when present."""
    source = Path(image)
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    tool = shutil.which("foremost") or shutil.which("scalpel")
    if tool:
        completed = subprocess.run([tool, "-i", str(source), "-o", str(destination)], capture_output=True, text=True, timeout=1800, check=False)
        files = [str(p) for p in destination.rglob("*") if p.is_file()]
        return {"engine": Path(tool).name, "count": len(files), "files": files[:2000], "output_dir": str(destination), "returncode": completed.returncode}
    # Fallback: signature carving over the whole image.
    data = source.read_bytes()
    result = carve(data, destination)
    result["engine"] = "kspr-carver"
    return result
