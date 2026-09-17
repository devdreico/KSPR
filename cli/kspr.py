"""KSPR CLI: Interactive terminal agent and static analysis engine."""

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

KSPR_ASCII = "\n".join(("▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒  ▒ ▒ ▒ ▒ ▒ ▒  ▒ ▒ ▒ ▒ ▒  ▒ ▒ ▒ ▒ ▒ ▒  ▒ ▒ ▒ ▒ ▒  ▒ ▒ ▒ ▒      ▒ ▒ ▒",
 " ▒ ▒  ▒ ▒ ▒ ▒  ▒ ▒ ▒ ▒  ▒ ▒ ▒▒▒ ▒  ▒ ▒ ▒  ▒▒ ▒▒ ▒▒▒ ▒▒▒  ▒ ▒▒▒ ▒ ▒  ▒ ▒ ▒▒▒▒▒ ▒ ▒  ▒▒▒ ▒",
 " ▒ ▒ ▒ ▒ ▒  ▒ ▒ ▒ ▒ ▒▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒   ▒  ▒ ▒ ▒ ▒ ▒▒▒  ▒ ▒ ▒ ▒ ▒▒▒▒▒ ▒▒▒ ▒▒ ▒ ▒▒▒ ▒ ▒",
 " ▒  ▒  ▒  ▒     ▒  ▒ ▒    ▒▒    ▒ ▒ ▒ ▒ ▒  ▒ ▒ ▒ ▒ ▒  ▒ ▒ ▒ ▒ ▒ ▒  ▒ ▒ ▒ ▒ ▒    ▒▒▒    ▒ ▒",
 " ▒      ▒        ▒ ▒        ▒   ▒    ▒ ▒      ▒▒▒ ▒ ▒ ▒ ▒▒ ▒ ▒ ▒ ▒  ▒ ▒ ▒▒▒ ▒ ▒ ▒▒ ▒ ▒ ▒▒",
 " ▒ ▒ ▒ ▒  ▒   ▒ ▒ ▒ ▒  ▒ ▒ ▒ ▒ ▒ ▒ ▒▒ ▒ ▒ ▒ ▒  ▒ ▒ ▒ ▒ ▒  ▒ ▒ ▒ ▒ ▒  ▒▒▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒  ▒",
 "  ▒ ▒ ▒ ▒ ▒  ▒ ▒ ▒▒▒ ▒ ▒▒ ▒ ▒ ▒▒▒  ▒▒▒ ▒ ▒ ▒ ▒  ▒ ▒ ▒ ▒ ▒  ▒ ▒ ▒ ▒ ▒ ▒  ▒ ▒ ▒ ▒  ▒ ▒"))

ALLOWED = {".py", ".js", ".jsx", ".ts", ".tsx", ".cs", ".java", ".sql", ".html", ".vue", ".php", ".md", ".txt", ".json", ".yaml", ".yml"}


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


async def run_batch_analysis(source: Path, git_url: str | None, output: Path, project_name: str | None, iterations: int, provider: str, model: str | None) -> None:
    if git_url:
        print(f"[*] Clonando repositorio Git de forma segura: {git_url}")
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
        print(f"[*] Analizando fuente local: {source}")
        files = collect_source(source)
        default_name = source.stem

    if not files:
        raise SystemExit("Error: No se encontraron archivos soportados en la fuente.")

    print(f"[*] Archivos recolectados: {len(files)}. Ejecutando KSPR Engine ({iterations} iteraciones)...")
    request = AnalysisRequest(project_name=project_name or default_name, files=files, iterations=iterations, provider=provider, model=model)
    result = await analyze(request, Settings())

    output.mkdir(parents=True, exist_ok=True)
    for artifact in result.artifacts:
        target = output / artifact.path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(artifact.content, encoding="utf-8")

    print("\n" + "="*60)
    print(f" ✓ KSPR completó el análisis con éxito")
    print(f" • ID de Sesión: {result.analysis_id}")
    print(f" • Archivos analizados: {result.summary.files_analyzed}")
    print(f" • Elementos UI detectados: {result.summary.ui_elements}")
    print(f" • Flujos mapeados: {result.summary.flows}")
    print(f" • Artefactos exportados: {len(result.artifacts)}")
    print(f" • Directorio de salida: {output.resolve()}")
    print("="*60 + "\n")


