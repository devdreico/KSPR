# KSPR AI CLI TOOL

**Knowledge Source Parsing & Reconstruction Artificial Intelligence Command Line Interface Tool**

KSPR AI CLI TOOL es una herramienta de línea de comandos para descomponer y reconstruir procesos ingenieriles, sistemas legados, objetos técnicos y fuentes de conocimiento complejas. Convierte código, documentación, artefactos binarios y contexto disperso en una representación técnica estructurada, trazable y reutilizable por personas y agentes de IA.

Su principio es simple: separar lo que la evidencia demuestra de lo que el análisis infiere. KSPR identifica componentes, relaciones, flujos, dependencias, riesgos y preguntas abiertas; conserva las referencias que sustentan cada hallazgo y entrega un paquete de contexto que puede inspeccionarse, contrastarse y continuar desarrollándose.

## Qué resuelve

- **Descomposición de sistemas**: extrae interfaces, handlers, rutas HTTP, operaciones SQL, dependencias, eventos y mutaciones de estado.
- **Reconstrucción de conocimiento**: organiza múltiples fuentes en índices, inventarios, mapas de flujo, contratos, riesgos, contradicciones y preguntas abiertas.
- **Ingeniería inversa estática**: inspecciona archivos, binarios, firmware y capturas sin ejecutar el artefacto analizado; conserva hashes, offsets, símbolos y firmas.
- **Análisis progresivo**: combina respuesta directa para contextos pequeños con jobs asíncronos, streaming de progreso e iteraciones para contextos grandes.
- **Orquestación extensible**: conecta Gemini, proveedores OpenAI-compatible, modelos locales, MCP, plugins y capabilities externas bajo permisos explícitos.
- **Salida auditable**: exporta Markdown y JSON para que otro equipo, sistema o agente pueda verificar el origen de cada conclusión.

## Capacidades verificables

- Importación de archivos pegados, múltiples archivos, ZIP y repositorios Git mediante `--git-url`.
- Shell interactivo con sesiones persistentes, paleta `Ctrl/Cmd+K`, comandos slash, referencias `@archivo`, historial y configuración de agente.
- Catálogo de modelos consultable por API y modelos manuales con proveedor y endpoint compatible.
- `KSPR Local` para validar el flujo de conversación sin credenciales externas.
- Configuración portable en `examples/kspr.config.example.json`.
- UI React con estados de progreso observables y contexto de sesión.

## Ejecutar el motor

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
uvicorn kspr_engine.main:app --app-dir backend --reload
```

La API queda en `http://localhost:8000` y la documentación OpenAPI en `/docs`.

## Ejecutar la UI

```bash
cd frontend
npm install
npm run dev
```

La UI espera la API en `http://localhost:8000` o en `VITE_API_URL`.

Para Vercel, importa `frontend/` como proyecto Vite y define `VITE_API_URL` con la URL pública del backend. El rewrite SPA ya está incluido en `frontend/vercel.json`. El backend FastAPI puede desplegarse como proyecto Vercel independiente siguiendo la entrada `backend/kspr_engine/main.py` y manteniendo las variables `KSPR_*` exclusivamente en el entorno del servidor.

## CLI de KSPR AI

Puedes instalar y ejecutar KSPR directamente desde **npm**:

```bash
npm install -g kspr-ai
# o ejecución instantánea con npx:
npx kspr-ai
```

O bien ejecutar el script localmente:

```bash
python cli/kspr.py ./mi-repositorio --output ./kspr-context --iterations 3
# o interactivo tipo OpenCode:
python cli/kspr.py
# o un repositorio Git:
python cli/kspr.py --git-url https://github.com/org/repo.git --output ./kspr-context
```

La CLI nunca ejecuta el código analizado: solo lee archivos permitidos y genera evidencia estructurada.

### Shell interactivo

El shell usa `prompt_toolkit` + `rich` con paleta grayscale y temas opcionales (`/theme phosphor`,
`amber`, `ice`, `void`). Al escribir `/` se despliega el menú completo de comandos y cada letra
filtra por similitud fuzzy (`/c` → `clear`, `config`, `carve`, `crypto`, `cfg`…) mostrando categoría,
alias, uso y advertencia para comandos peligrosos. `@` autocompleta archivos del workspace, `#`
modelos, `%` agentes. `Ctrl+K` abre la paleta de comandos, `F1` la ayuda, `F2` el mapa de comandos,
`F3` la interconexión de rutas y el toolbar inferior muestra proveedor, modelo, contexto, workspace
y tema en vivo. El historial persiste en `~/.kspr/shell_history`. Cuando no hay TTY se usa un
fallback `readline` con historial.

El motor visual aplica el tema activo tanto en `rich` como en el fallback ANSI 24-bit (colores
truecolor derivados de cada tema) e incluye animaciones de escaneo, typewriter y spinner con
resultado `✓/✕` y tiempo transcurrido. Se controlan con `/visual on|off|preview|demo|status`.

Comandos visuales e interconexión: `/map` (mapa de comandos por categoría), `/palette <texto>`
(buscador fuzzy), `/status` (panel con barra de contexto y sparkline de actividad), `/routes`
(introspecciona las rutas FastAPI del backend y las mapea al comando CLI equivalente), `/tour`
(recorrido animado de bienvenida) y `/visual` (efectos, temas y demo de componentes).


### Ingeniería inversa estática

Comandos de análisis: `/recon`, `/file`, `/hashes`, `/strings`, `/hex`, `/sections`, `/imports`,
`/exports`, `/symbols`, `/entropy`, `/disasm`, `/decompile`, `/pseudo`, `/cfg`, `/graph`,
`/callgraph`, `/xrefs`, `/diff`, `/signature`, `/packer`, `/yara`, `/capa`, `/crypto`, `/iocs`,
`/pcap` (capturas de red), `/carve`, `/recover`, `/extract`, `/unpack`, `/firmware`, `/report`,
`/sbom`, `/ask`, `/index` (RAG), `/kg` (grafo de conocimiento), `/verify`, `/agents`, `/plan`,
`/memory` y `/tools`. El motor parsea ELF/PE/Mach-O/archivos, desensambla con
`capstone`/`objdump`, decompila con `radare2`/RetDec o pseudocódigo asistido por IA anclado a
evidencia, detecta packers/YARA/crypto, y recupera archivos con carving (interno o `foremost`).
`/tools detect|install` detecta e instala herramientas externas (radare2, binwalk, ghidra, jadx…).

Comandos base: `/help`, `/doctor`, `/config`, `/api`, `/project`, `/model`, `/provider`, `/mcp`,
`/plugins`, `/capabilities`, `/prompts`, `/skills`, `/decompilate`, `/trees`, `/todo`, `/ast`,
`/remember`, `/recall`, `/sandbox`, `/run`, `/export`, `/context`, `/compact`, `/new`, `/sessions`,
`/banner`, `/theme`, `/update`, `/map`, `/palette`, `/status`, `/routes`, `/tour`, `/visual` y
`/exit`. El wordmark ASCII de KSPR se dibuja al iniciar y con `/banner`.

## Proveedores de IA

Configura `KSPR_GEMINI_API_KEY` en el entorno o conéctala desde `/connect` en la interfaz. KSPR consulta los modelos reales mediante `models.list` y el chat usa `models.generateContent` con el modelo seleccionado. También puedes conectar un endpoint `openai-compatible` desde la misma pantalla. Las credenciales se mantienen en el ámbito de la sesión y no se persisten en el servidor.
