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
if [ -d "$INSTALL_DIR" ]; then
    cd "$INSTALL_DIR"
    git pull origin main || true
else
    git clone https://github.com/devdreiortiz/KSPR.git "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

echo "[*] Creando entorno virtual aislado (venv)..."
python3 -m venv "$INSTALL_DIR/.venv"

echo "[*] Instalando dependencias en el entorno virtual..."
"$INSTALL_DIR/.venv/bin/pip" install --upgrade pip
"$INSTALL_DIR/.venv/bin/pip" install "$INSTALL_DIR"

echo "[*] Creando script ejecutable en $BIN_DIR/kspr..."
mkdir -p "$BIN_DIR"
cat << 'EOF' > "$BIN_DIR/kspr"
#!/usr/bin/env bash
exec "$HOME/.kspr/.venv/bin/python" "$HOME/.kspr/cli/kspr.py" "$@"
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
