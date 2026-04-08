# Pure Hexa AGI v0.1 — Ubuntu Deployment

## Target Server

| Spec | Value |
|------|-------|
| OS | Ubuntu (Tailscale) |
| IP | 100.96.193.56 |
| CPU | AMD Ryzen 9600X |
| RAM | 30 GB |
| Storage | NVMe 841 GB |
| GPU | NVIDIA RTX 5070 12 GB |

## Quick Start

```bash
# 1. Cross-compile for Linux (from macOS)
./deploy_hexa_agi.sh --build

# 2. Deploy only (if binary already built)
./deploy_hexa_agi.sh

# 3. Deploy + install systemd service
./deploy_hexa_agi.sh --build --systemd

# 4. Dry run (preview without executing)
./deploy_hexa_agi.sh --build --dry-run
```

## Prerequisites

- **Tailscale** connected (server at 100.96.193.56)
- **SSH key** at `~/.ssh/id_ed25519` (or set `SSH_KEY` env var)
- **Rust cross-compilation** — one of:
  - `cross` installed (`cargo install cross`) — recommended, uses Docker
  - `x86_64-unknown-linux-gnu` target + linker configured

## What Gets Deployed

```
~/hexa-agi/
  hexa                    # Linux x86_64 binary
  core/
    engine.hexa           # Core AGI engine
    decoder.hexa          # Neural decoder
    trinity.hexa          # Trinity architecture
    bench.hexa            # Benchmark suite
    conscious_chat.hexa   # Conscious chat interface
  logs/                   # Runtime logs
  data/                   # Runtime data
```

## Deployment Steps

1. **Preflight** — SSH connectivity check
2. **Build** (optional) — Cross-compile hexa for `x86_64-unknown-linux-gnu`
3. **Create dirs** — `~/hexa-agi/{core,logs,data}` on remote
4. **Transfer** — SCP binary + .hexa files
5. **Verify** — Run `./hexa core/conscious_chat.hexa status` on remote
6. **Systemd** (optional) — Install always-on service

## Configuration

| Env Variable | Default | Description |
|-------------|---------|-------------|
| `DEPLOY_USER` | current user | SSH username |
| `SSH_KEY` | `~/.ssh/id_ed25519` | SSH private key path |

## Systemd Service

When deployed with `--systemd`:

```bash
# On the server
sudo systemctl status hexa-agi
sudo systemctl stop hexa-agi
sudo systemctl start hexa-agi
sudo systemctl restart hexa-agi
journalctl -u hexa-agi -f          # live logs
```

The service auto-restarts on failure with a 5-second delay. Memory is capped at 24 GB (leaving 6 GB for the OS).

## Manual Operation

```bash
ssh 100.96.193.56
cd ~/hexa-agi
./hexa core/conscious_chat.hexa          # interactive
./hexa core/bench.hexa                   # benchmark
./hexa core/conscious_chat.hexa status   # status check
```
