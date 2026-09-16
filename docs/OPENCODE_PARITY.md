# CASPER AI - Empresarial / OpenCode Desktop parity

CASPER AI - Empresarial toma como referencia el flujo de trabajo de OpenCode Desktop: sesión a la izquierda, conversación central, compositor único y configuración accesible desde comandos. La implementación conserva la identidad de KSPR y añade el análisis estático seguro del proyecto.

## Capacidades implementadas

| Capacidad de trabajo | KSPR |
| --- | --- |
| Sesiones nuevas, búsqueda, selección, eliminación y persistencia local | Implementado |
| Modelo y agente activos conservados por sesión | Implementado |
| Modo de permisos visible por sesión (`ask`/`allow`/`deny`) | Implementado para el perímetro seguro de KSPR |
| Crear agentes personalizados con prompt, modo y permisos | Implementado |
| Composer de texto con Enter/Shift+Enter | Implementado |
| Adjuntar múltiples archivos y ZIP | Implementado |
| Pegar o arrastrar archivos al workspace | Implementado |
| Contexto adjunto persistente por sesión con preview y eliminación | Implementado |
| Referencias `@archivo` | Implementado |
| Audio a texto con reconocimiento del navegador o Gemini | Implementado |
| Selector de modelos por proveedor | Implementado |
| Variantes de modelo por sesión | Implementado en configuración y contexto (`low`/`high`/`default`) |
| Descubrimiento de modelos Gemini y OpenAI-compatible | Implementado |
| Conexión de proveedor personalizado compatible con `/chat/completions` | Implementado |
| Proveedores compatibles importados desde configuración | Implementado |
| `KSPR Local` para smoke test sin credenciales | Implementado |
| Main Prompt global para todos los modelos | Implementado |
| Comandos slash integrados y paleta `Ctrl/Cmd+K` | Implementado |
| Comandos personalizados con `template`, descripción y `$ARGUMENTS`/`$1` | Implementado |
| Importación/exportación de configuración portable | Implementado |
| MCP remoto declarativo (`type`, `url`, `enabled`) | Implementado |
| Registro MCP nombrado remoto/local, activar/desactivar y eliminar | Implementado en configuración local; ejecución de herramientas aún deshabilitada |
| Paquete Markdown/JSON de contexto recuperado | Implementado |
| Detener respuesta, copiar, deshacer/rehacer y compartir transcripción | Implementado localmente |
| Eventos de progreso del análisis para respuesta observable | Implementado mediante SSE |
| Deltas de texto visibles mientras responde | Implementado para Gemini/OpenAI-compatible; fallback completo para proveedores sin streaming |

## Límites deliberados de la primera versión

- KSPR no ejecuta código del repositorio analizado.
- La autenticación de proveedores se mantiene en memoria de la sesión del navegador; no se exporta ni se persiste en Supabase.
- El modo compartir actual copia una transcripción portable; el enlace público requiere todavía un servicio de sharing en Supabase.
- La interfaz web muestra el progreso de jobs asíncronos y solicita su cancelación al servidor; si el proveedor ya está dentro de una llamada externa, la interrupción efectiva ocurre al volver al siguiente punto de progreso.
- El editor de archivos nativo, permisos de herramientas y streaming token-a-token son las siguientes piezas para cerrar la paridad de escritorio.

## Referencias de diseño

- [OpenCode commands](https://opencode.ai/docs/commands/)
- [OpenCode providers](https://opencode.ai/docs/providers)
- [OpenCode config](https://dev.opencode.ai/docs/config/)
- [OpenCode keybinds](https://opencode.ai/docs/keybinds)
