"""Reverse-engineering endpoints: analyze uploaded artifacts safely.

Artifacts are received by upload (never by server path) and written to a
temporary file that is removed immediately after analysis. Nothing is executed.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from ..auth import get_current_user
from ..models import UserProfile
from ..re.analyze import analyze_artifact
from ..re.carve import carve
from ..re.installer import status as tools_status

router = APIRouter(prefix="/api/v1/re", tags=["reverse-engineering"])

MAX_UPLOAD_BYTES = 64 * 1024 * 1024


async def _stage_upload(file: UploadFile) -> Path:
    raw = await file.read()
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="El artefacto supera el límite de 64 MB")
    suffix = Path(file.filename or "artifact.bin").suffix[:16]
    descriptor, name = tempfile.mkstemp(prefix="kspr-re-", suffix=suffix)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(raw)
    return Path(name)


@router.get("/tools")
async def re_tools() -> dict:
    """Report which external reverse-engineering tools are installed."""
    return tools_status()


@router.post("/analyze")
async def re_analyze(
    file: UploadFile = File(...),
    current_user: UserProfile = Depends(get_current_user),
) -> dict:
    """Triage and static analysis of an uploaded artifact."""
    staged = await _stage_upload(file)
    try:
        report = analyze_artifact(staged)
        return {"status": "ok", "report": report.to_dict()}
    finally:
        staged.unlink(missing_ok=True)


@router.post("/carve")
async def re_carve(
    file: UploadFile = File(...),
    current_user: UserProfile = Depends(get_current_user),
) -> dict:
    """Carve embedded artifacts from an uploaded image."""
    staged = await _stage_upload(file)
    try:
        with tempfile.TemporaryDirectory(prefix="kspr-carve-") as workdir:
            result = carve(staged.read_bytes(), workdir)
            return {
                "status": "ok",
                "count": result["count"],
                "carved": [
                    {"offset": item["offset"], "size": item["size"], "kind": item["kind"], "name": Path(str(item["path"])).name}
                    for item in result["carved"]
                ],
            }
    finally:
        staged.unlink(missing_ok=True)
