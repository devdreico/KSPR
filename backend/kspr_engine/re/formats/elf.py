"""ELF parsing via pyelftools (with a LIEF fallback)."""

from __future__ import annotations

from typing import Any

ELF_MACHINES = {
    0x03: "x86", 0x3E: "x86-64", 0x28: "ARM", 0xB7: "AArch64",
    0x08: "MIPS", 0x14: "PowerPC", 0x16: "S390", 0xF3: "RISC-V",
}
ELF_TYPES = {1: "REL", 2: "EXEC", 3: "DYN", 4: "CORE"}


def parse_elf(path: str) -> dict[str, Any]:
    """Return ELF header, sections, symbols and imported libraries."""
    try:
        return _parse_with_pyelftools(path)
    except Exception:
        return _parse_with_lief(path)


def _parse_with_pyelftools(path: str) -> dict[str, Any]:
    from elftools.elf.elffile import ELFFile  # type: ignore

    with open(path, "rb") as handle:
        elf = ELFFile(handle)
        header = elf.header
        machine = header["e_machine"]
        result: dict[str, Any] = {
            "format": "ELF",
            "class": "64-bit" if elf.elfclass == 64 else "32-bit",
            "endianness": "little" if elf.little_endian else "big",
            "type": ELF_TYPES.get(header["e_type"], str(header["e_type"])),
            "machine": ELF_MACHINES.get(machine, str(machine)),
            "entry": header["e_entry"],
            "sections": [],
            "symbols": [],
            "imports": [],
            "exports": [],
        }
        from ..traits import entropy as _entropy

        for section in elf.iter_sections():
            flags = int(section["sh_flags"])
            try:
                section_bytes = section.data()
            except Exception:
                section_bytes = b""
            result["sections"].append({
                "name": section.name,
                "type": str(section["sh_type"]),
                "addr": int(section["sh_addr"]),
                "size": int(section["sh_size"]),
                "permissions": _section_permissions(flags),
                "entropy": round(_entropy(section_bytes), 3),
            })
        for name in (".symtab", ".dynsym"):
            section = elf.get_section_by_name(name)
            if section is None:
                continue
            for symbol in section.iter_symbols():
                entry = symbol.entry
                info_type = entry["st_info"]["type"]
                symbol_name = entry["st_name"]
                result["symbols"].append(symbol_name)
                if info_type == "STT_FUNC":
                    result["exports"].append(symbol_name)
        dynamic = elf.get_section_by_name(".dynamic")
        if dynamic is not None:
            for tag in dynamic.iter_tags():
                if tag.entry.d_tag == "DT_NEEDED":
                    result["imports"].append(tag.needed)
                elif tag.entry.d_tag == "DT_RPATH":
                    result.setdefault("rpath", []).append(tag.rpath)
                elif tag.entry.d_tag == "DT_RUNPATH":
                    result.setdefault("runpath", []).append(tag.runpath)
        result["symbols"] = sorted(filter(None, set(result["symbols"])))
        result["exports"] = sorted(filter(None, set(result["exports"])))
        result["imports"] = sorted(set(result["imports"]))
        return result


def _parse_with_lief(path: str) -> dict[str, Any]:
    import lief  # type: ignore

    binary = lief.parse(path)
    if binary is None:
        raise ValueError("LIEF no pudo interpretar el ELF")
    result: dict[str, Any] = {
        "format": "ELF",
        "entry": getattr(binary, "entrypoint", 0),
        "machine": str(getattr(binary.header, "machine_type", "unknown")),
        "sections": [
            {
                "name": section.name,
                "addr": getattr(section, "virtual_address", 0),
                "size": getattr(section, "size", 0),
                "entropy": round(getattr(section, "entropy", 0.0), 3),
                "permissions": "---",
            }
            for section in getattr(binary, "sections", [])
        ],
        "symbols": [s.name for s in getattr(binary, "symbols", []) if s.name],
        "imports": sorted(set(getattr(binary, "libraries", []))),
        "exports": sorted({f.name for f in getattr(binary, "exported_functions", [])}),
    }
    return result


def _section_permissions(flags: int) -> str:
    perms = ""
    perms += "R" if flags & 0x4 else "-"
    perms += "W" if flags & 0x1 else "-"
    perms += "X" if flags & 0x2 else "-"
    return perms
