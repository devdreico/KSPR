"""Specialized reverse-engineering subagents and task planning."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AgentProfile:
    key: str
    name: str
    role: str
    tools: tuple[str, ...] = ()
    model_hint: str = "reasoning"  # fast | reasoning


SUBAGENTS: tuple[AgentProfile, ...] = (
    AgentProfile("recon", "KSPR Recon", "Clasifica el artefacto, calcula hashes/entropía y hace triage.", ("file", "hashes", "strings", "entropy"), "fast"),
    AgentProfile("static", "KSPR Static", "Analiza formatos, secciones, imports/exports y símbolos.", ("sections", "imports", "exports", "symbols"), "fast"),
    AgentProfile("disasm", "KSPR Disasm", "Desensambla y construye CFG/callgraph.", ("disasm", "cfg", "callgraph", "xrefs"), "reasoning"),
    AgentProfile("decompiler", "KSPR Decompiler", "Reconstruye pseudocódigo con motores reales o IA.", ("decompile", "pseudo"), "reasoning"),
    AgentProfile("crypto", "KSPR Crypto", "Identifica algoritmos, constantes y material clave.", ("crypto", "entropy", "strings"), "reasoning"),
    AgentProfile("network", "KSPR Network", "Analiza capturas y extrae endpoints, protocolos e IOCs.", ("iocs", "strings"), "fast"),
    AgentProfile("carver", "KSPR Carver", "Recupera archivos embebidos y borrados.", ("carve", "recover", "extract", "firmware"), "fast"),
    AgentProfile("writer", "KSPR Writer", "Redacta el informe técnico auditable.", ("report", "graph"), "reasoning"),
    AgentProfile("verifier", "KSPR Verifier", "Audita hallazgos contra la evidencia y marca contradicciones.", ("verify",), "reasoning"),
    AgentProfile("planner", "KSPR Planner", "Descompone el objetivo en un grafo de tareas.", ("plan", "todo"), "reasoning"),
)

_BY_KEY = {agent.key: agent for agent in SUBAGENTS}


def list_agents() -> list[AgentProfile]:
    return list(SUBAGENTS)


def select_agent(name: str) -> AgentProfile | None:
    key = (name or "").strip().lower()
    return _BY_KEY.get(key) or next((a for a in SUBAGENTS if key in a.name.lower()), None)


@dataclass
class PlanStep:
    title: str
    agent: str
    commands: list[str] = field(default_factory=list)


def plan_for(goal: str) -> list[PlanStep]:
    """Build a deterministic analysis plan for a goal/artifact."""
    lowered = (goal or "").lower()
    steps = [
        PlanStep("Triage del artefacto", "recon", ["/recon <ruta>", "/hashes <ruta>"]),
        PlanStep("Análisis estático de formato", "static", ["/sections <ruta>", "/imports <ruta>", "/symbols <ruta>"]),
    ]
    if any(word in lowered for word in ("malware", "muestra", "sospechoso", "apt", "ransom")):
        steps.append(PlanStep("Detección de amenazas", "crypto", ["/packer <ruta>", "/yara <ruta>", "/capa <ruta>"]))
    steps.append(PlanStep("Desensamblado y descompilación", "decompiler", ["/disasm <ruta>", "/decompile <ruta>", "/pseudo <ruta>"]))
    if any(word in lowered for word in ("firmware", "imagen", "disco", "recuperar", "borrado")):
        steps.append(PlanStep("Recuperación de archivos", "carver", ["/carve <ruta>", "/firmware <ruta>", "/recover <ruta>"]))
    steps.append(PlanStep("Informe y verificación", "writer", ["/report <ruta>", "/verify <ruta>"]))
    return steps
