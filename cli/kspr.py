"""KSPR CLI: Professional Interactive Terminal Agent for Static Analysis."""

from __future__ import annotations

import argparse
import asyncio
import os
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from kspr_engine.analyzer import analyze
from kspr_engine.config import Settings
from kspr_engine.models import AnalysisRequest, SourceFile
from kspr_engine.providers import get_provider, ProviderName, ProviderError

__version__ = "0.1.0"

class Color:
    """ANSI color codes for terminal styling."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    UNDERLINE = "\033[4m"
    
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"

KSPR_ASCII = [
    "▒▒▒▒▒▒▒▒▒▒▒▒ ▒▒ ▒▒ ▒▒▒▒▒▒▒▒▒ ▒▒▒▒▒  ",
    "▒   ▒   ▒  ▒▒▒  ▒▒▒  ▒   ▒▒   ▒▒",
    "▒▒▒▒▒▒▒▒▒  ▒▒ ▒   ▒▒ ▒▒▒▒▒▒▒▒▒▒  ",
    "▒▒▒   ▒▒▒  ▒▒  ▒▒▒▒▒ ▒▒   ▒▒  ▒▒",
    " ▒▒▒ ▒ ▒▒▒ ▒▒▒ ▒▒▒  ▒▒▒ ▒ ▒▒▒▒  ",
    "  ▒▒▒ ▒  █ █  █ █ █  █ █  █ █ █  ",
    "   █ █   █ █ █ █ █ █  █ █  █ █ █  ",
    "    █    █ █  █ █  █  █ █  █ █  █",
    "     █    █ █  █ █ █  █  █  █ █"
]

ALLOWED = {".py", ".js", ".jsx", ".ts", ".tsx", ".cs", ".java", ".sql", ".html", ".vue", ".php", ".md", ".txt", ".json", ".yaml", ".yml"}


def print_colored(text: str, color: Color, bold: bool = False) -> None:
    prefix = Color.BOLD if bold else ""
    print(f"{color}{prefix}{text}{Color.RESET}")


def get_terminal_width() -> int:
    try:
        return os.get_terminal_size().columns
    except OSError:
        return 80


def print_box(title: str, lines: list[str], color: Color = Color.BRIGHT_GREEN) -> None:
    width = min(max(len(title) + 4, max((len(l) for l in lines), default=40) + 4), get_terminal_width() - 2)
    horizontal = "─" * (width - 2)
    
    print_colored(f"┌─ {title} " + "─" * max(0, width - len(title) - 4) + "┐", color)
    for line in lines:
        # Pad line to fit box
        padding = max(0, width - len(line) - 4)
        print_colored(f"│  {line}" + " " * padding + "│", color)
    print_colored(f"└{horizontal}┘", color)


def print_header() -> None:
    for line in KSPR_ASCII:
        print_colored(line, Color.BRIGHT_GREEN, True)
    print()


def print_dashboard(provider: str, model: str, agent: str, iterations: int, workspace: Path, attached_count: int) -> None:
    width = min(get_terminal_width() - 2, 82)
    horizontal = "─" * (width - 2)
    
    print_colored(f"┌{horizontal}┐", Color.CYAN)
    print_colored(f"│ {Color.BOLD}KSPR CLI v0.1.0{Color.RESET} │ {Color.YELLOW}Provider:{Color.RESET} {provider:<10} │ {Color.YELLOW}Model:{Color.RESET} {model:<18} │ {Color.YELLOW}Iter:{Color.RESET} {iterations} │", Color.CYAN)
    print_colored(f"│ {Color.YELLOW}Agent:{Color.RESET} {agent:<10} │ {Color.YELLOW}Workspace:{Color.RESET} {str(workspace):<36} │ {Color.YELLOW}Files:{Color.RESET} {attached_count:<3} │", Color.CYAN)
    print_colored(f"└{horizontal}┘", Color.CYAN)


async def animate_spinner(task_coro, message: str) -> Any:
    spinners = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    idx = 0
    
    task = asyncio.create_task(task_coro)
    
    sys.stdout.write("\033[?25l") # Hide cursor
    try:
        while not task.done():
            sys.stdout.write(f"\r{Color.BRIGHT_CYAN}{spinners[idx]} {message}{Color.RESET}")
            sys.stdout.flush()
            idx = (idx + 1) % len(spinners)
            await asyncio.sleep(0.08)
        sys.stdout.write("\r\033[K") # Clear line
        return await task
    finally:
        sys.stdout.write("\033[?25h") # Show cursor
        sys.stdout.flush()


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


# ---- Batch Analysis ----

async def run_batch_analysis(source: Path, git_url: str | None, output: Path, project_name: str | None, iterations: int, provider: str, model: str | None) -> None:
    if git_url:
        print_colored(f"[*] Clonando repositorio Git de forma segura: {git_url}", Color.CYAN)
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
        print_colored(f"[*] Analizando fuente local: {source}", Color.CYAN)
        files = collect_source(source)
        default_name = source.stem

    if not files:
        raise SystemExit("Error: No se encontraron archivos soportados en la fuente.")

    print_colored(f"[*] Archivos recolectados: {len(files)}. Ejecutando KSPR Engine ({iterations} iteraciones)...", Color.YELLOW)
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
    ], Color.BRIGHT_GREEN)


# ---- Interactive Shell ----

async def interactive_shell() -> None:
    print_header()
    
    current_workspace = Path.cwd()
    active_model = "gemini-2.5-flash"
    active_provider = "gemini"
    active_agent = "Architect"
    active_iterations = 3
    attached_files: dict[str, str] = {}

    print_dashboard(active_provider, active_model, active_agent, active_iterations, current_workspace, len(attached_files))
    print()

    while True:
        try:
            prompt = input(f"{Color.BRIGHT_CYAN}┌─[{active_agent.lower()}@{active_provider}] \n└─> {Color.RESET}").strip()
        except (KeyboardInterrupt, EOFError):
            print_colored("\n¡Hasta luego!", Color.MAGENTA)
            break

        if not prompt:
            continue

        if prompt.startswith("/"):
            parts = prompt.split(maxsplit=1)
            cmd = parts[0].lower()
            arg = parts[1] if len(parts) > 1 else ""

            if cmd in {"/exit", "/quit"}:
                print_colored("Saliendo de la sesión de KSPR CLI.", Color.MAGENTA)
                break
            elif cmd == "/help":
                print_box("KSPR CLI Commands", [
                    "/help              - Muestra esta ayuda de comandos",
                    "/analyze [path]    - Ejecuta el análisis estático",
                    "/model [name]      - Cambia o muestra el modelo activo",
                    "/provider [name]   - Cambia el proveedor (gemini/local/openai/groq/deepseek)",
                    "/agent [name]      - Establece el rol del agente (Architect, Developer, Auditor)",
                    "/iterations [n]    - Cambia iteraciones de análisis (1-8)",
                    "/context           - Muestra los archivos en contexto",
                    "/clear             - Limpia la pantalla y redibuja el dashboard",
                    "/exit              - Sale de la sesión interactiva",
                    "Ctrl+K             - Panel de configuración rápida (o /ctrlk)"
                ], Color.BRIGHT_BLUE)
            elif cmd == "/clear":
                os.system("cls" if os.name == "nt" else "clear")
                print_header()
                print_dashboard(active_provider, active_model, active_agent, active_iterations, current_workspace, len(attached_files))
                print()
            elif cmd == "/model":
                if arg:
                    active_model = arg
                    print_colored(f"[✓] Modelo activo actualizado a: {active_model}", Color.GREEN)
                else:
                    print_colored(f"[*] Modelo activo actual: {active_model}", Color.CYAN)
                print_dashboard(active_provider, active_model, active_agent, active_iterations, current_workspace, len(attached_files))
            elif cmd == "/provider":
                if arg in {"gemini", "local", "openai", "groq", "deepseek"}:
                    active_provider = arg
                    print_colored(f"[✓] Proveedor activo actualizado a: {active_provider}", Color.GREEN)
                else:
                    print_colored(f"[!] Proveedor activo actual: {active_provider} (opciones: gemini, local, openai, groq, deepseek)", Color.YELLOW)
                print_dashboard(active_provider, active_model, active_agent, active_iterations, current_workspace, len(attached_files))
            elif cmd == "/agent":
                if arg:
                    active_agent = arg
                    print_colored(f"[✓] Agente activo actualizado a: {active_agent}", Color.GREEN)
                else:
                    print_colored(f"[*] Agente activo actual: {active_agent}", Color.CYAN)
                print_dashboard(active_provider, active_model, active_agent, active_iterations, current_workspace, len(attached_files))
            elif cmd == "/iterations":
                if arg.isdigit() and 1 <= int(arg) <= 8:
                    active_iterations = int(arg)
                    print_colored(f"[✓] Iteraciones activas actualizadas a: {active_iterations}", Color.GREEN)
                else:
                    print_colored(f"[*] Iteraciones activas actuales: {active_iterations} (rango 1-8)", Color.YELLOW)
                print_dashboard(active_provider, active_model, active_agent, active_iterations, current_workspace, len(attached_files))
            elif cmd == "/context":
                lines = [f"Workspace: {current_workspace}", f"Archivos adjuntos ({len(attached_files)}):"]
                for path in attached_files:
                    lines.append(f" - @{path}")
                print_box("Active Context", lines, Color.BRIGHT_CYAN)
            elif cmd == "/analyze":
                target_path = Path(arg) if arg else current_workspace
                print_colored(f"[*] Iniciando análisis estático sobre {target_path}...", Color.YELLOW)
                await run_batch_analysis(
                    target_path, None, target_path.parent / "kspr-context", None, active_iterations, active_provider, active_model
                )
            elif cmd == "/ctrlk" or cmd == "ctrl+k":
                print_box("Panel de Configuración Rápida (Ctrl+K)", [
                    f"1. Cambiar proveedor   [ Actual: {active_provider} ]",
                    f"2. Cambiar modelo      [ Actual: {active_model} ]",
                    f"3. Cambiar esfuerzo    [ Actual: {active_iterations} iteraciones ]",
                    f"4. Cambiar agente      [ Actual: {active_agent} ]",
                    "5. Salir del panel"
                ], Color.BRIGHT_MAGENTA)
                choice = input(f"{Color.BRIGHT_MAGENTA}Selecciona opción (1-5): {Color.RESET}").strip()
                
                if choice == "1":
                    p = input("Nuevo proveedor (gemini, local, openai, groq, deepseek): ").strip().lower()
                    if p in {"gemini", "local", "openai", "groq", "deepseek"}:
                        active_provider = p
                        print_colored(f"[✓] Proveedor cambiado a: {p}", Color.GREEN)
                elif choice == "2":
                    m = input("Nuevo modelo: ").strip()
                    if m:
                        active_model = m
                        print_colored(f"[✓] Modelo cambiado a: {m}", Color.GREEN)
                elif choice == "3":
                    it = input("Iteraciones (1-8): ").strip()
                    if it.isdigit() and 1 <= int(it) <= 8:
                        active_iterations = int(it)
                        print_colored(f"[✓] Iteraciones cambiadas a: {it}", Color.GREEN)
                elif choice == "4":
                    ag = input("Agente (Architect, Developer, Auditor): ").strip()
                    if ag:
                        active_agent = ag
                        print_colored(f"[✓] Agente cambiado a: {ag}", Color.GREEN)
                print_dashboard(active_provider, active_model, active_agent, active_iterations, current_workspace, len(attached_files))
            else:
                print_colored(f"[!] Comando desconocido: {cmd}. Escribe /help para ver los comandos.", Color.YELLOW)
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
                        print_colored(f"[+] Archivo adjuntado al contexto: @{filepath}", Color.GREEN)
                    except Exception as e:
                        print_colored(f"[!] No se pudo leer {filepath}: {e}", Color.YELLOW)
                else:
                    print_colored(f"[!] Archivo no encontrado: {filepath}", Color.YELLOW)

        # Call the provider with animated spinner
        try:
            settings = Settings()
            provider_instance = get_provider(ProviderName(active_provider.lower()), settings, api_key=getattr(settings, f'{active_provider.lower()}_api_key', None))
            
            async def call_llm():
                full_prompt = referenced_content + "\n\n" + prompt if referenced_content else prompt
                return await provider_instance.complete(full_prompt, active_model, effort=None if active_iterations < 3 else "high")

            response = await animate_spinner(call_llm(), f"KSPR I ({active_agent}) procesando con {active_provider}:{active_model}...")
            
            # Print response in decorated box
            response_lines = response.splitlines()
            print_box(f"KSPR I · {active_agent} ({active_provider}:{active_model})", response_lines if response_lines else [response], Color.BRIGHT_CYAN)
            if attached_files:
                print_colored(f"[*] Contexto activo: {list(attached_files.keys())}", Color.DIM)
        except ProviderError as e:
            print_colored(f"\n[!] Error de proveedor: {e}", Color.RED)
            print_colored("[*] Intentando fallback con modo local...", Color.YELLOW)
            local_provider = get_provider(ProviderName.local, settings)
            response = await local_provider.complete(prompt, 'kspr-local')
            print_box(f"KSPR I · {active_agent} (Fallback Local)", response.splitlines(), Color.YELLOW)
        except Exception as e:
            print_colored(f"\n[!] Error inesperado: {e}", Color.RED)
            print_box(f"KSPR I · {active_agent} (Fallback)", [
                "KSPR I está funcionando en modo local de demostración.",
                "Conecta un proveedor válido para obtener razonamiento LLM completo."
            ], Color.YELLOW)
        
        print()


def main() -> None:
    parser = argparse.ArgumentParser(prog="kspr", description="KSPR AI - Empresarial CLI Engine")
    parser.add_argument("-V", "--version", action="version", version=f"%(prog)s {__version__}", help="Muestra la versión y sale")
    parser.add_argument("source", type=Path, nargs="?", default=None, help="Ruta al directorio o ZIP a analizar (si se omite, abre el shell interactivo)")
    parser.add_argument("--interactive", "-i", action="store_true", help="Inicia el shell interactivo")
    parser.add_argument("--git-url", default=None, help="Clona un repositorio Git en modo lectura para analizarlo")
    parser.add_argument("--output", type=Path, default=Path("kspr-context"), help="Directorio de salida para los artefactos Markdown")
    parser.add_argument("--project-name", default=None, help="Nombre del proyecto para el reporte")
    parser.add_argument("--iterations", type=int, default=3, choices=range(1, 9), help="Número de iteraciones de análisis (1-8)")
    parser.add_argument("--provider", choices=["local", "gemini", "openai", "groq", "deepseek"], default="gemini", help="Proveedor de IA a utilizar")
    parser.add_argument("--model", default=None, help="Modelo de IA a utilizar (ej. gemini-2.5-flash)")
    args = parser.parse_args()

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
