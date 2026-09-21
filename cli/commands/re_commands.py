"""Reverse-engineering slash commands for the KSPR interactive shell."""

from __future__ import annotations

import inspect
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from kspr_core import safe_workspace_path
from kspr_engine.config import Settings
from kspr_engine.providers import get_provider
from kspr_engine.re import installer
from kspr_engine.re.analyze import analyze_artifact
from kspr_engine.re.carve import carve, recover
from kspr_engine.re.decompile import build_ai_decompile_prompt, decompile
from kspr_engine.re.detect import detect_crypto, scan_with_rules
from kspr_engine.re.disasm import available_backends, disassemble, objdump_disassemble
from kspr_engine.re.formats.archives import extract_archive
from kspr_engine.re.graph import build_cfg
from kspr_engine.re.graph import export as export_graph
from kspr_engine.re.models import ArtifactReport
from kspr_engine.re.traits import entropy_blocks, hexdump, read_artifact
from kspr_terminal_ui import TerminalUI

IOC_PATTERNS = {
    "ipv4": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    "url": re.compile(r"https?://[^\s\"'<>]{4,200}"),
    "domain": re.compile(r"\b(?:[a-zA-Z0-9-]+\.)+(?:com|net|org|io|ru|cn|onion|xyz|top|info)\b"),
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "registry": re.compile(r"\b(?:HKEY_[A-Z_]+|SOFTWARE\\[A-Za-z0-9_\\]+)\b"),
    "btc": re.compile(r"\b(?:bc1|[13])[a-zA-HJ-NP-Z0-9]{25,39}\b"),
    "onion": re.compile(r"\b[a-z2-7]{16,56}\.onion\b"),
}

RE_COMMANDS = {
    "tools", "recon", "file", "strings", "hex", "sections", "imports", "exports", "symbols",
    "entropy", "hashes", "disasm", "decompile", "pseudo", "cfg", "callgraph", "xrefs", "diff",
    "signature", "packer", "yara", "capa", "crypto", "iocs", "carve", "recover", "extract",
    "unpack", "firmware", "report", "sbom", "graph", "ask", "pcap", "index",
}


@dataclass
class REContext:
    """Everything the RE commands need from the interactive shell."""

    workspace: Path
    provider_name: str = "local"
    model: str = "kspr-local"
    config: dict[str, Any] = field(default_factory=dict)

    def resolve(self, argument: str) -> Path | None:
        """Resolve an artifact path (absolute allowed, otherwise workspace-scoped)."""
        candidate = (argument or "").strip().strip('"').strip("'")
        if not candidate:
            return None
        direct = Path(candidate).expanduser()
        if direct.is_file():
            return direct.resolve()
        scoped = safe_workspace_path(self.workspace, candidate)
        if scoped and scoped.is_file():
            return scoped
        return None

    async def ai_complete(self, prompt: str) -> str:
        settings = Settings()
        api_key = os.getenv(f"KSPR_{self.provider_name.upper()}_API_KEY")
        provider = get_provider(self.provider_name, settings, api_key=api_key)
        return str(await provider.complete(prompt, self.model))


def _need_path(ctx: REContext, argument: str, usage: str) -> Path | None:
    path = ctx.resolve(argument)
    if path is None:
        TerminalUI.print_box("Artefacto no encontrado", [f"Uso: {usage}", "La ruta debe existir (absoluta) o estar dentro del workspace."])
    return path


async def dispatch_re_command(cmd: str, arg: str, ctx: REContext) -> bool:
    """Handle an RE command. Returns True when the command was handled."""
    command = cmd.lstrip("/").lower()
    if command not in RE_COMMANDS:
        return False
    parts = arg.strip().split()
    try:
        result = _HANDLERS[command](ctx, parts)
        if inspect.isawaitable(result):
            return bool(await result)
        return bool(result)
    except Exception as exc:
        TerminalUI.print_box(f"Error en /{command}", [str(exc)])
        return True


# ---- handlers ----

