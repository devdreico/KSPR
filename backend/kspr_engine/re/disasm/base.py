"""Disassembly via capstone, with an objdump fallback."""

from __future__ import annotations

import re
import shutil
import subprocess
from typing import Any

ARCHITECTURES = {
    "x86": ("x86", 32),
    "x86-64": ("x86", 64),
    "arm": ("arm", 32),
    "aarch64": ("arm64", 64),
    "mips": ("mips", 32),
    "riscv": ("riscv", 64),
    "powerpc": ("ppc", 32),
}


def available_backends() -> list[str]:
    backends = []
    try:
        import capstone  # noqa: F401

        backends.append("capstone")
    except ImportError:
        pass
    if shutil.which("objdump"):
        backends.append("objdump")
    if shutil.which("r2") or shutil.which("radare2"):
        backends.append("radare2")
    return backends


def _capstone_md(arch: str):
    import capstone  # type: ignore

    name, bits = ARCHITECTURES.get(arch.lower(), ("x86", 64))
    mapping = {
        "x86": (capstone.CS_ARCH_X86, capstone.CS_MODE_64 if bits == 64 else capstone.CS_MODE_32),
        "arm": (capstone.CS_ARCH_ARM, capstone.CS_MODE_ARM),
        "arm64": (capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM),
        "mips": (capstone.CS_ARCH_MIPS, capstone.CS_MODE_MIPS32),
        "riscv": (capstone.CS_ARCH_RISCV, capstone.CS_MODE_RISCV64),
        "ppc": (capstone.CS_ARCH_PPC, capstone.CS_MODE_32),
    }
    cs_arch, cs_mode = mapping.get(name, mapping["x86"])
    md = capstone.Cs(cs_arch, cs_mode)
    md.detail = False
    return md


def disassemble(data: bytes, arch: str = "x86-64", base_address: int = 0, offset: int = 0, count: int = 64) -> list[dict[str, Any]]:
    """Disassemble `count` instructions from `offset` using capstone."""
    md = _capstone_md(arch)
    start = offset
    code = data[start : start + count * 16]
    instructions: list[dict[str, Any]] = []
    for insn in md.disasm(code, base_address + start):
        instructions.append({
            "address": insn.address,
            "mnemonic": insn.mnemonic,
            "op_str": insn.op_str,
            "bytes": insn.bytes.hex(),
            "size": insn.size,
        })
        if len(instructions) >= count:
            break
    return instructions


_OBJDUMP_LINE = re.compile(r"^\s*([0-9a-f]+):\s+((?:[0-9a-f]{2}\s)+)\s*(\S+)\s*(.*)$")


def objdump_disassemble(path: str, offset: int = 0, count: int = 64, tool: str = "objdump") -> list[dict[str, Any]]:
    """Disassemble a range of a binary using objdump."""
    if not shutil.which(tool):
        raise FileNotFoundError(f"{tool} no está disponible")
    command = [tool, "-d", "--no-show-raw-insn", f"--start-address={offset}", f"--stop-address={offset + count * 16}", path]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=60, check=False)
    instructions: list[dict[str, Any]] = []
    for line in completed.stdout.splitlines():
        match = _OBJDUMP_LINE.match(line)
        if not match:
            continue
        address, raw, mnemonic, operands = match.groups()
        instructions.append({
            "address": int(address, 16),
            "mnemonic": mnemonic,
            "op_str": operands.strip(),
            "bytes": raw.replace(" ", ""),
            "size": len(raw.split()),
        })
        if len(instructions) >= count:
            break
    return instructions
