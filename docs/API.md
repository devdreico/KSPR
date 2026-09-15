# API inicial

Base local: http://localhost:8000.

| Método | Ruta | Propósito |
| --- | --- | --- |
| GET | /api/v1/health | Estado del motor y catálogo de proveedores disponible |
| POST | /api/v1/analyze | Ejecuta un análisis directo; devuelve el paquete completo |
| POST | /api/v1/analyze/stream | Emite progreso y resultado como eventos SSE |
| POST | /api/v1/jobs | Encola un análisis híbrido/asíncrono |
| GET | /api/v1/jobs/{job_id} | Consulta progreso y resultado del job |
| DELETE | /api/v1/jobs/{job_id} | Cancela un job en cola o en ejecución |
| POST | /api/v1/ingest/files | Previsualiza archivos cargados |
| POST | /api/v1/ingest/archive | Extrae un ZIP de forma segura |
| GET | /api/v1/providers/status?provider=gemini | Valida la clave y consulta modelos reales del proveedor |
| GET | /api/v1/providers/gemini/status | Alias compatible para Gemini |
| POST | /api/v1/transcribe | Transcribe audio usando Gemini |

## Cuerpo de análisis

    {
      "project_name": "Sistema legado",
      "files": [{"path": "src/form.cs", "content": "..."}],
      "provider": "gemini",
      "model": "gemini-2.5-flash",
      "variant": "high",
      "iterations": 3,
      "mode": "auto"
    }

`mode: auto` ejecuta directo para contextos pequeños y obliga a usar `/api/v1/jobs` para contextos grandes. Los proveedores iniciales son `gemini` y `openai-compatible`; `local` existe únicamente para pruebas deterministas. Las credenciales efímeras viajan en `X-KSPR-API-Key` y un endpoint compatible puede definirse en `X-KSPR-Base-URL`.

`/api/v1/analyze/stream` devuelve eventos SSE con `type: progress`, `type: delta`, `type: result` o `type: error`. El cliente puede cerrar la conexión para cancelar la tarea en curso.

La interfaz incluye `local`/`kspr-local` para el smoke test de conversación, permite añadir modelos manuales y puede importar proveedores personalizados. Para `openai-compatible` y proveedores personalizados, el `model` se envía al endpoint `/chat/completions`; para Gemini se envía a `models/{model}:generateContent`.