def _cmd_tools(ctx: REContext, parts: list[str]) -> bool:
    action = parts[0].lower() if parts else "detect"
    if action in {"detect", "status"}:
        info = installer.status()
        rows = [[t["key"], "sí" if t["installed"] else "no", t["path"] or "—", t["description"][:44]] for t in info["tools"]]
        TerminalUI.print_table(f"Herramientas RE · gestor: {info['manager']}", ["TOOL", "OK", "RUTA", "DESCRIPCIÓN"], rows)
    elif action == "which":
        name = parts[1] if len(parts) > 1 else ""
        info = installer.detect()
        match = [t for t in info if t["key"] == name or t["binary"] == name]
        TerminalUI.print_box("Tool", [f"{t['key']}: {'sí' if t['installed'] else 'no'} {t['path']}" for t in match] or ["No encontrado"])
    elif action == "install":
        keys = parts[1:] or None
        result = installer.install(keys or None, only_critical=not keys)
        lines = [f"{item.get('key')}: {item.get('status')}" for item in result["results"]]
        TerminalUI.print_box(f"Instalación ({result['manager']})", lines or ["Nada que instalar"])
    else:
        TerminalUI.print_box("Uso", ["/tools [detect|status|which <tool>|install [tool...]]"])
    return True


def _cmd_recon(ctx: REContext, parts: list[str]) -> bool:
    path = _need_path(ctx, " ".join(parts), "/recon <ruta>")
    if not path:
        return True
    report = analyze_artifact(path)
    TerminalUI.print_box(f"Recon · {path.name}", [
        f"Tipo: {report.kind} ({report.description})",
        f"Tamaño: {report.size} bytes · Entropía: {report.entropy}",
        f"SHA-256: {report.hashes.get('sha256')}",
        f"Secciones: {len(report.sections)} · Imports: {len(report.imports)} · Exports: {len(report.exports)}",
        f"Strings: {len(report.strings)} · Hallazgos: {len(report.findings)}",
    ])
    if report.findings:
        TerminalUI.print_table("Hallazgos", ["SEVERIDAD", "CATEGORÍA", "TÍTULO"], [[f.severity, f.category, f.title] for f in report.findings])
    return True


def _cmd_file(ctx: REContext, parts: list[str]) -> bool:
    path = _need_path(ctx, " ".join(parts), "/file <ruta>")
    if not path:
        return True
    report = analyze_artifact(path)
    lines = [f"{k}: {v}" for k, v in report.to_dict().items() if k in {"path", "size", "kind", "description", "mime", "entropy"}]
    lines += [f"hash.sha256: {report.hashes.get('sha256')}"]
    lines += [f"hash.md5: {report.hashes.get('md5')}"]
    TerminalUI.print_box(f"File · {path.name}", lines)
    return True


def _cmd_strings(ctx: REContext, parts: list[str]) -> bool:
    path = _need_path(ctx, parts[0] if parts else "", "/strings <ruta> [min]")
    if not path:
        return True
    minimum = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 5
    from kspr_engine.re.traits import extract_strings

    strings = extract_strings(read_artifact(path), min_length=minimum)
    rows = [[f"0x{offset:x}", text[:120]] for offset, text in strings[:400]]
    TerminalUI.print_table(f"Strings · {path.name} ({len(strings)})", ["OFFSET", "CADENA"], rows)
    return True


def _cmd_hex(ctx: REContext, parts: list[str]) -> bool:
    path = _need_path(ctx, parts[0] if parts else "", "/hex <ruta> [offset] [len]")
    if not path:
        return True
    offset = int(parts[1], 0) if len(parts) > 1 else 0
    length = int(parts[2], 0) if len(parts) > 2 else 256
    lines = hexdump(read_artifact(path), offset=offset, length=length)
    TerminalUI.print_box(f"Hexdump · {path.name} 0x{offset:x}", lines or ["(sin datos)"])
    return True


def _format_artifact(ctx: REContext, argument: str, title: str) -> ArtifactReport | None:
    path = _need_path(ctx, argument, f"/{title} <ruta>")
    if not path:
        return None
    return analyze_artifact(path)


