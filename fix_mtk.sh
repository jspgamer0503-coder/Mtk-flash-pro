#!/bin/bash
# MTK Flash Pro — Fix Script
# Run as normal user (NOT sudo): bash fix_mtk.sh

GREEN="\033[1;32m"; CYAN="\033[1;36m"; RED="\033[1;31m"; NC="\033[0m"
ok()  { echo -e "${GREEN}✓ $*${NC}"; }
inf() { echo -e "${CYAN}→ $*${NC}"; }
err() { echo -e "${RED}✗ $*${NC}"; exit 1; }

if [[ "$EUID" -eq 0 ]]; then
    echo -e "${RED}✗ Do NOT run with sudo. Run as your normal user:${NC}"
    echo "  bash fix_mtk.sh"
    exit 1
fi

APP_DIR="$HOME/.local/share/mtk_flash_pro"
VENV="$APP_DIR/venv"
VENV_PY="$VENV/bin/python3"
VENV_PIP="$VENV/bin/pip"
WRAPPER="$APP_DIR/mtk_run.sh"
SUDOERS="/etc/sudoers.d/mtk-flash-pro"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ""
echo "══════════════════════════════════════════"
echo "   MTK Flash Pro — Fix Script"
echo "   User: $USER   Home: $HOME"
echo "══════════════════════════════════════════"
echo ""

# 1. System deps
inf "Installing system deps (git, python3-venv, libusb)..."
sudo apt-get update -qq
sudo apt-get install -y -qq python3 python3-pip python3-venv python3-tk git libusb-1.0-0 libusb-dev
ok "System deps ready."

# 2. Venv
mkdir -p "$APP_DIR"
if [[ ! -f "$VENV_PY" ]]; then
    inf "Creating venv at $VENV ..."
    python3 -m venv "$VENV"
    ok "Venv created."
else
    ok "Venv exists."
fi

# 3. Install mtkclient
# NOTE: mtkclient is NOT on PyPI — GitHub only. Binary is 'mtk', package is 'mtkclient'.
inf "Upgrading pip..."
"$VENV_PIP" install --upgrade pip --quiet

inf "Installing mtkclient from GitHub (60–120s)..."
"$VENV_PIP" install "git+https://github.com/bkerler/mtkclient.git" || {
    inf "pip git URL failed — trying manual clone..."
    TMP=$(mktemp -d)
    git clone --depth=1 https://github.com/bkerler/mtkclient.git "$TMP/src"
    "$VENV_PIP" install "$TMP/src"
    rm -rf "$TMP"
}

# Verify using correct package name 'mtkclient'
inf "Verifying installation..."
if "$VENV_PY" -c "import mtkclient" 2>/dev/null; then
    ok "mtkclient is installed and importable."
elif "$VENV_PY" -m mtk --version &>/dev/null; then
    ok "mtk binary works (import check skipped)."
else
    err "Install failed — 'python3 -c import mtkclient' returns error. Check internet."
fi

# 4. Wrapper script (activates venv so mtk works under sudo)
inf "Writing mtk_run.sh wrapper..."
cat > "$WRAPPER" << WRAP
#!/bin/bash
source "$VENV/bin/activate"
exec python3 -m mtk "\$@"
WRAP
chmod +x "$WRAPPER"
ok "Wrapper: $WRAPPER"

# 5. Sudoers — passwordless sudo for wrapper only
inf "Adding sudoers rule..."
echo "$USER ALL=(ALL) NOPASSWD: /bin/bash $WRAPPER" | sudo tee "$SUDOERS" > /dev/null
sudo chmod 440 "$SUDOERS"
ok "Sudoers: $SUDOERS"

if sudo -n bash "$WRAPPER" --version &>/dev/null; then
    ok "Passwordless sudo confirmed working."
else
    ok "Sudoers rule written."
fi

# 6. Copy latest app
if [[ -f "$SCRIPT_DIR/mtk_flash_pro.py" ]]; then
    cp "$SCRIPT_DIR/mtk_flash_pro.py" "$APP_DIR/mtk_flash_pro.py"
    ok "App updated."
fi

# 7. Launcher
mkdir -p "$HOME/.local/bin"
cat > "$HOME/.local/bin/mtk-flash-pro" << LAUNCHER
#!/bin/bash
exec "$VENV_PY" "$APP_DIR/mtk_flash_pro.py" "\$@"
LAUNCHER
chmod +x "$HOME/.local/bin/mtk-flash-pro"
ok "Launcher: ~/.local/bin/mtk-flash-pro"

echo ""
echo "══════════════════════════════════════════"
ok "All done!  Run:  mtk-flash-pro"
echo "══════════════════════════════════════════"
echo ""
