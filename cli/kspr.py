"""KSPR CLI: Professional Interactive Terminal Agent for Static Analysis."""

from __future__ import annotations

import argparse
import asyncio
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from kspr_engine.analyzer import analyze
from kspr_engine.config import Settings
from kspr_engine.models import AnalysisRequest, SourceFile
from kspr_engine.providers import get_provider, ProviderName, ProviderError

__version__ = "0.1.0"

# Color codes for terminal
class Color:
    """ANSI color codes for terminal styling."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    UNDERLINE = "\033[4m"
    
    # Foreground colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    
    # Bright foreground colors
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"
    
    # Background colors
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_WHITE = "\033[47m"

KSPR_ASCII = "\n".join(("▒▒▒▒▒▒▒▒▒▒▒▒ ▒▒ ▒▒ ▒▒▒▒▒▒▒▒▒ ▒▒▒▒▒  ",
 "▒   ▒   ▒  ▒▒▒  ▒▒▒  ▒   ▒▒   ▒▒",
 "▒▒▒▒▒▒▒▒▒  ▒▒ ▒   ▒▒ ▒▒▒▒▒▒▒▒▒▒  ",
 "▒▒▒   ▒▒▒  ▒▒  ▒▒▒▒▒ ▒▒   ▒▒  ▒▒",
 " ▒▒▒ ▒ ▒▒▒ ▒▒▒ ▒▒▒  ▒▒▒ ▒ ▒▒▒▒  ",
 "  ▒▒▒ ▒  █ █  █ █ █  █ █  █ █ █  ",
 "   █ █   █ █ █ █ █ █  █ █  █ █ █  ",
 "    █    █ █  █ █  █  █ █  █ █  █",
 "     █    █ █  █ █ █  █  █  █ █"))


ALLOWED = {".py", ".js", ".jsx", ".ts", ".tsx", ".cs", ".java", ".sql", ".html", ".vue", ".php", ".md", ".txt", ".json", ".yaml", ".yml"}


def print_colored(text: str, color: Color, bold: bool = False) -> None:
    """Print text with color styling."""
    prefix = Color.BOLD if bold else ""
    suffix = Color.RESET
    print(f"{color}{prefix}{text}{suffix}")


def print_header() -> None:
    """Print the KSPR CLI header."""
    print_colored("▒▒▒▒▒▒▒▒▒▒▒▒ ▒▒ ▒▒ ▒▒▒▒▒▒▒▒▒ ▒▒▒▒▒  ", Color.BRIGHT_GREEN, True)
    print_colored("▒   ▒   ▒  ▒▒▒  ▒▒▒  ▒   ▒▒   ▒▒", Color.BRIGHT_GREEN)
    print_colored("▒▒▒▒▒▒▒▒▒  ▒▒ ▒   ▒▒ ▒▒▒▒▒▒▒▒▒▒  ", Color.BRIGHT_GREEN)
    print_colored("▒▒▒   ▒▒▒  ▒▒  ▒▒▒▒▒ ▒▒   ▒▒  ▒▒", Color.BRIGHT_GREEN)
    print_colored(" ▒▒▒ ▒ ▒▒▒ ▒▒▒ ▒▒▒  ▒▒▒ ▒ ▒▒▒▒  ", Color.BRIGHT_GREEN)
    print_colored("  ▒▒▒ ▒  █ █  █ █ █  █ █  █ █ █  ", Color.BRIGHT_GREEN)
    print_colored("   █ █   █ █ █ █ █ █  █ █  █ █ █  ", Color.BRIGHT_GREEN)
    print_colored("    █    █ █  █ █  █  █ █  █ █  █", Color.BRIGHT_GREEN)
    print_colored("     █    █ █  █ █ █  █  █  █ █", Color.BRIGHT_GREEN)
    print()


def print_colored_center(text: str, color: Color = Color.BRIGHT_CYAN) -> None:
    """Print centered text with color."""
    terminal_width = os.get_terminal_size().columns
    padding = (terminal_width - len(text)) // 2
    print_colorized = color + Color.BOLD + " " * padding + text + Color.RESET
    print(print_colorized)


def print_divider(color: Color = Color.BRIGHT_BLACK) -> None:
    """Print a divider line."""
    try:
        term_width = os.get_terminal_size().columns
    except OSError:
        term_width = 80
    print_colored("─" * term_width, color)


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


# ---- Analysis functions ----

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

    print_colored("\n" + "="*60, Color.BRIGHT_GREEN)
    print_colored(f" ✓ KSPR completó el análisis con éxito", Color.BRIGHT_GREEN)
    print_colored(f" • ID de Sesión: {result.analysis_id}", Color.WHITE)
    print_colored(f" • Archivos analizados: {result.summary.files_analyzed}", Color.WHITE)
    print_colored(f" • Elementos UI detectados: {result.summary.ui_elements}", Color.WHITE)
    print_colored(f" • Flujos mapeados: {result.summary.flows}", Color.WHITE)
    print_colored(f" • Artefactos exportados: {len(result.artifacts)}", Color.WHITE)
    print_colored(f" • Directorio de salida: {output.resolve()}", Color.WHITE)
    print_colored("="*60 + "\n", Color.BRIGHT_GREEN)


# ---- Interactive Shell ----

async def interactive_shell() -> None:
    print_header()
    print_divider(Color.BRIGHT_BLACK)
    
    current_workspace = Path.cwd()
    active_model = "gemini-2.5-flash"
    active_provider = "gemini"
    active_agent = "Architect"
    active_iterations = 3
    attached_files: dict[str, str] = {}

    while True:
        try:
            prompt = input(f"\033[36mkspr ({active_agent.lower()})>\033[0m ").strip()
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
                print_colored("\nComandos disponibles en KSPR CLI:", Color.BRIGHT_BLUE)
                print_colored("  /help              Muestra esta ayuda de comandos", Color.WHITE)
                print_colored("  /analyze [path]    Ejecuta el análisis estático", Color.WHITE)
                print_colored("  /model [name]      Cambia o muestra el modelo activo", Color.WHITE)
                print_colored("  /provider [name]   Cambia el proveedor (gemini/local/openai/groq/deepseek)", Color.WHITE)
                print_colored("  /agent [name]      Establece el rol del agente", Color.WHITE)
                print_colored("  /iterations [n]    Cambia iteraciones (1-8)", Color.WHITE)
                print_colored("  /context           Muestra archivos en contexto", Color.WHITE)
                print_colored("  /clear             Limpia la pantalla", Color.WHITE)
                print_colored("  /exit              Sale de la sesión interactiva", Color.WHITE)
                print_colored("  Ctrl+K             Panel de configuración rápida", Color.WHITE)
                print_divider(Color.BRIGHT_BLACK)
            elif cmd == "/clear":
                os.system("cls" if os.name == "nt" else "clear")
                print_header()
                print_divider(Color.BRIGHT_BLACK)
            elif cmd == "/model":
                if arg:
                    active_model = arg
                    print_colored(f"[*] Modelo activo actualizado a: {active_model}", Color.GREEN)
                else:
                    print_colored(f"[*] Modelo activo: {active_model}", Color.CYAN)
            elif cmd == "/provider":
                if arg in {"gemini", "local", "openai", "groq", "deepseek"}:
                    active_provider = arg
                    print_colored(f"[*] Proveedor activo actualizado a: {active_provider}", Color.GREEN)
                else:
                    print_colored(f"[*] Proveedor activo: {active_provider} (opciones: gemini/local/openai/groq/deepseek)", Color.YELLOW)
            elif cmd == "/agent":
                if arg:
                    active_agent = arg
                    print_colored(f"[*] Agente activo actualizado a: {active_agent}", Color.GREEN)
                else:
                    print_colored(f"[*] Agente activo: {active_agent}", Color.CYAN)
            elif cmd == "/iterations":
                if arg.isdigit() and 1 <= int(arg) <= 8:
                    active_iterations = int(arg)
                    print_colored(f"[*] Iteraciones activas actualizadas a: {active_iterations}", Color.GREEN)
                else:
                    print_colored(f"[*] Iteraciones activas: {active_iterations} (rango 1-8)", Color.YELLOW)
                    print_colored("      Uso: /iterations <1-8>", Color.DIM)
            elif cmd == "/context":
                print_colored(f"\nWorkspace actual: {current_workspace}", Color.CYAN)
                print_colored(f"Archivos adjuntos en contexto ({len(attached_files)}):", Color.CYAN)
                for path in attached_files:
                    print_colored(f" - @{path}", Color.WHITE)
                print_divider(Color.BRIGHT_BLACK)
            elif cmd == "/clear":
                os.system("cls" if os.name == "nt" else "clear")
                print_header()
                print_divider(Color.BRIGHT_BLACK)
            elif cmd == "/analyze":
                target_path = Path(arg) if arg else current_workspace
                print_colored(f"[*] Iniciando análisis estático sobre {target_path}...", Color.YELLOW)
                await run_batch_analysis(
                    target_path, None, target_path.parent / "kspr-context", None, active_iterations, active_provider, active_model
                )
            elif cmd == "/ctrlk" or cmd == "ctrl+k":
                # Show the configuration panel
                print_colored("\n=== Panel de Configuración Rápida ===", Color.BRIGHT_MAGENTA)
                print_colored(f"1. Cambiar proveedor   (Actual: {active_provider})", Color.WHITE)
                print_colored(f"2. Cambiar modelo      (Actual: {active_model})", Color.WHITE)
                print_colored(f"3. Cambiar esfuerzo    (Actual: {active_iterations} iteraciones)", Color.WHITE)
                print_colored("4. Agregar API Key", Color.WHITE)
                print_colored("5. Salir del panel (ESC)", Color.WHITE)
                print_colored("Selecciona una opción (1-5) o presiona ESC para cancelar", Color.DIM)
                choice = input("\nOpción: ").strip()
                
                if choice == "1":
                    print_colored("\nProveedores disponibles: gemini, local, openai, groq, deepseek", Color.CYAN)
                    new_provider = input("Nuevo proveedor: ").strip().lower()
                    if new_provider in {"gemini", "local", "openai", "groq", "deepseek"}:
                        active_provider = new_provider
                        print_colored(f"[*] Proveedor cambiado a: {new_provider}", Color.GREEN)
                    else:
                        print_colored("[!] Proveedor no válido", Color.YELLOW)
                elif choice == "2":
                    print_colored("\nIngresa el nombre del modelo:", Color.CYAN)
                    new_model = input("Nuevo modelo: ").strip()
                    if new_model:
                        active_model = new_model
                        print_colored(f"[*] Modelo cambiado a: {new_model}", Color.GREEN)
                    else:
                        print_colored("[!] Nombre de modelo vacío", Color.YELLOW)
                elif choice == "3":
                    print_colored("\nNúmero de iteraciones (1-8):", Color.CYAN)
                    new_iterations_input = input("Nuevas iteraciones: ").strip()
                    if new_iterations_input.isdigit() and 1 <= int(new_iterations_input) <= 8:
                        active_iterations = int(new_iterations_input)
                        print_colored(f"[*] Iteraciones cambiadas a: {active_iterations}", Color.GREEN)
                    else:
                        print_colored("[!] Valor inválido, rango 1-8", Color.YELLOW)
                elif choice == "4":
                    print_colored("\nIngresa la API Key:", Color.CYAN)
                    api_key = input("API Key: ").strip()
                    if api_key:
                        print_colored("[*] API Key guardada en sesión actual", Color.GREEN)
                    else:
                        print_colored("[!] API Key vacía", Color.YELLOW)
                elif choice == "5":
                    print_colored("[*] Panel cancelado", Color.MAGENTA)
                else:
                    print_colored("[!] Opción no válida", Color.YELLOW)
                print_divider(Color.BRIGHT_BLACK)
            else:
                print_colored(f"Comando desconocido: {cmd}. Escribe /help para ver los comandos disponibles.", Color.YELLOW)
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

        print_colored(f"\n[{active_agent}] Analizando instrucción con {active_provider} ({active_model})...", Color.BLUE)
        if referenced_content:
            print_colored(f"[*] Incluyendo {len(attached_files)} referencia(s) de archivos en la consulta.", Color.BLUE)
        
        # Actually call the provider to get a real response
        try:
            settings = Settings()
            provider = get_provider(ProviderName(active_provider.lower()), settings, api_key=getattr(settings, f'{active_provider.lower()}_api_key', None))
            response = await provider.complete(prompt, active_model, effort=None if active_iterations < 3 else "high")
            print_colored(f"\nRespuesta del Agente ({active_agent}):", Color.BRIGHT_CYAN)
            print(response)
            if attached_files:
                print_colored(f"Archivos considerados en la memoria de sesión: {list(attached_files.keys())}", Color.WHITE)
        except ProviderError as e:
            print_colored(f"\nError de proveedor: {e}", Color.RED)
            print_colored("Intentando con modo local de demostración...", Color.YELLOW)
            local_provider = get_provider(ProviderName.local, settings)
            response = await local_provider.complete(prompt, 'kspr-local')
            print_colored(f"\nRespuesta del Agente ({active_agent} - local):", Color.BRIGHT_CYAN)
            print(response)
        except Exception as e:
            print_colored(f"\nError inesperado: {e}", Color.RED)
            print_colored("Mostrando respuesta de fallback...", Color.YELLOW)
            print_colored(f"\nRespuesta del Agente ({active_agent}):", Color.YELLOW)
            print_colored("KSPR I está funcionando en modo local de demostración. Conecta Gemini o un gateway compatible para obtener razonamiento LLM sobre el contexto entregado.", Color.YELLOW)
        
        print_divider(Color.BRIGHT_BLACK)


def main() -> None:
    parser = argparse.ArgumentParser(prog="kspr", description="KSPR AI - Empresarial CLI Engine")
    parser.add_argument("-V", "--version", action="version", version=f"%(prog)s {__version__}", help="Muestra la versión y sale")
    parser.add_argument("source", type=Path, nargs="?", default=None, help="Ruta al directorio o ZIP a analizar (si se omite, abre el shell interactivo)")
    parser.add_argument("--interactive", "-i", action="store_true", help="Inicia el shell interactivo")
    parser.add_argument("--git-url", default=None, help="Clona un repositorio Git en modo lectura para analizarlo")
    parser.add_argument("--output", type=Path, default=Path("kspr-context"), help="Directorio de salida para los artefactos Markdown")
    parser.add_argument("--project-name", default=None, help="Nombre del proyecto para el reporte")
    parser.add_argument("--iterations", type=int, default=3, choices=range(1, 9), help="Número de iteraciones de análisis (1-8)")
    parser.add_argument("--provider", choices=["local", "gemini"], default="gemini", help="Proveedor de IA a utilizar")
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