def _cmd_sections(ctx: REContext, parts: list[str]) -> bool:
    report = _format_artifact(ctx, " ".join(parts), "sections")
    if not report:
        return True
    if not report.sections:
        TerminalUI.print_box("Sections", ["El artefacto no expone secciones (no es ELF/PE o el parser falló)."])
        return True
    rows = [[s.get("name"), f"0x{s.get('addr', 0):x}", s.get("size", 0), s.get("permissions", "—"), s.get("entropy", 0)] for s in report.sections]
    TerminalUI.print_table(f"Secciones · {report.path}", ["NOMBRE", "DIRECCIÓN", "TAMAÑO", "PERM", "ENTROPÍA"], rows)
    return True


def _cmd_imports(ctx: REContext, parts: list[str]) -> bool:
    report = _format_artifact(ctx, " ".join(parts), "imports")
    if not report:
        return True
    TerminalUI.print_table(f"Imports · {report.path} ({len(report.imports)})", ["IMPORT"], [[item] for item in report.imports[:300]] or [["(ninguno)"]])
    return True


def _cmd_exports(ctx: REContext, parts: list[str]) -> bool:
    report = _format_artifact(ctx, " ".join(parts), "exports")
    if not report:
        return True
    TerminalUI.print_table(f"Exports · {report.path} ({len(report.exports)})", ["EXPORT"], [[item] for item in report.exports[:300]] or [["(ninguno)"]])
    return True


def _cmd_symbols(ctx: REContext, parts: list[str]) -> bool:
    report = _format_artifact(ctx, " ".join(parts), "symbols")
    if not report:
        return True
    TerminalUI.print_table(f"Símbolos · {report.path} ({len(report.symbols)})", ["SÍMBOLO"], [[item] for item in report.symbols[:400]] or [["(ninguno)"]])
    return True


def _cmd_entropy(ctx: REContext, parts: list[str]) -> bool:
    path = _need_path(ctx, parts[0] if parts else "", "/entropy <ruta> [bloque]")
    if not path:
        return True
    block = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1024
    values = entropy_blocks(read_artifact(path), block_size=block)
    rows = [[f"0x{i * block:x}", value, "█" * int(value * 4)] for i, value in enumerate(values[:400])]
    TerminalUI.print_table(f"Entropía · {path.name} (bloque {block})", ["OFFSET", "ENTROPÍA", ""], rows)
    return True


def _cmd_hashes(ctx: REContext, parts: list[str]) -> bool:
    path = _need_path(ctx, " ".join(parts), "/hashes <ruta>")
    if not path:
        return True
    report = analyze_artifact(path)
    TerminalUI.print_box(f"Hashes · {path.name}", [f"{k}: {v}" for k, v in report.hashes.items()])
    return True


def _cmd_disasm(ctx: REContext, parts: list[str]) -> bool:
    path = _need_path(ctx, parts[0] if parts else "", "/disasm <ruta> [offset] [n]")
    if not path:
        return True
    offset = int(parts[1], 0) if len(parts) > 1 else 0
    count = int(parts[2]) if len(parts) > 2 else 64
    report = analyze_artifact(path)
    arch = _arch_of(report)
    data = read_artifact(path)
    instructions: list[dict[str, Any]] = []
    base = 0
    if arch in {"x86", "x86-64", "arm", "aarch64", "mips", "riscv", "powerpc"}:
        try:
            instructions = disassemble(data, arch=arch, base_address=base, offset=offset, count=count)
        except Exception:
            instructions = []
    if not instructions and "objdump" in available_backends():
        instructions = objdump_disassemble(str(path), offset=offset, count=count)
    if not instructions:
        TerminalUI.print_box("Disasm", [f"Sin backend de desensamblado para {arch}. Instala radare2/objdump con /tools install."])
        return True
    rows = [[f"0x{insn['address']:x}", insn["bytes"], insn["mnemonic"], insn["op_str"]] for insn in instructions]
    TerminalUI.print_table(f"Disasm · {path.name} ({arch})", ["DIR", "BYTES", "MNEMONIC", "OPERANDOS"], rows)
    return True


def _cmd_decompile(ctx: REContext, parts: list[str]) -> bool:
    path = _need_path(ctx, parts[0] if parts else "", "/decompile <ruta> [símbolo|offset]")
    if not path:
        return True
    target = parts[1] if len(parts) > 1 else None
    result = decompile(str(path), target=target)
    if result.get("engine") == "none":
        jvm = _try_jvm_decompile(path)
        if jvm is not None:
            result = jvm
    if result.get("engine") == "none":
        TerminalUI.print_box("Decompilador no disponible", [
            result.get("message", ""),
            f"Disponibles: {', '.join(result.get('available') or []) or 'ninguno'}",
        ])
        return True
    TerminalUI.print_response(f"Decompile · {result['engine']} · {target or 'entry'}", result.get("output", ""))
    return True


