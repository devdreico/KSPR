# KSPR AI CLI TOOL — plan de capacidades, `/prompts` y `gsap-skills`

---

## 1. Resumen Ejecutivo

Este plan documenta la evolución de KSPR AI CLI TOOL hacia una plataforma extensible para descubrir, describir y ejecutar capacidades externas desde una interfaz unificada. La capa de capacidades amplía el análisis sin ocultar el origen de cada herramienta ni sus permisos.

### Los Tres Cambios

| Cambio | Descripción | Impacto |
|--------|-------------|---------|
| **Capability Layer** | Capa de abstracción para descubrir, registrar y ejecutar herramientas externas (CLIs, MCP, plugins, nativas) bajo una interfaz unificada `CapabilitySchema` | Alto — habilita composición de herramientas |
| **/prompts** | Sistema de gestión de prompts personalizados que permite al usuario guardar, seleccionar y reutilizar System Prompts | Medio — mejora productividad del usuario |
| **gsap-skills** | Sistema de skills empaquetados que enseñan al LLM nuevas competencias mediante bundles de SKILL.md + manifest | Alto — amplía capacidades del agente sin cambio de código |

### Principio Fundamental

> **KSPR I NUNCA conoce los detalles internos de CLI-Anything.**

La Capability Layer interactúa con CLI-Anything exclusivamente a través de:
- Detección de ejecutables en PATH (`shutil.which`)
- Lectura de archivos `registry.json` instalados localmente
- Parsing de archivos `SKILL.md` en formato YAML frontmatter + markdown
- Ejecución de comandos CLI como procesos externos (subprocess)

KSPR I no importa, no hereda y no referencia directamente ningún módulo de CLI-Anything. La interfaz es puramente de filesystem y subprocess.

---

## 2. Arquitectura Actual

### 2.1 Backend: `backend/kspr_engine/`

```
backend/kspr_engine/
├── config.py           # Configuración global (API keys, modelos, parámetros)
├── models.py           # MCPTool, PluginInfo, MCPServerConfig
├── providers/          # 9 proveedores LLM (OpenAI, Anthropic, Google, etc.)
├── analyzer.py         # Análisis de código y sugerencias
├── scanner.py          # Escaneo de proyecto y detección de stack
├── mcp_client.py       # MCPClient + MCPManager (conexión a servidores MCP)
├── plugin_manager.py   # Gestión de plugins externos
├── prompts/            # Templates de prompts del sistema
├── memory.py           # Gestión de contexto y memoria de conversación
├── sandbox.py          # Ejecución aislada de código
└── permissions.py      # Sistema de permisos de usuario
```

### 2.2 Modelos de Datos Existentes

```python
# models.py
class MCPTool:
    """Herramienta descubierta vía MCP."""
    name: str
    description: str
    parameters: dict       # JSON Schema
    server_name: str       # Servidor MCP que la provee

class PluginInfo:
    """Plugin registrado externamente."""
    name: str
    description: str
    version: str
    entry_point: str
    commands: list[str]

class MCPServerConfig:
    """Configuración de conexión a un servidor MCP."""
    name: str
    command: str           # Ej: "npx @modelcontextprotocol/server-filesystem"
    args: list[str]
    env: dict[str, str]
```

### 2.3 Flujo de Tool Calling Actual

```
Usuario → Shell CLI → Tool Calling Loop
                         ├── MCPManager.get_tools() → MCPTool[]
                         ├── PluginManager.get_tools() → PluginInfo[]
                         ├── Filter por permisos
                         ├── Serializa como JSON Schema para LLM
                         ├── LLM decide tool call
                         ├── MCPClient.execute() / PluginManager.execute()
                         └── Retorna resultado al LLM
```

### 2.4 Infraestructura de Skills: NO EXISTE

Actualmente **no existe** ninguna infraestructura de skills, bundles, capa de capabilities ni gestión de prompts personalizados. Este plan crea todo desde cero.

---

## 3. CLI-Anything Architecture (Estudiada)

### 3.1 Estructura del Harness

```
cli-anything-harness/
├── setup.py              # pip install -e .
├── cli.py                # Click CLI entry point
├── core/
│   ├── __init__.py
│   ├── orchestrator.py   # Orquestación de comandos
│   └── config.py         # Configuración del harness
├── utils/
│   ├── __init__.py
│   ├── json_utils.py     # Serialización JSON con fallback
│   └── shell.py          # Helpers de subprocess
└── skills/
    └── SKILL.md          # Skill empaquetado (YAML + Markdown)
```

### 3.2 Formato SKILL.md

Cada skill se define en un archivo `SKILL.md` con frontmatter YAML y cuerpo markdown:

```markdown
---
name: code-analysis
description: Análisis de código para detectar bugs, code smells y vulnerabilidades
---

## Análisis de Código

Comandos para análisis de calidad de código.

| Comando | Descripción | Ejemplo |
|---------|-------------|---------|
| `analyze <file>` | Analiza un archivo de código | `analyze src/main.py` |
| `lint <dir>` | Ejecuta linter en directorio | `lint src/` |
| `report` | Genera reporte completo | `report --format json` |
```

### 3.3 Schema de registry.json

```json
{
  "version": "1.0.0",
  "skills": {
    "cli-anything-default": {
      "name": "cli-anything-default",
      "description": "Herramientas base de CLI-Anything",
      "version": "0.1.0",
      "skill_path": "/path/to/SKILL.md",
      "installed": true,
      "dependencies": [],
      "commands": {
        "analyze": {
          "description": "Analiza un archivo de código",
          "usage": "analyze <file>",
          "args": ["file"]
        }
      }
    }
  }
}
```

### 3.4 CLI-Hub

- **Instalación**: `pip install cli-anything-hub`
- **Listar skills**: `cli-hub list`
- **Buscar skills**: `cli-hub search <query>`
- **Instalar skill**: `cli-hub install <skill-name>`

### 3.5 Comandos opencode (5 existentes)

1. `opencode /capabilities` — Lista capabilities instaladas
2. `opencode /capability run <name> <args>` — Ejecuta una capability
3. `opencode /capability info <name>` — Info detallada de una capability
4. `opencode /capability install <name>` — Instala una capability via CLI-Hub
5. `opencode /capability refresh` — Refresca el catálogo de capabilities

---

## 4. Tarea 1: Capability Layer

### 4.1 Estructura de Directorios

```
backend/kspr_engine/
├── capabilities/
│   ├── __init__.py          # CapabilityManager
│   ├── schemas.py           # CapabilitySchema, CapabilityResult, CapabilityValidation
│   ├── registry.py          # CapabilityRegistry
│   ├── discovery.py         # CapabilityDiscovery
│   ├── loader.py            # CapabilityLoader
│   ├── executor.py          # CapabilityExecutor
│   ├── validator.py         # CapabilityValidator
│   └── permissions.py       # CapabilityPermissions
└── adapters/
    ├── __init__.py          # BaseAdapter ABC
    └── cli_anything/
        ├── __init__.py      # CLIAnythingAdapter
        ├── detector.py      # Detects installed harnesses
        ├── parser.py        # Parses SKILL.md
        └── runner.py        # Executes CLIs
```

### 4.2 `capabilities/schemas.py` — Modelos de Datos

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
import time
import uuid


class SourceType(Enum):
    """Tipos de fuente de donde proviene una capability."""
    CLI_ANYTHING = "cli-anything"
    MCP = "mcp"
    PLUGIN = "plugin"
    NATIVE = "native"


class ErrorType(Enum):
    """Clasificación de errores en ejecución."""
    NOT_FOUND = "not_found"
    TIMEOUT = "timeout"
    PERMISSION_ERROR = "permission_error"
    EXECUTION_ERROR = "execution_error"
    VALIDATION_ERROR = "validation_error"
    UNKNOWN = "unknown"


