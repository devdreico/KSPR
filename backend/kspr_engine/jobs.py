from __future__ import annotations

from uuid import uuid4

from .analyzer import analyze
from .models import AnalysisRequest, JobStatus
from .repository import SupabaseRepository


class JobCancelled(Exception):
    """Señal interna para detener un job solicitado por el usuario."""


class JobStore:
    def __init__(self):
        self.jobs: dict[str, JobStatus] = {}

    def create(self) -> JobStatus:
        job = JobStatus(job_id=uuid4().hex, status="queued", progress=0, stage="queued", message="Esperando ejecución")
        self.jobs[job.job_id] = job
        return job

    def get(self, job_id: str) -> JobStatus | None:
        return self.jobs.get(job_id)

    def cancel(self, job_id: str) -> bool:
        job = self.jobs.get(job_id)
        if not job or job.status in {"completed", "failed", "cancelled"}:
            return False
        job.status = "cancelled"
        job.stage = "cancelled"
        job.message = "Cancelado por el usuario"
        return True

    async def run(
        self,
        job_id: str,
        request: AnalysisRequest,
        settings,
        gemini_api_key: str | None = None,
        provider_base_url: str | None = None,
        provider_auth_mode: str = "api_key",
    ) -> None:
        async def progress(value: int, stage: str, message: str):
            job = self.jobs[job_id]
            if job.status == "cancelled":
                raise JobCancelled()
            job.status = "running" if value < 100 else "completed"
            job.progress, job.stage, job.message = value, stage, message

        try:
            await progress(1, "queued", "Iniciando agente KSPR")
            result = await analyze(request, settings, progress, gemini_api_key, provider_base_url, provider_auth_mode)
            await SupabaseRepository(settings).save_analysis(result)
            self.jobs[job_id].result = result
            self.jobs[job_id].status = "completed"
        except JobCancelled:
            self.jobs[job_id].status = "cancelled"
            self.jobs[job_id].stage = "cancelled"
            self.jobs[job_id].message = "Cancelado por el usuario"
        except Exception as exc:  # noqa: BLE001 - job boundary must persist failure state
            self.jobs[job_id].status = "failed"
            self.jobs[job_id].stage = "error"
            self.jobs[job_id].error = str(exc)
            self.jobs[job_id].message = "El análisis terminó con error"


job_store = JobStore()
