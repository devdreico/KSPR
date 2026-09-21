# KSPR AI CLI TOOL — arquitectura del motor

## Identidad

**KSPR AI CLI TOOL** utiliza inteligencia artificial y análisis estático para convertir código, UI, artefactos y contexto de sistemas legados en conocimiento técnico reutilizable por personas y agentes.

## Flujo de análisis

1. **Ingesta segura**: recibe texto, archivos o ZIP; valida rutas, extensiones y tamaños; nunca ejecuta el repositorio.
2. **Extracción estática**: detecta controles, formularios, enlaces, eventos, rutas, operaciones SQL, dependencias y evidencias de archivo/línea.
3. **Mapa cinético**: organiza relaciones causa-efecto entre acción de usuario, handler, backend y cambio de estado.
4. **Iteración agéntica**: cada pasada reevalúa la evidencia, registra hipótesis, riesgos y contradicciones y consolida una revisión.
5. **Documentación**: genera Markdown navegable y report.json, aptos para entregar a otro agente.
6. **Persistencia opcional**: Supabase guarda el resultado completo cuando se configuran sus variables de servidor; la migración auth añade `user_id` de forma incremental incluso si el núcleo ya fue aplicado.
7. **Workspace conversacional**: la UI mantiene sesiones, modelos y configuración local; el Main Prompt y el historial reciente viajan junto al mensaje para que todos los proveedores reciban el mismo contexto operativo.

## Despliegue preparado

- `frontend/vercel.json` habilita el fallback SPA de Vite.
- `pyproject.toml` declara `backend.kspr_engine.main:app` como entrypoint FastAPI para Vercel.
- `VITE_API_URL` debe apuntar al backend público; las variables `KSPR_*` permanecen exclusivamente en el backend.

La conexión real inicial es Google Gemini. `KSPR Local` permite completar el smoke test de interfaz sin credenciales. El contrato de proveedor permite añadir gateways compatibles y proveedores importados sin cambiar la interfaz de chat.

## Límites deliberados

- La salida distingue evidencia encontrada de inferencia y pregunta abierta.
- El motor no promete recuperar comportamiento ausente en el contexto.
- El razonamiento exportado es un registro técnico auditable, no una transcripción de razonamiento privado.
- La ejecución de código, migraciones o procedimientos del sistema analizado queda fuera del alcance de KSPR.
