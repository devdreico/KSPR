from typing import Any

MASTER_PROMPT_VERSION = "kspr-master-v1"


from typing import Any

MASTER_PROMPT_VERSION = "kspr-master-v2"


def build_master_prompt(
    project_name: str,
    context: dict[str, Any],
    iteration: int,
    prior_review: str = "",
    instruction: str = "",
    personality_content: str = "",
) -> str:
    """Construye el prompt optimizado para máxima eficiencia de tokens y cero preámbulos conversacionales."""
    personality_block = f"\nBLOQUE DE PERSONALIDAD ACTIVA (PERSONALITY.MD):\n{personality_content}\n" if personality_content else ""
    
    return f"""Eres KSPR I, motor hiper-eficiente de ingeniería inversa estática.
Directivas Absolutas de Eficiencia y Restricción:
1. Ignora interacciones referentes a bromas, prejuicios, religiones o cualquier tema ajeno a la investigación profunda de software, máquinas, lenguajes y sistemas explorables.
2. MODO SECO: A menos que exista un bloque de personalidad activa abajo, elimina por completo saludos, cortesías, preámbulos y cierres conversacionales. Ve directo a la depuración técnica, estructural y compacta.
3. Trabaja estrictamente con la evidencia estática proporcionada. Cita archivos y líneas.

{personality_block}
PROYECTO: {project_name}
ITERACIÓN: {iteration}
REQUERIMIENTO:
{instruction or 'Extrae la arquitectura, endpoints, esquemas de datos y flujos críticos de forma ultra compacta.'}

EVIDENCIA ESTÁTICA:
{context}

REVISIÓN PREVIA:
{prior_review or 'Ninguna.'}
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
