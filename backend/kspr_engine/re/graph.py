"""Control-flow and call graph construction/export."""

from __future__ import annotations

from typing import Any

BRANCH_MNEMONICS = {
    "jmp", "je", "jne", "jz", "jnz", "jg", "jge", "jl", "jle", "ja", "jae",
    "jb", "jbe", "js", "jns", "jo", "jno", "jp", "jnp", "call", "ret", "retn",
    "beq", "bne", "b", "bl", "bx", "blr", "br",
}


def build_cfg(instructions: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a linear+branch control-flow graph from a disassembly listing."""
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, int]] = []
    addresses = [int(insn["address"]) for insn in instructions]
    address_set = set(addresses)
    for index, insn in enumerate(instructions):
        address = int(insn["address"])
        mnemonic = str(insn["mnemonic"]).lower()
        nodes.append({"address": address, "label": f"{insn['mnemonic']} {insn.get('op_str', '')}".strip()})
        if index + 1 < len(instructions):
            edges.append({"source": address, "target": int(instructions[index + 1]["address"]), "kind": "flow"})
        if mnemonic in BRANCH_MNEMONICS and mnemonic.startswith(("j", "b")) and not mnemonic.startswith("bl"):
            operand = str(insn.get("op_str", "")).split(",")[0].strip()
            try:
                target = int(operand, 16)
            except ValueError:
                continue
            if target in address_set:
                edges.append({"source": address, "target": target, "kind": "branch"})
    return {"nodes": nodes, "edges": edges}


def to_mermaid(cfg: dict[str, Any], title: str = "CFG") -> str:
    lines = ["---", f"title: {title}", "---", "flowchart TD"]
    for node in cfg["nodes"]:
        address = node["address"]
        label = node["label"].replace('"', "'")
        lines.append(f'    n{address:x}["0x{address:x}: {label}"]')
    for edge in cfg["edges"]:
        arrow = "-->" if edge["kind"] == "flow" else "==>"
        lines.append(f"    n{edge['source']:x} {arrow} n{edge['target']:x}")
    return "\n".join(lines)


def to_dot(cfg: dict[str, Any], title: str = "CFG") -> str:
    lines = [f'digraph "{title}" {{', "    rankdir=TB;"]
    for node in cfg["nodes"]:
        address = node["address"]
        label = node["label"].replace('"', "'")
        lines.append(f'    n{address:x} [label="0x{address:x}: {label}"];')
    for edge in cfg["edges"]:
        style = "solid" if edge["kind"] == "flow" else "dashed"
        lines.append(f"    n{edge['source']:x} -> n{edge['target']:x} [style={style}];")
    lines.append("}")
    return "\n".join(lines)


def export(cfg: dict[str, Any], fmt: str = "mermaid", title: str = "CFG") -> str:
    return to_dot(cfg, title) if fmt.lower() in {"dot", "graphviz"} else to_mermaid(cfg, title)