def _try_jvm_decompile(path: Path) -> dict[str, Any] | None:
    """Decompile JVM/Android artifacts with jadx when available."""
    import shutil
    import subprocess
    import tempfile

    if path.suffix.lower() not in {".jar", ".apk", ".class", ".dex", ".zip"} or not shutil.which("jadx"):
        return None
    with tempfile.TemporaryDirectory(prefix="kspr-jadx-") as workdir:
        completed = subprocess.run(["jadx", "-d", workdir, "--no-res", str(path)], capture_output=True, text=True, timeout=600, check=False)
        sources: list[str] = []
        for source_file in sorted(Path(workdir).rglob("*.java"))[:5]:
            sources.append(f"// ==== {source_file.relative_to(workdir)} ====")
            sources.append(source_file.read_text(encoding="utf-8", errors="replace")[:8000])
        output = "\n".join(sources) or (completed.stdout + completed.stderr)[:8000]
        return {"engine": "jadx", "output": output, "returncode": completed.returncode}


async def _cmd_pseudo(ctx: REContext, parts: list[str]) -> bool:
    path = _need_path(ctx, parts[0] if parts else "", "/pseudo <ruta> [offset] [len]")
    if not path:
        return True
    offset = int(parts[1], 0) if len(parts) > 1 else 0
    count = int(parts[2]) if len(parts) > 2 else 120
    report = analyze_artifact(path)
    prompt = build_ai_decompile_prompt(str(path), read_artifact(path), arch=_arch_of(report), offset=offset, count=count)
    response = await ctx.ai_complete(prompt)
    TerminalUI.print_response(f"Pseudo-IA · {path.name} @0x{offset:x}", response)
    return True


def _cmd_cfg(ctx: REContext, parts: list[str]) -> bool:
    path = _need_path(ctx, parts[0] if parts else "", "/cfg <ruta> [offset]")
    if not path:
        return True
    offset = int(parts[1], 0) if len(parts) > 1 else 0
    report = analyze_artifact(path)
    arch = _arch_of(report)
    try:
        instructions = disassemble(read_artifact(path), arch=arch, offset=offset, count=60)
    except Exception:
        instructions = []
    if not instructions:
        TerminalUI.print_box("CFG", ["No se pudo desensamblar para construir el grafo."])
        return True
    cfg = build_cfg(instructions)
    TerminalUI.print_box("CFG (mermaid)", export_graph(cfg, "mermaid", f"CFG {path.name}").splitlines())
    return True


def _cmd_graph(ctx: REContext, parts: list[str]) -> bool:
    path = _need_path(ctx, parts[0] if parts else "", "/graph <ruta> [mermaid|dot]")
    if not path:
        return True
    fmt = parts[1] if len(parts) > 1 else "mermaid"
    report = analyze_artifact(path)
    try:
        instructions = disassemble(read_artifact(path), arch=_arch_of(report), count=80)
    except Exception:
        instructions = []
    cfg = build_cfg(instructions)
    out = export_graph(cfg, fmt, f"CFG {path.name}")
    target = ctx.workspace / f"kspr_graph_{path.stem}.{ 'dot' if fmt == 'dot' else 'mmd' }"
    target.write_text(out, encoding="utf-8")
    TerminalUI.print_box("Grafo exportado", [str(target), f"nodos: {len(cfg['nodes'])} · aristas: {len(cfg['edges'])}"])
    return True


def _cmd_packer(ctx: REContext, parts: list[str]) -> bool:
    report = _format_artifact(ctx, " ".join(parts), "packer")
    if not report:
        return True
    packer_findings = [f for f in report.findings if f.category == "packer"]
    TerminalUI.print_box(f"Packer · {report.path}", [f.label() for f in packer_findings] or ["Sin firmas de packer detectadas."])
    return True


