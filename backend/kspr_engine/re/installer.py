"""Detection and installation of external reverse-engineering tools.

The author authorized automatic installation. Installations still report every
command they run and degrade gracefully when a package manager or permission
is unavailable.
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ToolSpec:
    key: str
    binary: str
    description: str
    apt: str = ""
    dnf: str = ""
    pacman: str = ""
    brew: str = ""
    pip: str = ""
    critical: bool = False


TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec("radare2", "r2", "Desensamblador/decompilador r2 (pdc)", apt="radare2", dnf="radare2", pacman="radare2", brew="radare2", critical=True),
    ToolSpec("rizin", "rizin", "Suite Rizin (fork de radare2)", apt="rizin", dnf="rizin", pacman="rizin", brew="rizin"),
    ToolSpec("binwalk", "binwalk", "Análisis y extracción de firmware", apt="binwalk", dnf="binwalk", pacman="binwalk", brew="binwalk", critical=True),
    ToolSpec("yara", "yara", "Motor de reglas YARA (CLI)", apt="yara", dnf="yara", pacman="yara", brew="yara"),
    ToolSpec("capa", "capa", "Detección de capacidades MITRE ATT&CK", pip="flare-capa"),
    ToolSpec("upx", "upx", "Empaquetador/desempaquetador UPX", apt="upx-ucl", dnf="upx", pacman="upx", brew="upx"),
    ToolSpec("jadx", "jadx", "Decompilador JVM/Android", apt="jadx", dnf="jadx", pacman="jadx", brew="jadx", critical=True),
    ToolSpec("apktool", "apktool", "Ingeniería inversa de APK", apt="apktool", dnf="apktool", pacman="apktool", brew="apktool"),
    ToolSpec("ghidra", "analyzeHeadless", "Decompilador Ghidra (headless)", brew="ghidra"),
    ToolSpec("retdec", "retdec-decompiler", "Decompilador RetDec", pip="retdec-python"),
    ToolSpec("foremost", "foremost", "Carving forense", apt="foremost", dnf="foremost", pacman="foremost", brew="foremost"),
    ToolSpec("scalpel", "scalpel", "Carving forense alternativo", apt="scalpel", dnf="scalpel", pacman="scalpel", brew="scalpel"),
    ToolSpec("testdisk", "photorec", "Recuperación de archivos borrados", apt="testdisk", dnf="testdisk", pacman="testdisk", brew="testdisk"),
    ToolSpec("sleuthkit", "fls", "Sleuth Kit (fls/icat)", apt="sleuthkit", dnf="sleuthkit", pacman="sleuthkit", brew="sleuthkit"),
    ToolSpec("7z", "7z", "7-Zip para extracción total", apt="p7zip-full", dnf="p7zip", pacman="p7zip", brew="p7zip"),
    ToolSpec("strace", "strace", "Trazado de syscalls", apt="strace", dnf="strace", pacman="strace", brew="strace"),
    ToolSpec("gdb", "gdb", "Depurador GNU", apt="gdb", dnf="gdb", pacman="gdb", brew="gdb"),
    ToolSpec("tshark", "tshark", "Análisis de capturas de red", apt="tshark", dnf="wireshark-cli", pacman="wireshark-cli", brew="wireshark"),
    ToolSpec("unblob", "unblob", "Extracción de firmware moderna", pip="unblob"),
)

STATE_FILE = Path.home() / ".kspr" / "tools.json"


def _os_family() -> str:
    system = platform.system().lower()
    if system == "darwin":
        return "brew"
    if system == "windows":
        return "winget"
    return "linux"


def _linux_manager() -> str:
    for manager, package in (("apt-get", "apt"), ("dnf", "dnf"), ("pacman", "pacman"), ("yum", "dnf")):
        if shutil.which(manager):
            return package
    return ""


def detect() -> list[dict[str, object]]:
    """Report which RE tools are present on the system."""
    result = []
    for spec in TOOLS:
        path = shutil.which(spec.binary)
        result.append({
            "key": spec.key,
            "binary": spec.binary,
            "installed": bool(path),
            "path": path or "",
            "description": spec.description,
            "critical": spec.critical,
        })
    return result


def status() -> dict[str, object]:
    tools = detect()
    return {
        "platform": platform.platform(),
        "manager": "brew" if _os_family() == "brew" else (_linux_manager() or "winget"),
        "installed": [t["key"] for t in tools if t["installed"]],
        "missing": [t["key"] for t in tools if not t["installed"]],
        "tools": tools,
    }


def _package_for(spec: ToolSpec, manager: str) -> str:
    return getattr(spec, manager, "") if manager in {"apt", "dnf", "pacman", "brew", "pip"} else ""


def _install_command(spec: ToolSpec, manager: str) -> list[str]:
    package = _package_for(spec, manager)
    if not package:
        return []
    if manager == "apt":
        return ["apt-get", "install", "-y", package]
    if manager == "dnf":
        return ["dnf", "install", "-y", package]
    if manager == "pacman":
        return ["pacman", "-S", "--noconfirm", package]
    if manager == "brew":
        return ["brew", "install", package]
    if manager == "pip":
        return [os.sys.executable, "-m", "pip", "install", package]
    return []


def install(keys: list[str] | None = None, only_critical: bool = False) -> dict[str, object]:
    """Install the requested (or all missing) tools using the OS package manager."""
    manager = "brew" if _os_family() == "brew" else _linux_manager()
    if not manager:
        manager = "pip"
    targets = [spec for spec in TOOLS if (not keys or spec.key in keys) and (not only_critical or spec.critical)]
    results = []
    for spec in targets:
        if shutil.which(spec.binary):
            results.append({"key": spec.key, "status": "already-installed"})
            continue
        command = _install_command(spec, manager)
        if not command:
            results.append({"key": spec.key, "status": "no-package", "manager": manager, "hint": f"Instala {spec.binary} manualmente"})
            continue
        try:
            completed = subprocess.run(command, capture_output=True, text=True, timeout=1800, check=False)
            results.append({
                "key": spec.key,
                "status": "installed" if shutil.which(spec.binary) or completed.returncode == 0 else "failed",
                "command": " ".join(command),
                "returncode": completed.returncode,
                "output": (completed.stdout + completed.stderr)[-1200:],
            })
        except (OSError, subprocess.SubprocessError) as exc:
            results.append({"key": spec.key, "status": "error", "command": " ".join(command), "error": str(exc)})
    _save_state(results)
    return {"manager": manager, "results": results}


def _save_state(results: list[dict[str, object]]) -> None:
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        history = []
        if STATE_FILE.is_file():
            history = json.loads(STATE_FILE.read_text(encoding="utf-8")).get("history", [])
        history.append({"results": results})
        STATE_FILE.write_text(json.dumps({"history": history[-20:]}, ensure_ascii=False, indent=2), encoding="utf-8")
    except (OSError, json.JSONDecodeError):
        pass
