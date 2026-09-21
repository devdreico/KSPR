"""Safe archive listing and extraction (zip-slip and bomb protection)."""

from __future__ import annotations

import bz2
import gzip
import lzma
import tarfile
import zipfile
from pathlib import Path

MAX_FILES = 5_000
MAX_TOTAL_BYTES = 500 * 1024 * 1024
MAX_MEMBER_BYTES = 100 * 1024 * 1024


def _is_safe_member(name: str, base: Path) -> bool:
    normalized = name.replace("\\", "/")
    if not normalized or normalized.startswith("/") or ".." in normalized.split("/"):
        return False
    try:
        target = (base / normalized).resolve()
        return target == base.resolve() or base.resolve() in target.parents
    except (OSError, RuntimeError):
        return False


def list_archive(path: str | Path) -> dict[str, object]:
    """List archive members without extracting them."""
    target = Path(path)
    members: list[dict[str, object]] = []
    if zipfile.is_zipfile(target):
        with zipfile.ZipFile(target) as archive:
            for info in archive.infolist():
                if info.is_dir():
                    continue
                members.append({"name": info.filename, "size": info.file_size, "compressed": info.compress_size})
        return {"format": "zip", "members": members, "count": len(members)}
    if tarfile.is_tarfile(target):
        with tarfile.open(target) as archive:
            for info in archive.getmembers():
                if info.isdir():
                    continue
                members.append({"name": info.name, "size": info.size, "compressed": None})
        return {"format": "tar", "members": members, "count": len(members)}
    for fmt, opener in (("gzip", gzip.open), ("bzip2", bz2.open), ("xz", lzma.open)):
        try:
            with opener(target, "rb") as handle:
                handle.read(1)
            return {"format": fmt, "members": [{"name": Path(target).stem, "size": Path(target).stat().st_size}], "count": 1}
        except OSError:
            continue
    try:
        import py7zr  # type: ignore

        with py7zr.SevenZipFile(target) as archive:
            for name, info in archive.list() if hasattr(archive, "list") else []:
                members.append({"name": name, "size": getattr(info, "uncompressed", 0)})
        return {"format": "7z", "members": members, "count": len(members)}
    except Exception:
        pass
    try:
        import rarfile  # type: ignore

        with rarfile.RarFile(target) as archive:
            for info in archive.infolist():
                members.append({"name": info.filename, "size": info.file_size})
        return {"format": "rar", "members": members, "count": len(members)}
    except Exception:
        pass
    raise ValueError(f"Formato de archivo no soportado: {path}")


def extract_archive(path: str | Path, destination: str | Path, max_files: int = MAX_FILES) -> dict[str, object]:
    """Extract an archive safely, rejecting traversal, symlinks and bombs."""
    source = Path(path)
    dest = Path(destination)
    dest.mkdir(parents=True, exist_ok=True)
    extracted: list[str] = []
    skipped: list[str] = []
    total_bytes = 0

    def _check(name: str, size: int) -> bool:
        nonlocal total_bytes
        if len(extracted) >= max_files or size > MAX_MEMBER_BYTES or total_bytes + size > MAX_TOTAL_BYTES:
            skipped.append(name)
            return False
        return True

    if zipfile.is_zipfile(source):
        with zipfile.ZipFile(source) as archive:
            for info in archive.infolist():
                if info.is_dir() or not _is_safe_member(info.filename, dest) or not _check(info.filename, info.file_size):
                    skipped.append(info.filename)
                    continue
                archive.extract(info, dest)
                extracted.append(info.filename)
                total_bytes += info.file_size
    elif tarfile.is_tarfile(source):
        with tarfile.open(source) as archive:
            for info in archive.getmembers():
                if info.isdir() or info.issym() or info.islnk() or not _is_safe_member(info.name, dest) or not _check(info.name, info.size):
                    skipped.append(info.name)
                    continue
                archive.extract(info, dest, filter="data")
                extracted.append(info.name)
                total_bytes += info.size
    else:
        # Single-stream compression (gzip/bzip2/xz) -> one output file.
        for fmt, opener, suffix in (("gzip", gzip.open, ".out"), ("bzip2", bz2.open, ".out"), ("xz", lzma.open, ".out")):
            try:
                with opener(source, "rb") as reader, open(dest / (source.stem + suffix), "wb") as writer:
                    writer.write(reader.read(MAX_MEMBER_BYTES))
                extracted.append(source.stem + suffix)
                return {"format": fmt, "extracted": extracted, "skipped": skipped, "total_bytes": 0}
            except OSError:
                continue
        raise ValueError(f"No se pudo extraer el archivo: {path}")

    return {"format": "archive", "extracted": extracted, "skipped": skipped, "total_bytes": total_bytes}