def _cmd_yara(ctx: REContext, parts: list[str]) -> bool:
    path = _need_path(ctx, parts[0] if parts else "", "/yara <ruta> [reglas]")
    if not path:
        return True
    rules = parts[1] if len(parts) > 1 else None
    findings = scan_with_rules(str(path), rules_path=rules)
    TerminalUI.print_table(f"YARA · {path.name}", ["SEVERIDAD", "REGLA", "DESCRIPCIÓN"], [[f.severity, f.title, f.description[:60]] for f in findings] or [["—", "sin coincidencias", ""]])
    return True


def _cmd_capa(ctx: REContext, parts: list[str]) -> bool:
    path = _need_path(ctx, " ".join(parts), "/capa <ruta>")
    if not path:
        return True
    import shutil
    import subprocess

    if not shutil.which("capa"):
        TerminalUI.print_box("capa no disponible", ["Instálalo con /tools install capa (pip install flare-capa)."])
        return True
    completed = subprocess.run(["capa", str(path)], capture_output=True, text=True, timeout=300, check=False)
    TerminalUI.print_response(f"capa · {path.name}", (completed.stdout or completed.stderr)[:8000])
    return True


def _cmd_crypto(ctx: REContext, parts: list[str]) -> bool:
    path = _need_path(ctx, " ".join(parts), "/crypto <ruta>")
    if not path:
        return True
    findings = detect_crypto(read_artifact(path))
    TerminalUI.print_box(f"Crypto · {path.name}", [f.label() for f in findings] or ["Sin constantes criptográficas conocidas."])
    return True


def _cmd_iocs(ctx: REContext, parts: list[str]) -> bool:
    path = _need_path(ctx, " ".join(parts), "/iocs <ruta>")
    if not path:
        return True
    from kspr_engine.re.traits import extract_strings

    text = "\n".join(item[1] for item in extract_strings(read_artifact(path), min_length=5))
    rows: list[list[str]] = []
    seen: set[str] = set()
    for kind, pattern in IOC_PATTERNS.items():
        for match in pattern.findall(text):
            if match in seen:
                continue
            seen.add(match)
            rows.append([kind, match[:120]])
    TerminalUI.print_table(f"IOCs · {path.name}", ["TIPO", "VALOR"], rows[:300] or [["—", "sin indicadores"]])
    return True


def _cmd_carve(ctx: REContext, parts: list[str]) -> bool:
    path = _need_path(ctx, parts[0] if parts else "", "/carve <imagen> [salida]")
    if not path:
        return True
    out = Path(parts[1]).expanduser() if len(parts) > 1 else ctx.workspace / f"carved_{path.stem}"
    result = carve(read_artifact(path), out)
    rows = [[f"0x{item['offset']:x}", item["kind"], item["size"], Path(str(item["path"])).name] for item in result["carved"][:200]]
    TerminalUI.print_table(f"Carving · {path.name} ({result['count']})", ["OFFSET", "TIPO", "TAMAÑO", "ARCHIVO"], rows or [["—", "", "", "nada encontrado"]])
    TerminalUI.print_box("Salida", [str(result["output_dir"])])
    return True


def _cmd_recover(ctx: REContext, parts: list[str]) -> bool:
    path = _need_path(ctx, parts[0] if parts else "", "/recover <imagen> [salida]")
    if not path:
        return True
    out = Path(parts[1]).expanduser() if len(parts) > 1 else ctx.workspace / f"recovered_{path.stem}"
    result = recover(path, out)
    TerminalUI.print_box(f"Recuperación · {path.name}", [f"motor: {result.get('engine')}", f"archivos: {result.get('count')}", f"salida: {out}"])
    return True


def _cmd_extract(ctx: REContext, parts: list[str]) -> bool:
    path = _need_path(ctx, parts[0] if parts else "", "/extract <archivo> [salida]")
    if not path:
        return True
    out = Path(parts[1]).expanduser() if len(parts) > 1 else ctx.workspace / f"extracted_{path.stem}"
    result = extract_archive(path, out)
    TerminalUI.print_box("Extracción segura", [f"extraídos: {len(result['extracted'])}", f"omitidos: {len(result['skipped'])}", f"salida: {out}"])
    return True