@dataclass
class CapabilitySchema:
    """
    Representación unificada de una capability disponible en el sistema.
    Cualquier fuente (CLI-Anything, MCP, plugin, nativa) se normaliza a este formato.
    """
    id: str                                  # UUID único o ID determinista (ej: "cli-any:code-analysis")
    name: str                                # Nombre legible: "code-analysis"
    description: str                         # Descripción en lenguaje natural
    source: str                              # Identificador de la fuente: "cli-anything-default"
    source_type: SourceType                  # Tipo de fuente
    category: str                            # Categoría: "analysis", "security", "utility", etc.
    command: list[str]                       # Comando base: ["cli-anything", "analyze"]
    arguments: dict[str, Any]                # Argumentos disponibles (JSON Schema-like)
    returns_json: bool                       # Si la capability retorna JSON válido
    requires: list[str]                      # Dependencias necesarias: ["python3", "git"]
    skill_path: Optional[str]                # Ruta al SKILL.md (si aplica)
    skill_content: Optional[str]             # Contenido raw del SKILL.md
    installed: bool                          # Si la capability está instalada/disponible
    version: str                             # Versión semántica: "0.1.0"
    metadata: dict[str, Any]                 # Campo libre para metadata extra

    def to_dict(self) -> dict:
        """Serializa a diccionario para persistencia."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "source": self.source,
            "source_type": self.source_type.value,
            "category": self.category,
            "command": self.command,
            "arguments": self.arguments,
            "returns_json": self.returns_json,
            "requires": self.requires,
            "skill_path": self.skill_path,
            "skill_content": self.skill_content,
            "installed": self.installed,
            "version": self.version,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CapabilitySchema":
        """Deserializa desde diccionario."""
        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            source=data["source"],
            source_type=SourceType(data["source_type"]),
            category=data["category"],
            command=data["command"],
            arguments=data.get("arguments", {}),
            returns_json=data.get("returns_json", False),
            requires=data.get("requires", []),
            skill_path=data.get("skill_path"),
            skill_content=data.get("skill_content"),
            installed=data.get("installed", True),
            version=data.get("version", "0.0.1"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class CapabilityResult:
    """
    Resultado de la ejecución de una capability.
    Captura tanto éxitos como fallos con metadata completa.
    """
    capability_id: str                       # ID de la capability ejecutada
    success: bool                            # Si la ejecución fue exitosa
    exit_code: int                           # Código de salida del proceso (0 = éxito)
    stdout: str                              # Salida estándar completa
    stderr: str                              # Salida de error completa
    parsed_output: Optional[Any]             # Output parseado (si returns_json=True)
    error_type: Optional[ErrorType]          # Clasificación del error (si success=False)
    error_message: Optional[str]             # Mensaje de error legible
    duration_ms: float                       # Duración en milisegundos
    metadata: dict[str, Any]                 # Metadata extra (archivos leídos, etc.)

    @property
    def display_output(self) -> str:
        """Retorna el mejor output disponible para mostrar al usuario."""
        if self.parsed_output is not None:
            if isinstance(self.parsed_output, dict):
                import json
                return json.dumps(self.parsed_output, indent=2, ensure_ascii=False)
            return str(self.parsed_output)
        if self.success:
            return self.stdout
        return self.error_message or self.stderr or "Error desconocido"


@dataclass
class CapabilityValidation:
    """Resultado de validación de un CapabilityResult."""
    is_valid: bool                           # Si el resultado cumple expectations
    issues: list[str]                        # Lista de problemas encontrados
    warnings: list[str]                      # Advertencias no bloqueantes
    validated_at: float                      # Timestamp de validación
```

### 4.3 `capabilities/registry.py` — CapabilityRegistry

```python
import json
import os
from pathlib import Path
from typing import Optional
from .schemas import CapabilitySchema, SourceType


class CapabilityRegistry:
    """
    Registro central de todas las capabilities conocidas por el sistema.
    Persiste a ~/.kspr/capabilities.json.
    """

    REGISTRY_PATH = Path.home() / ".kspr" / "capabilities.json"

    def __init__(self):
        self._capabilities: dict[str, CapabilitySchema] = {}
        self._load()

    # ── CRUD Operations ──────────────────────────────────────────────

    def register(self, cap: CapabilitySchema) -> None:
        """Registra una capability. Sobrescribe si el ID ya existe."""
        self._capabilities[cap.id] = cap
        self._save()

    def unregister(self, cap_id: str) -> bool:
        """Elimina una capability del registro. Retorna True si existía."""
        if cap_id in self._capabilities:
            del self._capabilities[cap_id]
            self._save()
            return True
        return False

    def get(self, cap_id: str) -> Optional[CapabilitySchema]:
        """Obtiene una capability por ID exacto."""
        return self._capabilities.get(cap_id)

    # ── Search ───────────────────────────────────────────────────────

    def search(self, query: str) -> list[CapabilitySchema]:
        """Búsqueda por nombre o descripción (case-insensitive, parcial)."""
        query_lower = query.lower()
        results = []
        for cap in self._capabilities.values():
            if (query_lower in cap.name.lower() or
                query_lower in cap.description.lower()):
                results.append(cap)
        return sorted(results, key=lambda c: c.name)

    def list_all(self) -> list[CapabilitySchema]:
        """Retorna todas las capabilities registradas."""
        return list(self._capabilities.values())

    def list_by_source(self, source_type: SourceType) -> list[CapabilitySchema]:
        """Filtra capabilities por tipo de fuente."""
        return [c for c in self._capabilities.values()
                if c.source_type == source_type]

    def list_installed(self) -> list[CapabilitySchema]:
        """Retorna solo capabilities instaladas y disponibles."""
        return [c for c in self._capabilities.values() if c.installed]

    # ── Persistence ──────────────────────────────────────────────────

    def _save(self) -> None:
        """Persiste el registro a disco."""
        self.REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": "1.0.0",
            "capabilities": {
                cap_id: cap.to_dict()
                for cap_id, cap in self._capabilities.items()
            },
        }
        with open(self.REGISTRY_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _load(self) -> None:
        """Carga el registro desde disco si existe."""
        if not self.REGISTRY_PATH.exists():
            return
        try:
            with open(self.REGISTRY_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            for cap_id, cap_data in data.get("capabilities", {}).items():
                self._capabilities[cap_id] = CapabilitySchema.from_dict(cap_data)
        except (json.JSONDecodeError, KeyError):
            self._capabilities = {}
```

### 4.4 `capabilities/discovery.py` — CapabilityDiscovery

```python
import logging
from typing import Optional
from .schemas import CapabilitySchema
from .registry import CapabilityRegistry
from ..adapters import BaseAdapter

logger = logging.getLogger(__name__)


class CapabilityDiscovery:
    """
    Motor de descubrimiento que orquesta adapters para poblar el registry.
    Cada adapter sabe cómo buscar capabilities de un tipo específico.
    """

    def __init__(self, registry: CapabilityRegistry):
        self._registry = registry
        self._adapters: list[BaseAdapter] = []

    def register_adapter(self, adapter: BaseAdapter) -> None:
        """Registra un adapter de descubrimiento."""
        self._adapters.append(adapter)
        logger.info(f"Adapter registrado: {adapter.__class__.__name__}")

    def discover_all(self) -> list[CapabilitySchema]:
        """
        Ejecuta discovery en TODOS los adapters registrados.
        Retorna la lista completa de capabilities encontradas.
        """
        all_capabilities = []
        for adapter in self._adapters:
            try:
                caps = adapter.discover()
                all_capabilities.extend(caps)
                logger.info(
                    f"{adapter.__class__.__name__} encontró {len(caps)} capabilities"
                )
            except Exception as e:
                logger.error(
                    f"Error en adapter {adapter.__class__.__name__}: {e}"
                )
        # Registrar todas en el registry
        for cap in all_capabilities:
            self._registry.register(cap)
        return all_capabilities

    def discover_from(self, adapter_name: str) -> list[CapabilitySchema]:
        """Discovery desde un adapter específico por nombre de clase."""
        for adapter in self._adapters:
            if adapter.__class__.__name__ == adapter_name:
                caps = adapter.discover()
                for cap in caps:
                    self._registry.register(cap)
                return caps
        logger.warning(f"Adapter no encontrado: {adapter_name}")
        return []

    def refresh(self) -> list[CapabilitySchema]:
        """Refresca todo el discovery desde cero."""
        return self.discover_all()
```

### 4.5 `capabilities/loader.py` — CapabilityLoader

```python
import re
import subprocess
import yaml
from pathlib import Path
from typing import Optional
from .schemas import CapabilitySchema, SourceType


class CapabilityLoader:
    """
    Carga y enriquece CapabilitySchema desde distintas fuentes:
    - SKILL.md (YAML frontmatter + markdown)
    - CLI --help output
    - Registro manual
    """

    @staticmethod
    def load_skill_md(skill_path: str) -> Optional[CapabilitySchema]:
        """
        Parsea un archivo SKILL.md con frontmatter YAML.
        
        Formato esperado:
        ---
        name: code-analysis
        description: Análisis de código
        ---
        ## Comandos
        | Comando | Descripción |
        |---------|-------------|
        | analyze <file> | Analiza archivo |
        """
        path = Path(skill_path)
        if not path.exists():
            return None

        content = path.read_text(encoding="utf-8")

        # Extraer frontmatter YAML
        frontmatter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
        if not frontmatter_match:
            return None

        try:
            frontmatter = yaml.safe_load(frontmatter_match.group(1))
        except yaml.YAMLError:
            return None

        name = frontmatter.get("name", path.parent.name)
        description = frontmatter.get("description", "Sin descripción")

        # Extraer commandos del body markdown (tablas)
        body = content[frontmatter_match.end():]
        commands = CapabilityLoader._parse_markdown_commands(body)

        skill_content = frontmatter_match.group(0) + body

        return CapabilitySchema(
            id=f"skill:{name}",
            name=name,
            description=description,
            source=str(path),
            source_type=SourceType.CLI_ANYTHING,
            category=frontmatter.get("category", "utility"),
            command=frontmatter.get("command", []),
            arguments=commands,
            returns_json=frontmatter.get("returns_json", False),
            requires=frontmatter.get("requires", []),
            skill_path=str(path),
            skill_content=skill_content,
            installed=True,
            version=frontmatter.get("version", "0.0.1"),
            metadata=frontmatter.get("metadata", {}),
        )

    @staticmethod
    def _parse_markdown_commands(body: str) -> dict:
        """
        Extrae commandos de tablas markdown.
        Formato: | comando | descripción | args |
        """
        commands = {}
        # Buscar filas de tabla que contengan backticks (código)
        table_pattern = re.compile(
            r"\|\s*`([^`]+)`\s*\|\s*(.+?)\s*\|", re.MULTILINE
        )
        for match in table_pattern.finditer(body):
            cmd_str = match.group(1).strip()
            desc = match.group(2).strip()
            # Extraer nombre del comando (primera palabra)
            cmd_name = cmd_str.split()[0] if cmd_str else cmd_str
            commands[cmd_name] = {
                "description": desc,
                "usage": cmd_str,
                "args": re.findall(r"<(\w+)>", cmd_str),
            }
        return commands

    @staticmethod
    def load_cli_help(command: list[str], help_flag: str = "--help") -> dict:
        """
        Ejecuta un CLI con --help y extrae información básica.
        Retorna dict con descripción, argumentos y opciones.
        """
        try:
            result = subprocess.run(
                command + [help_flag],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                return {"error": f"Exit code {result.returncode}"}

            output = result.stdout or result.stderr
            # Extraer primera línea como descripción
            lines = [l.strip() for l in output.split("\n") if l.strip()]
            description = lines[0] if lines else "Sin descripción"

            # Extraer argumentos posicionales (<arg>) y opciones (--flag)
            args = re.findall(r"<(\w+)>", output)
            options = re.findall(r"--(\w[\w-]*)", output)

            return {
                "description": description,
                "positional_args": args,
                "options": options,
                "raw_help": output,
            }
        except subprocess.TimeoutExpired:
            return {"error": "Timeout ejecutando --help"}
        except FileNotFoundError:
            return {"error": "Comando no encontrado"}

    @staticmethod
    def enrich_capability(
        cap: CapabilitySchema,
        cli_help: Optional[dict] = None,
    ) -> CapabilitySchema:
        """
        Enriquece un CapabilitySchema con información adicional.
        Si se proporciona cli_help, mergea argumentos y descripción.
        """
        if cli_help and "error" not in cli_help:
            # Enriquecer descripción si la capability tiene una genérica
            if cap.description == "Sin descripción" and "description" in cli_help:
                cap.description = cli_help["description"]

            # Enriquecer argumentos desde --help
            for arg in cli_help.get("positional_args", []):
                if arg not in cap.arguments:
                    cap.arguments[arg] = {
                        "type": "string",
                        "required": True,
                        "source": "cli-help",
                    }

            # Guardar raw help en metadata
            cap.metadata["cli_help_raw"] = cli_help.get("raw_help", "")

        return cap
```

### 4.6 `capabilities/executor.py` — CapabilityExecutor

```python
import json
import logging
import subprocess
import time
from typing import Any, Optional
from .schemas import CapabilitySchema, CapabilityResult, ErrorType

logger = logging.getLogger(__name__)


class CapabilityExecutor:
    """
    Ejecuta capabilities construyendo comandos y parseando resultados.
    Soporta ejecución con --json (para parseo automático) y raw.
    """

    def __init__(self, default_timeout: int = 30):
        self._default_timeout = default_timeout

    def execute(
        self,
        cap: CapabilitySchema,
        args: dict[str, Any],
        prefer_json: bool = True,
        timeout: Optional[int] = None,
    ) -> CapabilityResult:
        """
        Ejecuta una capability con argumentos.
        
        1. Construye el comando completo: cap.command + args
        2. Si prefer_json=True y cap.supports_json, agrega --json
        3. Ejecuta via subprocess.run
        4. Parsea stdout como JSON si returns_json
        5. Retorna CapabilityResult
        """
        timeout = timeout or self._default_timeout
        start_time = time.monotonic()

        # Construir comando
        command = list(cap.command)
        for key, value in args.items():
            if isinstance(value, bool):
                if value:
                    command.append(f"--{key}")
            elif value is not None:
                command.append(f"--{key}")
                command.append(str(value))

        # Agregar --json si soportado
        if prefer_json and cap.returns_json:
            command.append("--json")

        logger.info(f"Ejecutando: {' '.join(command)}")

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            duration_ms = (time.monotonic() - start_time) * 1000

            parsed_output = None
            if cap.returns_json and result.stdout.strip():
                try:
                    parsed_output = json.loads(result.stdout)
                except json.JSONDecodeError:
                    logger.warning("No se pudo parsear JSON del stdout")

            error_type = None
            error_message = None
            if result.returncode != 0:
                error_type = self._classify_error(result.stderr, result.returncode)
                error_message = result.stderr.strip() or f"Exit code: {result.returncode}"

            return CapabilityResult(
                capability_id=cap.id,
                success=(result.returncode == 0),
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                parsed_output=parsed_output,
                error_type=error_type,
                error_message=error_message,
                duration_ms=duration_ms,
                metadata={"command": command},
            )

        except subprocess.TimeoutExpired:
            duration_ms = (time.monotonic() - start_time) * 1000
            return CapabilityResult(
                capability_id=cap.id,
                success=False,
                exit_code=-1,
                stdout="",
                stderr=f"Timeout después de {timeout}s",
                parsed_output=None,
                error_type=ErrorType.TIMEOUT,
                error_message=f"Timeout después de {timeout}s",
                duration_ms=duration_ms,
                metadata={"command": command, "timeout": timeout},
            )
        except FileNotFoundError:
            duration_ms = (time.monotonic() - start_time) * 1000
            return CapabilityResult(
                capability_id=cap.id,
                success=False,
                exit_code=-1,
                stdout="",
                stderr=f"Comando no encontrado: {command[0]}",
                parsed_output=None,
                error_type=ErrorType.NOT_FOUND,
                error_message=f"Comando no encontrado: {command[0]}",
                duration_ms=duration_ms,
                metadata={"command": command},
            )
        except PermissionError:
            duration_ms = (time.monotonic() - start_time) * 1000
            return CapabilityResult(
                capability_id=cap.id,
                success=False,
                exit_code=-1,
                stdout="",
                stderr="Permiso denegado",
                parsed_output=None,
                error_type=ErrorType.PERMISSION_ERROR,
                error_message="Permiso denegado para ejecutar el comando",
                duration_ms=duration_ms,
                metadata={"command": command},
            )
        except Exception as e:
            duration_ms = (time.monotonic() - start_time) * 1000
            return CapabilityResult(
                capability_id=cap.id,
                success=False,
                exit_code=-1,
                stdout="",
                stderr=str(e),
                parsed_output=None,
                error_type=ErrorType.EXECUTION_ERROR,
                error_message=str(e),
                duration_ms=duration_ms,
                metadata={"command": command, "exception": type(e).__name__},
            )

    def execute_raw(
        self,
        command: list[str],
        timeout: Optional[int] = None,
        cwd: Optional[str] = None,
    ) -> CapabilityResult:
        """
        Ejecuta un comando raw sin asociar a una CapabilitySchema.
        Útil para comandos ad-hoc desde el shell.
        """
        timeout = timeout or self._default_timeout
        start_time = time.monotonic()

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
            )
            duration_ms = (time.monotonic() - start_time) * 1000

            return CapabilityResult(
                capability_id="raw",
                success=(result.returncode == 0),
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                parsed_output=None,
                error_type=None if result.returncode == 0 else ErrorType.EXECUTION_ERROR,
                error_message=None if result.returncode == 0 else result.stderr.strip(),
                duration_ms=duration_ms,
                metadata={"command": command, "raw": True},
            )
        except subprocess.TimeoutExpired:
            duration_ms = (time.monotonic() - start_time) * 1000
            return CapabilityResult(
                capability_id="raw",
                success=False,
                exit_code=-1,
                stdout="",
                stderr=f"Timeout después de {timeout}s",
                parsed_output=None,
                error_type=ErrorType.TIMEOUT,
                error_message=f"Timeout después de {timeout}s",
                duration_ms=duration_ms,
                metadata={"command": command},
            )
        except Exception as e:
            duration_ms = (time.monotonic() - start_time) * 1000
            return CapabilityResult(
                capability_id="raw",
                success=False,
                exit_code=-1,
                stdout="",
                stderr=str(e),
                parsed_output=None,
                error_type=ErrorType.EXECUTION_ERROR,
                error_message=str(e),
                duration_ms=duration_ms,
                metadata={"command": command},
            )

    @staticmethod
    def _classify_error(stderr: str, exit_code: int) -> ErrorType:
        """Clasifica el tipo de error basado en stderr y exit code."""
        stderr_lower = stderr.lower()
        if "not found" in stderr_lower or "no such file" in stderr_lower:
            return ErrorType.NOT_FOUND
        if "permission denied" in stderr_lower or "access denied" in stderr_lower:
            return ErrorType.PERMISSION_ERROR
        if exit_code == 126:
            return ErrorType.PERMISSION_ERROR
        if exit_code == 127:
            return ErrorType.NOT_FOUND
        return ErrorType.EXECUTION_ERROR
```

### 4.7 `capabilities/validator.py` — CapabilityValidator

```python
import json
from pathlib import Path
from typing import Any, Optional
from .schemas import CapabilityResult, CapabilityValidation


class CapabilityValidator:
    """
    Valida resultados de ejecución de capabilities.
    Soporta validación de exit codes, output y JSON Schema.
    """

    def validate_result(
        self,
        result: CapabilityResult,
        expected_exit_code: int = 0,
        expect_json: bool = False,
        json_schema: Optional[dict] = None,
    ) -> CapabilityValidation:
        """
        Valida un CapabilityResult contra expectativas.
        
        Checks:
        1. Exit code coincide con el esperado
        2. Si expect_json=True, parsed_output no es None
        3. Si json_schema se proporciona, valida contra él
        4. Stderr no debería tener contenido en éxito
        """
        issues = []
        warnings = []

        # Check exit code
        if result.exit_code != expected_exit_code:
            issues.append(
                f"Exit code inesperado: {result.exit_code} (esperado: {expected_exit_code})"
            )

        # Check JSON output
        if expect_json:
            if result.parsed_output is None:
                issues.append("Se esperaba JSON pero parsed_output es None")
            elif json_schema:
                schema_issues = self._validate_json_schema(
                    result.parsed_output, json_schema
                )
                issues.extend(schema_issues)

        # Warnings
        if result.stderr and result.success:
            warnings.append(
                "El comando fue exitoso pero produjo salida en stderr"
            )
        if result.duration_ms > 10000:
            warnings.append(
                f"Tiempo de ejecución alto: {result.duration_ms:.0f}ms"
            )

        return CapabilityValidation(
            is_valid=len(issues) == 0,
            issues=issues,
            warnings=warnings,
            validated_at=result.duration_ms,
        )

    def validate_file_output(
        self,
        file_path: str,
        expected_format: Optional[str] = None,
    ) -> CapabilityValidation:
        """
        Valida que un archivo generado existe y tiene el formato esperado.
        """
        issues = []
        warnings = []
        path = Path(file_path)

        if not path.exists():
            issues.append(f"Archivo no encontrado: {file_path}")
        else:
            if path.stat().st_size == 0:
                warnings.append("El archivo está vacío")
            if expected_format:
                suffix = path.suffix.lstrip(".")
                if suffix != expected_format:
                    issues.append(
                        f"Formato inesperado: {suffix} (esperado: {expected_format})"
                    )

        return CapabilityValidation(
            is_valid=len(issues) == 0,
            issues=issues,
            warnings=warnings,
            validated_at=0,
        )

    def validate_json_schema(
        self,
        data: Any,
        schema: dict,
    ) -> CapabilityValidation:
        """
        Valida datos contra un JSON Schema básico.
        Implementación simplificada: solo valida required fields y tipos.
        """
        issues = self._validate_json_schema(data, schema)
        return CapabilityValidation(
            is_valid=len(issues) == 0,
            issues=issues,
            warnings=[],
            validated_at=0,
        )

    @staticmethod
    def _validate_json_schema(data: Any, schema: dict) -> list[str]:
        """Validación básica de JSON Schema (required + type)."""
        issues = []
        if not isinstance(data, dict):
            issues.append(f"Se esperaba objeto, se recibió {type(data).__name__}")
            return issues

        # Validar campos requeridos
        for field in schema.get("required", []):
            if field not in data:
                issues.append(f"Campo requerido faltante: {field}")

        # Validar tipos básicos
        properties = schema.get("properties", {})
        for field, field_schema in properties.items():
            if field in data:
                expected_type = field_schema.get("type")
                actual_value = data[field]
                if expected_type == "string" and not isinstance(actual_value, str):
                    issues.append(f"Campo '{field}' debe ser string")
                elif expected_type == "number" and not isinstance(actual_value, (int, float)):
                    issues.append(f"Campo '{field}' debe ser number")
                elif expected_type == "boolean" and not isinstance(actual_value, bool):
                    issues.append(f"Campo '{field}' debe ser boolean")

        return issues
```

### 4.8 `capabilities/permissions.py` — CapabilityPermissions

```python
import json
import logging
from pathlib import Path
from typing import Optional
from .schemas import CapabilitySchema

logger = logging.getLogger(__name__)


class PermissionLevel:
    """Niveles de permiso para capabilities."""
    READ = 0       # Solo lectura / consulta
    EXECUTE = 1    # Ejecución básica
    WRITE = 2      # Escritura en filesystem
    ADMIN = 3      # Operaciones administrativas

    LEVEL_NAMES = {0: "read", 1: "execute", 2: "write", 3: "admin"}

    @classmethod
    def from_name(cls, name: str) -> int:
        """Convierte nombre a nivel numérico."""
        for level, level_name in cls.LEVEL_NAMES.items():
            if level_name == name:
                return level
        return cls.READ


class CapabilityPermissions:
    """
    Gestión de permisos para capabilities.
    Persiste a ~/.kspr/capability_permissions.json.
    """

    PERMISSIONS_PATH = Path.home() / ".kspr" / "capability_permissions.json"

    def __init__(self):
        self._permissions: dict[str, int] = {}  # cap_id -> permission_level
        self._load()

    def check(
        self,
        cap: CapabilitySchema,
        required_level: int = PermissionLevel.EXECUTE,
    ) -> bool:
        """
        Verifica si el nivel actual permite ejecutar esta capability.
        Si la capability no tiene permiso registrado, requiere confirmación
        del usuario (nivel por defecto: READ).
        """
        current_level = self._permissions.get(cap.id, PermissionLevel.READ)
        return current_level >= required_level

    def grant(self, cap_id: str, level: int) -> None:
        """Otorga un nivel de permiso a una capability."""
        if level < PermissionLevel.READ or level > PermissionLevel.ADMIN:
            raise ValueError(f"Nivel de permiso inválido: {level}")
        self._permissions[cap_id] = level
        self._save()
        logger.info(
            f"Permiso otorgado: {cap_id} -> nivel {PermissionLevel.LEVEL_NAMES[level]}"
        )

    def revoke(self, cap_id: str) -> bool:
        """Revoca permisos de una capability (vuelve al nivel READ por defecto)."""
        if cap_id in self._permissions:
            del self._permissions[cap_id]
            self._save()
            return True
        return False

    def get_level(self, cap_id: str) -> int:
        """Retorna el nivel de permiso actual para una capability."""
        return self._permissions.get(cap_id, PermissionLevel.READ)

    def prompt_user(
        self,
        cap: CapabilitySchema,
        required_level: int,
    ) -> bool:
        """
        Pide al usuario confirmación interactiva para otorgar permisos.
        Retorna True si el usuario acepta.
        
        Nota: Esta función es un stub que será integrada con el
        shell interactivo de KSPR. Por ahora retorna True.
        """
        level_name = PermissionLevel.LEVEL_NAMES.get(required_level, "unknown")
        print(f"\n⚠️  Capability '{cap.name}' requiere permiso '{level_name}'")
        print(f"   Descripción: {cap.description}")
        # TODO: Integrar con shell interactivo para input real
        response = input("¿Otorgar permiso? [s/N]: ").strip().lower()
        if response in ("s", "si", "sí", "y", "yes"):
            self.grant(cap.id, required_level)
            return True
        return False

    def _save(self) -> None:
        """Persiste permisos a disco."""
        self.PERMISSIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(self.PERMISSIONS_PATH, "w", encoding="utf-8") as f:
            json.dump(self._permissions, f, indent=2)

    def _load(self) -> None:
        """Carga permisos desde disco."""
        if not self.PERMISSIONS_PATH.exists():
            return
        try:
            with open(self.PERMISSIONS_PATH, "r", encoding="utf-8") as f:
                self._permissions = json.load(f)
        except (json.JSONDecodeError, KeyError):
            self._permissions = {}
```

### 4.9 `adapters/__init__.py` — BaseAdapter

```python
from abc import ABC, abstractmethod
from typing import List
from ..capabilities.schemas import CapabilitySchema


class BaseAdapter(ABC):
    """
    Interfaz abstracta para adapters de descubrimiento.
    Cada fuente de capabilities (CLI-Anything, MCP, plugins, etc.)
    implementa esta interfaz.
    """

    @abstractmethod
    def discover(self) -> List[CapabilitySchema]:
        """
        Descubre todas las capabilities disponibles de esta fuente.
        Retorna lista de CapabilitySchema normalizados.
        """
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """
        Verifica si esta fuente está disponible en el sistema.
        Ej: CLI-Anything está instalado, un servidor MCP está corriendo, etc.
        """
        ...

    @property
    @abstractmethod
    def source_type(self) -> str:
        """Retorna el tipo de fuente (SourceType.value)."""
        ...
```

### 4.10 `adapters/cli_anything/detector.py` — CLIAnythingDetector

```python
import json
import logging
import shutil
from pathlib import Path
from typing import Optional
import importlib.metadata

logger = logging.getLogger(__name__)


class CLIAnythingDetector:
    """
    Detecta harnesses de CLI-Anything instalados en el sistema.
    Múltiples estrategias de detección:
    1. shutil.which() para ejecutables en PATH
    2. ~/.cli-hub/installed.json para registro local
    3. registry.json para metadatos de skills
    4. pip distributions para instalación via pip
    """

    CLI_HUB_DIR = Path.home() / ".cli-hub"
    INSTALLED_JSON = CLI_HUB_DIR / "installed.json"

    def detect_installed(self) -> list[dict]:
        """
        Ejecuta todas las estrategias de detección y retorna
        lista unificada de harnesses encontrados.
        """
        harnesses = []

        # Estrategia 1: Ejecutables en PATH
        path_harnesses = self._detect_from_path()
        harnesses.extend(path_harnesses)

        # Estrategia 2: ~/.cli-hub/installed.json
        hub_harnesses = self._detect_from_hub_json()
        harnesses.extend(hub_harnesses)

        # Estrategia 3: pip distributions
        pip_harnesses = self._detect_from_pip()
        harnesses.extend(pip_harnesses)

        # Deduplicar por nombre
        seen = set()
        unique_harnesses = []
        for h in harnesses:
            name = h.get("name", "")
            if name and name not in seen:
                seen.add(name)
                unique_harnesses.append(h)

        logger.info(f"Detectados {len(unique_harnesses)} harnesses CLI-Anything")
        return unique_harnesses

    def _detect_from_path(self) -> list[dict]:
        """Busca ejecutables que empiecen con 'cli-anything-' en PATH."""
        harnesses = []
        common_prefixes = ["cli-anything-", "cli-hub-"]
        for prefix in common_prefixes:
            # Buscar en directorios comunes de PATH
            for path_dir in Path("/usr/local/bin").iterdir():
                if path_dir.name.startswith(prefix) and path_dir.is_file():
                    harnesses.append({
                        "name": path_dir.name,
                        "command": [str(path_dir)],
                        "source": "path",
                        "version": "unknown",
                    })
        return harnesses

    def _detect_from_hub_json(self) -> list[dict]:
        """Lee ~/.cli-hub/installed.json si existe."""
        if not self.INSTALLED_JSON.exists():
            return []
        try:
            with open(self.INSTALLED_JSON, "r", encoding="utf-8") as f:
                data = json.load(f)
            harnesses = []
            for name, info in data.get("installed", {}).items():
                harnesses.append({
                    "name": name,
                    "command": info.get("command", [name]),
                    "source": "cli-hub",
                    "version": info.get("version", "0.0.0"),
                    "registry_path": info.get("registry_path"),
                })
            return harnesses
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Error leyendo installed.json: {e}")
            return []

    def _detect_from_pip(self) -> list[dict]:
        """Busca paquetes pip que contengan 'cli-anything' en el nombre."""
        harnesses = []
        try:
            dists = importlib.metadata.distributions()
            for dist in dists:
                name = dist.metadata["Name"]
                if "cli-anything" in name.lower() or "cli-hub" in name.lower():
                    harnesses.append({
                        "name": name,
                        "command": [name.replace("-", "_")],  # Conversión básica
                        "source": "pip",
                        "version": dist.metadata["Version"],
                    })
        except Exception as e:
            logger.debug(f"Error escaneando pip: {e}")
        return harnesses

    def get_registry_path(self, harness_name: str) -> Optional[Path]:
        """Busca registry.json para un harness específico."""
        # Buscar en ubicaciones comunes
        search_paths = [
            Path.home() / ".cli-hub" / harness_name / "registry.json",
            Path(f"/usr/local/lib/{harness_name}/registry.json"),
            Path.home() / ".local" / "share" / harness_name / "registry.json",
        ]
        for path in search_paths:
            if path.exists():
                return path
        return None
```

### 4.11 `adapters/cli_anything/parser.py` — SKILL.md Parser

```python
import re
import yaml
from pathlib import Path
from typing import Optional
from ...capabilities.schemas import CapabilitySchema, SourceType


class SKILLParser:
    """
    Parser de archivos SKILL.md con frontmatter YAML.
    Extrae metadata y commandos del formato markdown.
    """

    @staticmethod
    def parse_skill_md(skill_path: str) -> Optional[CapabilitySchema]:
        """
        Parsea un SKILL.md y retorna un CapabilitySchema.
        
        Formato:
        ---
        name: code-analysis
        description: Análisis de código
        category: analysis
        command: [cli-anything, analyze]
        returns_json: true
        ---
        ## Comandos
        | Comando | Descripción |
        |---------|-------------|
        | `analyze <file>` | Analiza archivo |
        """
        path = Path(skill_path)
        if not path.exists():
            return None

        content = path.read_text(encoding="utf-8")

        # Extraer frontmatter YAML
        frontmatter_match = re.match(
            r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL
        )
        if not frontmatter_match:
            return None

        try:
            meta = yaml.safe_load(frontmatter_match.group(1))
        except yaml.YAMLError:
            return None

        # Extraer body markdown
        body = content[frontmatter_match.end():]

        # Extraer commandos de tablas markdown
        commands = SKILLParser._extract_commands_from_tables(body)

        skill_content = content

        return CapabilitySchema(
            id=f"cli-any:{meta.get('name', path.parent.name)}",
            name=meta.get("name", path.parent.name),
            description=meta.get("description", "Sin descripción"),
            source=meta.get("source", str(path)),
            source_type=SourceType.CLI_ANYTHING,
            category=meta.get("category", "utility"),
            command=meta.get("command", []),
            arguments=commands,
            returns_json=meta.get("returns_json", False),
            requires=meta.get("requires", []),
            skill_path=str(path),
            skill_content=skill_content,
            installed=True,
            version=meta.get("version", "0.0.1"),
            metadata=meta.get("metadata", {}),
        )

    @staticmethod
    def _extract_commands_from_tables(body: str) -> dict:
        """
        Extrae commandos de tablas markdown.
        
        Busca patrones:
        | `comando <arg>` | Descripción |
        """
        commands = {}
        # Regex para filas de tabla con código en backticks
        row_pattern = re.compile(
            r"\|\s*`([^`]+)`\s*\|\s*(.+?)\s*\|", re.MULTILINE
        )

        for match in row_pattern.finditer(body):
            cmd_str = match.group(1).strip()
            description = match.group(2).strip()

            # Extraer nombre del comando (primera palabra o token)
            parts = cmd_str.split()
            if parts:
                cmd_name = parts[0]
                # Extraer argumentos posicionales <arg>
                args = re.findall(r"<(\w+)>", cmd_str)
                # Extraer flags --flag
                flags = re.findall(r"--(\w[\w-]*)", cmd_str)

                commands[cmd_name] = {
                    "description": description,
                    "usage": cmd_str,
                    "positional_args": args,
                    "flags": flags,
                }

        return commands

    @staticmethod
    def parse_from_string(content: str, name: str = "unknown") -> Optional[CapabilitySchema]:
        """Parsea SKILL.md desde un string (para testing)."""
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            temp_path = f.name

        try:
            return SKILLParser.parse_skill_md(temp_path)
        finally:
            os.unlink(temp_path)
```

### 4.12 `adapters/cli_anything/runner.py` — CLI Runner

```python
import json
import logging
import subprocess
import time
from typing import Any, Optional
from ...capabilities.schemas import CapabilityResult, ErrorType

logger = logging.getLogger(__name__)


class CLIRunner:
    """
    Ejecuta comandos CLI-Anything como procesos externos.
    Maneja JSON parsing, timeout y clasificación de errores.
    """

    def __init__(self, default_timeout: int = 30):
        self._default_timeout = default_timeout

    def run(
        self,
        command: list[str],
        args: dict[str, Any] = None,
        use_json: bool = True,
        timeout: Optional[int] = None,
        cwd: Optional[str] = None,
    ) -> CapabilityResult:
        """
        Ejecuta un comando CLI-Anything.
        
        1. Construye comando: command + args + (--json si use_json)
        2. subprocess.run con capture_output
        3. Intenta parsear stdout como JSON
        4. Clasifica errores
        """
        timeout = timeout or self._default_timeout
        full_command = list(command)

        # Agregar argumentos
        if args:
            for key, value in args.items():
                if isinstance(value, bool):
                    if value:
                        full_command.append(f"--{key}")
                elif value is not None:
                    full_command.append(f"--{key}")
                    full_command.append(str(value))

        # Agregar --json
        if use_json:
            full_command.append("--json")

        start_time = time.monotonic()

        try:
            result = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
            )
            duration_ms = (time.monotonic() - start_time) * 1000

            # Intentar parsear JSON
            parsed_output = None
            if result.stdout.strip():
                try:
                    parsed_output = json.loads(result.stdout)
                except json.JSONDecodeError:
                    logger.debug("Output no es JSON válido, usando raw stdout")

            # Clasificar error
            error_type = None
            error_message = None
            if result.returncode != 0:
                error_type = self._classify_error(result.stderr, result.returncode)
                error_message = (
                    result.stderr.strip()
                    or f"Exit code: {result.returncode}"
                )

            return CapabilityResult(
                capability_id="cli-anything",
                success=(result.returncode == 0),
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                parsed_output=parsed_output,
                error_type=error_type,
                error_message=error_message,
                duration_ms=duration_ms,
                metadata={
                    "command": full_command,
                    "json_used": use_json,
                },
            )

        except subprocess.TimeoutExpired:
            duration_ms = (time.monotonic() - start_time) * 1000
            return CapabilityResult(
                capability_id="cli-anything",
                success=False,
                exit_code=-1,
                stdout="",
                stderr=f"Timeout después de {timeout}s",
                parsed_output=None,
                error_type=ErrorType.TIMEOUT,
                error_message=f"Timeout después de {timeout}s",
                duration_ms=duration_ms,
                metadata={"command": full_command},
            )
        except FileNotFoundError:
            duration_ms = (time.monotonic() - start_time) * 1000
            return CapabilityResult(
                capability_id="cli-anything",
                success=False,
                exit_code=-1,
                stdout="",
                stderr=f"Comando no encontrado: {full_command[0]}",
                parsed_output=None,
                error_type=ErrorType.NOT_FOUND,
                error_message=f"Comando no encontrado: {full_command[0]}",
                duration_ms=duration_ms,
                metadata={"command": full_command},
            )
        except PermissionError:
            duration_ms = (time.monotonic() - start_time) * 1000
            return CapabilityResult(
                capability_id="cli-anything",
                success=False,
                exit_code=-1,
                stdout="",
                stderr="Permiso denegado",
                parsed_output=None,
                error_type=ErrorType.PERMISSION_ERROR,
                error_message="Permiso denegado para ejecutar",
                duration_ms=duration_ms,
                metadata={"command": full_command},
            )
        except Exception as e:
            duration_ms = (time.monotonic() - start_time) * 1000
            return CapabilityResult(
                capability_id="cli-anything",
                success=False,
                exit_code=-1,
                stdout="",
                stderr=str(e),
                parsed_output=None,
                error_type=ErrorType.EXECUTION_ERROR,
                error_message=str(e),
                duration_ms=duration_ms,
                metadata={
                    "command": full_command,
                    "exception": type(e).__name__,
                },
            )

    @staticmethod
    def _classify_error(stderr: str, exit_code: int) -> ErrorType:
        """Clasifica el tipo de error."""
        stderr_lower = stderr.lower()
        if "not found" in stderr_lower or "no such command" in stderr_lower:
            return ErrorType.NOT_FOUND
        if "permission denied" in stderr_lower:
            return ErrorType.PERMISSION_ERROR
        if exit_code == 126:
            return ErrorType.PERMISSION_ERROR
        if exit_code == 127:
            return ErrorType.NOT_FOUND
        if "timeout" in stderr_lower:
            return ErrorType.TIMEOUT
        return ErrorType.EXECUTION_ERROR
```

### 4.13 `adapters/cli_anything/__init__.py` — CLIAnythingAdapter

```python
import logging
from typing import List
from .. import BaseAdapter
from ...capabilities.schemas import CapabilitySchema
from .detector import CLIAnythingDetector
from .parser import SKILLParser
from .runner import CLIRunner

logger = logging.getLogger(__name__)


class CLIAnythingAdapter(BaseAdapter):
    """
    Adapter para descubrir y ejecutar capabilities de CLI-Anything.
    Orquesta detector, parser y runner.
    
    KSPR I nunca importa módulos de CLI-Anything directamente.
    Toda interacción es vía:
    - shutil.which (detección de ejecutables)
    - Lectura de archivos JSON (registry, installed)
    - Parsing de SKILL.md (YAML + markdown)
    - subprocess.run (ejecución de comandos)
    """

    def __init__(self):
        self._detector = CLIAnythingDetector()
        self._parser = SKILLParser()
        self._runner = CLIRunner()

    @property
    def source_type(self) -> str:
        return "cli-anything"

    def is_available(self) -> bool:
        """Verifica si al menos un harness CLI-Anything está instalado."""
        harnesses = self._detector.detect_installed()
        return len(harnesses) > 0

    def discover(self) -> List[CapabilitySchema]:
        """
        Descubre todas las capabilities de CLI-Anything instaladas.
        
        Flujo:
        1. Detector busca harnesses (PATH, hub json, pip)
        2. Para cada harness, busca su registry.json
        3. Para cada skill en el registry, busca su SKILL.md
        4. Parser extrae CapabilitySchema de cada SKILL.md
        5. Retorna lista unificada
        """
        capabilities = []
        harnesses = self._detector.detect_installed()

        for harness in harnesses:
            try:
                caps = self._discover_from_harness(harness)
                capabilities.extend(caps)
            except Exception as e:
                logger.error(
                    f"Error descubriendo desde harness {harness['name']}: {e}"
                )

        logger.info(
            f"CLI-Anything: {len(capabilities)} capabilities descubiertas "
            f"desde {len(harnesses)} harnesses"
        )
        return capabilities

    def _discover_from_harness(self, harness: dict) -> List[CapabilitySchema]:
        """Descubre capabilities de un harness específico."""
        capabilities = []
        name = harness["name"]

        # Intentar encontrar registry.json
        registry_path = self._detector.get_registry_path(name)
        if registry_path:
            caps = self._discover_from_registry(registry_path, harness)
            capabilities.extend(caps)
        else:
            # Sin registry, intentar discover vía --help
            caps = self._discover_from_help(harness)
            capabilities.extend(caps)

        return capabilities

    def _discover_from_registry(
        self, registry_path, harness: dict
    ) -> List[CapabilitySchema]:
        """Descubre capabilities desde un registry.json."""
        import json
        capabilities = []

        try:
            with open(registry_path, "r", encoding="utf-8") as f:
                registry_data = json.load(f)

            for skill_id, skill_info in registry_data.get("skills", {}).items():
                skill_path = skill_info.get("skill_path")
                if skill_path:
                    cap = self._parser.parse_skill_md(skill_path)
                    if cap:
                        # Enriquecer con info del harness
                        cap.source = name = harness["name"]
                        cap.metadata["harness_name"] = name
                        cap.metadata["harness_version"] = harness.get("version")
                        capabilities.append(cap)

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Error leyendo registry {registry_path}: {e}")

        return capabilities

    def _discover_from_help(self, harness: dict) -> List[CapabilitySchema]:
        """Descubre capabilities ejecutando --help."""
        from ...capabilities.loader import CapabilityLoader

        command = harness.get("command", [harness["name"]])
        help_info = CapabilityLoader.load_cli_help(command)

        if "error" in help_info:
            return []

        # Crear capability básica desde --help
        cap = CapabilitySchema(
            id=f"cli-any:{harness['name']}",
            name=harness["name"],
            description=help_info.get("description", "CLI-Anything harness"),
            source=harness["name"],
            source_type=CapabilitySchema.source_type.fget(None),  # CLI_ANYTHING
            category="utility",
            command=command,
            arguments={},
            returns_json=False,
            requires=[],
            skill_path=None,
            skill_content=None,
            installed=True,
            version=harness.get("version", "0.0.0"),
            metadata={"from_help": True},
        )
        cap = CapabilityLoader.enrich_capability(cap, help_info)
        return [cap]

    # ── Execution ────────────────────────────────────────────────────

    def run(
        self,
        command: list[str],
        args: dict = None,
        use_json: bool = True,
        timeout: int = 30,
    ):
        """Proxy al CLIRunner para ejecutar comandos."""
        return self._runner.run(command, args, use_json, timeout)
```

### 4.14 `capabilities/__init__.py` — CapabilityManager

```python
import logging
from typing import Optional
from .schemas import CapabilitySchema, CapabilityResult, SourceType
from .registry import CapabilityRegistry
from .discovery import CapabilityDiscovery
from .loader import CapabilityLoader
from .executor import CapabilityExecutor
from .validator import CapabilityValidator
from .permissions import CapabilityPermissions, PermissionLevel

logger = logging.getLogger(__name__)


class CapabilityManager:
    """
    Orquestador central de la Capability Layer.
    Coordina registry, discovery, loader, executor, validator y permissions.
    
    Inicializado una vez al inicio del shell, usado por:
    - Comando /capabilities
    - Tool calling loop (para generar schemas para el LLM)
    - Sistema de permisos
    """

    def __init__(self):
        self.registry = CapabilityRegistry()
        self.discovery = CapabilityDiscovery(self.registry)
        self.loader = CapabilityLoader()
        self.executor = CapabilityExecutor()
        self.validator = CapabilityValidator()
        self.permissions = CapabilityPermissions()
        self._initialized = False

    def initialize(self) -> None:
        """
        Inicialización al startup del shell.
        1. Registrar adapters disponibles
        2. Ejecutar discovery inicial
        3. Cargar permisos existentes
        """
        if self._initialized:
            return

        # Registrar adapter CLI-Anything si está disponible
        try:
            from ..adapters.cli_anything import CLIAnythingAdapter
            adapter = CLIAnythingAdapter()
            if adapter.is_available():
                self.discovery.register_adapter(adapter)
                logger.info("CLI-Anything adapter registrado")
        except Exception as e:
            logger.debug(f"CLI-Anything no disponible: {e}")

        # Discovery inicial
        self.discovery.discover_all()

        self._initialized = True
        caps = self.registry.list_installed()
        logger.info(f"CapabilityManager inicializado: {len(caps)} capabilities")

    # ── Public API ───────────────────────────────────────────────────

    def list_capabilities(self) -> list[CapabilitySchema]:
        """Lista todas las capabilities disponibles."""
        return self.registry.list_installed()

    def search(self, query: str) -> list[CapabilitySchema]:
        """Busca capabilities por nombre o descripción."""
        return self.registry.search(query)

    def get(self, cap_id: str) -> Optional[CapabilitySchema]:
        """Obtiene una capability por ID."""
        return self.registry.get(cap_id)

    def execute(
        self,
        cap_id: str,
        args: dict = None,
        prefer_json: bool = True,
        timeout: int = 30,
    ) -> CapabilityResult:
        """
        Ejecuta una capability con permisos y validación.
        
        1. Verificar que la capability existe
        2. Verificar permisos
        3. Ejecutar
        4. Validar resultado
        5. Retornar resultado
        """
        cap = self.registry.get(cap_id)
        if not cap:
            return CapabilityResult(
                capability_id=cap_id,
                success=False,
                exit_code=-1,
                stdout="",
                stderr=f"Capability no encontrada: {cap_id}",
                parsed_output=None,
                error_type=None,
                error_message=f"Capability no encontrada: {cap_id}",
                duration_ms=0,
                metadata={},
            )

        # Verificar permisos
        if not self.permissions.check(cap, PermissionLevel.EXECUTE):
            granted = self.permissions.prompt_user(cap, PermissionLevel.EXECUTE)
            if not granted:
                return CapabilityResult(
                    capability_id=cap_id,
                    success=False,
                    exit_code=-1,
                    stdout="",
                    stderr="Permiso denegado por el usuario",
                    parsed_output=None,
                    error_type=None,
                    error_message="Permiso denegado por el usuario",
                    duration_ms=0,
                    metadata={},
                )

        # Ejecutar
        result = self.executor.execute(
            cap, args or {}, prefer_json, timeout
        )

        # Validar
        validation = self.validator.validate_result(
            result,
            expect_json=cap.returns_json,
        )
        if validation.warnings:
            for warning in validation.warnings:
                logger.warning(f"Validación: {warning}")

        return result

    def get_schemas_for_llm(self) -> list[dict]:
        """
        Genera lista de schemas JSON para enviar al LLM.
        Usado por el tool calling loop para que el LLM conozca
        las capabilities disponibles.
        """
        schemas = []
        for cap in self.registry.list_installed():
            schema = {
                "type": "function",
                "function": {
                    "name": f"capability_{cap.id.replace(':', '_')}",
                    "description": cap.description,
                    "parameters": {
                        "type": "object",
                        "properties": cap.arguments,
                        "required": [
                            k for k, v in cap.arguments.items()
                            if v.get("required", False)
                        ],
                    },
                },
            }
            schemas.append(schema)
        return schemas

    def refresh(self) -> list[CapabilitySchema]:
        """Refresca todas las capabilities desde las fuentes."""
        return self.discovery.refresh()

    def get_permissions_summary(self) -> dict:
        """Retorna resumen de permisos para todas las capabilities."""
        summary = {}
        for cap in self.registry.list_installed():
            level = self.permissions.get_level(cap.id)
            summary[cap.id] = {
                "name": cap.name,
                "level": level,
                "level_name": PermissionLevel.LEVEL_NAMES.get(level, "unknown"),
            }
        return summary
```

### 4.15 Integración con CLI

#### Comando `/capabilities`

```python
# En el shell CLI (comandos.py o equivalente)

def cmd_capabilities(args: str, manager: CapabilityManager):
    """
    /capabilities [subcomando] [args]
    
    Subcomandos:
    - /capabilities          → Lista todas las capabilities
    - /capabilities search <q> → Busca por nombre/descripción
    - /capabilities info <id>  → Info detallada
    - /capabilities skill <id> → Muestra SKILL.md
    - /capabilities run <id> [args] → Ejecuta una capability
    - /capabilities refresh    → Refresca catálogo
    - /capabilities install <name> → Instala vía CLI-Hub
    """
    parts = args.strip().split(maxsplit=2)
    
    if not parts:
        # Listar todas
        caps = manager.list_capabilities()
        for cap in caps:
            perm = manager.permissions.get_level(cap.id)
            perm_name = PermissionLevel.LEVEL_NAMES.get(perm, "?")
            print(f"  {cap.id:<30} {cap.name:<20} [{perm_name}] {cap.description[:50]}")
        return

    subcommand = parts[0]
    
    if subcommand == "search" and len(parts) > 1:
        results = manager.search(parts[1])
        for cap in results:
            print(f"  {cap.id}: {cap.description}")
            
    elif subcommand == "info" and len(parts) > 1:
        cap = manager.get(parts[1])
        if cap:
            print(f"ID:          {cap.id}")
            print(f"Name:        {cap.name}")
            print(f"Description: {cap.description}")
            print(f"Source:      {cap.source} ({cap.source_type.value})")
            print(f"Category:    {cap.category}")
            print(f"Version:     {cap.version}")
            print(f"Installed:   {cap.installed}")
            print(f"JSON:        {cap.returns_json}")
            print(f"Commands:    {list(cap.arguments.keys())}")
        else:
            print(f"Capability no encontrada: {parts[1]}")
            
    elif subcommand == "run" and len(parts) > 1:
        cap_id = parts[1]
        # Parsear args del tercer elemento
        run_args = {}
        if len(parts) > 2:
            # Simple parsing: key=value
            for arg in parts[2].split():
                if "=" in arg:
                    k, v = arg.split("=", 1)
                    run_args[k] = v
        
        result = manager.execute(cap_id, run_args)
        if result.success:
            print(result.display_output)
        else:
            print(f"❌ Error: {result.error_message}")
            
    elif subcommand == "refresh":
        caps = manager.refresh()
        print(f"Refrescadas {len(caps)} capabilities")
        
    else:
        print("Uso: /capabilities [list|search|info|run|refresh|install]")
```

#### Extensión del Tool Calling Loop

```python
# En el orquestador principal (tool_calling_loop o equivalente)

def build_tools_for_llm(mcp_tools, plugin_tools, capability_schemas):
    """
    Combina herramientas MCP, plugins y capabilities
    en una lista unificada para el LLM.
    """
    tools = []
    
    # MCP tools (formato existente)
    for tool in mcp_tools:
        tools.append({
            "type": "function",
            "function": {
                "name": f"mcp_{tool.name}",
                "description": tool.description,
                "parameters": tool.parameters,
            }
        })
    
    # Plugin tools (formato existente)
    for plugin in plugin_tools:
        tools.append({
            "type": "function",
            "function": {
                "name": f"plugin_{plugin.name}",
                "description": plugin.description,
                "parameters": plugin.parameters,
            }
        })
    
    # Capability schemas (nuevo)
    for cap_schema in capability_schemas:
        tools.append(cap_schema)
    
    return tools

# En la inicialización del shell:
capability_manager = CapabilityManager()
capability_manager.initialize()
# ...
# En el loop:
cap_schemas = capability_manager.get_schemas_for_llm()
all_tools = build_tools_for_llm(mcp_tools, plugin_tools, cap_schemas)
```

---

## 5. Tarea 2: Comando /prompts

### 5.1 Almacenamiento

Ubicación: `~/.kspr/prompts.json`

```json
{
  "version": "1.0.0",
  "prompts": {
    "code-reviewer": {
      "name": "code-reviewer",
      "description": "Revisor de código estricto enfocado en seguridad",
      "content": "Eres un revisor de código senior especializado en seguridad...",
      "created_at": "2025-01-15T10:30:00Z",
      "updated_at": "2025-01-15T10:30:00Z",
      "tags": ["security", "review"]
    },
    "doc-writer": {
      "name": "doc-writer",
      "description": "Escritor de documentación técnica",
      "content": "Eres un escritor de documentación técnica experto...",
      "created_at": "2025-01-15T11:00:00Z",
      "updated_at": "2025-01-15T11:00:00Z",
      "tags": ["documentation"]
    }
  }
}
```

### 5.2 Funciones de Persistencia

```python
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional


PROMPTS_PATH = Path.home() / ".kspr" / "prompts.json"


def load_prompts() -> dict:
    """Carga prompts desde disco."""
    if not PROMPTS_PATH.exists():
        return {"version": "1.0.0", "prompts": {}}
    try:
        with open(PROMPTS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, KeyError):
        return {"version": "1.0.0", "prompts": {}}


def save_prompts(data: dict) -> None:
    """Persiste prompts a disco."""
    PROMPTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PROMPTS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def add_prompt(name: str, content: str, description: str = "", tags: list[str] = None) -> dict:
    """Agrega un nuevo prompt personalizado."""
    data = load_prompts()
    now = datetime.now(timezone.utc).isoformat()
    data["prompts"][name] = {
        "name": name,
        "description": description,
        "content": content,
        "created_at": now,
        "updated_at": now,
        "tags": tags or [],
    }
    save_prompts(data)
    return data["prompts"][name]


def remove_prompt(name: str) -> bool:
    """Elimina un prompt. Retorna True si existía."""
    data = load_prompts()
    if name in data["prompts"]:
        del data["prompts"][name]
        save_prompts(data)
        return True
    return False


def get_prompt(name: str) -> Optional[dict]:
    """Obtiene un prompt por nombre."""
    data = load_prompts()
    return data["prompts"].get(name)


def list_prompts() -> list[dict]:
    """Lista todos los prompts."""
    data = load_prompts()
    return list(data["prompts"].values())
```

### 5.3 Comandos

```python
def cmd_prompts(args: str):
    """
    /prompts [subcomando] [args]
    
    Subcomandos:
    - /prompts              → Lista todos los prompts
    - /prompts add <name>   → Agrega prompt (modo interactivo)
    - /prompts select       → Lista y permite seleccionar uno
    - /prompts select <name> → Selecciona directamente
    - /prompts remove <name> → Elimina un prompt
    - /prompts info <name>  → Muestra info detallada
    """
    parts = args.strip().split(maxsplit=2)
    
    if not parts:
        # Listar prompts
        prompts = list_prompts()
        if not prompts:
            print("No hay prompts personalizados. Usa /prompts add <name> para crear uno.")
            return
        print("Prompts disponibles:")
        for p in prompts:
            tags = ", ".join(p.get("tags", []))
            print(f"  {p['name']:<20} {p.get('description', '')[:40]} [{tags}]")
        return
    
    subcommand = parts[0]
    
    if subcommand == "add" and len(parts) > 1:
        name = parts[1]
        # Verificar que no exista
        if get_prompt(name):
            print(f"El prompt '{name}' ya existe. Usa otro nombre.")
            return
        
        # Modo interactivo
        print(f"Creando prompt '{name}'. Escribe el contenido (línea vacía para terminar):")
        lines = []
        while True:
            line = input("> ")
            if line == "":
                break
            lines.append(line)
        
        content = "\n".join(lines)
        if not content.strip():
            print("Prompt vacío. Cancelado.")
            return
        
        description = input("Descripción (opcional): ").strip()
        tags_str = input("Tags separados por coma (opcional): ").strip()
        tags = [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else []
        
        add_prompt(name, content, description, tags)
        print(f"✅ Prompt '{name}' creado.")
    
    elif subcommand == "select":
        if len(parts) > 1:
            # Selección directa
            name = parts[1]
            prompt = get_prompt(name)
            if prompt:
                print(f"Prompt '{name}' seleccionado.")
                print("Contenido:")
                print(prompt["content"])
                return ("PROMPT_INJECT", prompt["content"])
            else:
                print(f"Prompt '{name}' no encontrado.")
                return
        else:
            # Selección interactiva
            prompts = list_prompts()
            if not prompts:
                print("No hay prompts para seleccionar.")
                return
            print("Selecciona un prompt:")
            for i, p in enumerate(prompts, 1):
                print(f"  {i}. {p['name']}")
            try:
                choice = int(input("Número: ")) - 1
                if 0 <= choice < len(prompts):
                    selected = prompts[choice]
                    print(f"Prompt '{selected['name']}' seleccionado.")
                    return ("PROMPT_INJECT", selected["content"])
            except (ValueError, IndexError):
                print("Selección inválida.")
                return
    
    elif subcommand == "remove" and len(parts) > 1:
        name = parts[1]
        if remove_prompt(name):
            print(f"✅ Prompt '{name}' eliminado.")
        else:
            print(f"Prompt '{name}' no encontrado.")
    
    elif subcommand == "info" and len(parts) > 1:
        name = parts[1]
        prompt = get_prompt(name)
        if prompt:
            print(f"Name:        {prompt['name']}")
            print(f"Description: {prompt.get('description', 'N/A')}")
            print(f"Created:     {prompt.get('created_at', 'N/A')}")
            print(f"Updated:     {prompt.get('updated_at', 'N/A')}")
            print(f"Tags:        {', '.join(prompt.get('tags', []))}")
            print(f"Content:     {prompt['content'][:100]}...")
        else:
            print(f"Prompt '{name}' no encontrado.")
    
    else:
        print("Uso: /prompts [list|add|select|remove|info]")
```

### 5.4 Inyección de System Prompt

Cuando el usuario selecciona un prompt con `/prompts select <name>`, el comando retorna una tupla especial:

```python
# En el shell CLI:
result = cmd_prompts("select code-reviewer")
if isinstance(result, tuple) and result[0] == "PROMPT_INJECT":
    # Inyectar contenido como System Prompt adicional
    system_prompt_injection = result[1]
    # Se agrega al System Prompt del LLM en la siguiente llamada
```

### 5.5 Actualización de /help

```markdown
## Comandos Disponibles

/comandos existentes...

### Prompts Personalizados
  /prompts                  Lista todos los prompts guardados
  /prompts add <name>       Crea un nuevo prompt (modo interactivo)
  /prompts select           Lista y permite seleccionar un prompt
  /prompts select <name>    Selecciona un prompt por nombre
  /prompts remove <name>    Elimina un prompt guardado
  /prompts info <name>      Muestra info detallada de un prompt
```

---

## 6. Tarea 3: gsap-skills

### 6.1 Estructura de Directorios

```
skills/gsap-skills/
├── manifest.json
├── cli-anything-default/
│   └── SKILL.md
├── code-analysis/
│   └── SKILL.md
└── security-audit/
    └── SKILL.md
```

### 6.2 manifest.json

```json
{
  "version": "1.0.0",
  "name": "gsap-skills",
    "description": "Skills base para KSPR AI CLI TOOL",
  "skills": {
    "cli-anything-default": {
      "name": "cli-anything-default",
      "description": "Herramientas base de CLI-Anything para KSPR",
      "version": "0.1.0",
      "skill_path": "cli-anything-default/SKILL.md",
      "enabled": true
    },
    "code-analysis": {
      "name": "code-analysis",
      "description": "Análisis de calidad de código",
      "version": "0.1.0",
      "skill_path": "code-analysis/SKILL.md",
      "enabled": true
    },
    "security-audit": {
      "name": "security-audit",
      "description": "Auditoría de seguridad de código",
      "version": "0.1.0",
      "skill_path": "security-audit/SKILL.md",
      "enabled": true
    }
  }
}
```

### 6.3 cli-anything-default/SKILL.md (El más importante)

Este skill enseña a KSPR I cómo usar la Capability Layer:

```markdown
---
name: cli-anything-default
description: Guía completa para usar la Capability Layer de KSPR AI CLI TOOL
category: core
version: 0.1.0
---

# Capability Layer — Guía para KSPR I

Eres KSPR I. Tienes acceso a una Capability Layer que te permite descubrir
y ejecutar herramientas externas instaladas en el sistema.

## Cómo Funciona

La Capability Layer descubre herramientas (CLIs) instaladas en tu sistema
y las presenta como capabilities que puedes ejecutar.

### Flujo de Uso

1. **Descubre** capabilities disponibles con `/capabilities`
2. **Revisa** info con `/capabilities info <id>`
3. **Ejecuta** con `/capabilities run <id> --key=value`

## Comandos Disponibles

| Comando | Descripción | Ejemplo |
|---------|-------------|---------|
| `/capabilities` | Lista todas las capabilities | `/capabilities` |
| `/capabilities search <query>` | Busca por nombre/descripción | `/capabilities search analysis` |
| `/capabilities info <id>` | Info detallada de una capability | `/capabilities info cli-any:code-analysis` |
| `/capabilities run <id> [args]` | Ejecuta una capability | `/capabilities run cli-any:code-analysis --file=src/main.py` |
| `/capabilities skill <id>` | Muestra el SKILL.md de una capability | `/capabilities skill cli-any:code-analysis` |
| `/capabilities refresh` | Refresca el catálogo | `/capabilities refresh` |

## Formato de Argumentos

Los argumentos se pasan como `--key=value` después del ID de la capability:

```
/capabilities run cli-any:analyze --file=src/main.py --format=json
```

Los booleanos se pasan sin valor:
```
/capabilities run cli-any:lint --verbose
```

## Manejo de Errores

Si una capability falla, revisa:
1. El código de salida (exit code)
2. El mensaje de error en stderr
3. Usa `/capabilities info <id>` para verificar que la capability está instalada

## Permisos

Cada capability tiene un nivel de permiso:
- **read**: Solo lectura de info
- **execute**: Ejecución básica (requiere confirmación)
- **write**: Escritura en filesystem
- **admin**: Operaciones administrativas
```

### 6.4 code-analysis/SKILL.md

```markdown
---
name: code-analysis
description: Herramientas de análisis de calidad de código
category: analysis
version: 0.1.0
---

# Code Analysis Skills

Herramientas para analizar calidad, complejidad y estilo de código.

## Comandos

| Comando | Descripción | Ejemplo |
|---------|-------------|---------|
| `analyze <file>` | Analiza un archivo en busca de code smells | `analyze src/main.py` |
| `lint <dir>` | Ejecuta linter en un directorio | `lint src/` |
| `complexity <file>` | Calcula métricas de complejidad | `complexity src/utils.py` |
| `duplicates <dir>` | Detecta código duplicado | `duplicates src/` |
| `report` | Genera reporte completo de calidad | `report --format=json` |

## Métricas

- **Cyclomatic Complexity**: Complejidad ciclómica por función
- **Lines of Code**: Líneas de código efectivas
- **Duplication %**: Porcentaje de código duplicado
- **Maintainability Index**: Índice de mantenibilidad
```

### 6.5 security-audit/SKILL.md

```markdown
---
name: security-audit
description: Auditoría de seguridad de código fuente
category: security
version: 0.1.0
---

# Security Audit Skills

Herramientas para detectar vulnerabilidades y problemas de seguridad.

## Comandos

| Comando | Descripción | Ejemplo |
|---------|-------------|---------|
| `audit <dir>` | Auditoría completa de seguridad | `audit src/` |
| `scan <file>` | Escaneo rápido de vulnerabilidades | `scan src/auth.py` |
| `secrets <dir>` | Busca secretos hardcodeados | `secrets src/` |
| `deps` | Analiza dependencias vulnerables | `deps` |
| `report` | Genera reporte de seguridad | `report --format=json` |

## Categorías de Vulnerabilidades

- **Injection**: SQL, XSS, Command injection
- **Authentication**: Problemas de autenticación
- **Authorization**: Bypass de permisos
- **Secrets**: Claves, tokens, passwords hardcodeados
- **Dependencies**: Dependencias con CVEs conocidos
```

### 6.6 SkillsManager: `backend/kspr_engine/skills.py`

```python
import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

SKILLS_DIR = Path(__file__).parent.parent.parent / "skills" / "gsap-skills"


class SkillBundle:
    """
    Representa un bundle de skill cargado desde disco.
    Contiene el SKILL.md parseado y metadata del manifest.
    """

    def __init__(
        self,
        name: str,
        description: str,
        version: str,
        skill_path: str,
        skill_content: str,
        enabled: bool = True,
        metadata: dict = None,
    ):
        self.name = name
        self.description = description
        self.version = version
        self.skill_path = skill_path
        self.skill_content = skill_content
        self.enabled = enabled
        self.metadata = metadata or {}

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "skill_path": self.skill_path,
            "skill_content": self.skill_content,
            "enabled": self.enabled,
            "metadata": self.metadata,
        }


class SkillsManager:
    """
    Gestiona la carga y contexto de skills para KSPR I.
    
    Carga bundles desde skills/gsap-skills/ y genera
    contexto para inyectar al LLM en cada llamada.
    """

    def __init__(self, skills_dir: str = None):
        self._skills_dir = Path(skills_dir) if skills_dir else SKILLS_DIR
        self._bundles: dict[str, SkillBundle] = {}
        self._load_default_bundles()

    def _load_default_bundles(self) -> None:
        """Carga todos los bundles habilitados desde el directorio de skills."""
        manifest_path = self._skills_dir / "manifest.json"
        if not manifest_path.exists():
            logger.warning(f"Manifest no encontrado: {manifest_path}")
            return

        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Error leyendo manifest: {e}")
            return

        for skill_id, skill_info in manifest.get("skills", {}).items():
            if not skill_info.get("enabled", True):
                continue

            skill_path = self._skills_dir / skill_info["skill_path"]
            if not skill_path.exists():
                logger.warning(f"SKILL.md no encontrado: {skill_path}")
                continue

            try:
                content = skill_path.read_text(encoding="utf-8")
                bundle = SkillBundle(
                    name=skill_info["name"],
                    description=skill_info["description"],
                    version=skill_info.get("version", "0.0.1"),
                    skill_path=str(skill_path),
                    skill_content=content,
                    enabled=True,
                    metadata=skill_info.get("metadata", {}),
                )
                self._bundles[skill_id] = bundle
                logger.info(f"Skill bundle cargado: {skill_id}")
            except Exception as e:
                logger.error(f"Error cargando skill {skill_id}: {e}")

        logger.info(
            f"SkillsManager: {len(self._bundles)} bundles cargados"
        )

    def list_bundles(self) -> list[SkillBundle]:
        """Retorna todos los bundles cargados."""
        return list(self._bundles.values())

    def get_bundle(self, name: str) -> Optional[SkillBundle]:
        """Obtiene un bundle por nombre."""
        return self._bundles.get(name)

    def get_skill_context(self) -> str:
        """
        Genera contexto concatenado de todos los skills habilitados.
        Este contexto se inyecta al System Prompt del LLM.
        """
        contexts = []
        for bundle in self._bundles.values():
            if bundle.enabled:
                contexts.append(
                    f"=== Skill: {bundle.name} ===\n"
                    f"{bundle.skill_content}\n"
                    f"=== Fin Skill: {bundle.name} ===\n"
                )
        return "\n".join(contexts)

    def enable(self, name: str) -> bool:
        """Habilita un skill bundle."""
        if name in self._bundles:
            self._bundles[name].enabled = True
            return True
        return False

    def disable(self, name: str) -> bool:
        """Deshabilita un skill bundle."""
        if name in self._bundles:
            self._bundles[name].enabled = False
            return True
        return False

    def reload(self) -> None:
        """Recarga todos los bundles desde disco."""
        self._bundles.clear()
        self._load_default_bundles()
```

### 6.7 Comando `/skills`

```python
def cmd_skills(args: str, skills_manager: SkillsManager):
    """
    /skills [subcomando] [args]
    
    Subcomandos:
    - /skills             → Lista todos los skills
    - /skills load <name> → Carga/recarga un skill
    - /skills info <name> → Info detallada
    - /skills context     → Muestra contexto inyectado al LLM
    """
    parts = args.strip().split()
    
    if not parts:
        # Listar todos
        bundles = skills_manager.list_bundles()
        if not bundles:
            print("No hay skills cargados.")
            return
        print("Skills disponibles:")
        for b in bundles:
            status = "✅" if b.enabled else "❌"
            print(f"  {status} {b.name:<25} v{b.version}  {b.description[:40]}")
        return
    
    subcommand = parts[0]
    
    if subcommand == "info" and len(parts) > 1:
        bundle = skills_manager.get_bundle(parts[1])
        if bundle:
            print(f"Name:        {bundle.name}")
            print(f"Description: {bundle.description}")
            print(f"Version:     {bundle.version}")
            print(f"Path:        {bundle.skill_path}")
            print(f"Enabled:     {bundle.enabled}")
            print(f"\nContenido:")
            print(bundle.skill_content)
        else:
            print(f"Skill '{parts[1]}' no encontrado.")
    
    elif subcommand == "context":
        context = skills_manager.get_skill_context()
        if context:
            print("Contexto inyectado al LLM:")
            print(context)
        else:
            print("No hay contexto de skills.")
    
    elif subcommand == "load" and len(parts) > 1:
        # Reload el bundle específico
        skills_manager.reload()
        bundle = skills_manager.get_bundle(parts[1])
        if bundle:
            print(f"✅ Skill '{parts[1]}' recargado.")
        else:
            print(f"Skill '{parts[1]}' no encontrado.")
    
    else:
        print("Uso: /skills [list|load|info|context]")
```

### 6.8 Inyección de Contexto al LLM

```python
# En la inicialización del shell:
skills_manager = SkillsManager()
skill_context = skills_manager.get_skill_context()

# En cada llamada al LLM, se inyecta al System Prompt:
system_prompt = f"""
{base_system_prompt}

