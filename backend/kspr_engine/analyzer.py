from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import uuid4

from .models import (
    AnalysisArtifact,
    AnalysisRequest,
    AnalysisResult,
    AnalysisSummary,
)
from .prompts import build_master_prompt, output_schema
from .providers import get_provider
from .scanner import ScanResult, scan_files

ProgressCallback = Callable[[int, str, str], Awaitable[None]]
TokenCallback = Callable[[str], Awaitable[None]]


def _evidence(file: dict) -> str:
    return f"{file.get('path', file.get('file', '?'))}:{file.get('line', '?')}"


def build_deterministic_report(request: AnalysisRequest, scan: ScanResult, iterations: int) -> dict[str, Any]:
    flows = []
    for event in scan.events:
        source = event["file"]
        related_ui = next((item for item in scan.ui_elements if item["file"] == source), None)
        flows.append({
            "accion_usuario": related_ui["name"] if related_ui else event["handler"],
            "funcion_interna_gatillada": event["handler"],
            "impacto_en_estado": "Requiere revisión de mutación o lectura de datos; evidencia: " + _evidence(event),
            "confianza": "media",
            "evidencia": [_evidence(event)],
        })

    endpoints = []
    for route in scan.routes:
        endpoints.append({
            "ruta": route["path"], "metodo_http": route["method"],
            "descripcion_funcional": "Ruta recuperada del código fuente.",
            "requiere_parametros_body_o_query": {},
            "accion_equivalente_backend_viejo": f"Handler en {route['file']}:{route['line']}",
            "evidencia": [_evidence(route)],
        })
    if not endpoints and scan.data_operations:
        endpoints.append({
            "ruta": "/api/v1/recovered-operation", "metodo_http": "POST",
            "descripcion_funcional": "Candidato generado para encapsular una operación de datos recuperada.",
            "requiere_parametros_body_o_query": {"payload": "object"},
            "accion_equivalente_backend_viejo": scan.data_operations[0]["operation"],
            "evidencia": [_evidence(scan.data_operations[0])],
        })

    risks = []
    for operation in scan.data_operations:
        if any(token in operation["operation"].upper() for token in ["SELECT", "UPDATE", "INSERT", "DELETE", "SP_"]):
            risks.append({
                "tipo": "data-access", "severidad": "alta" if "UPDATE" in operation["operation"].upper() else "media",
                "descripcion": "Operación de datos recuperada; validar parametrización, autorización y transacción.",
                "evidencia": [_evidence(operation)],
            })
    contradictions = []
    if scan.events and not scan.routes:
        contradictions.append({
            "tema": "UI sin contrato HTTP explícito",
            "descripcion": "Se detectaron eventos de interfaz, pero no una ruta API equivalente en el contexto entregado.",
            "estado": "abierta",
        })
    open_questions = []
    if not scan.data_operations:
        open_questions.append("¿Qué fuente de datos o servicio muta el estado detrás de los eventos recuperados?")
    if not scan.ui_elements:
        open_questions.append("¿Existe una capa visual no incluida en los archivos analizados?")

    return {
        "version": "kspr-report-v1",
        "analisis_cinetico": {
            "pantalla_origen": request.project_name,
            "flujos_detectados": flows,
        },
        "propuesta_endpoints_api": endpoints,
        "inventario_ui": scan.ui_elements,
        "eventos": scan.events,
        "operaciones_datos": scan.data_operations,
        "dependencias": scan.dependencies,
        "archivos": scan.files,
        "estadisticas": scan.stats,
        "riesgos": risks,
        "contradicciones": contradictions,
        "preguntas_abiertas": open_questions,
        "iteraciones": [
            {"numero": i, "objetivo": objective, "resultado": "completada", "fuente": "evidencia estática + revisión estructurada"}
            for i, objective in enumerate(["extraer señales", "contrastar flujos", "consolidar documentación"][:iterations], 1)
        ],
        "esquema_salida": output_schema(),
    }


