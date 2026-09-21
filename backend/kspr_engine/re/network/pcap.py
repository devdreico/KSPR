"""PCAP analysis using scapy when available."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

HTTP_HOST = re.compile(rb"(?:Host:\s*)([A-Za-z0-9._-]+)")
HTTP_URI = re.compile(rb"(?:GET|POST|PUT|HEAD|DELETE)\s+(\S{1,120})\s+HTTP")


def available() -> bool:
    try:
        import scapy  # noqa: F401

        return True
    except ImportError:
        return False


def analyze_pcap(path: str | Path, max_packets: int = 5000) -> dict[str, object]:
    """Summarize protocols, endpoints, DNS names, HTTP hosts and payload strings."""
    if not available():
        return {"error": "scapy no está instalado; instala el extra [re] o /tools install."}
    from scapy.all import DNS, DNSQR, IP, TCP, UDP, IPv6, Raw, rdpcap  # type: ignore

    try:
        packets = rdpcap(str(path))
    except Exception as exc:
        return {"error": f"No es una captura de red válida: {exc}"}
    protocols: Counter[str] = Counter()
    endpoints: Counter[str] = Counter()
    dns_queries: Counter[str] = Counter()
    http_hosts: Counter[str] = Counter()
    uris: Counter[str] = Counter()
    payloads: list[str] = []

    for packet in packets[:max_packets]:
        if IP in packet:
            protocols["IPv4"] += 1
            source, destination = packet[IP].src, packet[IP].dst
        elif IPv6 in packet:
            protocols["IPv6"] += 1
            source, destination = packet[IPv6].src, packet[IPv6].dst
        else:
            protocols[packet.__class__.__name__] += 1
            continue
        if TCP in packet:
            protocols["TCP"] += 1
            endpoints[f"{source}:{packet[TCP].sport} -> {destination}:{packet[TCP].dport}"] += 1
        elif UDP in packet:
            protocols["UDP"] += 1
            endpoints[f"{source}:{packet[UDP].sport} -> {destination}:{packet[UDP].dport}"] += 1
        if DNS in packet and packet[DNS].qd is not None and isinstance(packet[DNS].qd, DNSQR):
            try:
                dns_queries[packet[DNS].qd.qname.decode("utf-8", "replace").rstrip(".")] += 1
            except (AttributeError, UnicodeDecodeError):
                pass
        if Raw in packet:
            raw = bytes(packet[Raw].load)
            for match in HTTP_HOST.findall(raw):
                http_hosts[match.decode("utf-8", "replace")] += 1
            for match in HTTP_URI.findall(raw):
                uris[match.decode("utf-8", "replace")] += 1
            printable = "".join(chr(b) if 32 <= b < 127 else " " for b in raw[:400]).strip()
            if len(printable) > 20:
                payloads.append(printable[:200])

    return {
        "packets": len(packets),
        "protocols": dict(protocols),
        "endpoints": endpoints.most_common(40),
        "dns_queries": dns_queries.most_common(40),
        "http_hosts": http_hosts.most_common(40),
        "uris": uris.most_common(40),
        "payload_samples": payloads[:40],
    }
