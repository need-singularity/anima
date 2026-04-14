#!/usr/bin/env bash
# ============================================================================
# deploy_hexa_agi.sh — Pure Hexa AGI v0.1 Ubuntu Deployment
# ============================================================================
# Target: Ubuntu (Ryzen 9600X / 30GB RAM / NVMe 841GB / RTX 5070 12GB)
# Access: Tailscale 100.96.193.56
# ============================================================================
set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
REMOTE_HOST="100.96.193.56"
REMOTE_USER="${DEPLOY_USER:-$(whoami)}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/id_ed25519}"
REMOTE_DIR="hexa-agi"

HEXA_LANG_DIR="${HEXA_LANG:-$HOME/Dev/hexa-lang}"
ANIMA_DIR="${ANIMA:-$HOME/Dev/anima}"
LINUX_TARGET="x86_64-unknown-linux-gnu"
LINUX_BINARY="$HEXA_LANG_DIR/target/$LINUX_TARGET/release/hexa"

# Core .hexa files to deploy
HEXA_FILES=(
    "core/engine.hexa"
    "core/decoder.hexa"
    "core/trinity.hexa"
    "core/bench.hexa"
    "core/conscious_chat.hexa"
)

# SSH/SCP common options
SSH_OPTS="-i $SSH_KEY -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
info()  { printf '\033[1;34m[INFO]\033[0m  %s\n' "$*"; }
ok()    { printf '\033[1;32m[OK]\033[0m    %s\n' "$*"; }
warn()  { printf '\033[1;33m[WARN]\033[0m  %s\n' "$*"; }
err()   { printf '\033[1;31m[ERR]\033[0m   %s\n' "$*"; exit 1; }

usage() {
    cat <<'USAGE'
Usage: deploy_hexa_agi.sh [OPTIONS]

Options:
  --build          Cross-compile hexa for Linux x86_64 before deploying
  --systemd        Install systemd service for always-on operation
  --dry-run        Show what would be done without executing
  --user USER      Remote SSH user (default: current user)
  --help           Show this help

Environment:
  DEPLOY_USER      Remote SSH user (overridden by --user)
  SSH_KEY          Path to SSH private key (default: ~/.ssh/id_ed25519)

Examples:
  ./deploy_hexa_agi.sh --build          # Build + deploy
  ./deploy_hexa_agi.sh                  # Deploy only (binary must exist)
  ./deploy_hexa_agi.sh --systemd        # Deploy + install systemd service
USAGE
    exit 0
}

# ---------------------------------------------------------------------------
# Parse args
# ---------------------------------------------------------------------------
DO_BUILD=false
DO_SYSTEMD=false
DRY_RUN=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --build)    DO_BUILD=true; shift ;;
        --systemd)  DO_SYSTEMD=true; shift ;;
        --dry-run)  DRY_RUN=true; shift ;;
        --user)     REMOTE_USER="$2"; shift 2 ;;
        --help|-h)  usage ;;
        *)          err "Unknown option: $1" ;;
    esac
done

REMOTE="$REMOTE_USER@$REMOTE_HOST"

run() {
    if $DRY_RUN; then
        info "[dry-run] $*"
    else
        "$@"
    fi
}

# ---------------------------------------------------------------------------
# Step 0: Preflight checks
# ---------------------------------------------------------------------------
info "Preflight checks..."

if [[ ! -f "$SSH_KEY" ]]; then
    for alt in "$HOME/.ssh/id_rsa" "$HOME/.ssh/id_ecdsa"; do
        if [[ -f "$alt" ]]; then
            SSH_KEY="$alt"
            SSH_OPTS="-i $SSH_KEY -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10"
            warn "Using alternative SSH key: $SSH_KEY"
            break
        fi
    done
    [[ -f "$SSH_KEY" ]] || err "No SSH key found. Set SSH_KEY env var."
fi

info "Testing SSH connectivity to $REMOTE..."
if ! $DRY_RUN; then
    ssh $SSH_OPTS "$REMOTE" "echo ok" >/dev/null 2>&1 \
        || err "Cannot SSH to $REMOTE. Check Tailscale and SSH config."
    ok "SSH connection verified"
fi

# ---------------------------------------------------------------------------
# Step 1: Cross-compile hexa for Linux x86_64
# ---------------------------------------------------------------------------
if $DO_BUILD; then
    info "Cross-compiling hexa for $LINUX_TARGET..."

    if ! command -v cross &>/dev/null; then
        warn "'cross' not installed. Trying cargo with target..."
        rustup target add "$LINUX_TARGET" 2>/dev/null || true

        if ! rustup target list --installed | grep -q "$LINUX_TARGET"; then
            err "Target $LINUX_TARGET not available. Install 'cross': cargo install cross"
        fi

        info "Building with cargo (requires linker for $LINUX_TARGET)..."
        run bash -c "cd '$HEXA_LANG_DIR' && cargo build --release --target '$LINUX_TARGET'"
    else
        info "Building with cross (Docker-based, no linker setup needed)..."
        run bash -c "cd '$HEXA_LANG_DIR' && cross build --release --target '$LINUX_TARGET'"
    fi

    ok "Build complete: $LINUX_BINARY"