async def analyze(
    request: AnalysisRequest,
    settings,
    on_progress: ProgressCallback | None = None,
    gemini_api_key: str | None = None,
    provider_base_url: str | None = None,
    provider_auth_mode: str = "api_key",
    on_token: TokenCallback | None = None,
) -> AnalysisResult:
    if on_progress:
        await on_progress(8, "ingestion", "Normalizando archivos de contexto")
    scan = scan_files(request.files)
    provider_name = request.provider or settings.default_provider
    provider = get_provider(
        provider_name,
        settings,
        api_key=gemini_api_key,
        base_url=provider_base_url,
        auth_mode=provider_auth_mode,
    )
    model = request.model or settings.default_model
    report = build_deterministic_report(request, scan, request.iterations)
    prior_review = ""
    completed = 0
    response_text = ""
    source_context = "\n\n".join(
        f"FILE: {source.path}\n{source.content[:40_000]}" for source in request.files
    )[:250_000]

    for iteration in range(1, request.iterations + 1):
        if on_progress:
            await on_progress(10 + iteration * (55 // request.iterations), "reasoning", f"Iteración {iteration}/{request.iterations}: revisión de evidencia")
        # Extraer contenido de personality.md si viene en los archivos del request
        personality_file = next((f.content for f in request.files if f.path == "personality.md"), "")
        prompt = build_master_prompt(
            request.project_name,
            {**report, "source_context": source_context},
            iteration,
            prior_review,
            instruction=request.instruction or "",
            personality_content=personality_file,
        )
        stream_completion = getattr(provider, "complete_stream", None)
        if on_token and stream_completion:
            model_response = await stream_completion(prompt, model, on_token, effort=request.effort)
        else:
            model_response = await provider.complete(prompt, model, effort=request.effort)
            if on_token and model_response:
                await on_token(model_response)
        response_text = model_response.strip()
        report.setdefault("revisiones_modelo", []).append({
            "iteracion": iteration, "provider": provider_name, "model": model,
            "variant": request.variant,
            "respuesta": response_text[:20_000],
        })
        prior_review = (
            f"Iteración {iteration} consolidada con {len(scan.ui_elements)} elementos UI y "
            f"{len(scan.events)} eventos.\n\n"
            "RESPUESTA TÉCNICA DE LA ITERACIÓN ANTERIOR:\n"
            f"{response_text[:20_000]}"
        )
        completed = iteration

    if on_progress:
        await on_progress(76, "documentation", "Generando paquete Markdown de contexto")
    artifacts = build_artifacts(request, report)
    summary = AnalysisSummary(
        project_name=request.project_name, status="completed", provider=str(provider_name), model=model,
        files_analyzed=scan.stats["files"], total_lines=scan.stats["lines"], ui_elements=len(scan.ui_elements),
        flows=len(report["analisis_cinetico"]["flujos_detectados"]), endpoints=len(report["propuesta_endpoints_api"]),
        risks=len(report["riesgos"]), contradictions=len(report["contradicciones"]), iterations_completed=completed,
    )
    if on_progress:
        await on_progress(100, "completed", "Análisis terminado")
    return AnalysisResult(
        analysis_id=uuid4().hex,
        summary=summary,
        report=report,
        artifacts=artifacts,
        response_text=response_text,
    )


def build_artifacts(request: AnalysisRequest, report: dict[str, Any]) -> list[AnalysisArtifact]:
    summary = report["estadisticas"]
    index = f"""# KSPR Context Package\n\n## {request.project_name}\n\n> Generado por KSPR — Reverse Engineering Artificial Intelligence Agent.\n\n- Archivos: {summary['files']}\n- Líneas: {summary['lines']}\n- Elementos UI: {len(report['inventario_ui'])}\n- Flujos: {len(report['analisis_cinetico']['flujos_detectados'])}\n- Endpoints candidatos: {len(report['propuesta_endpoints_api'])}\n\n## Navegación\n\n- [Inventario de interfaz](01-ui-inventory.md)\n- [Flujos y contratos](02-flows-and-contracts.md)\n- [Dependencias y datos](03-data-and-dependencies.md)\n- [Riesgos y contradicciones](04-risks-and-open-questions.md)\n- [Registro de iteraciones](05-iteration-log.md)\n"""
    ui = "# Inventario de interfaz\n\n" + _markdown_table(report["inventario_ui"], ["kind", "name", "file", "line", "description"])
    flows = "# Flujos y contratos\n\n## Flujos recuperados\n\n" + _markdown_table(report["analisis_cinetico"]["flujos_detectados"], ["accion_usuario", "funcion_interna_gatillada", "impacto_en_estado", "confianza", "evidencia"])
    flows += "\n## Endpoints candidatos\n\n" + _markdown_table(report["propuesta_endpoints_api"], ["metodo_http", "ruta", "descripcion_funcional", "accion_equivalente_backend_viejo", "evidencia"])
    data = "# Dependencias y datos\n\n## Operaciones\n\n" + _markdown_table(report["operaciones_datos"], ["operation", "file", "line"])
    data += "\n## Dependencias\n\n" + _markdown_table(report["dependencias"], ["name", "file", "line"])
    risks = "# Riesgos y preguntas abiertas\n\n## Riesgos\n\n" + _markdown_table(report["riesgos"], ["tipo", "severidad", "descripcion", "evidencia"])
    risks += "\n## Contradicciones\n\n" + _markdown_table(report["contradicciones"], ["tema", "descripcion", "estado"])
    risks += "\n## Preguntas abiertas\n\n" + "\n".join(f"- {item}" for item in report["preguntas_abiertas"]) + "\n"
    iterations = "# Registro de iteraciones\n\n" + _markdown_table(report["iteraciones"], ["numero", "objetivo", "resultado", "fuente"])
    raw = json.dumps(report, ensure_ascii=False, indent=2)
    return [
        AnalysisArtifact(path="README.md", title="Context package", content=index, kind="index"),
        AnalysisArtifact(path="01-ui-inventory.md", title="UI inventory", content=ui, kind="documentation"),
        AnalysisArtifact(path="02-flows-and-contracts.md", title="Flows and contracts", content=flows, kind="documentation"),
        AnalysisArtifact(path="03-data-and-dependencies.md", title="Data and dependencies", content=data, kind="documentation"),
        AnalysisArtifact(path="04-risks-and-open-questions.md", title="Risks and questions", content=risks, kind="documentation"),
        AnalysisArtifact(path="05-iteration-log.md", title="Iteration log", content=iterations, kind="documentation"),
        AnalysisArtifact(path="report.json", title="Structured report", content=raw, kind="machine-readable"),
    ]


def _markdown_table(items: list[dict[str, Any]], columns: list[str]) -> str:
    if not items:
        return "_Sin hallazgos._\n"
    header = "| " + " | ".join(columns) + " |\n|" + "|".join("---" for _ in columns) + "|\n"
    rows = []
    for item in items:
        values = []
        for column in columns:
            value = item.get(column, "—")
            if isinstance(value, list):
                value = ", ".join(str(x) for x in value)
            values.append(str(value).replace("|", "\\|").replace("\n", " ")[:500])
        rows.append("| " + " | ".join(values) + " |")
    return header + "\n".join(rows) + "\n"
