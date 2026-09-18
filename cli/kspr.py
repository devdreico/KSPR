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
from kspr_engine.models import AnalysisRequest, SourceFile
from kspr_engine.providers import get_provider, ProviderName, ProviderError

__version__ = "0.1.0"

CONFIG_DIR = Path.home() / ".kspr"
CONFIG_FILE = CONFIG_DIR / "config.json"
PROJECTS_FILE = CONFIG_DIR / "projects.json"


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


class Color:
    """High-contrast monochrome and grayscale ANSI color codes."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    UNDERLINE = "\033[4m"
    INVERSE = "\033[7m"
    
    WHITE = "\033[97m"         # Bright white for titles and primary focus
    LIGHT_GRAY = "\033[37m"    # Normal readable text
    MID_GRAY = "\033[90m"      # Borders, dividers, metadata
    DARK_CHARCOAL = "\033[2m"  # Dim background accents
    BLACK = "\033[30m"


KSPR_ASCII = [
    "░                             ",
    " ░░░░░░░░░░                              ",
    "░░░░░░░░░░   ░░  ░░ ░░░░░░ ░░░░░░  ░░░░░ ",
    "░   ░░   ░   ░░ ░░  ░░░░░  ░░   ░ ░░   ░░",
    "░░░░░░░░░░   ░░░░     ░░░░ ░░░░░░ ░░░░░░ ",
    "░░░░  ░░░░   ░░ ░░░ ░░░░░░ ░░░    ░░   ░░"
]

ALLOWED = {".py", ".js", ".jsx", ".ts", ".tsx", ".cs", ".java", ".sql", ".html", ".vue", ".php", ".md", ".txt", ".json", ".yaml", ".yml", ".pdf", ".csv", ".toml", ".ini", ".xml", ".db", ".sqlite"}


def print_colored(text: str, color: Color, bold: bool = False) -> None:
    prefix = Color.BOLD if bold else ""
    print(f"{color}{prefix}{text}{Color.RESET}")


def get_terminal_width() -> int:
    try:
        return os.get_terminal_size().columns
    except OSError:
        return 80


def print_box(title: str, lines: list[str], color: Color = Color.WHITE) -> None:
    width = min(max(len(title) + 4, max((len(l) for l in lines), default=40) + 4), get_terminal_width() - 2)
    horizontal = "─" * (width - 2)
    
    print()
    print_colored(f"┌─ {title} " + "─" * max(0, width - len(title) - 4) + "┐", color)
    for line in lines:
        padding = max(0, width - len(line) - 4)
        print_colored(f"│  {line}" + " " * padding + "│", Color.LIGHT_GRAY)
    print_colored(f"└{horizontal}┘", color)
    print()


def print_header() -> None:
    print()
    for line in KSPR_ASCII:
        print_colored(line, Color.WHITE, True)
    print()


def tokens_weight(tokens: int) -> str:
    if tokens >= 1000:
        return f"{tokens / 1000:.1f}k"
    return str(tokens)


def print_dashboard(provider: str, model: str, iterations: int, workspace: Path, attached_count: int, tokens_used: int, max_tokens: int) -> None:
    width = min(get_terminal_width() - 2, 86)
    horizontal = "─" * (width - 2)
    
    pct = int((tokens_used / max_tokens) * 100) if max_tokens > 0 else 0
    filled = int((pct / 100) * 16)
    bar = "█" * filled + "░" * (16 - filled)
    
    workspace_str = str(workspace)
    if len(workspace_str) > 34:
        workspace_str = "..." + workspace_str[-31:]

    print()
    print_colored(f"┌{horizontal}┐", Color.MID_GRAY)
    print_colored(f"│ {Color.WHITE}{Color.BOLD}KSPR CLI v0.1.0{Color.RESET} │ {Color.LIGHT_GRAY}Provider:{Color.RESET} {provider:<8} │ {Color.LIGHT_GRAY}Model:{Color.RESET} {model:<16} │ {Color.LIGHT_GRAY}Iter:{Color.RESET} {iterations} │", Color.MID_GRAY)
    print_colored(f"│ {Color.LIGHT_GRAY}Agent:{Color.RESET} KSPR I     │ {Color.LIGHT_GRAY}Workdir:{Color.RESET} 📁 {workspace_str:<29} │ {Color.LIGHT_GRAY}Files:{Color.RESET} {attached_count:<2} │", Color.MID_GRAY)
    print_colored(f"│ {Color.LIGHT_GRAY}Context:{Color.RESET} [{bar}] {tokens_weight(tokens_used)}/{tokens_weight(max_tokens)} ({pct}%)" + " " * max(0, width - 48 - len(tokens_weight(tokens_used)) - len(tokens_weight(max_tokens))) + " │", Color.MID_GRAY)
    print_colored(f"└{horizontal}┘", Color.MID_GRAY)
    print()


async def animate_spinner(task_coro, message: str) -> tuple[Any, float]:
    spinners = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    idx = 0
    start_time = time.time()
    
    task = asyncio.create_task(task_coro)
    
    sys.stdout.write("\033[?25l")
    try:
        while not task.done():
            elapsed = time.time() - start_time
            sys.stdout.write(f"\r{Color.WHITE}{spinners[idx]} {message} {Color.MID_GRAY}[ {elapsed:.1f}s ]{Color.RESET}")
            sys.stdout.flush()
            idx = (idx + 1) % len(spinners)
            await asyncio.sleep(0.08)
        sys.stdout.write("\r\033[K")
        elapsed = time.time() - start_time
        return await task, elapsed
    finally:
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()


def print_response_box(title: str, text: str | list[str], latency: float = 0.0) -> None:
    if isinstance(text, list):
        lines = text
    else:
        lines = text.splitlines()
        if not lines:
            lines = [text]
    width = min(max(len(title) + 12, max((len(l) for l in lines), default=40) + 4), get_terminal_width() - 2)
    horizontal = "─" * (width - 2)
    
    lat_str = f" [ {latency:.2f}s ]" if latency > 0 else ""
    header_title = f"{title}{lat_str}"
    
    print()
    print_colored(f"┌─ {header_title} " + "─" * max(0, width - len(header_title) - 3) + "┐", Color.WHITE)
    for line in lines:
        while len(line) > width - 4:
            chunk = line[:width - 4]
            line = line[width - 4:]
            print_colored(f"│  {chunk}  │", Color.LIGHT_GRAY)
        padding = max(0, width - len(line) - 4)
        print_colored(f"│  {line}" + " " * padding + "│", Color.LIGHT_GRAY)
    print_colored(f"└{horizontal}┘", Color.WHITE)
    print()


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
    active_iterations = config.get("active_iterations", 3)
    attached_files: dict[str, str] = {}
    indexed_models: dict[str, list[dict[str, Any]]] = config.get("indexed_models", {})
    tokens_used = 1250
    max_tokens = 128000

    def persist_state() -> None:
        cfg = load_local_config()
        cfg["active_model"] = active_model
        cfg["active_provider"] = active_provider
        cfg["active_iterations"] = active_iterations
        cfg["indexed_models"] = indexed_models
        cfg["current_workspace"] = str(current_workspace)
        save_local_config(cfg)

    print_dashboard(active_provider, active_model, active_iterations, current_workspace, len(attached_files), tokens_used, max_tokens)
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
                    "/help              - Muestra esta ayuda de comandos",
                    "/login             - Activa tu licencia con tu código único para desbloquear /api",
                    "/api               - Configura proveedores, API Keys e indexa modelos",
                    "/project           - Gestión de proyectos locales (New project / Anteriores)",
                    "/model [name/num]  - Muestra o selecciona un modelo indexado",
                    "/analyze [path]    - Ejecuta el análisis estático",
                    "/provider [name]   - Cambia el proveedor activo",
                    "/iterations [n]    - Cambia iteraciones de análisis (1-8)",
                    "/context           - Muestra los archivos en contexto",
                    "/clear             - Limpia la pantalla y redibuja el dashboard",
                    "/update            - Actualiza KSPR a la última versión",
                    "/exit              - Sale de la sesión interactiva",
                ], Color.WHITE)
            elif cmd == "/clear":
                os.system("cls" if os.name == "nt" else "clear")
                print_header()
                print_dashboard(active_provider, active_model, active_iterations, current_workspace, len(attached_files), tokens_used, max_tokens)
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
                print_dashboard(active_provider, active_model, active_iterations, current_workspace, len(attached_files), tokens_used, max_tokens)
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
                print_dashboard(active_provider, active_model, active_iterations, current_workspace, len(attached_files), tokens_used, max_tokens)
            elif cmd == "/provider":
                if arg in {"gemini", "local", "openai", "groq", "deepseek"}:
                    active_provider = arg
                    print_colored(f"[✓] Proveedor activo actualizado a: {active_provider}", Color.WHITE)
                    persist_state()
                else:
                    print_colored(f"[!] Proveedor activo actual: {active_provider} (opciones: gemini, local, openai, groq, deepseek)", Color.LIGHT_GRAY)
                print_dashboard(active_provider, active_model, active_iterations, current_workspace, len(attached_files), tokens_used, max_tokens)
            elif cmd == "/iterations":
                if arg.isdigit() and 1 <= int(arg) <= 8:
                    active_iterations = int(arg)
                    print_colored(f"[✓] Iteraciones activas actualizadas a: {active_iterations}", Color.WHITE)
                    persist_state()
                else:
                    print_colored(f"[*] Iteraciones activas actuales: {active_iterations} (rango 1-8)", Color.LIGHT_GRAY)
                print_dashboard(active_provider, active_model, active_iterations, current_workspace, len(attached_files), tokens_used, max_tokens)
            elif cmd == "/context":
                lines = [f"Workspace: {current_workspace}", f"Archivos adjuntos ({len(attached_files)}):"]
                for path in attached_files:
                    lines.append(f" - @{path}")
                print_box("Active Context", lines, Color.WHITE)
            elif cmd == "/api":
                cfg = load_local_config()
                if not cfg.get("unlocked", False):
                    print_box("🔒 KSPR Security Lock", [
                        "Acceso restringido: Se requiere un código único de acceso.",
                        "Por favor ejecuta el comando /login e introduce tu código para desbloquear /api."
                    ], Color.WHITE)
                    print()
                    continue
                providers_list = ["gemini", "openai", "groq", "deepseek", "local"]
                print_box("API & Provider Configuration", [
                    "Selecciona el proveedor para configurar su API Key e indexar modelos:",
                    " 1. gemini   (Google Generative AI)",
                    " 2. openai   (OpenAI GPT-4 / GPT-3.5)",
                    " 3. groq     (Groq Llama / Mixtral)",
                    " 4. deepseek (Deepseek Chat / Reasoner)",
                    " 5. local    (Modo local sin API Key)"
                ], Color.WHITE)
                
                prov_choice = arg.strip().lower() if arg else input(f"{Color.WHITE}Elige proveedor (1-5 o nombre): {Color.RESET}").strip().lower()
                
                selected_prov = active_provider
                if prov_choice in {"1", "gemini"}:
                    selected_prov = "gemini"
                elif prov_choice in {"2", "openai"}:
                    selected_prov = "openai"
                elif prov_choice in {"3", "groq"}:
                    selected_prov = "groq"
                elif prov_choice in {"4", "deepseek"}:
                    selected_prov = "deepseek"
                elif prov_choice in {"5", "local"}:
                    selected_prov = "local"
                elif prov_choice in providers_list:
                    selected_prov = prov_choice
                
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
                print_dashboard(active_provider, active_model, active_iterations, current_workspace, len(attached_files), tokens_used, max_tokens)
            elif cmd == "/analyze":
                target_path = Path(arg) if arg else current_workspace
                print_colored(f"[*] Iniciando análisis estático sobre {target_path}...", Color.LIGHT_GRAY)
                await run_batch_analysis(
                    target_path, None, target_path.parent / "kspr-context", None, active_iterations, active_provider, active_model
                )
            else:
                print_colored(f"[!] Comando desconocido: {cmd}. Escribe /help para ver los comandos.", Color.MID_GRAY)
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

        # Call the provider with animated spinner & latency tracking
        try:
            settings = Settings()
            provider_instance = get_provider(ProviderName(active_provider.lower()), settings, api_key=getattr(settings, f'{active_provider.lower()}_api_key', None))
            
            async def call_llm():
                return await provider_instance.complete(full_prompt, active_model, effort=None if active_iterations < 3 else "high")

            (response, latency) = await animate_spinner(call_llm(), f"KSPR I procesando con {active_provider}:{active_model}...")
            
            tokens_used += len(response.encode()) // 3
            print_response_box(f"KSPR I ({active_provider}:{active_model})", response, latency=latency)
            if attached_files:
                print_colored(f"[*] Contexto activo: {list(attached_files.keys())}", Color.MID_GRAY)
        except ProviderError as e:
            msg = str(e)
            if "API Key" in msg or "configura" in msg.lower():
                msg = 'para usar KSPR AI con tus modelos frontier y sacar su maximo provecho inicia sesion con /login-> (pide codigo) o registrate en "https://kspr.membership.vercel.app/"'
            print_colored(f"\n[!] Error de proveedor: {msg}", Color.WHITE)
            print_colored("[*] Intentando fallback con modo local...", Color.LIGHT_GRAY)
            local_provider = get_provider(ProviderName.local, settings)
            response, latency = await animate_spinner(local_provider.complete(prompt, 'kspr-local'), "KSPR I (Fallback Local)...")
            print_response_box(f"KSPR I (Fallback Local)", response, latency=latency)
        except Exception as e:
            print_colored(f"\n[!] Error inesperado: {e}", Color.WHITE)
            print_response_box(f"KSPR I (Fallback)", [
                "KSPR I está funcionando en modo local de demostración.",
                "Conecta un proveedor válido para obtener razonamiento LLM completo."
            ])
        
        print_dashboard(active_provider, active_model, active_iterations, current_workspace, len(attached_files), tokens_used, max_tokens)
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
    parser.add_argument("--iterations", type=int, default=3, choices=range(1, 9), help="Número de iteraciones de análisis (1-8)")
    parser.add_argument("--provider", choices=["local", "gemini", "openai", "groq", "deepseek"], default="gemini", help="Proveedor de IA a utilizar")
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
                iterations=args.iterations,
                provider=args.provider,
                model=args.model,
            )
        )


if __name__ == "__main__":
    main()