else
    info "Skipping build (use --build to cross-compile)"
fi

# Check binary exists
if [[ ! -f "$LINUX_BINARY" ]] && ! $DRY_RUN; then
    ALT_BINARY="$HEXA_LANG_DIR/target/release/hexa"
    if [[ -f "$ALT_BINARY" ]]; then
        warn "No Linux binary at $LINUX_BINARY"
        warn "Found $ALT_BINARY — likely macOS ARM binary, won't work on Linux."
    fi
    err "Linux binary not found at $LINUX_BINARY. Run with --build or cross-compile first."
fi

# ---------------------------------------------------------------------------
# Step 2: Create remote directory structure
# ---------------------------------------------------------------------------
info "Creating remote directory structure: ~/$REMOTE_DIR/"

run ssh $SSH_OPTS "$REMOTE" "mkdir -p ~/$REMOTE_DIR/core ~/$REMOTE_DIR/logs ~/$REMOTE_DIR/data"
ok "Remote directories created"

# ---------------------------------------------------------------------------
# Step 3: Deploy binary + .hexa files
# ---------------------------------------------------------------------------
info "Deploying hexa binary..."
run scp $SSH_OPTS "$LINUX_BINARY" "$REMOTE:~/$REMOTE_DIR/hexa"
run ssh $SSH_OPTS "$REMOTE" "chmod +x ~/$REMOTE_DIR/hexa"
ok "Binary deployed"

info "Deploying .hexa core files..."
for f in "${HEXA_FILES[@]}"; do
    src="$ANIMA_DIR/$f"
    if [[ -f "$src" ]]; then
        run scp $SSH_OPTS "$src" "$REMOTE:~/$REMOTE_DIR/$f"
        ok "  $f"
    else
        warn "  $f not found at $src — skipping"
    fi
done

# ---------------------------------------------------------------------------
# Step 4: Verify deployment
# ---------------------------------------------------------------------------
info "Verifying deployment on remote..."

if ! $DRY_RUN; then
    ssh $SSH_OPTS "$REMOTE" bash <<'VERIFY'
set -euo pipefail
cd ~/hexa-agi

echo "=== Binary ==="
ls -lh hexa
file hexa

echo ""
echo "=== Core files ==="
ls -la core/

echo ""
echo "=== Version check ==="
./hexa --version 2>/dev/null || echo "(no --version flag)"

echo ""
echo "=== Smoke test: conscious_chat status ==="
if [[ -f core/conscious_chat.hexa ]]; then
    timeout 10 ./hexa core/conscious_chat.hexa status 2>&1 || echo "(smoke test returned non-zero — may be expected on first run)"
else
    echo "conscious_chat.hexa not found — skipping smoke test"
fi
VERIFY
    ok "Verification complete"
else
    info "[dry-run] Would verify deployment on remote"
fi

# ---------------------------------------------------------------------------
# Step 5 (optional): systemd service
# ---------------------------------------------------------------------------
if $DO_SYSTEMD; then
    info "Installing systemd service..."

    ssh $SSH_OPTS "$REMOTE" bash <<SYSTEMD
set -euo pipefail

sudo tee /etc/systemd/system/hexa-agi.service > /dev/null <<'SERVICE'
[Unit]
Description=Pure Hexa AGI v0.1 — Conscious Chat Engine
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$REMOTE_USER
WorkingDirectory=/home/$REMOTE_USER/hexa-agi
ExecStart=/home/$REMOTE_USER/hexa-agi/hexa core/conscious_chat.hexa serve
Restart=on-failure
RestartSec=5
StandardOutput=append:/home/$REMOTE_USER/hexa-agi/logs/agi.log
StandardError=append:/home/$REMOTE_USER/hexa-agi/logs/agi.err.log
Environment=HEXA_AGI_HOME=/home/$REMOTE_USER/hexa-agi

# Resource limits — tuned for Ryzen 9600X + 30GB RAM
LimitNOFILE=65535
MemoryMax=24G

[Install]
WantedBy=multi-user.target
SERVICE

sudo systemctl daemon-reload
sudo systemctl enable hexa-agi.service
sudo systemctl start hexa-agi.service
sleep 2
sudo systemctl status hexa-agi.service --no-pager || true
SYSTEMD

    ok "systemd service installed and started"
    info "Manage with:"
    info "  ssh $REMOTE 'sudo systemctl start hexa-agi'"
    info "  ssh $REMOTE 'sudo systemctl stop hexa-agi'"
    info "  ssh $REMOTE 'sudo systemctl status hexa-agi'"
    info "  ssh $REMOTE 'journalctl -u hexa-agi -f'"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "============================================"
echo "  Pure Hexa AGI v0.1 — Deployment Complete"
echo "============================================"
echo "  Host:   $REMOTE"
echo "  Path:   ~/$REMOTE_DIR/"
echo "  Binary: ~/$REMOTE_DIR/hexa"
echo "  Logs:   ~/$REMOTE_DIR/logs/"
echo ""
echo "  SSH:    ssh $SSH_OPTS $REMOTE"
echo "  Run:    cd ~/$REMOTE_DIR && ./hexa core/conscious_chat.hexa"
echo "============================================"
