# KSPR AI CLI TOOL — diseño y funcionalidad

Este documento registra cómo KSPR AI CLI TOOL separa la experiencia de uso de la lógica que descompone, analiza y reconstruye fuentes de conocimiento. La interfaz presenta el estado del trabajo; el motor conserva la evidencia y ejecuta el procesamiento.

---

## 1. Principio Arquitectónico

Para garantizar mantenibilidad, testendibilidad y evolución independiente, KSPR separa:
- **Funcionalidad (Business Logic & Core Engine)**: La lógica que procesa datos, conecta con APIs de IA, analiza código AST, gestiona seguridad/permisos y ejecuta comandos de sistema.
- **Diseño (Presentation & UI Layer)**: La capa encargada exclusivamente de la representación visual, formato de terminal (ANSI/grayscale), renderizado de cajas, barras de progreso, iconos y componentes web React.

---

## 2. Desglose de Componentes por Capa

### Capa de Funcionalidad (`backend/kspr_engine/` y lógica de negocio en CLI)
- **`analyzer.py` / `scanner.py`**: Análisis estático de código fuente, escaneo de árboles de directorios y extracción de artefactos.
- **`providers.py`**: Adaptadores de comunicación HTTP con proveedores de modelos de lenguaje (LLM), manejo de autenticación Bearer/API Key y parseo de respuestas.
- **`main.py`**: Enrutamiento de la API FastAPI, validación de esquemas Pydantic y gestión de endpoints REST/SSE.
- **`auth.py` / `permissions.py` / `todos.py` / `memory.py`**: Seguridad JWT, hashing, control de acceso perimetral y gestión de tareas.
- **`cli/kspr.py` (Lógica Funcional)**: Bucle interactivo de comandos, lectura de entrada de usuario (`get_input_with_tab`), carga/guardado de configuración JSON, manejo de referencias `@archivo` y llamadas asíncronas a proveedores.

### Capa de Diseño y Presentación (`cli/kspr_terminal_ui.py` & `frontend/`)
- **`TerminalTheme` (Clase ANSI)**: Definición de paleta monocromática de alto contraste (Blanco, Silver, Graphite, Charcoal).
- **`KSPR_ASCII`**: Wordmark ASCII oficial de KSPR (bloque monocromo `░`), restaurado y alineado en la capa de UI.
- **`TerminalUI.print_header()`**: Renderizado del wordmark y la cabecera visual al iniciar la CLI; también accesible con `/banner`.
- **`print_dashboard()`**: Representación visual del estado de sesión (Proveedor, Modelo, Iteraciones, Workspace, Archivos adjuntos y barra de uso de contexto con pesos en tokens).
- **`print_box()` / `print_response_box()`**: Constructores de cajas de texto dinámicas con ajuste de ancho de terminal y soporte flexible para cadenas (`str`) o listas de cadenas (`list[str]`).
- **`animate_spinner()`**: Animación de espera visual con indicador de tiempo transcurrido en segundos.
- **`frontend/src/`**: Aplicación web SPA en React con componentes visuales desacoplados del backend.

---

## 3. Beneficios de la Separación

1. **Estabilidad del Motor**: Modificaciones en la interfaz visual (como reordenar el dashboard o ajustar estilos ANSI) no afectan jamás la lógica de análisis estático ni las llamadas a los proveedores LLM.
2. **Testabilidad**: Las pruebas unitarias (`pytest`) pueden verificar la integridad del motor, autenticación y análisis sin depender de terminales interactivas ni renderizado visual.
3. **Mantenimiento Limpio**: Las responsabilidades están acotadas a módulos específicos, reduciendo la complejidad ciclomática y previniendo errores de tipo (`TypeError`, `NameError`).
