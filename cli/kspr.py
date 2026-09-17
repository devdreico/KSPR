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
    "▒▒▒▒▒▒▒▒▒▒ ▒▒ ▒▒ ▒▒▒▒▒▒▒▒▒ ▒▒▒▒ ",
    "▒   ▒   ▒  ▒▒▒  ▒▒▒  ▒   ▒▒   ▒▒",
    "▒▒▒▒▒▒▒▒▒  ▒▒ ▒   ▒▒ ▒▒▒▒▒▒▒▒▒▒ ",
    "▒▒▒   ▒▒▒  ▒▒  ▒▒▒▒▒ ▒▒   ▒▒  ▒▒ "
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
    
    sys.stdout.write("\033[?25l")
    try:
        while not task.done():
            sys.stdout.write(f"\r{Color.BRIGHT_CYAN}{spinners[idx]} {message}{Color.RESET}")
            sys.stdout.flush()
            idx = (idx + 1) % len(spinners)
            await asyncio.sleep(0.08)
        sys.stdout.write("\r\033[K")
        return await task
    finally:
        sys.stdout.write("\033[?25h")
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


def run_update() -> None:
    print_colored("[*] Actualizando KSPR AI a la última versión...", Color.CYAN)
    cmd = "curl -sSL https://raw.githubusercontent.com/devdreiortiz/KSPR/main/bin/install.sh | bash"
    try:
        subprocess.run(cmd, shell=True, check=True)
        print_colored("[✓] ¡KSPR se ha actualizado exitosamente!", Color.BRIGHT_GREEN)
    except Exception as e:
        print_colored(f"[!] Error al actualizar: {e}", Color.RED)


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
    indexed_models: dict[str, list[dict[str, Any]]] = {}

    print_dashboard(active_provider, active_model, active_agent, active_iterations, current_workspace, len(attached_files))
    print()

    while True:
        try:
            prompt = input(f"{Color.BRIGHT_CYAN}┌─[{active_agent.lower()}@{active_provider}:{active_model}] \n└─> {Color.RESET}").strip()
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
                    "/api               - Configura proveedores, API Keys e indexa modelos disponibles",
                    "/model [name/num]  - Muestra, busca o selecciona un modelo indexado",
                    "/analyze [path]    - Ejecuta el análisis estático",
                    "/provider [name]   - Cambia el proveedor activo",
                    "/agent [name]      - Establece el rol del agente (Architect, Developer, Auditor)",
                    "/iterations [n]    - Cambia iteraciones de análisis (1-8)",
                    "/context           - Muestra los archivos en contexto",
                    "/clear             - Limpia la pantalla y redibuja el dashboard",
                    "/update            - Actualiza KSPR a la última versión",
                    "/exit              - Sale de la sesión interactiva"
                ], Color.BRIGHT_BLUE)
            elif cmd == "/clear":
                os.system("cls" if os.name == "nt" else "clear")
                print_header()
                print_dashboard(active_provider, active_model, active_agent, active_iterations, current_workspace, len(attached_files))
                print()
            elif cmd == "/update":
                run_update()
            elif cmd == "/model":
                if arg:
                    # Check if arg is a number selecting from indexed models
                    if active_provider in indexed_models and arg.isdigit():
                        idx = int(arg) - 1
                        models = indexed_models[active_provider]
                        if 0 <= idx < len(models):
                            active_model = models[idx].get("id")
                            print_colored(f"[✓] Modelo activo actualizado a: {active_model}", Color.GREEN)
                        else:
                            print_colored("[!] Índice de modelo fuera de rango.", Color.RED)
                    else:
                        active_model = arg
                        print_colored(f"[✓] Modelo activo actualizado a: {active_model}", Color.GREEN)
                elif active_provider in indexed_models and indexed_models[active_provider]:
                    models = indexed_models[active_provider]
                    print_box(f"Modelos Disponibles ({active_provider})", [f" {idx+1}. {m.get('id')} ({m.get('name', '')})" for idx, m in enumerate(models)], Color.BRIGHT_CYAN)
                    m_choice = input(f"{Color.BRIGHT_CYAN}Elige número de modelo o escribe nombre: {Color.RESET}").strip()
                    if m_choice.isdigit() and 1 <= int(m_choice) <= len(models):
                        active_model = models[int(m_choice)-1].get("id")
                        print_colored(f"[✓] Modelo activo actualizado a: {active_model}", Color.GREEN)
                    elif m_choice:
                        active_model = m_choice
                        print_colored(f"[✓] Modelo activo actualizado a: {active_model}", Color.GREEN)
                else:
                    print_colored(f"[*] Modelo activo actual: {active_model}", Color.CYAN)
                    print_colored("[*] Consejo: Ejecuta /api para indexar automáticamente los modelos de tu proveedor.", Color.YELLOW)
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
            elif cmd == "/api":
                providers_list = ["gemini", "openai", "groq", "deepseek", "local"]
                print_box("API & Provider Configuration", [
                    "Selecciona el proveedor para configurar su API Key e indexar modelos:",
                    " 1. gemini   (Google Generative AI)",
                    " 2. openai   (OpenAI GPT-4 / GPT-3.5)",
                    " 3. groq     (Groq Llama / Mixtral)",
                    " 4. deepseek (Deepseek Chat / Reasoner)",
                    " 5. local    (Modo local sin API Key)"
                ], Color.BRIGHT_MAGENTA)
                
                prov_choice = arg.strip().lower() if arg else input(f"{Color.BRIGHT_MAGENTA}Elige proveedor (1-5 o nombre): {Color.RESET}").strip().lower()
                
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
                    print_colored("[✓] El proveedor local no requiere API Key.", Color.GREEN)
                    active_provider = selected_prov
                    indexed_models[selected_prov] = [{"id": "kspr-local", "name": "KSPR Local Demo"}]
                else:
                    env_key = f"KSPR_{selected_prov.upper()}_API_KEY"
                    current_key = os.getenv(env_key, "")
                    masked = (current_key[:6] + "..." + current_key[-4:]) if len(current_key) > 10 else ("Configurada" if current_key else "No configurada")
                    
                    print_colored(f"[*] Proveedor seleccionado: {selected_prov}", Color.CYAN)
                    print_colored(f"[*] Estado actual API Key: {masked}", Color.YELLOW)
                    
                    new_key = input(f"{Color.BRIGHT_CYAN}Introduce la API Key para {selected_prov}: {Color.RESET}").strip()
                    if new_key:
                        os.environ[env_key] = new_key
                        if selected_prov == "gemini":
                            os.environ["GEMINI_API_KEY"] = new_key
                        print_colored(f"[✓] API Key para '{selected_prov}' guardada y aplicada exitosamente.", Color.GREEN)
                        active_provider = selected_prov
                        
                        # Automatically index models
                        try:
                            settings = Settings()
                            temp_prov = get_provider(ProviderName(selected_prov), settings, api_key=new_key)
                            print_colored(f"[*] Indexando modelos disponibles desde la API de {selected_prov}...", Color.YELLOW)
                            models = await animate_spinner(temp_prov.list_models(), f"Consultando modelos de {selected_prov}...")
                            if models:
                                indexed_models[selected_prov] = models
                                model_lines = [f" {idx+1}. {m.get('id')} ({m.get('name', '')})" for idx, m in enumerate(models[:20])]
                                print_box(f"Modelos Indexados ({selected_prov}) - Total: {len(models)}", model_lines, Color.BRIGHT_GREEN)
                                active_model = models[0].get("id")
                                print_colored(f"[✓] Modelo predeterminado establecido a: {active_model}", Color.GREEN)
                            else:
                                print_colored("[!] No se encontraron modelos en la respuesta de la API.", Color.YELLOW)
                        except Exception as ex:
                            print_colored(f"[!] No se pudieron indexar modelos automáticamente: {ex}", Color.RED)
                            print_colored("[*] Puedes configurar el modelo manualmente usando /model <nombre>", Color.YELLOW)
                    else:
                        print_colored("[!] API Key no modificada (vacía).", Color.YELLOW)
                print_dashboard(active_provider, active_model, active_agent, active_iterations, current_workspace, len(attached_files))
            elif cmd == "/analyze":
                target_path = Path(arg) if arg else current_workspace
                print_colored(f"[*] Iniciando análisis estático sobre {target_path}...", Color.YELLOW)
                await run_batch_analysis(
                    target_path, None, target_path.parent / "kspr-context", None, active_iterations, active_provider, active_model
                )
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
    if len(sys.argv) > 1 and sys.argv[1] == "update":
        run_update()
        return

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
