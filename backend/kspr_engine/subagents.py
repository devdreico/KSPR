"""KSPR Autonomous Cognitive OS: Subagent Orchestration Engine."""

from __future__ import annotations

from typing import ClassVar

from .prompts import KSPR_I_SYSTEM_PROMPT


class SubagentOrchestrator:
    AGENTS: ClassVar[dict[str, dict[str, str]]] = {
        "architect": {
            "name": "KSPR I",
            "role": "Descomposición estructural, ingeniería inversa, análisis estático y supervisión general.",
            "instructions": "Analiza sistemas complejos, define flujos, ejecuta análisis profundo y delega subtareas técnicas."
        },
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
