"""Decompilation adapters (radare2, RetDec, Ghidra) and AI prompt builder."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

from ..disasm.base import disassemble

MAX_OUTPUT = 40_000


def available_decompilers() -> list[str]:
    found: list[str] = []
    if shutil.which("r2") or shutil.which("radare2"):
        found.append("radare2")
    if shutil.which("retdec-decompiler"):
        found.append("retdec")
    if shutil.which("ghidraRun") or shutil.which("analyzeHeadless"):
        found.append("ghidra")
    if shutil.which("jadx"):
        found.append("jadx")
    if shutil.which("ilspycmd"):
        found.append("ilspy")
    return found


def decompile(path: str, target: str | None = None, timeout: int = 180) -> dict[str, Any]:
    """Decompile a function/offset with the best available engine."""
    r2 = shutil.which("r2") or shutil.which("radare2")
    if r2:
        return _run_radare2(r2, path, target, timeout)
    retdec = shutil.which("retdec-decompiler")
    if retdec:
        return _run_retdec(retdec, path, timeout)
    return {
        "engine": "none",
        "output": "",
        "available": available_decompilers(),
        "message": "No hay decompilador instalado. Usa /tools install radare2 (o retdec) o /pseudo para decompilación asistida por IA.",
    }


def _run_radare2(r2: str, path: str, target: str | None, timeout: int) -> dict[str, Any]:
    location = target or "entry0"
    command = f"aaa; pdc @ {location}"
    completed = subprocess.run([r2, "-q", "-e", "scr.color=0", "-c", command, path], capture_output=True, text=True, timeout=timeout, check=False)
    output = (completed.stdout or completed.stderr)[:MAX_OUTPUT]
    return {"engine": "radare2", "target": location, "output": output, "available": available_decompilers(), "returncode": completed.returncode}


def _run_retdec(retdec: str, path: str, timeout: int) -> dict[str, Any]:
    out_path = str(Path(path).with_suffix(".c"))
    completed = subprocess.run([retdec, path, "-o", out_path], capture_output=True, text=True, timeout=timeout, check=False)
    output = ""
    if Path(out_path).is_file():
        output = Path(out_path).read_text(encoding="utf-8", errors="replace")[:MAX_OUTPUT]
    return {"engine": "retdec", "output": output or (completed.stdout + completed.stderr)[:MAX_OUTPUT], "available": available_decompilers(), "returncode": completed.returncode}


def build_ai_decompile_prompt(path: str, data: bytes, arch: str = "x86-64", offset: int = 0, count: int = 120) -> str:
    """Build a grounded prompt for AI-assisted pseudocode reconstruction."""
    instructions = disassemble(data, arch=arch, offset=offset, count=count)
    listing = "\n".join(f"0x{insn['address']:x}: {insn['mnemonic']} {insn['op_str']}" for insn in instructions)
    preview = data[offset : offset + 160].hex(" ")
    return (
        "Eres un ingeniero inverso experto. Reconstruye pseudocódigo C-like de la función a partir "
        "exclusivamente del desensamblado y bytes aportados. No inventes símbolos: quando no sepas un "
        "nombre usa sub_XXXX. Cada afirmación debe referenciar una dirección (0x...). Responde en texto "
        "plano sin markdown.\n\n"
        f"BINARIO: {path}\nARQUITECTURA: {arch}\nOFFSET: 0x{offset:x}\nBYTES: {preview}\n\n"
        f"DESENSAMBLADO:\n{listing}\n"
    )
