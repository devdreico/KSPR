# KSPR

**KSPR — Reverse Engineering Artificial Intelligence Agent** transforma repositorios y contextos legados en un mapa técnico auditable y reutilizable por otros agentes.

KSPR I recupera funcionalidades de interfaces y backend —botones, enlaces, formularios, eventos, consultas, procedimientos, rutas y mutaciones de estado—, contrasta sus hallazgos mediante iteraciones y exporta una carpeta Markdown de contexto masivo.

## Alcance inicial

- Importación de archivos pegados, múltiples archivos, ZIP y repositorios Git mediante la CLI (opción --git-url).
- Extracción estática segura por heurísticas: componentes UI, handlers, rutas HTTP, SQL, dependencias y puntos de mutación.
- Análisis híbrido: respuesta directa para contextos pequeños y jobs asíncronos para contextos grandes.
- Conexión real con Google Gemini, selección de modelos habilitados por API y `KSPR Local` para comprobar la interfaz sin credenciales.
- Conexión de endpoints OpenAI-compatible para gateways y proveedores compatibles, con distribución de modelos por proveedor; los proveedores personalizados importados se enrutan por el mismo contrato.
- Shell de trabajo tipo agente: sesiones persistentes locales, paleta `Ctrl/Cmd+K`, comandos slash con plantillas y argumentos, referencias `@archivo`, pegar/arrastrar archivos, detener respuestas con `Ctrl+G`, Main Prompt y configuración de agente.
- Catálogo extensible: descubre modelos desde la API o crea modelos manuales con ID, proveedor y endpoint compatible.
- Configuración portable de referencia en `examples/kspr.config.example.json`, compatible con el flujo de importación/exportación de la interfaz.
- Paquete de contexto con índice, inventario UI, mapa de flujos, contratos, riesgos, contradicciones, preguntas abiertas y trazabilidad.
- UI React con identidad Phantom: negro carbón, grises fríos, líneas finas, tipografía técnica y estados de progreso legibles.

## Ejecutar el backend

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

## CLI

```bash
python cli/kspr.py ./mi-repositorio --output ./kspr-context --iterations 3
# o un repositorio Git:
python cli/kspr.py . --git-url https://github.com/org/repo.git --output ./kspr-context
```

La CLI nunca ejecuta el código analizado: solo lee archivos permitidos y genera evidencia estructurada.

## Gemini real

Configura `KSPR_GEMINI_API_KEY` en el entorno o conéctala desde `/connect` en la interfaz. KSPR consulta los modelos reales mediante `models.list` y el chat usa `models.generateContent` con el modelo seleccionado. También puedes conectar un endpoint `openai-compatible` desde la misma pantalla.
