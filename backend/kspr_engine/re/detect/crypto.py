"""Cryptographic constant detection (AES, SHA, MD5, RC4, Base64 alphabets)."""

from __future__ import annotations

from ..models import Evidence, Finding

# Firmas de constantes conocidas -> (nombre, descripción, severidad)
CRYPTO_SIGNATURES: tuple[tuple[bytes, str, str, str], ...] = (
    (bytes.fromhex("637c777bf26b6fc5"), "AES S-box", "Tabla de sustitución AES detectada.", "medium"),
    (bytes.fromhex("52096ad53036a538"), "AES Te0", "Tabla Te0 de AES detectada.", "medium"),
    (bytes.fromhex("428a2f98d728ae22"), "SHA-256 K", "Constantes de ronda SHA-256 detectadas.", "medium"),
    (bytes.fromhex("6a09e667bb67ae85"), "SHA-256 IV", "Vector inicial SHA-256 detectado.", "medium"),
    (bytes.fromhex("67452301efcdab89"), "MD5/SHA-1 IV", "Vector inicial MD5/SHA-1 detectado.", "low"),
    (bytes.fromhex("0123456789abcdef"), "CRC/Init table", "Posible tabla de inicialización criptográfica.", "low"),
)

ALPHABET_MARKERS = (
    (b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/", "Base64 estándar", "low"),
    (b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_", "Base64 URL-safe", "low"),
)


def detect_crypto(data: bytes) -> list[Finding]:
    findings: list[Finding] = []
    for signature, name, description, severity in CRYPTO_SIGNATURES:
        offset = data.find(signature)
        if offset >= 0:
            findings.append(Finding(
                title=f"Constante criptográfica: {name}",
                category="crypto",
                severity=severity,
                description=description,
                evidence=[Evidence("constant", name, offset=offset)],
            ))
    for marker, name, severity in ALPHABET_MARKERS:
        offset = data.find(marker)
        if offset >= 0:
            findings.append(Finding(
                title=f"Alfabeto detectado: {name}",
                category="crypto",
                severity=severity,
                description="Alfabeto de codificación embebido (posible ofuscación o exfiltración).",
                evidence=[Evidence("alphabet", name, offset=offset)],
            ))
    return findings
