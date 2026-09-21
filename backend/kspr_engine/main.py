from __future__ import annotations

import asyncio
import ipaddress
import json
import socket
from pathlib import Path
from urllib.parse import urlparse

from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    Header,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .analyzer import analyze
from .auth import get_current_user, hash_password
from .config import get_settings
from .decompiler import DecompilerEngine
from .jobs import job_store
from .models import (
    AnalysisRequest,
    AnalysisResult,
    JobStatus,
    OAuthLoginRequest,
    TokenResponse,
    UserLoginRequest,
    UserProfile,
    UserRegisterRequest,
)
from .providers import GeminiProvider, ProviderError, get_provider
from .repository import SupabaseRepository, UserRepository

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0", description="KSPR AI - Empresarial (Powered by KSPR Engine).")
app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


MAX_CONTEXT_BYTES = 20_000_000


def _enforce_context_limit(request: AnalysisRequest) -> int:
    """Return the total context size, rejecting abusive payloads."""
    total = sum(len(item.content) for item in request.files)
    if total > MAX_CONTEXT_BYTES:
        raise HTTPException(
            status_code=413,
            detail="El contexto supera el límite de 20 MB; divide el análisis en partes.",
        )
    return total


def _safe_stage_name(filename: str | None, fallback: str = "upload.bin") -> str:
    """Strip directories and reject traversal in an uploaded filename."""
    base = Path((filename or fallback).replace("\\", "/")).name.strip()
    if not base or base in {".", ".."} or ".." in base:
        return fallback
    return base