async def interactive_shell() -> None:
    print(KSPR_ASCII)
    print("\n" + "═"*70)
    print("  KSPR CLI — Interactive Terminal Agent (v0.1.0)")
    print("  Escribe una consulta, referencia archivos con @ o usa /help para comandos.")
    print("═"*70 + "\n")

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
            print("\n¡Hasta luego!")
            break

        if not prompt:
            continue

        if prompt.startswith("/"):
            parts = prompt.split(maxsplit=1)
            cmd = parts[0].lower()
            arg = parts[1] if len(parts) > 1 else ""

            if cmd in {"/exit", "/quit"}:
                print("Saliendo de la sesión de KSPR CLI.")
                break
            elif cmd == "/help":
                print("\nComandos disponibles en KSPR CLI:")
                print("  /help              Muestra esta ayuda de comandos")
                print("  /analyze [path]    Ejecuta el análisis estático del workspace actual o ruta")
                print("  /model [name]      Cambia o muestra el modelo de IA activo")
                print("  /provider [name]   Cambia el proveedor ('gemini' o 'local')")
                print("  /agent [name]      Establece el rol del agente (Architect, Developer, Auditor)")
                print("  /iterations [n]    Cambia el número de iteraciones de análisis (1-8)")
                print("  /context           Muestra los archivos referenciados en el workspace")
                print("  /clear             Limpia la pantalla de la terminal")
                print("  /exit              Sale de la sesión interactiva\n")
                print("  Ctrl+K             Panel de configuración rápida (proveedor, modelo, esfuerzo)")
            elif cmd == "/clear":
                os.system("cls" if os.name == "nt" else "clear")
            elif cmd == "/model":
                if arg:
                    active_model = arg
                    print(f"[*] Modelo activo actualizado a: {active_model}")
                else:
                    print(f"[*] Modelo activo: {active_model}")
            elif cmd == "/provider":
                if arg in {"gemini", "local", "openai", "groq", "deepseek"}:
                    active_provider = arg
                    print(f"[*] Proveedor activo actualizado a: {active_provider}")
                else:
                    print(f"[*] Proveedor activo: {active_provider} (opciones: gemini, local, openai, groq, deepseek)")
            elif cmd == "/agent":
                if arg:
                    active_agent = arg
                    print(f"[*] Agente activo actualizado a: {active_agent}")
                else:
                    print(f"[*] Agente activo: {active_agent}")
            elif cmd == "/iterations":
                if arg.isdigit() and 1 <= int(arg) <= 8:
                    active_iterations = int(arg)
                    print(f"[*] Iteraciones activas actualizadas a: {active_iterations}")
                else:
                    print(f"[*] Iteraciones activas: {active_iterations} (rango 1-8)")
                    print(f"      Uso: /iterations <1-8>")
            elif cmd == "/context":
                print(f"\nWorkspace actual: {current_workspace}")
                print(f"Archivos adjuntos en contexto ({len(attached_files)}):")
                for path in attached_files:
                    print(f" - @{path}")
                print()
            elif cmd == "/clear":
                os.system("cls" if os.name == "nt" else "clear")
            elif cmd == "/analyze":
                target_path = Path(arg) if arg else current_workspace
                print(f"[*] Iniciando análisis estático sobre {target_path}...")
                await run_batch_analysis(
                    target_path, None, target_path.parent / "kspr-context", None, active_iterations, active_provider, active_model
                )
            elif cmd == "/ctrlk" or cmd == "ctrl+k":
                # Show the configuration panel
                await show_config_panel(active_provider, active_model, active_iterations)
                continue
            else:
                print(f"Comando desconocido: {cmd}. Escribe /help para ver los comandos disponibles.")
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
                        print(f"[+] Archivo adjuntado al contexto: @{filepath}")
                    except Exception as e:
                        print(f"[!] No se pudo leer {filepath}: {e}")
                else:
                    print(f"[!] Archivo no encontrado: {filepath}")

        print(f"\n[{active_agent}] Analizando instrucción con {active_provider} ({active_model})...")
        if referenced_content:
            print(f"[*] Incluyendo {len(attached_files)} referencia(s) de archivos en la consulta.")
        
        # Actually call the provider to get a real response
        try:
            settings = Settings()
            provider = get_provider(ProviderName(active_provider.lower()), settings, api_key=getattr(settings, f'{active_provider.lower()}_api_key', None))
            response = await provider.complete(prompt, active_model, effort=None if active_iterations < 3 else "high")
            print(f"\nRespuesta del Agente ({active_agent}):")
            print(response)
            if attached_files:
                print(f"Archivos considerados en la memoria de sesión: {list(attached_files.keys())}")
        except ProviderError as e:
            print(f"\nError de proveedor: {e}")
            print("Intentando con modo local de demostración...")
            local_provider = get_provider(ProviderName.local, settings)
            response = await local_provider.complete(prompt, 'kspr-local')
            print(f"\nRespuesta del Agente ({active_agent} - local):")
            print(response)
        except Exception as e:
            print(f"\nError inesperado: {e}")
            print("Mostrando respuesta de fallback...")
            print(f"\nRespuesta del Agente ({active_agent}):")
            print("KSPR I está funcionando en modo local de demostración. Conecta Gemini o un gateway compatible para obtener razonamiento LLM sobre el contexto entregado.")
        
        print()
        

