#!/usr/bin/env bash
# KSPR AI - Instalador y auto-reparación para Bash.
# Separa la instalación (~/.kspr/app) de la configuración del usuario (~/.kspr).
set -euo pipefail

REPO_URL="https://github.com/devdreiortiz/KSPR.git"
RAW_BASE="https://raw.githubusercontent.com/devdreiortiz/KSPR/main"

echo "=================================================="
echo "  KSPR AI - Instalador Automático para Bash"
echo "=================================================="

if ! command -v python3 &> /dev/null; then
    echo "[!] Error: python3 es requerido."
    exit 1
fi

CONFIG_DIR="${KSPR_CONFIG_DIR:-$HOME/.kspr}"
INSTALL_DIR="${KSPR_INSTALL_DIR:-$HOME/.kspr/app}"
BIN_DIR="${KSPR_BIN_DIR:-$HOME/.local/bin}"
VENV_DIR="$INSTALL_DIR/.venv"

echo "[*] Instalando KSPR en $INSTALL_DIR"
mkdir -p "$INSTALL_DIR" "$CONFIG_DIR"

if [ -d "$INSTALL_DIR/.git" ]; then
    git -C "$INSTALL_DIR" fetch origin main || true
    git -C "$INSTALL_DIR" reset --hard origin/main || true
else
    if ! git clone --depth 1 "$REPO_URL" "$INSTALL_DIR"; then
        echo "[!] No se pudo clonar el repositorio. Se intentará descargar un paquete mínimo."
    fi
fi

# Garantizar los scripts críticos incluso si el clonado falló.
mkdir -p "$INSTALL_DIR/cli" "$INSTALL_DIR/backend"
for asset in "cli/kspr.py" "cli/kspr_terminal_ui.py" "cli/kspr_core.py" "pyproject.toml"; do
    if [ ! -f "$INSTALL_DIR/$asset" ]; then
        echo "[*] Descargando $asset..."
        mkdir -p "$(dirname "$INSTALL_DIR/$asset")"
        curl -fsSL "$RAW_BASE/$asset" -o "$INSTALL_DIR/$asset" || true
    fi
done

echo "[*] Creando entorno virtual aislado (venv)..."
python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --upgrade pip >/dev/null

echo "[*] Instalando dependencias..."
if [ -f "$INSTALL_DIR/pyproject.toml" ]; then
    "$VENV_DIR/bin/pip" install "$INSTALL_DIR[re]" || "$VENV_DIR/bin/pip" install "$INSTALL_DIR"
else
    "$VENV_DIR/bin/pip" install fastapi httpx pydantic pydantic-settings python-multipart uvicorn bcrypt PyJWT PyYAML \
        prompt_toolkit rich pyelftools pefile filetype
fi

echo "[*] Detectando herramientas de ingeniería inversa..."
"$VENV_DIR/bin/python" - <<'PY' || true
try:
    from kspr_engine.re.installer import status
    info = status()
    print(f"    instaladas: {', '.join(info['installed']) or 'ninguna'}")
    print(f"    faltantes:  {', '.join(info['missing'][:8])}{'...' if len(info['missing'])>8 else ''}")
    print("    instala el resto desde el shell con: /tools install")
except Exception as exc:
    print(f"    (no se pudo detectar: {exc})")
PY

echo "[*] Creando lanzador auto-reparable en $BIN_DIR/kspr..."
mkdir -p "$BIN_DIR"
cat << 'EOF' > "$BIN_DIR/kspr"
#!/usr/bin/env bash
# KSPR launcher con auto-reparación y soporte de instalaciones legacy.
set -e
INSTALL_DIR="${KSPR_INSTALL_DIR:-$HOME/.kspr/app}"
LEGACY_DIR="$HOME/.kspr"

if [ ! -f "$INSTALL_DIR/cli/kspr.py" ] && [ -f "$LEGACY_DIR/cli/kspr.py" ]; then
    INSTALL_DIR="$LEGACY_DIR"
fi

if [ ! -f "$INSTALL_DIR/cli/kspr.py" ]; then
    echo "[*] Reparando KSPR CLI automáticamente..."
    mkdir -p "$INSTALL_DIR/cli"
    curl -fsSL https://raw.githubusercontent.com/devdreiortiz/KSPR/main/cli/kspr.py -o "$INSTALL_DIR/cli/kspr.py"
    curl -fsSL https://raw.githubusercontent.com/devdreiortiz/KSPR/main/cli/kspr_core.py -o "$INSTALL_DIR/cli/kspr_core.py"
    curl -fsSL https://raw.githubusercontent.com/devdreiortiz/KSPR/main/cli/kspr_terminal_ui.py -o "$INSTALL_DIR/cli/kspr_terminal_ui.py"
fi

if [ -x "$INSTALL_DIR/.venv/bin/python" ]; then
    exec "$INSTALL_DIR/.venv/bin/python" "$INSTALL_DIR/cli/kspr.py" "$@"
fi
exec python3 "$INSTALL_DIR/cli/kspr.py" "$@"
EOF

chmod +x "$BIN_DIR/kspr"

if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    SHELL_RC="$HOME/.bashrc"
    echo "export PATH=\"$BIN_DIR:\$PATH\"" >> "$SHELL_RC"
    echo "[*] Se añadió $BIN_DIR a tu PATH en $SHELL_RC"
fi

echo ""
echo " ✓ ¡KSPR AI instalado con éxito!"
echo " Instala la configuración en: $CONFIG_DIR"
echo " Ejecuta 'source ~/.bashrc' y luego 'kspr --help' o 'kspr --interactive'."
echo "=================================================="