def _cmd_unpack(ctx: REContext, parts: list[str]) -> bool:
    path = _need_path(ctx, parts[0] if parts else "", "/unpack <ruta> [salida]")
    if not path:
        return True
    import shutil
    import subprocess

    data = read_artifact(path)
    if b"UPX!" in data and shutil.which("upx"):
        out = Path(parts[1]).expanduser() if len(parts) > 1 else ctx.workspace / f"unpacked_{path.stem}"
        out.parent.mkdir(parents=True, exist_ok=True)
        completed = subprocess.run(["upx", "-d", str(path), "-o", str(out)], capture_output=True, text=True, timeout=300, check=False)
        TerminalUI.print_box("UPX", [(completed.stdout + completed.stderr)[:1000], f"salida: {out}"])
        return True
    TerminalUI.print_box("Unpack", ["No se detectó un packer soportado (UPX) o falta la herramienta. Prueba /extract o instala upx con /tools install upx."])
    return True


def _cmd_firmware(ctx: REContext, parts: list[str]) -> bool:
    path = _need_path(ctx, parts[0] if parts else "", "/firmware <imagen> [salida]")
    if not path:
        return True
    import shutil
    import subprocess

    out = Path(parts[1]).expanduser() if len(parts) > 1 else ctx.workspace / f"firmware_{path.stem}"
    if shutil.which("binwalk"):
        out.mkdir(parents=True, exist_ok=True)
        completed = subprocess.run(["binwalk", "-e", "--directory", str(out), str(path)], capture_output=True, text=True, timeout=1800, check=False)
        TerminalUI.print_box("binwalk", [(completed.stdout or completed.stderr)[:2000], f"salida: {out}"])
        return True
    result = carve(read_artifact(path), out)
    TerminalUI.print_box("Firmware (carver interno)", [f"binwalk no está instalado; carving interno encontró {result['count']} artefactos.", f"salida: {out}", "Instala binwalk con /tools install binwalk."])
    return True


def _cmd_signature(ctx: REContext, parts: list[str]) -> bool:
    path = _need_path(ctx, parts[0] if parts else "", "/signature <ruta> [offset]")
    if not path:
        return True
    offset = int(parts[1], 0) if len(parts) > 1 else 0
    data = read_artifact(path)[offset : offset + 32]
    if not data:
        TerminalUI.print_box("Signature", ["Offset fuera de rango."])
        return True
    pattern = " ".join(f"{b:02X}" for b in data)
    rule = (
        "rule KSPR_Custom_Signature\n{\n    meta:\n"
        f"        description = \"Firma en {path.name}+0x{offset:x}\"\n        severity = \"medium\"\n"
        "    strings:\n"
        f"        $sig = {{ {pattern} }}\n"
        "    condition:\n        $sig\n}"
    )
    TerminalUI.print_box(f"Firma · {path.name} @0x{offset:x}", rule.splitlines())
    return True


def _cmd_diff(ctx: REContext, parts: list[str]) -> bool:
    if len(parts) < 2:
        TerminalUI.print_box("Uso", ["/diff <ruta_a> <ruta_b>"])
        return True
    left = ctx.resolve(parts[0])
    right = ctx.resolve(parts[1])
    if not left or not right:
        TerminalUI.print_box("Diff", ["Ambas rutas deben existir."])
        return True
    a = analyze_artifact(left)
    b = analyze_artifact(right)
    columns = ["CAMPO", left.name, right.name]
    rows = [
        ["sha256", a.hashes.get("sha256", "")[:16], b.hashes.get("sha256", "")[:16]],
        ["tamaño", a.size, b.size],
        ["entropía", a.entropy, b.entropy],
        ["secciones", len(a.sections), len(b.sections)],
        ["símbolos", len(a.symbols), len(b.symbols)],
        ["imports", len(a.imports), len(b.imports)],
    ]
    TerminalUI.print_table("Diff de artefactos", columns, rows)
    return True


def _cmd_callgraph(ctx: REContext, parts: list[str]) -> bool:
    report = _format_artifact(ctx, " ".join(parts), "callgraph")
    if not report:
        return True
    children = [("símbolos", report.symbols[:60] or ["(sin símbolos)"]), ("imports", report.imports[:40] or ["(sin imports)"])]
    TerminalUI.print_tree(f"Callgraph (simbólico) · {report.path}", Path(report.path).name, children)
    return True


