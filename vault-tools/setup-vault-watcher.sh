#!/bin/bash
# setup-vault-watcher.sh — Install and configure the vault-watcher pipeline
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VAULT_DIR="/home/openclaw/obsidian-vault"
LOG_FILE="/var/log/vault-watcher.log"
SYSTEMD_USER_DIR="/home/openclaw/.config/systemd/user"

echo "=== Vault Watcher Setup ==="

# --- 1. Install inotify-tools if missing ---
if ! command -v inotifywait &>/dev/null; then
    echo "[1/6] Installing inotify-tools..."
    sudo apt-get update -qq
    sudo apt-get install -y inotify-tools jq curl
else
    echo "[1/6] inotify-tools already installed"
fi

# --- 2. Create vault directory if missing ---
if [[ ! -d "$VAULT_DIR" ]]; then
    echo "[2/6] Creating vault directory at $VAULT_DIR..."
    sudo mkdir -p "$VAULT_DIR"
    sudo chown openclaw:openclaw "$VAULT_DIR"
else
    echo "[2/6] Vault directory already exists at $VAULT_DIR"
fi

# --- 3. Initialize git repo if missing ---
if [[ ! -d "$VAULT_DIR/.git" ]]; then
    echo "[3/6] Initializing git repository in vault..."
    cd "$VAULT_DIR"
    git init
    git config user.name "vault-watcher"
    git config user.email "vault-watcher@localhost"
    # Create a placeholder so first commit works
    echo "# Obsidian Vault" > "$VAULT_DIR/README.md"
    echo "Initialized by vault-watcher setup" >> "$VAULT_DIR/README.md"
    git add README.md
    git commit -m "vault-watcher: initial commit"
else
    echo "[3/6] Git repository already initialized"
fi

# --- 4. Ensure log file exists ---
if [[ ! -f "$LOG_FILE" ]]; then
    echo "[4/6] Creating log file at $LOG_FILE..."
    sudo touch "$LOG_FILE"
    sudo chown openclaw:openclaw "$LOG_FILE"
else
    echo "[4/6] Log file already exists"
fi

# --- 5. Make vault-watcher.sh executable ---
echo "[5/6] Setting permissions on vault-watcher.sh..."
chmod +x "$SCRIPT_DIR/vault-watcher.sh"

# --- 6. Install systemd service ---
echo "[6/6] Installing systemd service..."

# Create user systemd directory if it doesn't exist
mkdir -p "$SYSTEMD_USER_DIR"

# Copy service file
cp "$SCRIPT_DIR/vault-watcher.service" "$SYSTEMD_USER_DIR/vault-watcher.service"

# Reload systemd, enable and start
systemctl --user daemon-reload
systemctl --user enable vault-watcher.service
systemctl --user start vault-watcher.service

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Service status:"
systemctl --user status vault-watcher.service --no-pager || true
echo ""
echo "Log (last 10 lines):"
tail -n 10 "$LOG_FILE" 2>/dev/null || echo "(no log yet)"
echo ""
echo "Useful commands:"
echo "  systemctl --user status vault-watcher   # check status"
echo "  systemctl --user restart vault-watcher  # restart"
echo "  journalctl --user -u vault-watcher -f   # follow logs"
echo "  tail -f $LOG_FILE                       # watch log file"