## Skills Disponibles

{skill_context}
"""
```

### 6.9 Actualización de /help

```markdown
## Comandos Disponibles

/comandos existentes...

### Skills
  /skills                   Lista todos los skills cargados
  /skills load <name>       Recarga un skill específico
  /skills info <name>       Info detallada de un skill
  /skills context           Muestra el contexto inyectado al LLM
```

---

## 7. Estructura de Archivos Final

### 7.1 Archivos Nuevos

| Ruta | Descripción |
|------|-------------|
| `backend/kspr_engine/capabilities/__init__.py` | CapabilityManager (orquestador) |
| `backend/kspr_engine/capabilities/schemas.py` | CapabilitySchema, CapabilityResult, CapabilityValidation |
| `backend/kspr_engine/capabilities/registry.py` | CapabilityRegistry (persistencia) |
| `backend/kspr_engine/capabilities/discovery.py` | CapabilityDiscovery (motor de discovery) |
| `backend/kspr_engine/capabilities/loader.py` | CapabilityLoader (SKILL.md + CLI help) |
| `backend/kspr_engine/capabilities/executor.py` | CapabilityExecutor (subprocess) |
| `backend/kspr_engine/capabilities/validator.py` | CapabilityValidator (resultados) |
| `backend/kspr_engine/capabilities/permissions.py` | CapabilityPermissions (niveles) |
| `backend/kspr_engine/adapters/__init__.py` | BaseAdapter ABC |
| `backend/kspr_engine/adapters/cli_anything/__init__.py` | CLIAnythingAdapter |
| `backend/kspr_engine/adapters/cli_anything/detector.py` | CLIAnythingDetector |
| `backend/kspr_engine/adapters/cli_anything/parser.py` | SKILLParser |
| `backend/kspr_engine/adapters/cli_anything/runner.py` | CLIRunner |
| `backend/kspr_engine/skills.py` | SkillsManager, SkillBundle |
| `skills/gsap-skills/manifest.json` | Manifest de skills default |
| `skills/gsap-skills/cli-anything-default/SKILL.md` | Skill: uso de Capability Layer |
| `skills/gsap-skills/code-analysis/SKILL.md` | Skill: análisis de código |
| `skills/gsap-skills/security-audit/SKILL.md` | Skill: auditoría de seguridad |

### 7.2 Archivos Modificados

| Ruta | Cambios |
|------|---------|
| `backend/kspr_engine/shell/commands.py` | Agregar /capabilities, /prompts, /skills |
| `backend/kspr_engine/shell/help.py` | Actualizar /help con nuevos comandos |
| `backend/kspr_engine/tool_calling.py` | Integrar capability schemas en tool loop |
| `backend/kspr_engine/__init__.py` | Exportar CapabilityManager, SkillsManager |
| `backend/main.py` | Inicializar CapabilityManager y SkillsManager al startup |

### 7.3 Archivos de Test

| Ruta | Descripción |
|------|-------------|
| `tests/test_capabilities.py` | Tests de schemas, registry, permissions, executor |
| `tests/test_cli_anything_adapter.py` | Tests de detector, parser, runner, adapter |
| `tests/test_skills.py` | Tests de SkillsManager, SkillBundle, context |
| `tests/test_prompts.py` | Tests de CRUD de prompts, selección, inyección |

---

## 8. Plan de Tests

### 8.1 `tests/test_capabilities.py`

#### Unit Tests (18)

```python
# test_capabilities.py

# ── Schemas ──────────────────────────────────────────────────────────

def test_capability_schema_creation():
    """Crea un CapabilitySchema con todos los campos requeridos."""
    # Verificar que se puede instanciar con campos válidos

def test_capability_schema_to_dict():
    """Serializa un CapabilitySchema a diccionario."""
    # Verificar round-trip to_dict -> from_dict

def test_capability_schema_from_dict():
    """Deserializa un CapabilitySchema desde diccionario."""
    # Verificar que source_type se convierte correctamente a enum

def test_capability_result_creation():
    """Crea un CapabilityResult exitoso."""
    # Verificar campos de éxito

def test_capability_result_error():
    """Crea un CapabilityResult con error."""
    # Verificar error_type, error_message

def test_capability_result_display_output_json():
    """Verifica display_output con parsed_output dict."""
    # Verificar que retorna JSON indentado

def test_capability_result_display_output_stdout():
    """Verifica display_output cuando no hay parsed_output."""
    # Verificar que retorna stdout

def test_capability_validation_valid():
    """Crea CapabilityValidation válida (sin issues)."""
    # Verificar is_valid=True

def test_capability_validation_with_issues():
    """Crea CapabilityValidation con issues."""
    # Verificar is_valid=False

# ── Registry ─────────────────────────────────────────────────────────

def test_registry_register_and_get():
    """Registra y recupera una capability."""
    # Crear registry enmem, register, get, verificar

def test_registry_unregister():
    """Elimina una capability del registry."""
    # Register, unregister, verificar que ya no existe

def test_registry_search():
    """Busca capabilities por query parcial."""
    # Registrar 3, buscar, verificar filtrado

def test_registry_list_by_source():
    """Filtra capabilities por source_type."""
    # Registrar de distintos tipos, filtrar

def test_registry_list_installed():
    """Lista solo capabilities instaladas."""
    # Registrar con installed=True y False

def test_registry_persistence():
    """Verifica persistencia a ~/.kspr/capabilities.json."""
    # Guardar, crear nuevo registry, cargar, verificar

# ── Permissions ──────────────────────────────────────────────────────

def test_permissions_check_default():
    """Verifica permiso por defecto es READ."""
    # Crear permisos, verificar nivel default

def test_permissions_grant_and_check():
    """Otorga permiso y verifica."""
    # Grant EXECUTE, verificar check(True)

def test_permissions_revoke():
    """Revuelve permiso y verifica."""
    # Grant, revoke, verificar nivel vuelve a READ

# ── Validator ────────────────────────────────────────────────────────

def test_validator_validate_result_success():
    """Valida resultado exitoso."""
    # Crear CapabilityResult exitoso, validar, verificar is_valid

def test_validator_validate_result_wrong_exit_code():
    """Valida resultado con exit code inesperado."""
    # Verificar que reporta issue

def test_validator_validate_json_schema():
    """Valida output contra JSON Schema básico."""
    # Verificar required y type checks

# ── Executor ─────────────────────────────────────────────────────────

def test_executor_execute_success():
    """Ejecuta capability con éxito (comando echo)."""
    # Crear cap con command=["echo", "hello"], ejecutar, verificar

def test_executor_execute_not_found():
    """Ejecuta capability con comando inexistente."""
    # Verificar ErrorType.NOT_FOUND

def test_executor_execute_timeout():
    """Ejecuta capability con timeout corto."""
    # Usar "sleep 10" con timeout=1

def test_executor_classify_error():
    """Verifica clasificación de errores."""
    # Test _classify_error con distintos stderr
```

#### Integration Tests (4)

```python
def test_integration_discovery_full():
    """Discovery completo: registrar adapter, discover, verificar registry."""
    # Crear CapabilityManager mock, registrar adapter, discover_all

def test_integration_execute_with_permissions():
    """Ejecución completa con verificación de permisos."""
    # Grant permiso, ejecutar, validar resultado

def test_integration_capability_to_llm_schemas():
    """Generación de schemas para LLM."""
    # Registrar capabilities, get_schemas_for_llm, verificar formato

def test_integration_lifecycle():
    """Ciclo completo: register -> execute -> validate -> cleanup."""
    # Todas las fases en secuencia
```

### 8.2 `tests/test_cli_anything_adapter.py`

#### Unit Tests (10)

```python
# test_cli_anything_adapter.py

def test_detector_detect_from_path():
    """Detector busca ejecutables en PATH."""
    # Mock shutil.which, verificar resultados

def test_detector_detect_from_hub_json():
    """Detector lee ~/.cli-hub/installed.json."""
    # Crear archivo temporal, detect, verificar

def test_detector_get_registry_path():
    """Detector encuentra registry.json."""
    # Crear estructura de archivos temporal

def test_parser_parse_skill_md():
    """Parser extrae frontmatter YAML de SKILL.md."""
    # Crear SKILL.md temporal, parsear, verificar campos

def test_parser_extract_commands():
    """Parser extrae commandos de tablas markdown."""
    # Test _extract_commands_from_tables

def test_parser_parse_from_string():
    """Parser funciona con string directo."""
    # Usar parse_from_string

def test_runner_run_success():
    """Runner ejecuta comando exitoso."""
    # Ejecutar "echo test", verificar resultado

def test_runner_run_not_found():
    """Runner maneja comando inexistente."""
    # Verificar ErrorType.NOT_FOUND

def test_runner_classify_error():
    """Runner clasifica errores correctamente."""
    # Test _classify_error con distintos casos

def test_adapter_is_available():
    """Adapter reporta disponibilidad."""
    # Mock detector, verificar is_available
```

#### Integration Tests (2)

```python
def test_adapter_discover_full():
    """Adapter completo: detect + parse + discover."""
    # Crear harness temporal con SKILL.md, descubrir

def test_adapter_run_command():
    """Adapter ejecuta un comando completo."""
    # Descubrir capability, ejecutar, verificar resultado
```

### 8.3 `tests/test_skills.py`

#### Unit Tests (7)

```python
# test_skills.py

def test_skill_bundle_creation():
    """Crea un SkillBundle con campos válidos."""
    # Verificar instancia

def test_skill_bundle_to_dict():
    """Serializa SkillBundle a diccionario."""
    # Verificar round-trip

def test_skills_manager_load_default():
    """SkillsManager carga bundles desde directorio."""
    # Crear directorio temporal con manifest + SKILL.md

def test_skills_manager_list_bundles():
    """SkillsManager lista todos los bundles."""
    # Verificar que retorna lista

def test_skills_manager_get_bundle():
    """SkillsManager obtiene bundle por nombre."""
    # Verificar get por nombre válido e inválido

def test_skills_manager_enable_disable():
    """SkillsManager habilita/deshabilita bundles."""
    # Toggle enabled, verificar

def test_skills_manager_get_skill_context():
    """SkillsManager genera contexto concatenado."""
    # Verificar que contexto contiene nombres de skills
```

#### Integration Tests (2)

```python
def test_skills_manager_full_load():
    """Carga completa desde directorio real."""
    # Apuntar a skills/gsap-skills/, verificar 3 bundles

def test_skills_context_injection():
    """Contexto se genera correctamente para inyección."""
    # Verificar que get_skill_context() retorna string válido
```

### 8.4 `tests/test_prompts.py`

#### Unit Tests (7)

```python
# test_prompts.py

def test_load_prompts_empty():
    """Carga prompts cuando no existe archivo."""
    # Verificar retorno por defecto

def test_add_prompt():
    """Agrega un prompt y verifica persistencia."""
    # Add, load, verificar exists

def test_remove_prompt():
    """Elimina un prompt existente."""
    # Add, remove, verificar

def test_remove_prompt_not_found():
    """Elimina prompt inexistente retorna False."""
    # Verificar retorno

def test_get_prompt():
    """Obtiene un prompt por nombre."""
    # Add, get, verificar campos

def test_list_prompts():
    """Lista todos los prompts."""
    # Add 2, list, verificar count

def test_save_prompts_persistence():
    """Verifica que save_prompts persiste a disco."""
    # Guardar, cargar en nueva función, verificar
```

#### Integration Test (1)

```python
def test_prompts_lifecycle():
    """Ciclo completo: add -> select -> inject -> remove."""
    # Flujo completo de prompts
```

---

## 9. Orden de Implementación

### Fase 1: Schemas, Registry y Permissions (Días 1-2)

**Objetivo**: Establecer los fundamentos de datos y persistencia.

| Día | Actividad | Archivos |
|-----|-----------|----------|
| 1 | Crear `schemas.py` con CapabilitySchema, CapabilityResult, CapabilityValidation | `capabilities/schemas.py` |
| 1 | Crear `registry.py` con CRUD y persistencia JSON | `capabilities/registry.py` |
| 2 | Crear `permissions.py` con niveles, check, grant, revoke | `capabilities/permissions.py` |
| 2 | Tests unitarios de schemas, registry y permissions | `tests/test_capabilities.py` (parcial) |

**Entregable**: Modelos de datos funcionales con persistencia verificada.

### Fase 2: Loader, Discovery y BaseAdapter (Días 3-4)

**Objetivo**: Infraestructra de descubrimiento y carga.

| Día | Actividad | Archivos |
|-----|-----------|----------|
| 3 | Crear `BaseAdapter` ABC | `adapters/__init__.py` |
| 3 | Crear `loader.py` con load_skill_md y load_cli_help | `capabilities/loader.py` |
| 4 | Crear `discovery.py` con register_adapter, discover_all | `capabilities/discovery.py` |
| 4 | Tests unitarios de loader y discovery | `tests/test_capabilities.py` (completar) |

**Entregable**: Sistema de discovery funcional con adapter mock.

### Fase 3: CLI-Anything Adapter (Días 5-7)

**Objetivo**: Implementar el adapter para CLI-Anything.

| Día | Actividad | Archivos |
|-----|-----------|----------|
| 5 | Crear `detector.py` con 4 estrategias de detección | `adapters/cli_anything/detector.py` |
| 5 | Crear `parser.py` con parse_skill_md | `adapters/cli_anything/parser.py` |
| 6 | Crear `runner.py` con run, JSON parsing, error classification | `adapters/cli_anything/runner.py` |
| 6 | Crear `__init__.py` del adapter (CLIAnythingAdapter) | `adapters/cli_anything/__init__.py` |
| 7 | Tests del adapter completo | `tests/test_cli_anything_adapter.py` |

**Entregable**: Adapter CLI-Anything funcional con detección, parsing y ejecución.

### Fase 4: Executor, Validator y CapabilityManager (Días 8-9)

**Objetivo**: Orquestador completo con ejecución y validación.

| Día | Actividad | Archivos |
|-----|-----------|----------|
| 8 | Crear `executor.py` con execute y execute_raw | `capabilities/executor.py` |
| 8 | Crear `validator.py` con validate_result, validate_json_schema | `capabilities/validator.py` |
| 9 | Crear `CapabilityManager` (orquestador) | `capabilities/__init__.py` |
| 9 | Tests de executor, validator y manager | `tests/test_capabilities.py` (completar) |

**Entregable**: CapabilityManager completo con execute, validate, permissions check.

### Fase 5: Integración CLI (Día 10)

**Objetivo**: Conectar Capability Layer con el shell interactivo.

| Día | Actividad | Archivos |
|-----|-----------|----------|
| 10 | Implementar comando `/capabilities` | `shell/commands.py` |
| 10 | Integrar schemas en tool calling loop | `tool_calling.py` |
| 10 | Inicializar CapabilityManager en shell startup | `main.py` |
| 10 | Actualizar `/help` | `shell/help.py` |

**Entregable**: Comando `/capabilities` funcional en el shell.

### Fase 6: Comando /prompts (Día 11)

**Objetivo**: Sistema de prompts personalizados.

| Día | Actividad | Archivos |
|-----|-----------|----------|
| 11 | Implementar funciones CRUD de prompts | `shell/prompts.py` |
| 11 | Implementar comando `/prompts` con todos los subcomandos | `shell/commands.py` |
| 11 | Implementar inyección de System Prompt | `tool_calling.py` |
| 11 | Tests de prompts | `tests/test_prompts.py` |
| 11 | Actualizar `/help` | `shell/help.py` |

**Entregable**: Comando `/prompts` funcional con selección e inyección.

### Fase 7: gsap-skills + SkillsManager + /skills (Día 12)

**Objetivo**: Sistema de skills bundles y contexto LLM.

| Día | Actividad | Archivos |
|-----|-----------|----------|
| 12 | Crear directorio `skills/gsap-skills/` con manifest.json | `skills/gsap-skills/manifest.json` |
| 12 | Crear SKILL.md para los 3 skills default | `skills/gsap-skills/*/SKILL.md` |
| 12 | Crear `SkillsManager` | `backend/kspr_engine/skills.py` |
| 12 | Implementar comando `/skills` | `shell/commands.py` |
| 12 | Integrar contexto de skills en System Prompt | `tool_calling.py` |
| 12 | Tests de skills | `tests/test_skills.py` |
| 12 | Actualizar `/help` | `shell/help.py` |

**Entregable**: Sistema de skills completo con 3 bundles default.

### Fase 8: Tests, Documentación y Verificación (Días 13-14)

**Objetivo**: Asegurar calidad y completitud.

| Día | Actividad | Archivos |
|-----|-----------|----------|
| 13 | Completar todos los tests unitarios y de integración | `tests/test_*.py` |
| 13 | Ejecutar suite completa, corregir failures | Todos los archivos |
| 14 | Revisión final de arquitectura | Todos los archivos |
| 14 | Documentación de implementación | `docs/IMPLEMENTATION_PLAN.md` |

**Entregable**: Suite de tests completa pasando, documentación finalizada.

---

## 10. Riesgos y Mitigaciones

### 10.1 Seguridad: Ejecución de Subprocess

**Riesgo**: La Capability Layer ejecuta comandos externos vía `subprocess.run`. Un comando malicioso o un path de ejecutable comprometido podría ejecutar código arbitrario.

**Mitigaciones**:
- **Permisos obligatorios**: Toda ejecución requiere nivel `EXECUTE` mínimo, con prompt de confirmación la primera vez
- **Whitelist de comandos**: Solo ejecutar comandos descubiertos por adapters legítimos (no comandos del usuario directamente)
- **Sandbox**: Futuro: ejecutar comandos en un entorno aislado (Docker/nsjail)
- **Logging**: Registrar toda ejecución en log con timestamp, comando y usuario
- **Timeouts**: Timeout máximo de 60 segundos por defecto, configurable

```python
# Mitigación: Logging de seguridad
def log_execution(cap_id, command, user, result):
    logger.info(
        f"SECURITY: Capability '{cap_id}' ejecutada por '{user}': "
        f"{' '.join(command)} → exit_code={result.exit_code} "
        f"duration={result.duration_ms:.0f}ms"
    )
```

### 10.2 Performance: Caché de Discovery

**Riesgo**: El discovery completo puede ser lento si hay muchos harnesses instalados o si se ejecutan múltiples `--help` en secuencia.

**Mitigaciones**:
- **Caché en disco**: Persistir resultados de discovery en `~/.kspr/capabilities.json` con TTL de 24 horas
- **Discovery incremental**: Solo re-descubrir fuentes que han cambiado (usar mtime de archivos)
- **Lazy loading**: No ejecutar discovery completo al startup; hacerlo on-demand o en background
- **Throttling**: Limitar a 5 segundos máximo por adapter de discovery

```python
# Mitigación: Discovery con caché
class CapabilityDiscovery:
    CACHE_TTL = 86400  # 24 horas
    
    def discover_all(self, force=False):
        if not force and self._cache_valid():
            return self._load_from_cache()
        # Discovery completo...
        self._save_to_cache(results)
        return results
```

### 10.3 Compatibilidad: CLIs No Instaladas

**Riesgo**: Un capability registrado en el registry puede no estar disponible si la CLI fue desinstalada o el PATH cambió.

**Mitigaciones**:
- **Validación de disponibilidad**: Antes de listar capabilities, verificar que el comando base existe (`shutil.which`)
- **Campo `installed`**: El CapabilitySchema tiene un campo `installed` que se actualiza en cada refresh
- **Mensajes claros**: Si un capability no está instalado, mostrar mensaje "Instalar con: pip install <package>"
- **Graceful degradation**: El sistema funciona sin capabilities; son enhancement, no dependencias críticas

### 10.4 Complejidad: Capas de Abstracción

**Riesgo**: La arquitectura crea múltiples capas (schemas, registry, discovery, loader, executor, validator, permissions, adapters) que podrían ser excesivas para el tamaño actual del proyecto.

**Mitigaciones**:
- **Implementación mínima viable**: Cada módulo inicia con implementación mínima, se expande según necesidad
- **Tests desde el inicio**: Cada fase tiene tests correspondientes para validar antes de agregar más capa
- **Refactoring programado**: Fase 8 incluye revisión de arquitectura para eliminar abstracciones innecesarias
- **Documentación de decisiones**: Cada clase documenta POR QUÉ existe (evitar over-engineering)

### 10.5 Contenido: Calidad de gsap-skills

**Riesgo**: Los SKILL.md de los skills default podrían no ser suficientemente instructivos para que KSPR I aprenda a usar las capabilities correctamente.

**Mitigaciones**:
- **Iteración con testing real**: Probar cada SKILL.md ejecutando comandos reales y verificando que el LLM los usa correctamente
- **Ejemplos concretos**: Cada SKILL.md incluye ejemplos de uso con comandos reales
- **Feedback loop**: Monitorear uso de capabilities en producción, ajustar skills según patrones de uso
- **Versionado**: Cada skill tiene versión semántica para trackear cambios

---

*Documento generado como parte del plan de implementación de KSPR AI CLI TOOL.*
*Fecha: 2026-09-18*
*Estado: Plan en revisión*