def _cmd_xrefs(ctx: REContext, parts: list[str]) -> bool:
    if len(parts) < 2:
        TerminalUI.print_box("Uso", ["/xrefs <ruta> <símbolo|addr>"])
        return True
    report = _format_artifact(ctx, parts[0], "xrefs")
    if not report:
        return True
    needle = parts[1].lower()
    matches = [s for s in report.symbols if needle in s.lower()][:40]
    TerminalUI.print_box(f"Xrefs · {needle}", matches or ["Sin coincidencias simbólicas."])
    return True


def _cmd_sbom(ctx: REContext, parts: list[str]) -> bool:
    report = _format_artifact(ctx, " ".join(parts), "sbom")
    if not report:
        return True
    libs = report.metadata.get("libraries") or report.imports
    TerminalUI.print_table(f"SBOM (imports) · {report.path}", ["COMPONENTE"], [[item] for item in libs[:300]] or [["(sin componentes)"]])
    return True


def _cmd_index(ctx: REContext, parts: list[str]) -> bool:
    path = _need_path(ctx, " ".join(parts), "/index <ruta>")
    if not path:
        return True
    from kspr_engine.memory import VectorMemory

    memory = VectorMemory(Path.home() / ".kspr" / "memory")
    report = analyze_artifact(path)
    indexed = 0
    for index, (offset, text) in enumerate(report.strings):
        if len(text) < 6:
            continue
        memory.add_document(f"{path.name}:str:{index}", text, {"artifact": str(path), "kind": "string", "offset": offset})
        indexed += 1
    for symbol in report.symbols[:200]:
        memory.add_document(f"{path.name}:sym:{symbol}", symbol, {"artifact": str(path), "kind": "symbol"})
        indexed += 1
    TerminalUI.print_box("Indexado", [f"Artefacto: {path.name}", f"Documentos indexados: {indexed}", "Usa /ask <ruta> <pregunta> para consultar con contexto recuperado."])
    return True


def _cmd_pcap(ctx: REContext, parts: list[str]) -> bool:
    path = _need_path(ctx, parts[0] if parts else "", "/pcap <ruta>")
    if not path:
        return True
    from kspr_engine.re.network.pcap import analyze_pcap, available

    if not available():
        TerminalUI.print_box("PCAP", ["scapy no está instalado. Instala el extra [re]."])
        return True
    result = analyze_pcap(path)
    if result.get("error"):
        TerminalUI.print_box("PCAP", [str(result["error"])])
        return True
    TerminalUI.print_box(f"PCAP · {path.name}", [
        f"Paquetes: {result['packets']}",
        f"Protocolos: {result['protocols']}",
        f"Hosts HTTP: {len(result['http_hosts'])} · DNS: {len(result['dns_queries'])}",
    ])
    if result["dns_queries"]:
        TerminalUI.print_table("DNS", ["CONSULTA", "REPETICIONES"], [[name, count] for name, count in result["dns_queries"][:40]])
    if result["endpoints"]:
        TerminalUI.print_table("Endpoints", ["FLUJO", "PAQUETES"], [[flow, count] for flow, count in result["endpoints"][:40]])
    if result["http_hosts"]:
        TerminalUI.print_table("HTTP Hosts", ["HOST", "REPETICIONES"], [[host, count] for host, count in result["http_hosts"][:40]])
    return True


