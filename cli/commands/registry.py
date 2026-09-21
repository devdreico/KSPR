"""Central command registry for the KSPR interactive shell.

The registry is the single source of truth for slash commands: the fuzzy
completer, the Ctrl+K palette, the generated `/help` and the "did you mean"
suggestions all read from here.

Nothing in this module imports the backend, so it is fully unit-testable.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Command:
    """Metadata for a single slash command."""

    name: str
    summary: str
    usage: str = ""
    category: str = "core"
    aliases: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()
    args: tuple[str, ...] = ()
    requires: tuple[str, ...] = ()
    dangerous: bool = False

    @property
    def slash(self) -> str:
        return f"/{self.name}"


# Categorías: core, session, provider, re, detect, recovery, ai, ops, help.
COMMANDS: tuple[Command, ...] = (
    # ---- core / sesión ----
    Command("help", "Muestra la ayuda y los comandos disponibles", "/help [comando]", "help", aliases=("h", "?",), keywords=("ayuda", "comandos")),
    Command("clear", "Limpia la pantalla y redibuja el dashboard", "/clear", "session", keywords=("limpiar", "cls")),
    Command("banner", "Redibuja el wordmark ASCII de KSPR", "/banner", "session", keywords=("logo", "ascii")),
    Command("new", "Inicia una sesión nueva", "/new", "session", keywords=("nueva", "reset")),
    Command("sessions", "Explora y restaura sesiones guardadas", "/sessions", "session", aliases=("resume", "continue"), keywords=("historial",)),
    Command("compact", "Compacta el contexto y el uso de tokens", "/compact", "session", keywords=("resumen", "summarize")),
    Command("context", "Muestra los archivos adjuntos activos", "/context", "session"),
    Command("export", "Exporta la transcripción de la sesión", "/export [md|json]", "session", args=("formato",)),
    Command("exit", "Cierra la sesión interactiva", "/exit", "session", aliases=("quit", "q")),
    Command("update", "Actualiza KSPR a la última versión", "/update", "ops"),

    # ---- proveedor / configuración ----
    Command("api", "Configura proveedores, API Keys e indexa modelos", "/api [proveedor]", "provider", aliases=("connect",), keywords=("api key", "token", "modelos")),
    Command("model", "Muestra o selecciona un modelo indexado", "/model [nombre|num]", "provider", aliases=("mo",), keywords=("modelo",)),
    Command("provider", "Cambia el proveedor activo", "/provider [nombre]", "provider", keywords=("proveedor",)),
    Command("login", "Autentica tu código de licencia para desbloquear /api", "/login", "provider", keywords=("licencia", "unlock")),
    Command("config", "Muestra rutas de configuración y estado activo", "/config", "provider"),

    # ---- proyectos / herramientas ----
    Command("project", "Gestor de proyectos locales", "/project", "ops", keywords=("workspace", "carpeta")),
    Command("mcp", "Gestiona servidores MCP", "/mcp [add|remove|enable|test|tools]", "ops", keywords=("contexto",)),
    Command("plugins", "Gestiona plugins externos", "/plugins [load|tools|info]", "ops"),
    Command("capabilities", "Descubre y ejecuta capacidades CLI", "/capabilities [search|info|run|refresh]", "ops", aliases=("caps",)),
    Command("skills", "Muestra y gestiona bundles de skills", "/skills [info|context|load]", "ops"),
    Command("prompts", "Gestiona prompts guardados", "/prompts [add|select|remove|info]", "ops"),
    Command("tools", "Detecta e instala herramientas de ingeniería inversa", "/tools [detect|status|install|which] [nombre]", "ops", keywords=("radare2", "ghidra", "binwalk", "yara", "instalar")),
    Command("doctor", "Autodiagnóstico de la instalación y proveedores", "/doctor", "ops"),
    Command("theme", "Cambia el tema visual del shell", "/theme [nombre]", "ops", keywords=("color", "tema", "grayscale")),
    Command("sandbox", "Muestra la política del sandbox", "/sandbox", "ops"),

    # ---- ingeniería inversa: triage ----
    Command("recon", "Triage completo de un artefacto (tipo, hashes, entropía, strings)", "/recon <ruta>", "re", keywords=("triage", "reconocimiento", "analizar")),
    Command("file", "Identifica el tipo de archivo y metadatos", "/file <ruta>", "re", keywords=("tipo", "magic", "identificar")),
    Command("strings", "Extrae cadenas ASCII/UTF-16 con offsets", "/strings <ruta> [min]", "re", keywords=("cadenas", "texto")),
    Command("hex", "Hexdump de un artefacto con offsets", "/hex <ruta> [offset] [len]", "re", keywords=("hexdump", "bytes")),
    Command("sections", "Lista secciones/segmentos de un binario", "/sections <ruta>", "re", keywords=("secciones", "segmentos")),
    Command("imports", "Lista imports/símbolos importados", "/imports <ruta>", "re", keywords=("importaciones", "dependencias")),
    Command("exports", "Lista exports/símbolos exportados", "/exports <ruta>", "re"),
    Command("symbols", "Lista símbolos y funciones", "/symbols <ruta>", "re"),
    Command("entropy", "Mapa de entropía por bloque", "/entropy <ruta> [bloque]", "re", keywords=("entropia", "compresion")),
    Command("hashes", "Calcula hashes del artefacto", "/hashes <ruta>", "re", keywords=("md5", "sha256")),

    # ---- ingeniería inversa: disasm / decompile ----
    Command("disasm", "Desensambla un rango de un binario", "/disasm <ruta> [offset] [n]", "re", aliases=("dis",), keywords=("desensamblar", "instrucciones")),
    Command("decompile", "Decompila una función (motor real o asistido por IA)", "/decompile <ruta> [símbolo|offset]", "re", keywords=("decompilar", "pseudocodigo")),
    Command("pseudo", "Genera pseudocódigo IA anclado a evidencia", "/pseudo <ruta> [offset] [len]", "ai", keywords=("pseudocodigo", "explicar")),
    Command("cfg", "Genera el grafo de flujo de control", "/cfg <ruta> [offset]", "re", keywords=("grafo", "control")),
    Command("callgraph", "Genera el grafo de llamadas", "/callgraph <ruta>", "re", aliases=("cg",)),
    Command("xrefs", "Referencias cruzadas a un símbolo/dirección", "/xrefs <ruta> <símbolo|addr>", "re", keywords=("referencias",)),
    Command("diff", "Compara dos binarios o versiones", "/diff <ruta_a> <ruta_b>", "re", keywords=("comparar", "version")),
    Command("signature", "Genera firmas únicas para reglas", "/signature <ruta> [offset]", "re", keywords=("firma", "yara")),

    # ---- detección de amenazas ----
    Command("packer", "Detecta packers/compresores", "/packer <ruta>", "detect", keywords=("upx", "empaquetado")),
    Command("yara", "Escanea con reglas YARA", "/yara <ruta> [reglas]", "detect", keywords=("malware", "reglas")),
    Command("capa", "Detecta capacidades (MITRE ATT&CK) con capa", "/capa <ruta>", "detect", keywords=("mitre", "capacidades")),
    Command("crypto", "Identifica constantes y algoritmos criptográficos", "/crypto <ruta>", "detect", keywords=("aes", "sha", "cifrado")),
    Command("iocs", "Extrae indicadores de compromiso", "/iocs <ruta>", "detect", keywords=("ioc", "indicadores", "red")),
    Command("pcap", "Analiza una captura de red (protocolos, DNS, HTTP)", "/pcap <ruta>", "detect", keywords=("red", "wireshark", "tcpdump", "dns")),

    # ---- recuperación / restauración ----
    Command("carve", "Carving de archivos embebidos en una imagen", "/carve <imagen> [salida]", "recovery", keywords=("recuperar", "carving", "forense")),
    Command("recover", "Recupera archivos borrados de una imagen", "/recover <imagen> [salida]", "recovery", keywords=("borrados", "undelete")),
    Command("extract", "Extrae un archivo comprimido de forma segura", "/extract <archivo> [salida]", "recovery", aliases=("unzip",)),
    Command("unpack", "Desempaqueta binarios/instaladores", "/unpack <ruta> [salida]", "recovery", keywords=("upx", "nsis", "inno", "instalador")),
    Command("firmware", "Extrae sistemas de archivos de firmware", "/firmware <imagen> [salida]", "recovery", keywords=("squashfs", "ubi", "binwalk")),

    # ---- IA / ecosistema ----
    Command("ask", "Pregunta a la IA sobre el artefacto (RAG citando offsets)", "/ask <ruta> <pregunta>", "ai", keywords=("preguntar", "rag", "consulta")),
    Command("index", "Indexa un artefacto en la memoria vectorial para RAG", "/index <ruta>", "ai", keywords=("rag", "memoria", "indexar")),
    Command("agents", "Lista y selecciona subagentes", "/agents [nombre]", "ai", keywords=("subagente",)),
    Command("plan", "Crea un plan de análisis reanudable", "/plan <objetivo>", "ai", keywords=("tareas", "objetivo")),
    Command("verify", "Verifica hallazgos contra la evidencia", "/verify [hallazgo]", "ai", keywords=("verificar", "auditar")),
    Command("memory", "Muestra la memoria vectorial indexada", "/memory", "ai", keywords=("memoria",)),
    Command("remember", "Guarda una nota en la memoria local", "/remember <texto>", "ai"),
    Command("recall", "Búsqueda semántica en la memoria local", "/recall <consulta>", "ai"),
    Command("todo", "Gestiona el grafo de tareas del workspace", "/todo [add|list|done|clear]", "ai"),
    Command("report", "Genera un informe técnico auditable", "/report <ruta> [salida]", "ai", keywords=("informe", "documentacion")),
    Command("sbom", "Genera un SBOM de dependencias", "/sbom <ruta>", "ai"),
    Command("graph", "Exporta el grafo de artefactos (mermaid/dot/json)", "/graph <ruta> [formato]", "ai"),

    # ---- helpers de código ----
    Command("ast", "Análisis AST de un archivo Python del workspace", "/ast <archivo.py>", "re"),
    Command("decompilate", "Indexa fuentes y genera Context Trees", "/decompilate", "ai", keywords=("contexto", "arbol")),
    Command("trees", "Lista los Context Trees generados", "/trees", "ai"),
    Command("run", "Ejecuta un comando de shell confinado al workspace", "/run <comando>", "ops", dangerous=True),
)


def fuzzy_score(query: str, text: str) -> int:
    """Score how well `text` matches `query` (higher is better, -1 = no match).

    Combines prefix match, subsequence match and a small edit-distance bonus so
    that `/c` ranks `clear`, `config`, `connect`, `carve`, `crypto`, `capa`...
    """
    if not query:
        return 0
    query = query.lower()
    text = (text or "").lower()
    if not text:
        return -1

    if text.startswith(query):
        return 1000 - len(text)
    if query in text:
        return 700 - text.index(query)

    # Subsequence match (e.g. "dcm" -> "decompile")
    it = iter(text)
    if all(char in it for char in query):
        return 500 - len(text)

    # Bounded Levenshtein as a fallback signal for typos.
    distance = _levenshtein(query, text[: max(len(query) + 4, 8)])
    if distance <= max(1, len(query) // 2 + 1):
        return 300 - distance * 10
    return -1


def _levenshtein(a: str, b: str) -> int:
    if not a:
        return len(b)
    if not b:
        return len(a)
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        current = [i]
        for j, cb in enumerate(b, 1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (ca != cb)))
        previous = current
    return previous[-1]


def search_commands(query: str, limit: int | None = None) -> list[Command]:
    """Return commands ranked by relevance to `query` (empty query = all)."""
    stripped = (query or "").strip().lstrip("/")
    if not stripped:
        ranked = list(COMMANDS)
    else:
        scored: list[tuple[int, Command]] = []
        for command in COMMANDS:
            candidates = [command.name, *command.aliases, *command.keywords]
            best = max((fuzzy_score(stripped, candidate) for candidate in candidates), default=-1)
            if best >= 0:
                scored.append((best, command))
        scored.sort(key=lambda item: item[0], reverse=True)
        ranked = [command for _score, command in scored]
    return ranked[:limit] if limit else ranked


def find_command(name: str) -> Command | None:
    """Resolve a command by name or alias."""
    normalized = (name or "").strip().lstrip("/").lower()
    for command in COMMANDS:
        if command.name == normalized or normalized in command.aliases:
            return command
    return None
