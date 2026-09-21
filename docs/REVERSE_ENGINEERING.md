# KSPR Reverse Engineering Engine

El motor de ingeniería inversa de KSPR (`backend/kspr_engine/re/`) analiza
binarios, firmware, archivos y capturas **sin ejecutar el artefacto**. Cada
hallazgo conserva su evidencia (offset, símbolo o firma) para que el resultado
sea auditable.

## Principios

- **Nunca ejecutar por defecto.** El análisis dinámico está deshabilitado y solo
  se habilita con permiso explícito Accept Once/Always y sandbox aislado.
- **Degradación elegante.** Cada backend pesado (`lief`, `capstone`, `yara`,
  `radare2`, `ghidra`, `binwalk`…) es opcional; si falta, se usa un fallback en
  Python puro y se informa.
- **Evidencia primero.** Hashes, offsets, entropía y strings acompañan a cada
  conclusión.

## Módulos

| Módulo | Función |
| --- | --- |
| `traits.py` | Magic bytes, hashes (md5/sha1/sha256/tlsh), entropía, strings ASCII/UTF-16, hexdump, detección de artefactos embebidos. |
| `formats/elf.py` | ELF vía `pyelftools` (fallback LIEF): cabecera, secciones, símbolos, librerías, rpath/runpath. |
| `formats/pe.py` | PE vía `pefile`: máquina, timestamp, secciones, imports/exports, imphash, imports peligrosos. |
| `formats/archives.py` | Listado y extracción segura (anti zip-slip y bombas) de zip/tar/gz/bz2/xz/7z/rar. |
| `detect/packer.py` | Firmas de packers (UPX, ASPack, Themida…) y secciones de alta entropía. |
| `detect/yara.py` | Reglas YARA embebidas + reglas del usuario. |
| `detect/crypto.py` | Constantes AES/SHA/MD5 y alfabetos Base64. |
| `disasm/base.py` | Desensamblado con `capstone` y fallback `objdump`. |
| `decompile/base.py` | Adaptadores `radare2`/RetDec/Ghidra y prompt de pseudocódigo IA anclado a evidencia. |
| `carve/carver.py` | Carving por firma (png/jpeg/pdf/zip/gzip) y recuperación con `foremost`/`scalpel`. |
| `graph.py` | CFG/callgraph exportable a Mermaid/DOT. |
| `installer.py` | Detección e instalación de herramientas externas por gestor de paquetes. |
| `analyze.py` | Orquestador de triage + formato + detección de amenazas. |
| `agents/` | Subagentes (recon, static, disasm, decompiler, crypto, network, carver, writer, verifier, planner) y planificador. |

## Comandos del shell

```
/recon <ruta>            /sections <ruta>     /disasm <ruta> [off] [n]
/file <ruta>             /imports <ruta>      /decompile <ruta> [sym]
/hashes <ruta>           /exports <ruta>      /pseudo <ruta> [off]
/strings <ruta> [min]    /symbols <ruta>      /cfg <ruta>
/hex <ruta> [off] [len]  /entropy <ruta>      /graph <ruta> [fmt]
/packer <ruta>           /yara <ruta> [reglas] /crypto <ruta>
/iocs <ruta>             /pcap <ruta>         /index <ruta>
/carve <img> [out]       /recover <img> [out]
/extract <archivo> [out] /unpack <ruta>       /firmware <img> [out]
/signature <ruta> [off]  /report <ruta>       /ask <ruta> <pregunta>
/verify <ruta>           /agents [clave]      /plan <objetivo>
/tools [detect|install]  /sbom <ruta>         /memory
```

## API

- `GET /api/v1/re/tools` — estado de herramientas.
- `POST /api/v1/re/analyze` — triage/analítica de un artefacto subido (requiere
  `Authorization: Bearer`). El archivo se escribe en un temporal y se elimina.
- `POST /api/v1/re/carve` — carving de una imagen subida.

## Seguridad

- Los artefactos se reciben por upload, nunca por ruta del servidor.
- Extracción con defensas anti traversal, symlinks y bombas de descompresión.
- Límites de tamaño (64 MB API, 500 MB extracción) y timeouts en cada herramienta.
- El análisis dinámico requiere permiso explícito y aislamiento (Docker/namespaces).
