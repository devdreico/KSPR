"""KSPR Autonomous Cognitive OS: Subagent Orchestration Engine."""

from __future__ import annotations

from typing import Any
from .prompts import KSPR_I_SYSTEM_PROMPT


class SubagentOrchestrator:
    AGENTS = {
        "architect": {
            "name": "KSPR I - Architect",
            "role": "Descomposición estructural, diseño de arquitectura y supervisión general.",
            "instructions": "Analiza sistemas complejos, define flujos y delega subtareas técnicas."
        },
        "developer": {
            "name": "KSPR II - Code Developer",
            "role": "Generación, refactorización y autocorrección de código fuente.",
            "instructions": "Escribe código limpio, robusto y compacto siguiendo estrictamente los estándares."
        },
        "auditor": {
            "name": "KSPR III - Security & Audit",
            "role": "Auditoría de seguridad estática, detección de vulnerabilidades y revisión de dependencias.",
            "instructions": "Revisa código en busca de riesgos de seguridad, dependencias obsoletas y contradicciones."
        }
    }

    @classmethod
    def get_agent_prompt(cls, agent_key: str, user_instruction: str) -> str:
        agent = cls.AGENTS.get(agent_key.lower(), cls.AGENTS["architect"])
        return f"""{KSPR_I_SYSTEM_PROMPT}

[PERFIL DE SUBAGENTE ACTIVO]: {agent['name']}
[ROL]: {agent['role']}
[INSTRUCCIONES ESPECÍFICAS]: {agent['instructions']}

[TAREA ASIGNADA]:
{user_instruction}
"""
