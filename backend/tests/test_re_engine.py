import zipfile
from pathlib import Path

import pytest
from kspr_engine.re.analyze import analyze_artifact
from kspr_engine.re.carve import carve
from kspr_engine.re.detect import detect_crypto, detect_packer
from kspr_engine.re.formats.archives import extract_archive, list_archive
from kspr_engine.re.graph import build_cfg, to_dot, to_mermaid
from kspr_engine.re.installer import detect, status
from kspr_engine.re.traits import (
    detect_type,
    entropy,
    entropy_blocks,
    extract_strings,
    find_embedded,
    hashes,
    hexdump,
    read_artifact,
)


def test_detect_type_recognizes_signatures():
    assert detect_type(b"\x7fELF\x02\x01\x01\x00")[0] == "elf"
    assert detect_type(b"MZ\x90\x00")[0] == "pe"
    assert detect_type(b"PK\x03\x04rest")[0] == "zip"
    assert detect_type(b"%PDF-1.7")[0] == "pdf"
    assert detect_type(b"plain ascii text")[0] == "text"


def test_entropy_extremes_and_blocks():
    assert entropy(b"") == 0.0
    assert entropy(b"AAAA" * 100) == 0.0
    assert entropy(bytes(range(256))) > 7.9
    blocks = entropy_blocks(b"A" * 2048, block_size=1024)
    assert blocks == [0.0, 0.0]


def test_strings_and_hexdump_and_hashes():
    data = b"\x00\x01hello\x00world\x00"
    strings = [text for _offset, text in extract_strings(data, min_length=4)]
    assert "hello" in strings and "world" in strings
    lines = hexdump(b"ABCD", offset=0, length=4)
    assert lines and lines[0].startswith("00000000")
    assert hashes(b"abc")["sha256"] == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def test_find_embedded_and_carve(tmp_path: Path):
    payload = b"prefix" + b"PK\x03\x04" + b"A" * 64 + b"suffix"
    embedded = find_embedded(payload)
    assert any(item["kind"] == "zip" for item in embedded)
    result = carve(payload, tmp_path)
    assert result["count"] >= 1


def test_packer_and_crypto_detection():
    findings = detect_packer(b"UPX!" + b"\x00" * 64)
    assert any("UPX" in finding.title for finding in findings)
    crypto = detect_crypto(bytes.fromhex("637c777bf26b6fc5"))
    assert any("AES" in finding.title for finding in crypto)


def test_scan_yara_builtin_rule():
    from kspr_engine.re.detect.yara_scan import scan_yara

    findings = scan_yara(b"UPX! compressed payload")
    assert any("UPX" in finding.title for finding in findings)


def test_analyze_artifact_zip_and_text(tmp_path: Path):
    archive = tmp_path / "ctx.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("a.txt", "hola")
    report = analyze_artifact(archive)
    assert report.kind == "zip"
    assert report.metadata["archive"]["count"] == 1

    text_file = tmp_path / "notes.md"
    text_file.write_text("contenido legible", encoding="utf-8")
    text_report = analyze_artifact(text_file)
    assert text_report.kind == "text"


def test_analyze_artifact_fake_elf_does_not_crash(tmp_path: Path):
    fake = tmp_path / "fake.elf"
    fake.write_bytes(b"\x7fELF" + b"\x00" * 64)
    report = analyze_artifact(fake)
    assert report.kind == "elf"
    assert report.hashes["md5"]


def test_archive_safe_extraction_blocks_traversal(tmp_path: Path):
    archive = tmp_path / "evil.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("../escape.txt", "no")
        handle.writestr("safe.txt", "sí")
    listing = list_archive(archive)
    assert listing["count"] == 2
    result = extract_archive(archive, tmp_path / "out")
    assert "safe.txt" in result["extracted"]
    assert not (tmp_path / "escape.txt").exists()


def test_cfg_export_formats():
    instructions = [
        {"address": 0x1000, "mnemonic": "mov", "op_str": "eax, 1"},
        {"address": 0x1002, "mnemonic": "jmp", "op_str": "0x1000"},
    ]
    cfg = build_cfg(instructions)
    assert len(cfg["nodes"]) == 2
    assert "flowchart" in to_mermaid(cfg)
    assert "digraph" in to_dot(cfg)


def test_installer_detect_and_status():
    tools = detect()
    assert isinstance(tools, list) and tools
    assert all({"key", "binary", "installed"} <= set(tool) for tool in tools)
    info = status()
    assert "installed" in info and "missing" in info


def test_read_artifact_missing_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        read_artifact(tmp_path / "nope.bin")


def test_pcap_analysis(tmp_path: Path):
    from kspr_engine.re.network import pcap_available

    if not pcap_available():
        pytest.skip("scapy no disponible")
    from kspr_engine.re.network.pcap import analyze_pcap
    from scapy.all import IP, TCP, Raw, wrpcap  # type: ignore

    packets = [IP(src="10.0.0.1", dst="10.0.0.2") / TCP(sport=1234, dport=80) / Raw(load=b"GET /x HTTP/1.1\r\nHost: example.com\r\n\r\n")]
    capture = tmp_path / "traffic.pcap"
    wrpcap(str(capture), packets)
    result = analyze_pcap(capture)
    assert result["packets"] == 1
    assert "TCP" in result["protocols"]
    assert any(host == "example.com" for host, _count in result["http_hosts"])


def test_agents_catalog_and_selection():
    from kspr_engine.agents import list_agents, plan_for, select_agent

    agents = list_agents()
    assert len(agents) >= 8
    assert select_agent("recon").key == "recon"
    assert select_agent("unknown") is None
    plan = plan_for("analizar malware sospechoso")
    assert any(step.agent == "crypto" for step in plan)
    assert all(step.commands for step in plan)
