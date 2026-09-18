#!/usr/bin/env bash
set -e

echo "=================================================="
echo "  KSPR AI - Instalador Automático para Bash"
echo "=================================================="

if ! command -v python3 &> /dev/null; then
    echo "[!] Error: python3 es requerido."
    exit 1
fi

INSTALL_DIR="${KSPR_INSTALL_DIR:-$HOME/.kspr}"
BIN_DIR="${KSPR_BIN_DIR:-$HOME/.local/bin}"

echo "[*] Clonando/Actualizando KSPR en $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"
if [ -d "$INSTALL_DIR/.git" ]; then
    cd "$INSTALL_DIR"
    git fetch origin main || true
    git reset --hard origin/main || true
else
    git clone https://github.com/devdreiortiz/KSPR.git "$INSTALL_DIR" || true
    cd "$INSTALL_DIR"
    git checkout main || true
    git pull origin main || true
fi

# Garantizar la existencia de la carpeta cli y los scripts críticos
mkdir -p "$INSTALL_DIR/cli"

if [ ! -f "$INSTALL_DIR/cli/kspr.py" ]; then
    echo "[*] Descargando kspr.py..."
    curl -fsSL https://raw.githubusercontent.com/devdreiortiz/KSPR/main/cli/kspr.py -o "$INSTALL_DIR/cli/kspr.py"
fi

if [ ! -f "$INSTALL_DIR/cli/kspr_terminal_ui.py" ]; then
    echo "[*] Descargando kspr_terminal_ui.py..."
    curl -fsSL https://raw.githubusercontent.com/devdreiortiz/KSPR/main/cli/kspr_terminal_ui.py -o "$INSTALL_DIR/cli/kspr_terminal_ui.py"
fi

echo "[*] Creando entorno virtual aislado (venv)..."
python3 -m venv "$INSTALL_DIR/.venv"

echo "[*] Instalando dependencias en el entorno virtual..."
"$INSTALL_DIR/.venv/bin/pip" install --upgrade pip
if [ -f "$INSTALL_DIR/pyproject.toml" ]; then
    "$INSTALL_DIR/.venv/bin/pip" install "$INSTALL_DIR"
else
    "$INSTALL_DIR/.venv/bin/pip" install fastapi httpx pydantic pydantic-settings python-multipart uvicorn passlib bcrypt PyJWT
fi

echo "[*] Creando script ejecutable autofix en $BIN_DIR/kspr..."
mkdir -p "$BIN_DIR"
cat << 'EOF' > "$BIN_DIR/kspr"
#!/usr/bin/env bash
INSTALL_DIR="${KSPR_INSTALL_DIR:-$HOME/.kspr}"
if [ ! -f "$INSTALL_DIR/cli/kspr.py" ]; then
    echo "[*] Reparando KSPR CLI automáticamente..."
    mkdir -p "$INSTALL_DIR/cli"
    curl -fsSL https://raw.githubusercontent.com/devdreiortiz/KSPR/main/cli/kspr.py -o "$INSTALL_DIR/cli/kspr.py"
    curl -fsSL https://raw.githubusercontent.com/devdreiortiz/KSPR/main/cli/kspr_terminal_ui.py -o "$INSTALL_DIR/cli/kspr_terminal_ui.py"
fi
exec "$INSTALL_DIR/.venv/bin/python" "$INSTALL_DIR/cli/kspr.py" "$@"
EOF

chmod +x "$BIN_DIR/kspr"

# Asegurar que ~/.local/bin esté en el PATH
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo "export PATH=\"\$HOME/.local/bin:\$PATH\"" >> ~/.bashrc
    echo "[*] Se añadió $BIN_DIR a tu PATH en ~/.bashrc"
fi

echo ""
echo " ✓ ¡KSPR AI instalado con éxito!"
echo " Ejecuta 'source ~/.bashrc' y luego 'kspr --help' o 'kspr --interactive'."
echo "=================================================="
