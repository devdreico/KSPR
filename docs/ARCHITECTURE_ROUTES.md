# KSPR AI CLI TOOL — arquitectura y rutas de ejecución

Este documento registra las rutas de ejecución comprobables del motor KSPR (`kspr_engine`) y de la CLI `kspr`. Sirve como mapa operativo para entender qué procesa cada entrada, qué salida produce y qué controles protegen las operaciones sensibles.

---

## 1. Endpoints de la API REST y Streaming (FastAPI / `backend/kspr_engine/main.py`)

El servidor backend expone los siguientes puntos de entrada (routes) bajo el prefijo `/api/v1`:

| Método | Ruta | Descripción | Estado / Estabilidad |
| --- | --- | --- | --- |
| `GET` | `/api/v1/health` | Estado del sistema, versión y verificación de credenciales Gemini. | Activo / Estable |
| `POST` | `/api/v1/auth/register` | Registro de nuevos usuarios y emisión de JWT. | Activo / Estable |
| `POST` | `/api/v1/auth/login` | Autenticación de usuarios por credenciales. | Activo / Estable |
| `GET` | `/api/v1/auth/me` | Perfil del usuario autenticado (requiere Bearer Token). | Activo / Estable |
| `POST` | `/api/v1/auth/oauth` | Inicio de sesión OAuth (Reservado / No implementado v1). | 501 Not Implemented |
| `POST` | `/api/v1/analyze` | Análisis estático síncrono del repositorio / archivos. | Activo / Estable |
| `POST` | `/api/v1/analyze/stream` | Análisis estático con emisión de progreso y deltas vía SSE (Server-Sent Events). | Activo / Estable |
| `POST` | `/api/v1/jobs` | Creación de tareas de análisis asíncronas en segundo plano. | Activo / Estable |
| `GET` | `/api/v1/jobs/{job_id}` | Consulta de estado de tareas asíncronas. | Activo / Estable |
| `GET` | `/api/v1/providers/status` | Estado de salud y descubrimiento de modelos por proveedor. | Activo / Estable |

---

## 2. Flujo de Ejecución y Enrutamiento en la CLI (`cli/kspr.py`)

La interfaz de comandos interactiva maneja el siguiente enrutamiento de comandos slash (`/`):

| Comando | Propósito |
| --- | --- |
| `/help` | Ayuda interactiva de comandos disponibles. |
| `/doctor` | Autodiagnóstico: Python, dependencias, rutas, proveedor y claves. |
| `/config` | Rutas de configuración y estado activo (proveedor, modelo, workspace). |
| `/login` | Valida códigos únicos contra el registro de licencias (`licenses.json`). |
| `/api` | Configura API Keys e indexa modelos remotos. |
| `/project` | Gestor de proyectos locales (nuevo, anterior, ruta personalizada). |
| `/model` | Selección e indexación de modelos activos por proveedor. |
| `/provider` | Cambio de proveedor activo (`gemini`, `openai`, `groq`, `deepseek`, `anthropic`, `openrouter`, `opencode-zen`, `local`). |
| `/mcp` | Registro y prueba de servidores MCP (`add`, `remove`, `enable`, `test`, `tools`). |
| `/plugins` | Gestión de plugins externos. |
| `/capabilities` | Descubrimiento y ejecución de capacidades CLI-Anything. |
| `/prompts` | Prompts guardados (`add`, `select`, `remove`, `info`) con `$ARGUMENTS`/`$1`. |
| `/skills` | Bundles de skills cargados. |
| `/decompilate` | Indexación multi-fuente y generación de Context Trees. |
| `/trees` | Lista de Context Trees generados. |
| `/todo` | Grafo de tareas del workspace (`add`, `list`, `done`, `clear`). |
| `/ast` | Análisis AST estático de un archivo Python del workspace. |
| `/remember` / `/recall` | Memoria vectorial local (guardar y búsqueda semántica). |
| `/sandbox` / `/run` | Ejecución de shell confinada al workspace con permisos explícitos. |
| `/export` | Exporta la transcripción de la sesión (`md`/`json`). |
| `/context` | Inspección de archivos adjuntos activos en la sesión. |
| `/compact` / `/new` / `/sessions` | Gestión de contexto y sesiones persistentes. |
| `/banner` | Redibuja el wordmark ASCII de KSPR con el proveedor/modelo activos. |
| `/theme [nombre]` | Cambia el tema (`grayscale`, `phosphor`, `amber`, `ice`, `void`). |
| `/tools [detect\|install]` | Detecta e instala herramientas de ingeniería inversa. |
| `/recon` `/file` `/hashes` `/strings` `/hex` | Triage y evidencia textual de un artefacto. |
| `/sections` `/imports` `/exports` `/symbols` | Análisis estático de formato ELF/PE. |
| `/entropy` `/packer` `/yara` `/capa` `/crypto` `/iocs` | Detección de amenazas y características. |
| `/disasm` `/cfg` `/graph` `/callgraph` `/xrefs` `/diff` `/signature` | Desensamblado, grafos y firmas. |
| `/decompile` `/pseudo` | Descompilación real o pseudocódigo asistido por IA con evidencia. |
| `/carve` `/recover` `/extract` `/unpack` `/firmware` | Recuperación, extracción y desempaquetado. |
| `/report` `/sbom` `/ask` `/verify` `/agents` `/plan` `/memory` | Informes, RAG, verificación y ecosistema de agentes. |
| `/clear` | Limpia la pantalla y redibuja el dashboard ejecutivo. |
| `/update` | Actualización automática mediante `install.sh`. |
| `/exit` | Cierre de la sesión interactiva. |

La lectura de entrada usa `readline` cuando está disponible (historial con flechas ↑/↓ y edición
de línea) y las referencias `@archivo` se resuelven siempre dentro del workspace activo.

---

## 3. Mecanismo de Fallback y Resiliencia en Proveedores (`backend/kspr_engine/providers.py`)

- **Proveedores Soportados**: `GeminiProvider`, `OpenAICompatibleProvider`, `OpenAIProvider`, `GroqProvider`, `DeepseekProvider`, `AnthropicProvider`, `OpenRouterProvider`, `OpenCodeZenProvider`, `LocalProvider`.
- **Estrategia de Resiliencia**: ante un `ProviderError` relacionado con credenciales ausentes, la CLI muestra el error y ejecuta un **fallback automático con `LocalProvider` (`kspr-local`)** para garantizar que la sesión nunca se bloquee. Para errores de otro tipo muestra guías orientadas a acción (`/login`, `/api`, `/model`, `/provider`) y registro en `https://kspr.membership.vercel.app/`.
- **Streaming**: cuando no hay herramientas activas, el chat usa `complete_stream` y muestra los deltas en vivo si la salida es una TTY; con herramientas activas usa `complete` para poder interpretar `tool_calls`.
