"""CLI local de KSPR: escanea archivos sin ejecutar el repositorio."""

from __future__ import annotations

import argparse
import asyncio
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from kspr_engine.analyzer import analyze
from kspr_engine.config import Settings
from kspr_engine.models import AnalysisRequest, SourceFile

ALLOWED = {".py", ".js", ".jsx", ".ts", ".tsx", ".cs", ".java", ".sql", ".html", ".vue", ".php", ".md", ".txt", ".json", ".yaml", ".yml"}


def collect(root: Path) -> list[SourceFile]:
    files = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in ALLOWED:
            continue
        if any(part in {".git", "node_modules", ".venv", "venv", "dist", "build"} for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if len(text.encode()) <= 2_000_000:
            files.append(SourceFile(path=str(path.relative_to(root)), content=text))
    return files


def collect_zip(archive_path: Path) -> list[SourceFile]:
    files = []
    with zipfile.ZipFile(archive_path) as archive:
        for member in archive.infolist()[:2_000]:
            name = member.filename.replace("\\", "/")
            suffix = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
            if member.is_dir() or suffix not in ALLOWED or name.startswith("/") or ".." in name.split("/") or member.file_size > 2_000_000:
                continue
            files.append(SourceFile(path=name, content=archive.read(member)[:2_000_000].decode("utf-8", errors="replace")))
    return files


def collect_source(source: Path) -> list[SourceFile]:
    if source.is_dir():
        return collect(source)
    if source.suffix.lower() == ".zip":
        return collect_zip(source)
    raise SystemExit("La fuente debe ser un directorio o un ZIP")


async def main() -> None:
    parser = argparse.ArgumentParser(description="KSPR - Reverse Engineering Artificial Intelligence Agent")
    parser.add_argument("source", type=Path)
    parser.add_argument("--git-url", default=None, help="Clona un repositorio Git en modo lectura para analizarlo")
    parser.add_argument("--output", type=Path, default=Path("kspr-context"))
    parser.add_argument("--project-name", default=None)
    parser.add_argument("--iterations", type=int, default=3)
    parser.add_argument("--provider", choices=["local", "gemini"], default="gemini")
    parser.add_argument("--model", default=None)
    args = parser.parse_args()
    if args.git_url:
        with tempfile.TemporaryDirectory(prefix="kspr-git-") as checkout:
            await asyncio.to_thread(
                subprocess.run,
                ["git", "clone", "--depth", "1", "--no-tags", args.git_url, checkout],
                check=True,
                capture_output=True,
                text=True,
            )
            files = collect(Path(checkout))
        default_name = args.git_url.rstrip("/").rsplit("/", 1)[-1].removesuffix(".git")
    else:
        files = collect_source(args.source)
        default_name = args.source.stem
    if not files:
        raise SystemExit("No se encontraron archivos soportados")
    request = AnalysisRequest(project_name=args.project_name or default_name, files=files, iterations=args.iterations, provider=args.provider, model=args.model)
    result = await analyze(request, Settings())
    args.output.mkdir(parents=True, exist_ok=True)
    for artifact in result.artifacts:
        target = args.output / artifact.path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(artifact.content, encoding="utf-8")
    print(f"KSPR completó el análisis: {result.analysis_id}")
    print(f"Archivos: {result.summary.files_analyzed} | UI: {result.summary.ui_elements} | Flujos: {result.summary.flows} | Artefactos: {len(result.artifacts)}")
    print(f"Salida: {args.output.resolve()}")


if __name__ == "__main__":
    asyncio.run(main())