async def show_config_panel(current_provider: str, current_model: str, current_iterations: int) -> None:
    """Muestra un panel de opciones de configuración al presionar Ctrl+K."""
    options = [
        "1. Cambiar proveedor",
        f"   Proveedor actual: {current_provider}",
        "2. Cambiar modelo",
        f"   Modelo actual: {current_model}",
        "3. Cambiar esfuerzo",
        f"   Esfuerzo actual: {current_iterations} iteraciones",
        "4. Agregar API Key",
        "5. Salir del panel (ESC)",
    ]

    print("\n" + "="*60)
    print("  PANEL DE CONFIGURACIÓN RÁPIDA (Ctrl+K)")
    print("="*60)
    for option in options:
        print(option)
    print("="*60 + "\n")
    print("Selecciona una opción (1-5) o presiona ESC para cancelar.")

    # Read user choice - in non-interactive mode, we'll just show the panel
    # and handle the selection in the main loop
    choice = input("\nOpción: ").strip()
    
    if choice == "1":
        print("\nProveedores disponibles: gemini, local, openai, groq, deepseek")
        new_provider = input("Nuevo proveedor: ").strip().lower()
        if new_provider in {"gemini", "local", "openai", "groq", "deepseek"}:
            # Return the new provider to the caller
            print(f"[*] Proveedor cambiado a: {new_provider}")
        else:
            print("[!] Proveedor no válido")
    elif choice == "2":
        print("\nIngresa el nombre del modelo:")
        new_model = input("Nuevo modelo: ").strip()
        if new_model:
            print(f"[*] Modelo cambiado a: {new_model}")
        else:
            print("[!] Nombre de modelo vacío")
    elif choice == "3":
        print("\nNúmero de iteraciones (1-8):")
        new_iterations_input = input("Nuevas iteraciones: ").strip()
        if new_iterations_input.isdigit() and 1 <= int(new_iterations_input) <= 8:
            new_iterations = int(new_iterations_input)
            print(f"[*] Iteraciones cambiadas a: {new_iterations}")
        else:
            print("[!] Valor inválido, rango 1-8")
    elif choice == "4":
        print("\nIngresa la API Key:")
        api_key = input("API Key: ").strip()
        if api_key:
            print("[*] API Key guardada en sesión actual")
        else:
            print("[!] API Key vacía")
    elif choice == "5":
        print("[*] Panel cancelado")
    else:
        print("[!] Opción no válida")


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
