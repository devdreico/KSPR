"""KSPR CLI: Professional Grayscale Interactive Terminal Agent for Static Analysis."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from kspr_engine.analyzer import analyze
from kspr_engine.config import Settings
from kspr_engine.models import AnalysisRequest, SourceFile, MCPServerConfig
from kspr_engine.providers import get_provider, ProviderName, ProviderError
from kspr_engine.mcp_client import MCPManager
from kspr_engine.plugin_manager import PluginManager
from kspr_engine.capabilities import CapabilityManager
from kspr_engine.skills import SkillsManager
from kspr_engine.decompiler import DecompilerEngine, CONTEXT_TREES_DIR
from kspr_terminal_ui import TerminalTheme, TerminalUI

__version__ = "0.1.0"

CONFIG_DIR = Path.home() / ".kspr"
CONFIG_FILE = CONFIG_DIR / "config.json"
PROJECTS_FILE = CONFIG_DIR / "projects.json"
MCP_SERVERS_FILE = CONFIG_DIR / "mcp_servers.json"
PLUGINS_DIR = Path.home() / ".kspr" / "plugins"
PROMPTS_FILE = CONFIG_DIR / "prompts.json"


def load_local_config() -> dict[str, Any]:
    if CONFIG_FILE.is_file():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_local_config(data: dict[str, Any]) -> None:
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[!] No se pudo guardar la configuración local: {e}")


def verify_license_code(code: str) -> bool:
    lic_path = Path(__file__).resolve().parents[1] / "backend" / "kspr_engine" / "licenses.json"
    if not lic_path.is_file():
        lic_path = CONFIG_DIR / "licenses.json"
    if not lic_path.is_file():
        return False
    try:
        data = json.loads(lic_path.read_text(encoding="utf-8"))
        codes = data.get("codes", {})
        if code.strip() in codes:
            return True
    except Exception:
        pass
    return False


def load_projects() -> list[dict[str, str]]:
    if PROJECTS_FILE.is_file():
        try:
            return json.loads(PROJECTS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def save_projects(projects: list[dict[str, str]]) -> None:
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        PROJECTS_FILE.write_text(json.dumps(projects, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[!] No se pudo guardar la lista de proyectos: {e}")


def load_mcp_servers() -> dict[str, dict]:
    if MCP_SERVERS_FILE.is_file():
        try:
            return json.loads(MCP_SERVERS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_mcp_servers(servers: dict[str, dict]) -> None:
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        MCP_SERVERS_FILE.write_text(json.dumps(servers, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[!] Could not save MCP servers: {e}")


def load_prompts() -> dict:
    if PROMPTS_FILE.is_file():
        try:
            return json.loads(PROMPTS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"version": "1.0.0", "prompts": {}}


def save_prompts(data: dict) -> None:
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        PROMPTS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[!] Could not save prompts: {e}")


def add_prompt(name: str, content: str, description: str = "", tags: list[str] | None = None) -> dict:
    data = load_prompts()
    from datetime import datetime, timezone
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
    data = load_prompts()
    if name in data["prompts"]:
        del data["prompts"][name]
        save_prompts(data)
        return True
    return False


def get_prompt(name: str) -> dict | None:
    data = load_prompts()
    return data["prompts"].get(name)


def list_prompts_data() -> list[dict]:
    data = load_prompts()
    return list(data["prompts"].values())


Color = TerminalTheme
print_colored = TerminalUI.print_colored
get_terminal_width = TerminalUI.get_width


def print_box(title: str, lines: list[str], color: Any = None) -> None:
    TerminalUI.print_box(title, lines)


def print_header() -> None:
    pass


print_dashboard = TerminalUI.print_session_banner
animate_spinner = TerminalUI.animate_spinner
print_response_box = TerminalUI.print_response


# ---- Collect functions ----

def collect(root: Path) -> list[SourceFile]:
    files = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in ALLOWED:
            continue
        if any(part in {".git", "node_modules", ".venv", "venv", "dist", "build"} for part in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
            if len(text.encode()) <= 2_000_000:
                files.append(SourceFile(path=str(path.relative_to(root)), content=text))
        except Exception:
            pass
    return files


def collect_zip(archive_path: Path) -> list[SourceFile]:
    files = []
    with zipfile.ZipFile(archive_path) as archive:
        for member in archive.infolist()[:2_000]:
            name = member.filename.replace("\\", "/")
            suffix = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
            if member.is_dir() or suffix not in ALLOWED or name.startswith("/") or ".." in name.split("/") or member.file_size > 2_000_000:
                continue
            try:
                files.append(SourceFile(path=name, content=archive.read(member)[:2_000_000].decode("utf-8", errors="replace")))
            except Exception:
                pass
    return files


def collect_source(source: Path) -> list[SourceFile]:
    if source.is_dir():
        return collect(source)
    if source.suffix.lower() == ".zip":
        return collect_zip(source)
    raise SystemExit("Error: La fuente debe ser un directorio o un archivo ZIP válido.")


def run_update() -> None:
    print_colored("[*] Actualizando KSPR AI a la última versión...", Color.WHITE)
    cmd = "curl -sSL https://raw.githubusercontent.com/devdreiortiz/KSPR/main/bin/install.sh | bash"
    try:
        subprocess.run(cmd, shell=True, check=True)
        print_colored("[✓] ¡KSPR se ha actualizado exitosamente!", Color.WHITE)
    except Exception as e:
        print_colored(f"[!] Error al actualizar: {e}", Color.LIGHT_GRAY)


# ---- Batch Analysis ----

async def run_batch_analysis(source: Path, git_url: str | None, output: Path, project_name: str | None, iterations: int, provider: str, model: str | None) -> None:
    if git_url:
        print_colored(f"[*] Clonando repositorio Git de forma segura: {git_url}", Color.WHITE)
        with tempfile.TemporaryDirectory(prefix="kspr-git-") as checkout:
            await asyncio.to_thread(
                subprocess.run,
                ["git", "clone", "--depth", "1", "--no-tags", git_url, checkout],
                check=True,
                capture_output=True,
                text=True,
            )
            files = collect(Path(checkout))
        default_name = git_url.rstrip("/").rsplit("/", 1)[-1].removesuffix(".git")
    else:
        print_colored(f"[*] Analizando fuente local: {source}", Color.WHITE)
        files = collect_source(source)
        default_name = source.stem

    if not files:
        raise SystemExit("Error: No se encontraron archivos soportados en la fuente.")

    print_colored(f"[*] Archivos recolectados: {len(files)}. Ejecutando KSPR Engine ({iterations} iteraciones)...", Color.LIGHT_GRAY)
    request = AnalysisRequest(project_name=project_name or default_name, files=files, iterations=iterations, provider=provider, model=model)
    result = await analyze(request, Settings())

    output.mkdir(parents=True, exist_ok=True)
    for artifact in result.artifacts:
        target = output / artifact.path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(artifact.content, encoding="utf-8")

    print_box("KSPR Analysis Success", [
        f"Session ID: {result.analysis_id}",
        f"Files Analyzed: {result.summary.files_analyzed}",
        f"UI Elements: {result.summary.ui_elements}",
        f"Flows Mapped: {result.summary.flows}",
        f"Exported Artifacts: {len(result.artifacts)}",
        f"Output Directory: {output.resolve()}"
    ], Color.WHITE)


# ---- Interactive Shell ----

def _sync_execute(manager: MCPManager, name: str, arguments: dict) -> str:
    """Synchronous wrapper to execute MCP tool from inside an async context."""
    import concurrent.futures
    import asyncio as _aio

    async def _run():
        return await manager.execute_tool(name, arguments)

    # Create a new event loop in a thread to avoid conflict with the running one
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(_aio.run, _run())
        return str(future.result(timeout=30))


def _build_messages_prompt(messages: list[dict[str, Any]]) -> str:
    parts = []
    for m in messages:
        role = m.get("role", "")
        content = m.get("content", "")
        if content:
            parts.append(f"[{role}]: {content}")
    return "\n".join(parts)

async def interactive_shell() -> None:
    print_header()
    
    config = load_local_config()
    api_keys = config.get("api_keys", {})
    for prov, key in api_keys.items():
        if key:
            os.environ[f"KSPR_{prov.upper()}_API_KEY"] = key
            if prov == "gemini":
                os.environ["GEMINI_API_KEY"] = key

    current_workspace = Path(config.get("current_workspace", Path.cwd()))
    active_model = config.get("active_model", "gemini-2.5-flash")
    active_provider = config.get("active_provider", "gemini")
    attached_files: dict[str, str] = {}
    indexed_models: dict[str, list[dict[str, Any]]] = config.get("indexed_models", {})
    tokens_used = 1250
    max_tokens = 128000
    session_id = time.strftime("%Y%m%d_%H%M%S")
    session_history: list[dict[str, str]] = []

    def persist_state() -> None:
        cfg = load_local_config()
        cfg["active_model"] = active_model
        cfg["active_provider"] = active_provider
        cfg["indexed_models"] = indexed_models
        cfg["current_workspace"] = str(current_workspace)
        save_local_config(cfg)

    def save_session() -> None:
        sessions_dir = CONFIG_DIR / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)
        session_file = sessions_dir / f"{session_id}.json"
        session_data = {
            "id": session_id,
            "provider": active_provider,
            "model": active_model,
            "workspace": str(current_workspace),
            "history": session_history,
            "files": list(attached_files.keys()),
            "tokens_used": tokens_used,
        }
        session_file.write_text(json.dumps(session_data, ensure_ascii=False, indent=2), encoding="utf-8")

    print_dashboard(active_provider, active_model, current_workspace, len(attached_files), tokens_used, max_tokens)
    print()

    def get_input_with_tab() -> str:
        """Lee input del usuario."""
        if os.name == "nt":
            width = min(get_terminal_width() - 2, 86)
            horizontal = "─" * (width - 2)
            print_colored(f"┌─ [ Input · kspr i @ {active_provider} ] " + "─" * max(0, width - 6 - len(active_provider) - 17) + "┐", Color.MID_GRAY)
            val = input(f"{Color.MID_GRAY}│ {Color.WHITE}❯ {Color.RESET}").strip()
            print_colored(f"└{horizontal}┘", Color.MID_GRAY)
            return val

        width = min(get_terminal_width() - 2, 86)
        horizontal = "─" * (width - 2)
        print_colored(f"┌─ [ Input · kspr i @ {active_provider} ] " + "─" * max(0, width - 6 - len(active_provider) - 17) + "┐", Color.MID_GRAY)
        sys.stdout.write(f"{Color.MID_GRAY}│ {Color.WHITE}❯ {Color.RESET}")
        sys.stdout.flush()

        import termios
        import tty
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        chars = []
        try:
            tty.setraw(fd)
            while True:
                ch = sys.stdin.read(1)
                if ch in ('\r', '\n'):
                    sys.stdout.write("\r\n")
                    sys.stdout.flush()
                    break
                elif ch == '\x7f' or ch == '\b':
                    if chars:
                        chars.pop()
                        sys.stdout.write("\b \b")
                        sys.stdout.flush()
                elif ord(ch) >= 32:
                    chars.append(ch)
                    sys.stdout.write(ch)
                    sys.stdout.flush()
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

        print_colored(f"└{horizontal}┘", Color.MID_GRAY)
        return "".join(chars).strip()

    while True:
        try:
            prompt = get_input_with_tab()
        except (KeyboardInterrupt, EOFError):
            print_colored("\n¡Hasta luego!", Color.LIGHT_GRAY)
            break

        if not prompt:
            continue

        tokens_used += len(prompt.encode()) // 3

        if prompt.startswith("/"):
            parts = prompt.split(maxsplit=1)
            cmd = parts[0].lower()
            arg = parts[1] if len(parts) > 1 else ""

            if cmd in {"/exit", "/quit"}:
                print_colored("Saliendo de la sesión de KSPR CLI.", Color.LIGHT_GRAY)
                break
            elif cmd == "/help":
                print_box("KSPR CLI Commands", [
                    "/help                - Show available commands",
                    "/login               - Authenticate with your license code to unlock /api",
                    "/api                 - Configure providers, API Keys and index models",
                    "/project             - Local project management (New / Existing)",
                    "/model [name/num]    - Show or select an indexed model",
                    "/provider [name]     - Switch active provider",
                    "/mcp [action]        - Configure and manage MCP servers",
                    "/plugins [action]    - Install and manage plugins",
                    "/capabilities [act]  - Discover and manage CLI capabilities",
                    "/prompts [action]    - Manage saved prompts (add/select/remove/info)",
                    "/skills [action]     - View and manage loaded skill bundles",
                    "/decompilate         - Index multiple files/links and generate Context Trees",
                    "/trees               - List generated Context Trees paths",
                    "/context             - Show attached files in context",
                    "/compact             - Compact context and token usage",
                    "/new                 - Start a fresh session",
                    "/sessions            - Browse and restore saved sessions",
                    "/clear               - Clear screen and redraw dashboard",
                    "/update              - Update KSPR to latest version",
                    "/exit                - Exit interactive session",
                ], Color.WHITE)
            elif cmd == "/clear":
                os.system("cls" if os.name == "nt" else "clear")
                print_header()
                print_dashboard(active_provider, active_model, current_workspace, len(attached_files), tokens_used, max_tokens)
                print()
            elif cmd == "/login":
                print_box("KSPR Authentication Gateway", [
                    "Ingresa tu código único de identificación proporcionado en tu software externo:"
                ], Color.WHITE)
                code_input = input(f"{Color.WHITE}Código único: {Color.RESET}").strip()
                if verify_license_code(code_input):
                    cfg = load_local_config()
                    cfg["unlocked"] = True
                    save_local_config(cfg)
                    print_colored("[✓] ¡Código verificado con éxito! Ya puedes utilizar /api para configurar tus proveedores con máxima eficiencia.", Color.WHITE)
                else:
                    print_colored("[✕] Código de identificación inválido o no reconocido.", Color.LIGHT_GRAY)
                print()
            elif cmd == "/update":
                run_update()
            elif cmd == "/project":
                print_box("KSPR Project Manager", [
                    " 1. New project (Crear nuevo proyecto local)",
                    " 2. Proyectos anteriores (Seleccionar workspace existente)",
                    " 3. Abrir carpeta existente del sistema (Ruta custom)"
                ], Color.WHITE)
                p_choice = input(f"{Color.WHITE}Elige opción (1-3): {Color.RESET}").strip()
                
                projects = load_projects()
                if p_choice == "1":
                    proj_name = input(f"{Color.WHITE}Nombre del nuevo proyecto: {Color.RESET}").strip()
                    if proj_name:
                        new_ws = Path.cwd() / "workspace" / proj_name
                        new_ws.mkdir(parents=True, exist_ok=True)
                        current_workspace = new_ws
                        
                        proj_entry = {"name": proj_name, "path": str(new_ws.resolve())}
                        if proj_entry not in projects:
                            projects.append(proj_entry)
                            save_projects(projects)
                        
                        persist_state()
                        print_colored(f"[✓] Proyecto '{proj_name}' creado en {new_ws.resolve()} con control CRUD total para el agente.", Color.WHITE)
                elif p_choice == "2":
                    if not projects:
                        print_colored("[!] No hay proyectos anteriores registrados.", Color.LIGHT_GRAY)
                    else:
                        print_box("Proyectos Anteriores", [f" {idx+1}. {p['name']} ({p['path']})" for idx, p in enumerate(projects)], Color.WHITE)
                        sel = input(f"{Color.WHITE}Selecciona número de proyecto: {Color.RESET}").strip()
                        if sel.isdigit() and 1 <= int(sel) <= len(projects):
                            chosen = projects[int(sel)-1]
                            p_path = Path(chosen["path"])
                            if p_path.is_dir():
                                current_workspace = p_path
                                persist_state()
                                print_colored(f"[✓] Workspace cambiado a: {current_workspace}", Color.WHITE)
                            else:
                                print_colored("[!] El directorio del proyecto ya no existe.", Color.LIGHT_GRAY)
                elif p_choice == "3":
                    raw_path = input(f"{Color.WHITE}Introduce la ruta absoluta o relativa de la carpeta: {Color.RESET}").strip()
                    if raw_path:
                        target_dir = Path(raw_path).expanduser().resolve()
                        if target_dir.is_dir():
                            current_workspace = target_dir
                            proj_name = target_dir.name
                            proj_entry = {"name": proj_name, "path": str(target_dir)}
                            if proj_entry not in projects:
                                projects.append(proj_entry)
                                save_projects(projects)
                            persist_state()
                            print_colored(f"[✓] Workspace vinculado exitosamente a: {target_dir}", Color.WHITE)
                        else:
                            print_colored("[!] La ruta especificada no es un directorio válido.", Color.LIGHT_GRAY)
                print_dashboard(active_provider, active_model, current_workspace, len(attached_files), tokens_used, max_tokens)
            elif cmd == "/model":
                if arg:
                    if active_provider in indexed_models and arg.isdigit():
                        idx = int(arg) - 1
                        models = indexed_models[active_provider]
                        if 0 <= idx < len(models):
                            active_model = models[idx].get("id")
                            print_colored(f"[✓] Modelo activo actualizado a: {active_model}", Color.WHITE)
                            persist_state()
                        else:
                            print_colored("[!] Índice de modelo fuera de rango.", Color.LIGHT_GRAY)
                    else:
                        active_model = arg
                        print_colored(f"[✓] Modelo activo actualizado a: {active_model}", Color.WHITE)
                        persist_state()
                elif active_provider in indexed_models and indexed_models[active_provider]:
                    models = indexed_models[active_provider]
                    print_box(f"Modelos Disponibles ({active_provider})", [f" {idx+1}. {m.get('id')} ({m.get('name', '')})" for idx, m in enumerate(models)], Color.WHITE)
                    m_choice = input(f"{Color.WHITE}Elige número de modelo o escribe nombre: {Color.RESET}").strip()
                    if m_choice.isdigit() and 1 <= int(m_choice) <= len(models):
                        active_model = models[int(m_choice)-1].get("id")
                        print_colored(f"[✓] Modelo activo actualizado a: {active_model}", Color.WHITE)
                        persist_state()
                    elif m_choice:
                        active_model = m_choice
                        print_colored(f"[✓] Modelo activo actualizado a: {active_model}", Color.WHITE)
                        persist_state()
                else:
                    print_colored(f"[*] Modelo activo actual: {active_model}", Color.LIGHT_GRAY)
                    print_colored("[*] Consejo: Ejecuta /api para indexar automáticamente los modelos de tu proveedor.", Color.MID_GRAY)
                print_dashboard(active_provider, active_model, current_workspace, len(attached_files), tokens_used, max_tokens)
            elif cmd == "/provider":
                if arg in {"gemini", "local", "openai", "groq", "deepseek", "anthropic", "openrouter", "opencode-zen"}:
                    active_provider = arg
                    print_colored(f"[✓] Proveedor activo actualizado a: {active_provider}", Color.WHITE)
                    persist_state()
                else:
                    print_colored(f"[!] Proveedor activo actual: {active_provider} (opciones: gemini, local, openai, groq, deepseek, anthropic, openrouter, opencode-zen)", Color.LIGHT_GRAY)
                print_dashboard(active_provider, active_model, current_workspace, len(attached_files), tokens_used, max_tokens)
            elif cmd == "/context":
                lines = [f"Workspace: {current_workspace}", f"Archivos adjuntos ({len(attached_files)}):"]
                for path in attached_files:
                    lines.append(f" - @{path}")
                print_box("Active Context", lines, Color.WHITE)
            elif cmd == "/mcp":
                mcp_args = arg.strip().split() if arg else []
                mcp_action = mcp_args[0] if mcp_args else ""
                if not mcp_action:
                    servers_data = load_mcp_servers()
                    if not servers_data:
                        print_colored("[!] No MCP servers configured.", Color.LIGHT_GRAY)
                        print_colored("    Usage: /mcp add <name> <url|command>", Color.MID_GRAY)
                    else:
                        lines = []
                        for sname, sconf in servers_data.items():
                            status = "active" if sconf.get("enabled", True) else "inactive"
                            url_or_cmd = sconf.get("url", "") or " ".join(sconf.get("command", []))
                            lines.append(f" {sname}  |  {sconf.get('type', 'remote')}  |  {url_or_cmd}  |  {status}")
                        print_box("MCP Servers", lines, Color.WHITE)
                elif mcp_action == "add" and len(mcp_args) >= 3:
                    sname = mcp_args[1]
                    target = mcp_args[2]
                    servers_data = load_mcp_servers()
                    if target.startswith("http://") or target.startswith("https://"):
                        servers_data[sname] = {"type": "remote", "url": target, "enabled": True}
                    else:
                        servers_data[sname] = {"type": "local", "command": [target] + mcp_args[3:], "enabled": True}
                    save_mcp_servers(servers_data)
                    print_colored(f"[✓] MCP server '{sname}' added.", Color.WHITE)
                elif mcp_action == "remove" and len(mcp_args) >= 2:
                    servers_data = load_mcp_servers()
                    if mcp_args[1] in servers_data:
                        del servers_data[mcp_args[1]]
                        save_mcp_servers(servers_data)
                        print_colored(f"[✓] MCP server '{mcp_args[1]}' removed.", Color.WHITE)
                    else:
                        print_colored(f"[!] MCP server '{mcp_args[1]}' not found.", Color.LIGHT_GRAY)
                elif mcp_action in {"enable", "disable"} and len(mcp_args) >= 2:
                    servers_data = load_mcp_servers()
                    if mcp_args[1] in servers_data:
                        servers_data[mcp_args[1]]["enabled"] = mcp_action == "enable"
                        save_mcp_servers(servers_data)
                        print_colored(f"[✓] MCP server '{mcp_args[1]}' {mcp_action}d.", Color.WHITE)
                    else:
                        print_colored(f"[!] MCP server '{mcp_args[1]}' not found.", Color.LIGHT_GRAY)
                elif mcp_action == "test" and len(mcp_args) >= 2:
                    servers_data = load_mcp_servers()
                    sname = mcp_args[1]
                    if sname not in servers_data:
                        print_colored(f"[!] MCP server '{sname}' not found.", Color.LIGHT_GRAY)
                    else:
                        print_colored(f"[*] Testing MCP server '{sname}'...", Color.LIGHT_GRAY)
                        mgr = MCPManager({sname: MCPServerConfig(**servers_data[sname])})
                        connected = asyncio.run(mgr.connect_all())
                        if connected:
                            tools = mgr.get_tools_sync()
                            print_colored(f"[✓] Connected. {len(tools)} tools available.", Color.WHITE)
                        else:
                            print_colored(f"[!] Failed to connect to '{sname}'.", Color.LIGHT_GRAY)
                elif mcp_action == "tools":
                    servers_data = load_mcp_servers()
                    if not servers_data:
                        print_colored("[!] No MCP servers configured.", Color.LIGHT_GRAY)
                    else:
                        mgr = MCPManager({k: MCPServerConfig(**v) for k, v in servers_data.items()})
                        asyncio.run(mgr.connect_all())
                        tools = mgr.get_tools_sync()
                        if tools:
                            tool_lines = [f" {t.name}  |  {t.server}  |  {t.description[:50]}" for t in tools]
                            print_box("MCP Tools", tool_lines, Color.WHITE)
                        else:
                            print_colored("[!] No tools available from connected MCP servers.", Color.LIGHT_GRAY)
                else:
                    print_colored("[!] Usage: /mcp [add|remove|enable|disable|test|tools] [args]", Color.LIGHT_GRAY)
                print_dashboard(active_provider, active_model, current_workspace, len(attached_files), tokens_used, max_tokens)
            elif cmd == "/plugins":
                pm = PluginManager(PLUGINS_DIR)
                plugin_args = arg.strip().split() if arg else []
                plugin_action = plugin_args[0] if plugin_args else ""
                if not plugin_action:
                    plugins = pm.scan_plugins()
                    if not plugins:
                        print_colored("[!] No plugins installed.", Color.LIGHT_GRAY)
                        print_colored(f"    Plugins directory: {PLUGINS_DIR}", Color.MID_GRAY)
                    else:
                        lines = []
                        for p in plugins:
                            status = "enabled" if p.enabled else "disabled"
                            lines.append(f" {p.name}  |  v{p.version}  |  {len(p.tools)} tools  |  {status}")
                        print_box("Installed Plugins", lines, Color.WHITE)
                elif plugin_action == "load":
                    loaded = pm.load_all()
                    print_colored(f"[✓] Loaded {loaded} plugin(s).", Color.WHITE)
                elif plugin_action == "tools":
                    pm.load_all()
                    tools = pm.get_tools()
                    if tools:
                        tool_lines = [f" {t.name}  |  {t.server}  |  {t.description[:50]}" for t in tools]
                        print_box("Plugin Tools", tool_lines, Color.WHITE)
                    else:
                        print_colored("[!] No tools from loaded plugins.", Color.LIGHT_GRAY)
                elif plugin_action == "info" and len(plugin_args) >= 2:
                    pm.load_all()
                    info = pm.get_plugin_info(plugin_args[1])
                    if info:
                        print_box(f"Plugin: {info.name}", [
                            f"Version: {info.version}",
                            f"Description: {info.description}",
                            f"Tools: {len(info.tools)}",
                        ], Color.WHITE)
                    else:
                        print_colored(f"[!] Plugin '{plugin_args[1]}' not found.", Color.LIGHT_GRAY)
                else:
                    print_colored("[!] Usage: /plugins [load|tools|info] [args]", Color.LIGHT_GRAY)
                print_dashboard(active_provider, active_model, current_workspace, len(attached_files), tokens_used, max_tokens)
            elif cmd == "/capabilities":
                cap_manager = CapabilityManager()
                cap_manager.initialize()
                cap_args = arg.strip().split() if arg else []
                cap_action = cap_args[0] if cap_args else ""
                if not cap_action:
                    caps = cap_manager.list_capabilities()
                    if not caps:
                        print_colored("[!] No capabilities discovered.", Color.LIGHT_GRAY)
                        print_colored("    Install CLI-Anything harnesses to add capabilities.", Color.MID_GRAY)
                    else:
                        lines = []
                        for c in caps:
                            lines.append(f" {c.id}  |  {c.name}  |  {c.source_type}  |  {c.description[:40]}")
                        print_box("Capabilities", lines, Color.WHITE)
                elif cap_action == "search" and len(cap_args) >= 2:
                    query = " ".join(cap_args[1:])
                    results = cap_manager.search(query)
                    if results:
                        lines = [f" {c.id}  |  {c.name}  |  {c.description[:50]}" for c in results]
                        print_box(f"Search: {query}", lines, Color.WHITE)
                    else:
                        print_colored(f"[!] No capabilities matching '{query}'.", Color.LIGHT_GRAY)
                elif cap_action == "info" and len(cap_args) >= 2:
                    cap = cap_manager.get(cap_args[1])
                    if cap:
                        print_box(f"Capability: {cap.name}", [
                            f"ID: {cap.id}",
                            f"Source: {cap.source}",
                            f"Type: {cap.source_type}",
                            f"Category: {cap.category}",
                            f"Version: {cap.version}",
                            f"Installed: {cap.installed}",
                            f"Returns JSON: {cap.returns_json}",
                            f"Description: {cap.description}",
                        ], Color.WHITE)
                    else:
                        print_colored(f"[!] Capability '{cap_args[1]}' not found.", Color.LIGHT_GRAY)
                elif cap_action == "run" and len(cap_args) >= 2:
                    cap_id = cap_args[1]
                    result = cap_manager.execute(cap_id, {}, prefer_json=True)
                    if result.success:
                        print_colored(f"[✓] Execution successful ({result.duration_ms:.0f}ms)", Color.WHITE)
                        if result.parsed_output:
                            print(json.dumps(result.parsed_output, ensure_ascii=False, indent=2)[:2000])
                        else:
                            print(result.stdout[:2000])
                    else:
                        print_colored(f"[!] Execution failed: {result.error_message}", Color.LIGHT_GRAY)
                elif cap_action == "refresh":
                    caps = cap_manager.refresh()
                    print_colored(f"[✓] Refreshed. {len(caps)} capabilities found.", Color.WHITE)
                else:
                    print_colored("[!] Usage: /capabilities [search|info|run|refresh] [args]", Color.LIGHT_GRAY)
                print_dashboard(active_provider, active_model, current_workspace, len(attached_files), tokens_used, max_tokens)
            elif cmd == "/prompts":
                prompt_args = arg.strip().split() if arg else []
                prompt_action = prompt_args[0] if prompt_args else ""
                if not prompt_action:
                    prompts = list_prompts_data()
                    if not prompts:
                        print_colored("[!] No saved prompts. Use /prompts add <name> to create one.", Color.LIGHT_GRAY)
                    else:
                        lines = []
                        for p in prompts:
                            tags = ", ".join(p.get("tags", []))
                            lines.append(f" {p['name']:<20} {p.get('description', '')[:40]} [{tags}]")
                        print_box("Saved Prompts", lines, Color.WHITE)
                elif prompt_action == "add" and len(prompt_args) >= 2:
                    pname = prompt_args[1]
                    if get_prompt(pname):
                        print_colored(f"[!] Prompt '{pname}' already exists.", Color.LIGHT_GRAY)
                    else:
                        print_colored(f"Creating prompt '{name}'. Type content (empty line to finish):", Color.WHITE)
                        lines_list = []
                        while True:
                            try:
                                line = input(f"{Color.WHITE}> {Color.RESET}")
                            except (EOFError, KeyboardInterrupt):
                                break
                            if line == "":
                                break
                            lines_list.append(line)
                        content = "\n".join(lines_list)
                        if not content.strip():
                            print_colored("[!] Empty prompt. Cancelled.", Color.LIGHT_GRAY)
                        else:
                            desc = input(f"{Color.WHITE}Description (optional): {Color.RESET}").strip()
                            tags_str = input(f"{Color.WHITE}Tags (comma separated, optional): {Color.RESET}").strip()
                            tags = [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else []
                            add_prompt(pname, content, desc, tags)
                            print_colored(f"[✓] Prompt '{pname}' created.", Color.WHITE)
                elif prompt_action == "select":
                    if len(prompt_args) >= 2:
                        pname = prompt_args[1]
                        prompt_data = get_prompt(pname)
                        if prompt_data:
                            print_colored(f"[✓] Prompt '{pname}' selected.", Color.WHITE)
                            return ("PROMPT_INJECT", prompt_data["content"])
                        else:
                            print_colored(f"[!] Prompt '{pname}' not found.", Color.LIGHT_GRAY)
                    else:
                        prompts = list_prompts_data()
                        if not prompts:
                            print_colored("[!] No prompts to select.", Color.LIGHT_GRAY)
                        else:
                            print_colored("Select a prompt:", Color.WHITE)
                            for i, p in enumerate(prompts, 1):
                                print_colored(f"  {i}. {p['name']}", Color.WHITE)
                            try:
                                choice = int(input(f"{Color.WHITE}Number: {Color.RESET}")) - 1
                                if 0 <= choice < len(prompts):
                                    selected = prompts[choice]
                                    return ("PROMPT_INJECT", selected["content"])
                                else:
                                    print_colored("[!] Invalid selection.", Color.LIGHT_GRAY)
                            except (ValueError, IndexError, EOFError):
                                print_colored("[!] Invalid selection.", Color.LIGHT_GRAY)
                elif prompt_action == "remove" and len(prompt_args) >= 2:
                    if remove_prompt(prompt_args[1]):
                        print_colored(f"[✓] Prompt '{prompt_args[1]}' removed.", Color.WHITE)
                    else:
                        print_colored(f"[!] Prompt '{prompt_args[1]}' not found.", Color.LIGHT_GRAY)
                elif prompt_action == "info" and len(prompt_args) >= 2:
                    prompt_data = get_prompt(prompt_args[1])
                    if prompt_data:
                        print_box(f"Prompt: {prompt_data['name']}", [
                            f"Description: {prompt_data.get('description', '')}",
                            f"Tags: {', '.join(prompt_data.get('tags', []))}",
                            f"Created: {prompt_data.get('created_at', '')}",
                            f"Content preview: {prompt_data['content'][:200]}...",
                        ], Color.WHITE)
                    else:
                        print_colored(f"[!] Prompt '{prompt_args[1]}' not found.", Color.LIGHT_GRAY)
                else:
                    print_colored("[!] Usage: /prompts [add|select|remove|info] [args]", Color.LIGHT_GRAY)
                print_dashboard(active_provider, active_model, current_workspace, len(attached_files), tokens_used, max_tokens)
            elif cmd == "/skills":
                skills_manager = SkillsManager()
                skills_args = arg.strip().split() if arg else []
                skills_action = skills_args[0] if skills_args else ""
                if not skills_action:
                    bundles = skills_manager.list_bundles()
                    if not bundles:
                        print_colored("[!] No skill bundles loaded.", Color.LIGHT_GRAY)
                    else:
                        lines = []
                        for b in bundles:
                            status = "[on]" if b.enabled else "[off]"
                            lines.append(f" {status} {b.name:<25} v{b.version}  {b.description[:40]}")
                        print_box("Skills", lines, Color.WHITE)
                elif skills_action == "info" and len(skills_args) >= 2:
                    bundle = skills_manager.get_bundle(skills_args[1])
                    if bundle:
                        print_box(f"Skill: {bundle.name}", [
                            f"Description: {bundle.description}",
                            f"Version: {bundle.version}",
                            f"Path: {bundle.skill_path}",
                            f"Enabled: {bundle.enabled}",
                        ], Color.WHITE)
                    else:
                        print_colored(f"[!] Skill '{skills_args[1]}' not found.", Color.LIGHT_GRAY)
                elif skills_action == "context":
                    context = skills_manager.get_skill_context()
                    if context:
                        print_colored("Injected LLM context:", Color.WHITE)
                        print(context[:3000])
                    else:
                        print_colored("[!] No skill context available.", Color.LIGHT_GRAY)
                elif skills_action == "load":
                    skills_manager.reload()
                    print_colored(f"[✓] Reloaded {len(skills_manager.list_bundles())} skill bundles.", Color.WHITE)
                else:
                    print_colored("[!] Usage: /skills [info|context|load] [args]", Color.LIGHT_GRAY)
                print_dashboard(active_provider, active_model, current_workspace, len(attached_files), tokens_used, max_tokens)
            elif cmd == "/decompilate":
                print_box("KSPR Decompiler — Indexación Multi-Fuente", [
                    "Añade archivos (PDF, imágenes .jpg/.png/.heif, .txt, .md) o enlaces web.",
                    "Introduce una ruta o URL por línea. Presiona Enter vacío para terminar y compilar."
                ], Color.WHITE)
                sources = []
                while True:
                    try:
                        src_input = input(f"{Color.WHITE}Fuente (archivo o URL) [Enter para terminar]: {Color.RESET}").strip()
                    except (EOFError, KeyboardInterrupt):
                        break
                    if not src_input:
                        break
                    sources.append(src_input)
                    print_colored(f"[+] Indexado: {src_input} (Total: {len(sources)})", Color.LIGHT_GRAY)

                if not sources:
                    print_colored("[!] No se seleccionaron fuentes. Operación cancelada.", Color.LIGHT_GRAY)
                else:
                    action_confirm = input(f"{Color.WHITE}¿Iniciar DECOMPILE con {len(sources)} fuentes? (Escribe DECOMPILE): {Color.RESET}").strip()
                    if action_confirm == "DECOMPILE":
                        print_colored("[*] Ingestionando y analizando fuentes con KSPR I...", Color.LIGHT_GRAY)
                        decompiler = DecompilerEngine()
                        ingested = [decompiler.ingest_source(s) for s in sources]
                        
                        # Build prompt for model to generate Context Tree
                        combined_text = "\n\n".join([f"SOURCE: {item['source']}\n{item.get('content', '')}" for item in ingested if item.get('success')])
                        
                        try:
                            settings = Settings()
                            provider_instance = get_provider(ProviderName(active_provider.lower()), settings, api_key=getattr(settings, f'{active_provider.lower()}_api_key', None))
                            prompt_text = f"Analiza la siguiente informacion recopilada de multiples fuentes y genera un Arbol de Contexto (Context Tree) estructurado. Identifica el concepto central y explica detalladamente hasta el mas minimo detalle en archivos tematicos markdown (.md).\n\n{combined_text}"
                            
                            async def run_decompile_complete():
                                return await provider_instance.complete(prompt_text, active_model)
                            
                            response, latency = asyncio.run(run_decompile_complete())
                            tree_path = decompiler.generate_context_trees(ingested, str(response))
                            print_colored(f"[✓] Context Tree generado exitosamente en: {tree_path}", Color.WHITE)
                        except Exception as e:
                            print_colored(f"[!] Error ejecutando análisis IA: {e}. Generando estructura estándar...", Color.LIGHT_GRAY)
                            tree_path = decompiler.generate_context_trees(ingested, "# Analisis Generado\n\nInformacion recopilada de fuentes.")
                            print_colored(f"[✓] Context Tree generado en: {tree_path}", Color.WHITE)
                    else:
                        print_colored("[!] Operación DECOMPILE cancelada.", Color.LIGHT_GRAY)
                print_dashboard(active_provider, active_model, current_workspace, len(attached_files), tokens_used, max_tokens)
            elif cmd == "/trees":
                decompiler = DecompilerEngine()
                trees = decompiler.list_trees()
                if not trees:
                    print_colored("[!] No hay Context Trees creados. Usa /decompilate para crear uno.", Color.LIGHT_GRAY)
                else:
                    lines = []
                    for t in trees:
                        files_str = ", ".join(t["files"])
                        lines.append(f" Concepto: {t['concept']}  |  Ruta: {t['path']}  |  Archivos: [{files_str}]")
                    print_box("Context Trees", lines, Color.WHITE)
                print_dashboard(active_provider, active_model, current_workspace, len(attached_files), tokens_used, max_tokens)
            elif cmd == "/compact":
                if session_history:
                    save_session()
                    before_tokens = tokens_used
                    compacted_history = []
                    seen = set()
                    for entry in reversed(session_history):
                        key = entry.get("prompt", "")
                        if key not in seen:
                            seen.add(key)
                            compacted_history.append(entry)
                    session_history.clear()
                    session_history.extend(reversed(compacted_history))
                    tokens_used = max(1250, tokens_used - len(compacted_history) * 50)
                    print_colored(f"[✓] Context compacted. Tokens: {before_tokens} → {tokens_used}", Color.WHITE)
                    print_colored(f"    Session saved and deduplicated ({len(compacted_history)} unique entries).", Color.LIGHT_GRAY)
                else:
                    tokens_used = 1250
                    attached_files.clear()
                    print_colored("[✓] Context cleared. Starting fresh token count.", Color.WHITE)
                print_dashboard(active_provider, active_model, current_workspace, len(attached_files), tokens_used, max_tokens)
            elif cmd == "/new":
                if session_history:
                    save_session()
                    print_colored(f"[✓] Session {session_id} saved.", Color.WHITE)
                session_id = time.strftime("%Y%m%d_%H%M%S")
                session_history.clear()
                attached_files.clear()
                tokens_used = 1250
                print_colored(f"[✓] New session started: {session_id}", Color.WHITE)
                print_dashboard(active_provider, active_model, current_workspace, len(attached_files), tokens_used, max_tokens)
            elif cmd == "/sessions":
                sessions_dir = CONFIG_DIR / "sessions"
                if not sessions_dir.is_dir():
                    print_colored("[!] No saved sessions found.", Color.LIGHT_GRAY)
                else:
                    session_files = sorted(sessions_dir.glob("*.json"), reverse=True)
                    if not session_files:
                        print_colored("[!] No saved sessions found.", Color.LIGHT_GRAY)
                    else:
                        session_lines = []
                        for sf in session_files[:20]:
                            try:
                                data = json.loads(sf.read_text(encoding="utf-8"))
                                sid = data.get("id", sf.stem)
                                prov = data.get("provider", "?")
                                model = data.get("model", "?")
                                hist_len = len(data.get("history", []))
                                files_len = len(data.get("files", []))
                                session_lines.append(f" {sid}  |  {prov}:{model}  |  {hist_len} messages  |  {files_len} files")
                            except Exception:
                                session_lines.append(f" {sf.stem}  |  (unreadable)")
                        print_box("Saved Sessions", session_lines, Color.WHITE)
                        sel = input(f"{Color.WHITE}Enter session ID to restore (or press Enter to cancel): {Color.RESET}").strip()
                        if sel:
                            target = sessions_dir / f"{sel}.json"
                            if target.is_file():
                                data = json.loads(target.read_text(encoding="utf-8"))
                                session_history.clear()
                                session_history.extend(data.get("history", []))
                                tokens_used = data.get("tokens_used", 1250)
                                for fp in data.get("files", []):
                                    fpath = current_workspace / fp
                                    if fpath.is_file():
                                        try:
                                            attached_files[fp] = fpath.read_text(encoding="utf-8", errors="replace")
                                        except Exception:
                                            pass
                                print_colored(f"[✓] Session {sel} restored ({len(session_history)} messages).", Color.WHITE)
                            else:
                                print_colored(f"[!] Session {sel} not found.", Color.LIGHT_GRAY)
                print_dashboard(active_provider, active_model, current_workspace, len(attached_files), tokens_used, max_tokens)
            elif cmd == "/api":
                cfg = load_local_config()
                if not cfg.get("unlocked", False):
                    print_box("🔒 KSPR Security Lock", [
                        "Acceso restringido: Se requiere un código único de acceso.",
                        "Por favor ejecuta el comando /login e introduce tu código para desbloquear /api."
                    ], Color.WHITE)
                    print()
                    continue
                providers_list = ["gemini", "openai", "groq", "deepseek", "anthropic", "openrouter", "opencode-zen", "local"]
                print_box("API & Provider Configuration", [
                    "Selecciona el proveedor para configurar su API Key e indexar modelos:",
                    " 1. gemini       (Google Generative AI)",
                    " 2. openai       (OpenAI GPT-4 / GPT-3.5)",
                    " 3. groq         (Groq Llama / Mixtral)",
                    " 4. deepseek     (Deepseek Chat / Reasoner)",
                    " 5. anthropic    (Anthropic Claude)",
                    " 6. openrouter   (OpenRouter AI Gateway)",
                    " 7. opencode-zen (OpenCode Zen Gateway)",
                    " 8. local        (Modo local sin API Key)"
                ], Color.WHITE)
                
                prov_choice = arg.strip().lower() if arg else input(f"{Color.WHITE}Elige proveedor (1-8 o nombre): {Color.RESET}").strip().lower()
                
                selected_prov = active_provider
                if prov_choice in {"1", "gemini"}:
                    selected_prov = "gemini"
                elif prov_choice in {"2", "openai"}:
                    selected_prov = "openai"
                elif prov_choice in {"3", "groq"}:
                    selected_prov = "groq"
                elif prov_choice in {"4", "deepseek"}:
                    selected_prov = "deepseek"
                elif prov_choice in {"5", "anthropic"}:
                    selected_prov = "anthropic"
                elif prov_choice in {"6", "openrouter"}:
                    selected_prov = "openrouter"
                elif prov_choice in {"7", "opencode-zen", "opencode_zen", "opencode"}:
                    selected_prov = "opencode-zen"
                elif prov_choice in {"8", "local"}:
                    selected_prov = "local"
                elif prov_choice in providers_list:
                    selected_prov = prov_choice
                elif prov_choice == "opencode_zen":
                    selected_prov = "opencode-zen"
                
                if selected_prov == "local":
                    print_colored("[✓] El proveedor local no requiere API Key.", Color.WHITE)
                    active_provider = selected_prov
                    indexed_models[selected_prov] = [{"id": "kspr-local", "name": "KSPR Local Demo"}]
                    persist_state()
                else:
                    env_key = f"KSPR_{selected_prov.upper()}_API_KEY"
                    current_key = os.getenv(env_key, "")
                    masked = (current_key[:6] + "..." + current_key[-4:]) if len(current_key) > 10 else ("Configurada" if current_key else "No configurada")
                    
                    print_colored(f"[*] Proveedor seleccionado: {selected_prov}", Color.LIGHT_GRAY)
                    print_colored(f"[*] Estado actual API Key: {masked}", Color.MID_GRAY)
                    
                    new_key = input(f"{Color.WHITE}Introduce la API Key para {selected_prov}: {Color.RESET}").strip()
                    if new_key:
                        os.environ[env_key] = new_key
                        if selected_prov == "gemini":
                            os.environ["GEMINI_API_KEY"] = new_key
                        
                        cfg = load_local_config()
                        cfg.setdefault("api_keys", {})[selected_prov] = new_key
                        cfg["active_provider"] = selected_prov
                        save_local_config(cfg)

                        print_colored(f"[✓] API Key para '{selected_prov}' guardada localmente y aplicada exitosamente.", Color.WHITE)
                        active_provider = selected_prov
                        
                        try:
                            settings = Settings()
                            temp_prov = get_provider(ProviderName(selected_prov), settings, api_key=new_key)
                            print_colored(f"[*] Indexando modelos disponibles desde la API de {selected_prov}...", Color.LIGHT_GRAY)
                            models, _ = await animate_spinner(temp_prov.list_models(), f"Consultando modelos de {selected_prov}...")
                            if models:
                                indexed_models[selected_prov] = models
                                model_lines = [f" {idx+1}. {m.get('id')} ({m.get('name', '')})" for idx, m in enumerate(models[:20])]
                                print_box(f"Modelos Indexados ({selected_prov}) - Total: {len(models)}", model_lines, Color.WHITE)
                                active_model = models[0].get("id")
                                print_colored(f"[✓] Modelo predeterminado establecido a: {active_model}", Color.WHITE)
                                persist_state()
                            else:
                                print_colored("[!] No se encontraron modelos en la respuesta de la API.", Color.MID_GRAY)
                        except Exception as ex:
                            print_colored(f"[!] No se pudieron indexar modelos automáticamente: {ex}", Color.LIGHT_GRAY)
                    else:
                        print_colored("[!] API Key no modificada (vacía).", Color.MID_GRAY)
                print_dashboard(active_provider, active_model, current_workspace, len(attached_files), tokens_used, max_tokens)
            else:
                print_colored(f"[!] Unknown command: {cmd}. Type /help to see available commands.", Color.MID_GRAY)
            print()
            continue

        # Handle file references like @filename
        referenced_content = ""
        words = prompt.split()
        for word in words:
            if word.startswith("@"):
                filepath = word[1:]
                fpath = current_workspace / filepath
                if fpath.is_file():
                    try:
                        content = fpath.read_text(encoding="utf-8", errors="replace")
                        attached_files[filepath] = content
                        referenced_content += f"\n\n--- Referencia @{filepath} ---\n{content[:4000]}"
                        print_colored(f"[+] Archivo adjuntado al contexto: @{filepath}", Color.WHITE)
                    except Exception as e:
                        print_colored(f"[!] No se pudo leer {filepath}: {e}", Color.MID_GRAY)
                else:
                    print_colored(f"[!] Archivo no encontrado: {filepath}", Color.MID_GRAY)

        full_prompt = prompt + referenced_content

        try:
            settings = Settings()
            provider_instance = get_provider(ProviderName(active_provider.lower()), settings, api_key=getattr(settings, f'{active_provider.lower()}_api_key', None))

            # Collect tools from MCP and plugins
            mcp_manager = None
            plugin_manager = None
            all_tool_schemas: list[dict[str, Any]] = []

            servers_data = load_mcp_servers()
            if servers_data:
                mcp_manager = MCPManager({k: MCPServerConfig(**v) for k, v in servers_data.items()})
                asyncio.run(mcp_manager.connect_all())
                all_tool_schemas.extend(mcp_manager.get_tool_schemas())

            plugin_manager = PluginManager(PLUGINS_DIR)
            plugin_manager.load_all()
            all_tool_schemas.extend(plugin_manager.get_tool_schemas())

            # Collect capabilities
            cap_manager = CapabilityManager()
            cap_manager.initialize()
            all_tool_schemas.extend(cap_manager.get_schemas_for_llm())

            # Tool calling loop (max 10 iterations)
            conversation_messages = [{"role": "user", "content": full_prompt}]
            max_tool_iterations = 10
            final_response = ""

            for _iteration in range(max_tool_iterations):
                async def call_llm():
                    return await provider_instance.complete(full_prompt, active_model, tools=all_tool_schemas if all_tool_schemas else None)

                (response, latency) = await animate_spinner(call_llm(), f"KSPR I processing with {active_provider}:{active_model}...")

                # Check if response is a tool call
                if isinstance(response, dict) and "tool_calls" in response:
                    tool_calls = response["tool_calls"]
                    TerminalUI.print_colored(f"  ● KSPR I requests {len(tool_calls)} tool call(s)", TerminalTheme.WHITE)

                    # Add assistant message with tool calls to conversation
                    conversation_messages.append({"role": "assistant", "content": None, "tool_calls": tool_calls})

                    for idx, tc in enumerate(tool_calls, 1):
                        fn_name = tc.get("function", {}).get("name", "")
                        fn_args = tc.get("function", {}).get("arguments", {})
                        tc_id = tc.get("id", "")

                        t_start = time.time()
                        # Execute tool via MCP or plugin or capability
                        tool_result = None
                        if mcp_manager:
                            tool_result = asyncio.run(mcp_manager.execute_tool(fn_name, fn_args) if asyncio.iscoroutinefunction(mcp_manager.execute_tool) else _sync_execute(mcp_manager, fn_name, fn_args))
                        if tool_result is None and plugin_manager:
                            tool_result = plugin_manager.execute_tool(fn_name, fn_args)
                        if tool_result is None:
                            tool_result = f"Tool '{fn_name}' not found."
                        t_dur = (time.time() - t_start) * 1000

                        TerminalUI.print_tool_step(fn_name, fn_args, str(tool_result), t_dur)

                        conversation_messages.append({"role": "tool", "content": str(tool_result)[:2000], "tool_call_id": tc_id})

                    # Rebuild prompt with tool results
                    full_prompt = _build_messages_prompt(conversation_messages)
                    continue

                # No tool calls — final response
                final_response = response
                break

            tokens_used += len(final_response.encode()) // 3
            session_history.append({"role": "user", "content": prompt})
            session_history.append({"role": "assistant", "content": final_response})
            print_response_box(f"KSPR I ({active_provider}:{active_model})", final_response, latency=latency)
            if attached_files:
                print_colored(f"[*] Contexto activo: {list(attached_files.keys())}", Color.MID_GRAY)
        except ProviderError as e:
            msg = str(e)
            hint_lines = []
            if "API Key" in msg or "configura" in msg.lower() or "Configure" in msg:
                hint_lines = [
                    "No API Key detected for the active provider.",
                    "  → Run /login to authenticate with your license code.",
                    "  → Run /api to configure a provider and API Key.",
                    "  → Register at: https://kspr.membership.vercel.app/",
                ]
            elif "devolvió" in msg.lower() or "respondió" in msg.lower() or "returned" in msg.lower() or "no devolvió" in msg.lower():
                hint_lines = [
                    f"Model \"{active_model}\" did not return a valid response.",
                    "  → Run /model to switch to a different model.",
                    "  → Run /provider to check your active provider.",
                ]
            else:
                hint_lines = [
                    f"Provider \"{active_provider}\" returned an error.",
                    "  → Run /provider to switch providers.",
                    "  → Run /api to reconfigure your API Key.",
                ]
            print_colored(f"\n[!] Provider Error: {msg}", Color.WHITE)
            for line in hint_lines:
                print_colored(line, Color.LIGHT_GRAY)
        except Exception as e:
            print_colored(f"\n[!] Unexpected Error: {e}", Color.WHITE)
            print_colored("  → Run /provider to switch providers.", Color.LIGHT_GRAY)
            print_colored("  → Run /model to switch models.", Color.LIGHT_GRAY)
        
        print_dashboard(active_provider, active_model, current_workspace, len(attached_files), tokens_used, max_tokens)
        print()


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "update":
        run_update()
        return

    parser = argparse.ArgumentParser(prog="kspr", description="KSPR AI - Empresarial CLI Engine")
    parser.add_argument("-V", "--version", action="version", version=f"%(prog)s {__version__}", help="Muestra la versión y sale")
    parser.add_argument("source", type=Path, nargs="?", default=None, help="Ruta al directorio o ZIP a analizar (si se omite, abre el shell interactivo)")
    parser.add_argument("--interactive", "-i", action="store_true", help="Inicia el shell interactivo")
    parser.add_argument("--uninstall", action="store_true", help="Desinstala KSPR completamente del sistema")
    parser.add_argument("--git-url", default=None, help="Clona un repositorio Git en modo lectura para analizarlo")
    parser.add_argument("--output", type=Path, default=Path("kspr-context"), help="Directorio de salida para los artefactos Markdown")
    parser.add_argument("--project-name", default=None, help="Nombre del proyecto para el reporte")
    parser.add_argument("--provider", choices=["local", "gemini", "openai", "groq", "deepseek", "anthropic", "openrouter", "opencode-zen"], default="gemini", help="Proveedor de IA a utilizar")
    parser.add_argument("--model", default=None, help="Modelo de IA a utilizar (ej. gemini-2.5-flash)")
    args = parser.parse_args()

    if args.uninstall:
        import shutil
        kspr_dir = str(Path.home() / ".kspr")
        if os.path.exists(kspr_dir):
            shutil.rmtree(kspr_dir)
            print_colored("KSPR desinstalado completamente del sistema.", Color.WHITE)
            print_colored("Se ha eliminado: ~/.kspr/", Color.LIGHT_GRAY)
        else:
            print_colored("No hay una instalacion de KSPR encontrada en ~/.kspr/.", Color.LIGHT_GRAY)
        return

    if args.interactive or args.source is None:
        asyncio.run(interactive_shell())
    else:
        asyncio.run(
            run_batch_analysis(
                source=args.source,
                git_url=args.git_url,
                output=args.output,
                project_name=args.project_name,
                iterations=3,
                provider=args.provider,
                model=args.model,
            )
        )


if __name__ == "__main__":
    main()