async def _cmd_ask(ctx: REContext, parts: list[str]) -> bool:
    if len(parts) < 2:
        TerminalUI.print_box("Uso", ["/ask <ruta> <pregunta>"])
        return True
    path = ctx.resolve(parts[0])
    if not path:
        TerminalUI.print_box("Ask", ["Artefacto no encontrado."])
        return True
    question = " ".join(parts[1:])
    report = analyze_artifact(path)
    context = [
        f"ARTEFACTO: {report.path}",
        f"TIPO: {report.kind} ({report.description})",
        f"ENTROPÍA: {report.entropy} · SHA256: {report.hashes.get('sha256')}",
        f"SECCIONES: {[s.get('name') for s in report.sections][:20]}",
        f"IMPORTS: {report.imports[:40]}",
        f"EXPORTS: {report.exports[:40]}",
    ]
    try:
        from kspr_engine.memory import VectorMemory

        memory = VectorMemory(Path.home() / ".kspr" / "memory")
        retrieved = [item for item in memory.search(question, top_k=30) if item.get("metadata", {}).get("artifact") == str(path)][:10]
        if retrieved:
            context.append("CONTEXTO RECUPERADO (memoria):")
            context.extend(f"  [{item['score']}] {item['content'][:160]}" for item in retrieved)
    except Exception:
        pass
    context.append("STRINGS (muestra):")
    context.append("\n".join(text for _off, text in report.strings[:120]))
    prompt = (
        "Eres KSPR I, experto en ingeniería inversa. Responde en texto plano sin markdown. "
        "Ancla cada afirmación a la evidencia de offsets/strings cuando sea posible.\n\n"
        f"PREGUNTA: {question}\n\nEVIDENCIA:\n" + "\n".join(context)
    )
    response = await ctx.ai_complete(prompt)
    TerminalUI.print_response(f"Ask · {path.name}", response)
    return True


def _cmd_report(ctx: REContext, parts: list[str]) -> bool:
    path = _need_path(ctx, parts[0] if parts else "", "/report <ruta> [salida]")
    if not path:
        return True
    report = analyze_artifact(path)
    out_dir = Path(parts[1]).expanduser() if len(parts) > 1 else ctx.workspace / "kspr-reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# KSPR Report — {path.name}",
        "",
        f"- Tipo: {report.kind} ({report.description})",
        f"- Tamaño: {report.size} bytes",
        f"- Entropía: {report.entropy}",
        f"- SHA-256: {report.hashes.get('sha256')}",
        f"- Secciones: {len(report.sections)}",
        f"- Imports: {len(report.imports)}",
        f"- Exports: {len(report.exports)}",
        "",
        "## Hallazgos",
        "",
    ]
    for finding in report.findings:
        lines.append(f"- [{finding.severity}] {finding.title}: {finding.description}")
        for evidence in finding.evidence[:6]:
            lines.append(f"  - {evidence.label()}")
    target = out_dir / f"{path.stem}.report.md"
    target.write_text("\n".join(lines), encoding="utf-8")
    import json

    (out_dir / f"{path.stem}.report.json").write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    TerminalUI.print_box("Reporte generado", [str(target), str(out_dir / f"{path.stem}.report.json")])
    return True


def _arch_of(report: ArtifactReport) -> str:
    metadata = report.metadata.get("format") or {}
    machine = str(metadata.get("machine", "")).lower()
    for key in ("x86-64", "x86", "aarch64", "arm", "mips", "riscv", "powerpc"):
        if key in machine:
            return key
    return "x86-64"


_HANDLERS = {
    "tools": _cmd_tools,
    "recon": _cmd_recon,
    "file": _cmd_file,
    "strings": _cmd_strings,
    "hex": _cmd_hex,
    "sections": _cmd_sections,
    "imports": _cmd_imports,
    "exports": _cmd_exports,
    "symbols": _cmd_symbols,
    "entropy": _cmd_entropy,
    "hashes": _cmd_hashes,
    "disasm": _cmd_disasm,
    "decompile": _cmd_decompile,
    "pseudo": _cmd_pseudo,
    "cfg": _cmd_cfg,
    "graph": _cmd_graph,
    "packer": _cmd_packer,
    "yara": _cmd_yara,
    "capa": _cmd_capa,
    "crypto": _cmd_crypto,
    "iocs": _cmd_iocs,
    "carve": _cmd_carve,
    "recover": _cmd_recover,
    "extract": _cmd_extract,
    "unpack": _cmd_unpack,
    "firmware": _cmd_firmware,
    "signature": _cmd_signature,
    "diff": _cmd_diff,
    "callgraph": _cmd_callgraph,
    "xrefs": _cmd_xrefs,
    "sbom": _cmd_sbom,
    "ask": _cmd_ask,
    "report": _cmd_report,
    "pcap": _cmd_pcap,
    "index": _cmd_index,
}
