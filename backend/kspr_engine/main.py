from __future__ import annotations

import asyncio
import json

from fastapi import (
    BackgroundTasks,
    FastAPI,
    File,
    Header,
    HTTPException,
    Query,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .analyzer import analyze
from .config import get_settings
from .jobs import job_store
from .models import AnalysisRequest, AnalysisResult, JobStatus
from .providers import GeminiProvider, ProviderError, get_provider
from .repository import SupabaseRepository

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0", description="KSPR - Reverse Engineering Artificial Intelligence Agent.")
app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.get("/api/v1/health")
async def health() -> dict:
    return {
        "name": settings.app_name,
        "status": "ok",
        "version": "0.1.0",
        "providers": ["local", "gemini", "openai-compatible"],
        "gemini_key_configured": bool(settings.gemini_api_key),
    }


@app.post("/api/v1/analyze", response_model=AnalysisResult)
async def create_analysis(
    request: AnalysisRequest,
    x_kspr_api_key: str | None = Header(default=None, alias="X-KSPR-API-Key"),
    x_gemini_api_key: str | None = Header(default=None, alias="X-Gemini-API-Key"),
    x_kspr_base_url: str | None = Header(default=None, alias="X-KSPR-Base-URL"),
    x_kspr_auth_mode: str = Header(default="api_key", alias="X-KSPR-Auth-Mode"),
) -> AnalysisResult:
    if request.mode.value == "async" or (request.mode.value == "auto" and sum(len(item.content) for item in request.files) > 250_000):
        raise HTTPException(status_code=409, detail="Este contexto requiere un job asíncrono; usa /api/v1/jobs")
    try:
        result = await analyze(
            request,
            settings,
            gemini_api_key=x_kspr_api_key or x_gemini_api_key,
            provider_base_url=x_kspr_base_url,
            provider_auth_mode=x_kspr_auth_mode,
        )
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    await SupabaseRepository(settings).save_analysis(result)
    return result


@app.post("/api/v1/analyze/stream")
async def stream_analysis(
    request: AnalysisRequest,
    x_kspr_api_key: str | None = Header(default=None, alias="X-KSPR-API-Key"),
    x_gemini_api_key: str | None = Header(default=None, alias="X-Gemini-API-Key"),
    x_kspr_base_url: str | None = Header(default=None, alias="X-KSPR-Base-URL"),
    x_kspr_auth_mode: str = Header(default="api_key", alias="X-KSPR-Auth-Mode"),
) -> StreamingResponse:
    """Emite progreso y resultado como eventos SSE para el compositor web."""

    async def events():
        queue: asyncio.Queue[dict] = asyncio.Queue()

        async def progress(value: int, stage: str, message: str):
            await queue.put({"type": "progress", "status": "running", "progress": value, "stage": stage, "message": message})

        async def token(delta: str):
            await queue.put({"type": "delta", "text": delta})

        async def run():
            try:
                result = await analyze(
                    request,
                    settings,
                    progress,
                    gemini_api_key=x_kspr_api_key or x_gemini_api_key,
                    provider_base_url=x_kspr_base_url,
                    provider_auth_mode=x_kspr_auth_mode,
                    on_token=token,
                )
                await SupabaseRepository(settings).save_analysis(result)
                await queue.put({"type": "result", "result": result.model_dump(mode="json")})
            except Exception as exc:  # noqa: BLE001 - serialized at the stream boundary
                await queue.put({"type": "error", "message": str(exc)})

        task = asyncio.create_task(run())
        try:
            while True:
                event = await queue.get()
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                if event["type"] in {"result", "error"}:
                    break
        except asyncio.CancelledError:
            task.cancel()
            raise
        finally:
            if not task.done():
                task.cancel()

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/v1/jobs", response_model=JobStatus, status_code=202)
async def create_job(
    request: AnalysisRequest,
    background_tasks: BackgroundTasks,
    x_kspr_api_key: str | None = Header(default=None, alias="X-KSPR-API-Key"),
    x_gemini_api_key: str | None = Header(default=None, alias="X-Gemini-API-Key"),
    x_kspr_base_url: str | None = Header(default=None, alias="X-KSPR-Base-URL"),
    x_kspr_auth_mode: str = Header(default="api_key", alias="X-KSPR-Auth-Mode"),
) -> JobStatus:
    job = job_store.create()
    background_tasks.add_task(
        job_store.run,
        job.job_id,
        request,
        settings,
        x_kspr_api_key or x_gemini_api_key,
        x_kspr_base_url,
        x_kspr_auth_mode,
    )
    return job


@app.get("/api/v1/jobs/{job_id}", response_model=JobStatus)
async def get_job(job_id: str) -> JobStatus:
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job no encontrado")
    return job


@app.delete("/api/v1/jobs/{job_id}")
async def cancel_job(job_id: str) -> dict:
    if not job_store.cancel(job_id):
        raise HTTPException(status_code=409, detail="El job no puede cancelarse en su estado actual")
    return {"job_id": job_id, "status": "cancelled", "message": "Job cancelado"}


@app.post("/api/v1/ingest/files")
async def ingest_files(files: list[UploadFile] = File(...)) -> dict:  # noqa: B008
    """Previsualiza archivos cargados; la ejecución de código está prohibida."""
    allowed = {".py", ".js", ".jsx", ".ts", ".tsx", ".cs", ".java", ".sql", ".html", ".vue", ".php", ".md", ".txt", ".json", ".yaml", ".yml"}
    result = []
    for file in files:
        name = (file.filename or "").replace("\\", "/")
        suffix = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
        if suffix not in allowed or name.startswith("/") or ".." in name.split("/"):
            continue
        content = (await file.read())[:2_000_000].decode("utf-8", errors="replace")
        result.append({"path": name, "content": content, "bytes": len(content.encode())})
    return {"files": result, "count": len(result)}


@app.post("/api/v1/ingest/archive")
async def ingest_archive(file: UploadFile = File(...)) -> dict:  # noqa: B008
    """Extrae ZIP sin permitir traversal de rutas ni ejecutar contenido."""
    import io
    import zipfile

    raw = await file.read()
    if len(raw) > 25_000_000:
        raise HTTPException(status_code=413, detail="El ZIP supera el límite de 25 MB")
    result = []
    allowed = {".py", ".js", ".jsx", ".ts", ".tsx", ".cs", ".java", ".sql", ".html", ".vue", ".php", ".md", ".txt", ".json", ".yaml", ".yml"}
    try:
        archive = zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile as exc:
        raise HTTPException(status_code=400, detail="El archivo no es un ZIP válido") from exc
    for member in archive.infolist()[:2_000]:
        name = member.filename.replace("\\", "/")
        suffix = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
        if member.is_dir() or suffix not in allowed or name.startswith("/") or ".." in name.split("/"):
            continue
        if member.file_size > 2_000_000:
            continue
        content = archive.read(member)[:2_000_000].decode("utf-8", errors="replace")
        result.append({"path": name, "content": content, "bytes": len(content.encode())})
    return {"files": result, "count": len(result), "source": "zip"}


@app.post("/api/v1/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),  # noqa: B008
    x_gemini_api_key: str | None = Header(default=None, alias="X-Gemini-API-Key"),
    x_kspr_api_key: str | None = Header(default=None, alias="X-KSPR-API-Key"),
    x_kspr_auth_mode: str = Header(default="api_key", alias="X-KSPR-Auth-Mode"),
) -> dict:
    """Transcribe audio through Gemini; the browser is the local fallback."""
    raw = await file.read()
    if len(raw) > 25_000_000:
        raise HTTPException(status_code=413, detail="El audio supera el límite de 25 MB")
    try:
        provider = GeminiProvider(settings, api_key=x_kspr_api_key or x_gemini_api_key, auth_mode=x_kspr_auth_mode)
        text = await provider.transcribe(raw, file.content_type or "audio/webm")
    except ProviderError as exc:
        raise HTTPException(status_code=503, detail=f"El reconocimiento de voz requiere configurar la API Key de Gemini: {exc}") from exc
    return {"text": text, "provider": "gemini"}


@app.get("/api/v1/providers/status")
async def provider_status(
    provider: str = Query(default="gemini"),
    base_url: str | None = Query(default=None),
    x_kspr_api_key: str | None = Header(default=None, alias="X-KSPR-API-Key"),
    x_gemini_api_key: str | None = Header(default=None, alias="X-Gemini-API-Key"),
    x_kspr_auth_mode: str = Header(default="api_key", alias="X-KSPR-Auth-Mode"),
) -> dict:
    """Checks a provider connection and returns models allowed for generation."""
    try:
        adapter = get_provider(
            provider,
            settings,
            api_key=x_kspr_api_key or x_gemini_api_key,
            base_url=base_url,
            auth_mode=x_kspr_auth_mode,
        )
        list_models = getattr(adapter, "list_models", None)
        if not list_models:
            raise ProviderError(f"El proveedor {provider} no expone descubrimiento de modelos.")
        models = await list_models()
    except (ProviderError, ValueError) as exc:
        return {"connected": False, "provider": provider, "models": [], "message": str(exc)}
    return {"connected": True, "provider": provider, "models": models, "message": f"{provider} conectado"}


@app.get("/api/v1/providers/gemini/status")
async def gemini_status(
    x_gemini_api_key: str | None = Header(default=None, alias="X-Gemini-API-Key"),
    x_kspr_api_key: str | None = Header(default=None, alias="X-KSPR-API-Key"),
    x_kspr_auth_mode: str = Header(default="api_key", alias="X-KSPR-Auth-Mode"),
) -> dict:
    """Backward-compatible Gemini status route."""
    return await provider_status(
        provider="gemini",
        x_kspr_api_key=x_kspr_api_key,
        x_gemini_api_key=x_gemini_api_key,
        x_kspr_auth_mode=x_kspr_auth_mode,
    )