def _is_safe_remote_url(url: str) -> bool:
    """Allow only http(s) URLs resolving to public addresses (anti-SSRF)."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False
    try:
        infos = socket.getaddrinfo(parsed.hostname, None)
    except OSError:
        return False
    for info in infos:
        try:
            address = ipaddress.ip_address(info[4][0])
        except ValueError:
            return False
        if (
            address.is_private
            or address.is_loopback
            or address.is_link_local
            or address.is_reserved
            or address.is_multicast
            or address.is_unspecified
        ):
            return False
    return True


@app.get("/api/v1/health")
async def health() -> dict:
    return {
        "name": settings.app_name,
        "status": "ok",
        "version": "0.1.0",
        "providers": ["local", "gemini", "openai-compatible"],
        "gemini_key_configured": bool(settings.gemini_api_key),
    }


# ==================== AUTHENTICATION ENDPOINTS ====================

@app.post("/api/v1/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(request: UserRegisterRequest) -> TokenResponse:
    user_repo = UserRepository(settings)

    email_exists, username_exists = await user_repo.user_exists(request.email, request.username)
    if email_exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El email ya está registrado")
    if username_exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El nombre de usuario ya está en uso")

    password_hash = hash_password(request.password)
    user = await user_repo.create_user(
        username=request.username,
        email=request.email,
        password_hash=password_hash,
    )

    from .auth import JWTHandler
    jwt_handler = JWTHandler(settings)
    access_token = jwt_handler.create_access_token(user.id)

    return TokenResponse(access_token=access_token, user=user)


@app.post("/api/v1/auth/login", response_model=TokenResponse)
async def login(request: UserLoginRequest) -> TokenResponse:
    user_repo = UserRepository(settings)

    user = await user_repo.verify_credentials(request.identifier, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        )

    from .auth import JWTHandler
    jwt_handler = JWTHandler(settings)
    access_token = jwt_handler.create_access_token(user.id)

    return TokenResponse(access_token=access_token, user=user)


@app.get("/api/v1/auth/me", response_model=UserProfile)
async def get_current_user_profile(current_user: UserProfile = Depends(get_current_user)) -> UserProfile:
    return current_user


@app.post("/api/v1/auth/oauth", response_model=TokenResponse, status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def oauth_login(request: OAuthLoginRequest) -> TokenResponse:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="OAuth login no implementado en v1. Próximamente: Google, GitHub.",
    )


@app.post("/api/v1/analyze", response_model=AnalysisResult)
async def create_analysis(
    request: AnalysisRequest,
    current_user: UserProfile = Depends(get_current_user),
    x_kspr_api_key: str | None = Header(default=None, alias="X-KSPR-API-Key"),
    x_gemini_api_key: str | None = Header(default=None, alias="X-Gemini-API-Key"),
    x_kspr_base_url: str | None = Header(default=None, alias="X-KSPR-Base-URL"),
    x_kspr_auth_mode: str = Header(default="api_key", alias="X-KSPR-Auth-Mode"),
) -> AnalysisResult:
    total_size = _enforce_context_limit(request)
    if request.mode.value == "async" or (request.mode.value == "auto" and total_size > 250_000):
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
    await SupabaseRepository(settings).save_analysis(result, user_id=current_user.id)
    return result


@app.post("/api/v1/analyze/stream")
async def stream_analysis(
    request: AnalysisRequest,
    current_user: UserProfile = Depends(get_current_user),
    x_kspr_api_key: str | None = Header(default=None, alias="X-KSPR-API-Key"),
    x_gemini_api_key: str | None = Header(default=None, alias="X-Gemini-API-Key"),
    x_kspr_base_url: str | None = Header(default=None, alias="X-KSPR-Base-URL"),
    x_kspr_auth_mode: str = Header(default="api_key", alias="X-KSPR-Auth-Mode"),
) -> StreamingResponse:
    """Emite progreso y resultado como eventos SSE para el compositor web."""
    _enforce_context_limit(request)

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
                await SupabaseRepository(settings).save_analysis(result, user_id=current_user.id)
                await queue.put({"type": "result", "result": result.model_dump(mode="json")})
            except Exception as exc:
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
    current_user: UserProfile = Depends(get_current_user),
    x_kspr_api_key: str | None = Header(default=None, alias="X-KSPR-API-Key"),
    x_gemini_api_key: str | None = Header(default=None, alias="X-Gemini-API-Key"),
    x_kspr_base_url: str | None = Header(default=None, alias="X-KSPR-Base-URL"),
    x_kspr_auth_mode: str = Header(default="api_key", alias="X-KSPR-Auth-Mode"),
) -> JobStatus:
    _enforce_context_limit(request)
    job = job_store.create()
    background_tasks.add_task(
        job_store.run,
        job.job_id,
        request,
        settings,
        x_kspr_api_key or x_gemini_api_key,
        x_kspr_base_url,
        x_kspr_auth_mode,
        current_user.id,
    )
    return job


@app.get("/api/v1/jobs/{job_id}", response_model=JobStatus)
async def get_job(job_id: str, current_user: UserProfile = Depends(get_current_user)) -> JobStatus:
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job no encontrado")
    return job


@app.delete("/api/v1/jobs/{job_id}")
async def cancel_job(job_id: str, current_user: UserProfile = Depends(get_current_user)) -> dict:
    if not job_store.cancel(job_id):
        raise HTTPException(status_code=409, detail="El job no puede cancelarse en su estado actual")
    return {"job_id": job_id, "status": "cancelled", "message": "Job cancelado"}


@app.post("/api/v1/ingest/files")
async def ingest_files(files: list[UploadFile] = File(...)) -> dict:
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
async def ingest_archive(file: UploadFile = File(...)) -> dict:
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
    file: UploadFile = File(...),
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
    x_kspr_base_url: str | None = Header(default=None, alias="X-KSPR-Base-URL"),
    x_kspr_auth_mode: str = Header(default="api_key", alias="X-KSPR-Auth-Mode"),
) -> dict:
    """Checks a provider connection and returns models allowed for generation."""
    try:
        adapter = get_provider(
            provider,
            settings,
            api_key=x_kspr_api_key or x_gemini_api_key,
            base_url=base_url or x_kspr_base_url,
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


@app.post("/api/v1/decompilate")
async def decompilate_sources(
    files: list[UploadFile] = File(default=[]),
    links: str | None = Query(default=None),
    provider: str = Query(default="gemini"),
    model: str = Query(default="gemini-2.5-flash"),
    current_user: UserProfile = Depends(get_current_user),
    x_kspr_api_key: str | None = Header(default=None, alias="X-KSPR-API-Key"),
    x_kspr_base_url: str | None = Header(default=None, alias="X-KSPR-Base-URL"),
    x_kspr_auth_mode: str = Header(default="api_key", alias="X-KSPR-Auth-Mode"),
) -> dict:
    """Ingests multiple files/links, runs AI analysis, and builds Context Trees."""
    decompiler = DecompilerEngine()
    ingested = []

    # Save uploaded files to staging with sanitized names (no traversal).
    for file in files:
        raw = await file.read()
        if len(raw) > 25_000_000:
            raise HTTPException(status_code=413, detail=f"El archivo {file.filename or 'sin nombre'} supera el límite de 25 MB")
        stage_path = decompiler.staging_dir / _safe_stage_name(file.filename)
        stage_path.write_bytes(raw)
        res = decompiler.ingest_source(str(stage_path))
        ingested.append(res)

    # Ingest links if provided (public http/https only, anti-SSRF).
    if links:
        for link in links.split(","):
            link_clean = link.strip()
            if not link_clean:
                continue
            if not _is_safe_remote_url(link_clean):
                ingested.append({"source": link_clean, "success": False, "error": "URL no permitida (solo http/https públicos)"})
                continue
            res = decompiler.ingest_source(link_clean)
            ingested.append(res)

    combined_text = "\n\n".join([f"SOURCE: {item['source']}\n{item.get('content', '')}" for item in ingested if item.get('success')])

    try:
        adapter = get_provider(
            provider,
            settings,
            api_key=x_kspr_api_key,
            base_url=x_kspr_base_url,
            auth_mode=x_kspr_auth_mode,
        )
        prompt_text = f"Analiza la siguiente informacion recopilada de multiples fuentes y genera un Arbol de Contexto (Context Trees) estructurado. Identifica el concepto central y explica detalladamente hasta el mas minimo detalle en archivos tematicos markdown (.md).\n\n{combined_text}"
        response = await adapter.complete(prompt_text, model)
        analysis_text = str(response)
    except Exception:
        analysis_text = "# Analisis Consolidado\n\nInformacion recopilada y estructurada por KSPR Decompiler."

    tree_path = decompiler.generate_context_trees(ingested, analysis_text)
    trees = decompiler.list_trees()

    return {
        "status": "success",
        "tree_path": str(tree_path),
        "concept": tree_path.name,
        "files": [f.name for f in tree_path.glob("*.md")],
        "all_trees": trees,
    }


@app.get("/api/v1/trees")
async def list_context_trees(current_user: UserProfile = Depends(get_current_user)) -> dict:
    """Lists all generated Context Trees."""
    decompiler = DecompilerEngine()
    return {"trees": decompiler.list_trees()}

