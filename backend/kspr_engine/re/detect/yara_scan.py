"""YARA scanning with embedded rules and optional user rule sets."""

from __future__ import annotations

from pathlib import Path

from ..models import Evidence, Finding

BUILTIN_RULES = r"""
rule KSPR_Packer_UPX {
    meta:
        description = "UPX packer marker"
        severity = "high"
    strings:
        $a = "UPX!"
    condition:
        $a
}

rule KSPR_Suspicious_PowerShell {
    meta:
        description = "PowerShell encoded command patterns"
        severity = "medium"
    strings:
        $a = "powershell" nocase
        $b = "-enc" nocase
        $c = "FromBase64String" nocase
    condition:
        any of them
}

rule KSPR_Shell_Command {
    meta:
        description = "Shell invocation strings"
        severity = "low"
    strings:
        $a = "/bin/sh"
        $b = "/bin/bash"
        $c = "cmd.exe" nocase
    condition:
        any of them
}

rule KSPR_Download_Exec {
    meta:
        description = "Download-and-execute behaviour indicators"
        severity = "high"
    strings:
        $a = "URLDownloadToFile" nocase
        $b = "WinExec" nocase
        $c = "InternetOpen" nocase
        $d = "curl " nocase
        $e = "wget " nocase
    condition:
        2 of them
}

rule KSPR_Credential_Theft {
    meta:
        description = "Credential access indicators"
        severity = "critical"
    strings:
        $a = "mimikatz" nocase
        $b = "sekurlsa" nocase
        $c = "lsass" nocase
    condition:
        any of them
}

rule KSPR_Ransom_Note {
    meta:
        description = "Ransomware note markers"
        severity = "critical"
    strings:
        $a = "your files have been encrypted" nocase
        $b = "bitcoin" nocase
        $c = "decrypt" nocase
    condition:
        2 of them
}
"""


def _compile(rules_source: str | None, rules_path: str | None):
    import yara  # type: ignore

    sources: list[str] = [BUILTIN_RULES]
    if rules_source:
        sources.append(rules_source)
    if rules_path:
        candidate = Path(rules_path).expanduser()
        if candidate.is_dir():
            for rule_file in sorted(candidate.rglob("*.yar")) + sorted(candidate.rglob("*.yara")):
                sources.append(rule_file.read_text(encoding="utf-8", errors="replace"))
        elif candidate.is_file():
            sources.append(candidate.read_text(encoding="utf-8", errors="replace"))
    combined = "\n".join(sources)
    return yara.compile(source=combined)


def scan_yara(data: bytes, rules_source: str | None = None, rules_path: str | None = None) -> list[Finding]:
    """Scan a byte buffer with built-in (and optional user) YARA rules."""
    try:
        rules = _compile(rules_source, rules_path)
    except ImportError:
        return [Finding(title="YARA no disponible", category="yara", severity="info", description="Instala yara-python para habilitar el escaneo.")]
    except Exception as exc:
        return [Finding(title="Error compilando reglas YARA", category="yara", severity="info", description=str(exc))]

    matches = rules.match(data=data)
    findings: list[Finding] = []
    for match in matches:
        meta = getattr(match, "meta", {}) or {}
        evidence: list[Evidence] = []
        for string_match in getattr(match, "strings", []) or []:
            for instance in getattr(string_match, "instances", []) or []:
                evidence.append(Evidence("yara", f"{getattr(string_match, 'identifier', '?')}", offset=getattr(instance, "offset", None)))
        findings.append(Finding(
            title=f"Regla YARA: {match.rule}",
            category="yara",
            severity=str(meta.get("severity", "medium")),
            description=str(meta.get("description", "Regla YARA coincidente.")),
            evidence=evidence[:20],
            metadata={"rule": match.rule},
        ))
    return findings


def scan_with_rules(path: str, rules_path: str | None = None) -> list[Finding]:
    data = Path(path).read_bytes()
    return scan_yara(data, rules_path=rules_path)
