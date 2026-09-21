"""PE parsing via pefile (with a LIEF fallback)."""

from __future__ import annotations

from typing import Any

PE_MACHINES = {
    0x014C: "x86", 0x8664: "x86-64", 0x01C0: "ARM", 0xAA64: "ARM64",
    0x0200: "IA64", 0x01C4: "ARMv7",
}
SUSPICIOUS_IMPORTS = {
    "VirtualAlloc", "VirtualProtect", "WriteProcessMemory", "CreateRemoteThread",
    "SetWindowsHookEx", "GetProcAddress", "LoadLibraryA", "LoadLibraryW",
    "WinExec", "ShellExecuteA", "ShellExecuteW", "URLDownloadToFileA",
    "InternetOpenA", "InternetReadFile", "RegSetValueExA", "NtUnmapViewOfSection",
}


def parse_pe(path: str) -> dict[str, Any]:
    try:
        return _parse_with_pefile(path)
    except Exception:
        return _parse_with_lief(path)


def _parse_with_pefile(path: str) -> dict[str, Any]:
    import pefile  # type: ignore

    pe = pefile.PE(path, fast_load=True)
    pe.parse_data_directories()
    machine = pe.FILE_HEADER.Machine
    result: dict[str, Any] = {
        "format": "PE",
        "machine": PE_MACHINES.get(machine, hex(machine)),
        "timestamp": pe.FILE_HEADER.TimeDateStamp,
        "entry": pe.OPTIONAL_HEADER.AddressOfEntryPoint,
        "image_base": pe.OPTIONAL_HEADER.ImageBase,
        "subsystem": pe.OPTIONAL_HEADER.Subsystem,
        "sections": [],
        "imports": [],
        "exports": [],
        "symbols": [],
        "imphash": "",
    }
    from ..traits import entropy as _entropy

    for section in pe.sections:
        name = section.Name.rstrip(b"\x00").decode("utf-8", "replace")
        characteristics = section.Characteristics
        result["sections"].append({
            "name": name,
            "addr": section.VirtualAddress,
            "size": section.SizeOfRawData,
            "entropy": round(section.get_entropy(), 3),
            "permissions": _section_permissions(characteristics),
            "raw_entropy": round(_entropy(section.get_data() or b""), 3),
        })
    if hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
        for entry in pe.DIRECTORY_ENTRY_IMPORT:
            dll = entry.dll.decode("utf-8", "replace")
            functions = [imp.name.decode("utf-8", "replace") for imp in entry.imports if imp.name]
            result["imports"].append({"dll": dll, "functions": functions})
    if hasattr(pe, "DIRECTORY_ENTRY_EXPORT"):
        for symbol in pe.DIRECTORY_ENTRY_EXPORT.symbols:
            if symbol.name:
                result["exports"].append(symbol.name.decode("utf-8", "replace"))
    try:
        result["imphash"] = pe.get_imphash()
    except Exception:
        pass
    result["suspicious_imports"] = sorted(
        {fn for entry in result["imports"] for fn in entry["functions"] if fn in SUSPICIOUS_IMPORTS}
    )
    return result


def _parse_with_lief(path: str) -> dict[str, Any]:
    import lief  # type: ignore

    binary = lief.parse(path)
    if binary is None:
        raise ValueError("LIEF no pudo interpretar el PE")
    return {
        "format": "PE",
        "entry": getattr(binary, "entrypoint", 0),
        "sections": [
            {"name": section.name, "addr": section.virtual_address, "size": section.size, "entropy": round(getattr(section, "entropy", 0.0), 3), "permissions": "---"}
            for section in getattr(binary, "sections", [])
        ],
        "imports": [],
        "exports": [],
        "symbols": [],
    }


def _section_permissions(characteristics: int) -> str:
    perms = ""
    perms += "R" if characteristics & 0x40000000 else "-"
    perms += "W" if characteristics & 0x80000000 else "-"
    perms += "X" if characteristics & 0x20000000 else "-"
    return perms
