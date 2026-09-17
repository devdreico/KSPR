#!/usr/bin/env bash
set -e

echo "=================================================="
echo "  KSPR AI - Instalador Automático para Bash"
echo "=================================================="

# Verificar dependencias
if ! command -v python3 &> /dev/null; then
    echo "[!] Error: python3 es requerido pero no está instalado."
    exit 1
fi

if ! command -v pip &> /dev/null; then
    echo "[!] Error: pip es requerido pero no está instalado."
    exit 1
fi

INSTALL_DIR="${KSPR_INSTALL_DIR:-$HOME/.kspr}"
BIN_DIR="${KSPR_BIN_DIR:-/usr/local/bin}"

echo "[*] Clonando KSPR en $INSTALL_DIR..."
if [ -d "$INSTALL_DIR" ]; then
    cd "$INSTALL_DIR"
    git pull origin main || true
else
    git clone https://github.com/devdreiortiz/KSPR.git "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

echo "[*] Instalando dependencias del motor Python..."
pip install -e .

echo "[*] Configurando enlace simbólico en $BIN_DIR/kspr..."
if [ -w "$BIN_DIR" ]; then
    ln -sf "$INSTALL_DIR/bin/kspr.sh" "$BIN_DIR/kspr"
else
    echo "[*] Se requieren permisos de administrador (sudo) para instalar en $BIN_DIR"
    sudo ln -sf "$INSTALL_DIR/bin/kspr.sh" "$BIN_DIR/kspr"
fi

echo ""
echo " ✓ ¡KSPR AI instalado con éxito!"
echo " Ejecuta 'kspr --help' o 'kspr --interactive' para comenzar."
echo "=================================================="
