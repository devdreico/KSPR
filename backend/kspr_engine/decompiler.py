"""Decompiler Engine — Multi-modal file indexing and Context Trees generator."""

from __future__ import annotations

import ipaddress
import logging
import re
import socket
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)


def _is_public_url(url: str) -> bool:
    """Only allow http(s) URLs resolving to public addresses (anti-SSRF)."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False
    try:
        infos = socket.getaddrinfo(parsed.hostname, None)
    except OSError:
        return False
    for info in infos:
        try:
            address = ipaddress.ip_address(info[4][0])
        except ValueError:
            return False
        if (
            address.is_private
            or address.is_loopback
            or address.is_link_local
            or address.is_reserved
            or address.is_multicast
            or address.is_unspecified
        ):
            return False
    return True

CONTEXT_TREES_DIR = Path.cwd() / "Context Trees"


class DecompilerEngine:
    """Manages multi-modal file ingestion, staging, and Context Trees generation."""

    def __init__(self, staging_dir: Path | None = None) -> None:
        self.staging_dir = staging_dir or (Path.home() / ".kspr" / "decompile_staging")
        self.staging_dir.mkdir(parents=True, exist_ok=True)

    def ingest_source(self, source_path_or_url: str) -> dict[str, Any]:
        """Ingest a file (pdf, txt, md, image) or a web URL."""
        source_str = source_path_or_url.strip()
        if source_str.startswith("http://") or source_str.startswith("https://"):
            return self._ingest_url(source_str)
        else:
            return self._ingest_file(Path(source_str))

    def _ingest_file(self, path: Path) -> dict[str, Any]:
        if not path.is_file():
            return {"source": str(path), "success": False, "error": "File not found"}

        suffix = path.suffix.lower()
        content = ""
        file_type = "unknown"

        try:
            if suffix in {".txt", ".md", ".json", ".csv", ".py", ".js", ".ts", ".html", ".css", ".yaml", ".yml"}:
                content = path.read_text(encoding="utf-8", errors="replace")
                file_type = "text"
            elif suffix == ".pdf":
                content = f"[PDF Document: {path.name}] (Extracted via PyPDF/Text reader)\n"
                try:
                    import pypdf
                    reader = pypdf.PdfReader(str(path))
                    for i, page in enumerate(reader.pages):
                        content += f"\n--- Page {i+1} ---\n" + (page.extract_text() or "")
                except Exception:
                    content += path.read_bytes().hex()[:2000]
                file_type = "pdf"
            elif suffix in {".jpg", ".jpeg", ".png", ".heif", ".webp", ".bmp"}:
                content = f"[Image Asset: {path.name} ({suffix})] Size: {path.stat().st_size} bytes."
                file_type = "image"
            else:
                content = path.read_text(encoding="utf-8", errors="replace")
                file_type = "binary_text"

            return {
                "source": str(path),
                "name": path.name,
                "type": file_type,
                "content": content,
                "success": True,
            }
        except Exception as e:
            return {"source": str(path), "success": False, "error": str(e)}

    def _ingest_url(self, url: str) -> dict[str, Any]:
        if not _is_public_url(url):
            return {"source": url, "success": False, "error": "URL no permitida (solo http/https públicos)"}
        try:
            resp = httpx.get(url, timeout=10, follow_redirects=True)
            text = resp.text
            # Basic HTML to clean text extraction
            clean_text = re.sub(r"<[^>]+>", " ", text)
            clean_text = re.sub(r"\s+", " ", clean_text).strip()
            return {
                "source": url,
                "name": url.split("/")[-1] or "web-page",
                "type": "web_link",
                "content": f"[Web Link: {url}]\n\n{clean_text[:10000]}",
                "success": True,
            }
        except Exception as e:
            return {"source": url, "success": False, "error": str(e)}

    def generate_context_trees(self, ingested_sources: list[dict[str, Any]], model_response_text: str) -> Path:
        """Parse AI response and generate Context Trees folder structure."""
        # Determine main concept from ingested sources or model response
        main_concept = "Analisis General"
        for src in ingested_sources:
            if src.get("success"):
                main_concept = Path(src["name"]).stem.replace("-", " ").title()
                break

        concept_dir = CONTEXT_TREES_DIR / main_concept
        concept_dir.mkdir(parents=True, exist_ok=True)

        # Create Contexto inicial.md
        initial_md = concept_dir / "Contexto inicial.md"
        initial_content = f"""# Contexto Inicial — {main_concept}

Analisis recopilado de {len(ingested_sources)} fuentes indexadas.

## Resumen del Concepto Principal
Este arbol de contexto desglosa la informacion analizada partiendo del nucleo fundamental hasta el nivel mas detallado de cada componente encontrado en las fuentes.

## Archivos Tematicos del Arbol
- aleaciones.md (o componentes derivados)
- temperaturas.md (o parametros operativos)
- estructuras moleculares.md (o arquitectura estructural)
"""
        initial_md.write_text(initial_content, encoding="utf-8")

        # Parse sections from model response or create default granular files
        sections = self._parse_markdown_sections(model_response_text)
        if not sections:
            sections = {
                "aleaciones.md": "# Componentes y Aleaciones\n\nDetalles tecnicos extraidos de las fuentes analizadas.",
                "temperaturas.md": "# Parametros y Temperaturas\n\nRegistro termodinamico y operativo.",
                "estructuras moleculares.md": "# Estructuras Moleculares\n\nAnalisis estructural y molecular detallado."
            }

        for filename, file_content in sections.items():
            safe_name = filename if filename.endswith(".md") else f"{filename}.md"
            (concept_dir / safe_name).write_text(file_content, encoding="utf-8")

        logger.info(f"Context Tree created at: {concept_dir}")
        return concept_dir

    def _parse_markdown_sections(self, text: str) -> dict[str, str]:
        sections: dict[str, str] = {}
        current_title = "detalles.md"
        current_lines: list[str] = []

        for line in text.splitlines():
            if line.startswith("# ") or line.startswith("## "):
                if current_lines:
                    sections[current_title] = "\n".join(current_lines)
                current_title = line.lstrip("# ").strip().lower().replace(" ", "-") + ".md"
                current_lines = [line]
            else:
                current_lines.append(line)

        if current_lines:
            sections[current_title] = "\n".join(current_lines)

        return sections

    def list_trees(self) -> list[dict[str, Any]]:
        trees = []
        if CONTEXT_TREES_DIR.is_dir():
            for item in CONTEXT_TREES_DIR.iterdir():
                if item.is_dir():
                    files = [f.name for f in item.glob("*.md")]
                    trees.append({
                        "concept": item.name,
                        "path": str(item.resolve()),
                        "files": files,
                    })
        return trees
