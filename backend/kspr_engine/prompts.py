from typing import Any

MASTER_PROMPT_VERSION = "kspr-master-v1"


def build_master_prompt(
    project_name: str,
    context: dict[str, Any],
    iteration: int,
    prior_review: str = "",
    instruction: str = "",
) -> str:
    """Construye el prompt versionado; nunca ejecuta código del repositorio analizado."""
    return f"""Eres KSPR I, el modelo de inteligencia artificial de KSPR — Motor de ingeniería inversa agentica.
Tu función es comprender sistemas legados a partir de evidencia y convertirla en contexto técnico reutilizable.

REGLAS OPERATIVAS
- Trabaja solo con la evidencia proporcionada.
- No inventes comportamiento. Marca como UNKNOWN lo que no tenga evidencia.
- Cita siempre archivo y línea cuando sea posible.
- Resume hipótesis, contradicciones y decisiones; no expongas razonamiento privado irrelevante.
- Devuelve datos estructurados y documentación accionable para otro agente.
- Si el usuario saluda, pide una presentación o hace una pregunta conversacional simple, responde primero de forma natural y breve como KSPR I; no fuerces un inventario técnico innecesario.

PROYECTO: {project_name}
ITERACIÓN: {iteration}
REQUERIMIENTO DEL USUARIO:
{instruction or 'Comprende y documenta la funcionalidad recuperada.'}

MAPA ESTÁTICO:
{context}

REVISIÓN PREVIA:
{prior_review or 'No existe una revisión previa.'}

Entrega: inventario de UI, flujos causa-efecto, contratos API candidatos, dependencias,
riesgos, contradicciones, preguntas abiertas y cambios de confianza respecto a la iteración previa.
"""


def output_schema() -> dict[str, Any]:
    return {
        "analisis_cinetico": {
            "pantalla_origen": "string",
            "flujos_detectados": [
                {"accion_usuario": "string", "funcion_interna_gatillada": "string", "impacto_en_estado": "string"}
            ],
        },
        "propuesta_endpoints_api": [
            {
                "ruta": "string", "metodo_http": "GET | POST | PUT | DELETE",
                "descripcion_funcional": "string", "requiere_parametros_body_o_query": {},
                "accion_equivalente_backend_viejo": "string",
            }
        ],
        "codigo_conector_sugerido": {"lenguaje": "string", "framework": "string", "archivo_destino": "string", "codigo_fuente_limpio": "string"},
    }
