# KSPR AI - Arquitectura y Rutas de Ejecución (Core Engine)

Este documento detalla las rutas verdaderas de ejecución del motor KSPR (`kspr_engine`) y la interfaz de comandos (`kspr` CLI), garantizando la estabilidad y asegurando que las operaciones críticas del sistema funcionen sin interrupciones.

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

1. **`/help`**: Muestra la ayuda interactiva de comandos disponibles.
2. **`/clear`**: Limpia la pantalla y redibuja el dashboard ejecutivo de KSPR.
3. **`/login`**: Valida códigos únicos de identificación contra el registro de licencias (`licenses.json`).
4. **`/project`**: Gestor de proyectos locales (Creación, selección de workspace anterior, ruta personalizada).
5. **`/model`**: Selección e indexación de modelos activos por proveedor.
6. **`/provider`**: Cambio de proveedor activo (`gemini`, `openai`, `groq`, `deepseek`, `local`).
7. **`/iterations`**: Ajuste del nivel de iteraciones de análisis (1-8).
8. **`/context`**: Inspección de archivos adjuntos activos en la sesión.
9. **`/api`**: Configuración de API Keys e indexación automática de modelos remotos.
10. **`/analyze`**: Ejecución de análisis estático sobre el workspace actual o ruta específica.
11. **`/update`**: Actualización automática de KSPR mediante `install.sh`.
12. **`/exit`**: Cierre de la sesión interactiva.

---

## 3. Mecanismo de Fallback y Resiliencia en Proveedores (`backend/kspr_engine/providers.py`)

- **Proveedores Soportados**: `GeminiProvider`, `OpenAICompatibleProvider`, `OpenAIProvider`, `GroqProvider`, `DeepseekProvider`, `LocalProvider`.
- **Estrategia de Resiliencia**: Ante cualquier error de proveedor (`ProviderError`) por ausencia de API Key o fallo de conectividad externa, la CLI intercepta la excepción, muestra una guía orientada a acción (`/login` y registro en `https://kspr.membership.vercel.app/`) y ejecuta un **fallback automático con `LocalProvider` (`kspr-local`)** para garantizar que la sesión nunca se bloquee ni sufra un error fatal.
