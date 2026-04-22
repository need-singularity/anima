#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════════════════
#  tool/launchd_install_local.bash — ROI item D20 + D24 + E26 activation script
#
#  PURPOSE
#    Per-user (LaunchAgents) installer for the anima-managed launchd plists in
#    config/launchd/.  Symlinks each plist into ~/Library/LaunchAgents/ then
#    (with --activate only) loads them via `launchctl load`.
#
#    THIS SCRIPT IS NEVER RUN BY THE AGENT.  The user must invoke it manually
#    when they decide to enable the periodic agents on their workstation.
#
#  COVERED PLISTS (config/launchd/)
#    - com.anima.h100_auto_kill.plist                 (D20: pre-existing)
#    - com.anima.cert_watch.plist                     (pre-existing)
#    - com.anima.airgenome_keyword_dispatch.plist     (pre-existing)
#    - com.anima.worktree_merge_bot.plist             (pre-existing)
#    - com.anima.adversarial_bench_periodic.plist     (D24: new, every 6h)
#    - com.anima.cert_dag_periodic.plist              (E26: new, every 12h)
#
#  USAGE
#    bash tool/launchd_install_local.bash                # default: --dry-run
#    bash tool/launchd_install_local.bash --link         # symlink only, no load
#    bash tool/launchd_install_local.bash --activate     # symlink + launchctl load
#    bash tool/launchd_install_local.bash --unload       # launchctl unload + unlink
#    bash tool/launchd_install_local.bash --status       # report current state
#
#  HARD CONSTRAINTS
#    - Idempotent: --link / --activate / --unload may be re-run safely.
#    - Dry-run by default — caller MUST opt in to side-effects via --activate.
#    - Never edits the plist files (read-only inputs).
#    - Never modifies .roadmap or any anima SSOT.
#    - logs/ directory is created on demand (mkdir -p) since the plists' StandardOutPath / StandardErrorPath assume it exists.
# ════════════════════════════════════════════════════════════════════════════

set -euo pipefail

ANIMA_ROOT="/Users/ghost/core/anima"
SRC_DIR="${ANIMA_ROOT}/config/launchd"
DST_DIR="${HOME}/Library/LaunchAgents"
LOGS_DIR="${ANIMA_ROOT}/logs"

PLISTS=(
    "com.anima.h100_auto_kill.plist"
    "com.anima.cert_watch.plist"
    "com.anima.airgenome_keyword_dispatch.plist"
    "com.anima.worktree_merge_bot.plist"
    "com.anima.adversarial_bench_periodic.plist"
    "com.anima.cert_dag_periodic.plist"
)

MODE="${1:-}"
if [[ -z "${MODE}" ]]; then
    MODE="--dry-run"
fi

ensure_logs_dir() {
    mkdir -p "${LOGS_DIR}"
}

dry_run() {
    echo "── launchd_install_local.bash  mode=DRY-RUN ──"
    echo "  src_dir = ${SRC_DIR}"
    echo "  dst_dir = ${DST_DIR}"
    echo
    for p in "${PLISTS[@]}"; do
        local src="${SRC_DIR}/${p}"
        local dst="${DST_DIR}/${p}"
        if [[ ! -f "${src}" ]]; then
            echo "  [MISSING-SRC]  ${p}"
            continue
        fi
        if [[ -L "${dst}" || -e "${dst}" ]]; then
            echo "  [LINKED     ]  ${p}"
        else
            echo "  [NOT-LINKED ]  ${p}"
        fi
    done
    echo
    echo "  → run with --link     to create symlinks (no launchctl load)"
    echo "  → run with --activate to symlink AND launchctl load each plist"
    echo "  → run with --status   to show launchctl list state"
    echo "  → run with --unload   to launchctl unload AND remove symlinks"
}

link_only() {
    echo "── launchd_install_local.bash  mode=LINK ──"
    ensure_logs_dir
    mkdir -p "${DST_DIR}"
    for p in "${PLISTS[@]}"; do
        local src="${SRC_DIR}/${p}"
        local dst="${DST_DIR}/${p}"
        if [[ ! -f "${src}" ]]; then
            echo "  [SKIP src missing]  ${p}"
            continue
        fi
        if [[ -L "${dst}" ]]; then
            local cur
            cur="$(readlink "${dst}")"
            if [[ "${cur}" == "${src}" ]]; then
                echo "  [OK already-linked]  ${p}"
                continue
            fi
            echo "  [REPLACE-LINK    ]  ${p}  (was ${cur})"
            rm "${dst}"
            ln -s "${src}" "${dst}"
        elif [[ -e "${dst}" ]]; then
            echo "  [SKIP non-symlink dst exists]  ${p} — manual review required"
            continue
        else
            ln -s "${src}" "${dst}"
            echo "  [LINK CREATED    ]  ${p}"
        fi
    done
}

activate() {
    link_only
    echo
    echo "── launchctl load (per-plist) ──"
    for p in "${PLISTS[@]}"; do
        local dst="${DST_DIR}/${p}"
        if [[ ! -e "${dst}" ]]; then
            echo "  [SKIP not-linked]  ${p}"
            continue
        fi
        # Idempotent: launchctl load is a no-op if already loaded; suppress its
        # "already loaded" stderr.
        if launchctl load -w "${dst}" 2>/dev/null; then
            echo "  [LOADED         ]  ${p}"
        else
            echo "  [ALREADY-LOADED ]  ${p}"
        fi
    done
    echo
    echo "  → check status: launchctl list | grep com.anima"
}

unload() {
    echo "── launchd_install_local.bash  mode=UNLOAD ──"
    for p in "${PLISTS[@]}"; do
        local dst="${DST_DIR}/${p}"
        if [[ -e "${dst}" ]]; then
            if launchctl unload "${dst}" 2>/dev/null; then
                echo "  [UNLOADED       ]  ${p}"
            else
                echo "  [UNLOAD-FAILED  ]  ${p}  (may not have been loaded)"
            fi
            if [[ -L "${dst}" ]]; then
                rm "${dst}"
                echo "  [UNLINKED       ]  ${p}"
            fi
        else
            echo "  [SKIP not-linked]  ${p}"
        fi
    done
}

status() {
    echo "── launchd_install_local.bash  mode=STATUS ──"
    echo "  loaded launchd entries (com.anima.*):"
    launchctl list | awk 'NR==1 || /com\.anima\./'
    echo
    echo "  symlinks in ${DST_DIR}:"
    ls -la "${DST_DIR}/com.anima."* 2>/dev/null || echo "  (none)"
}

case "${MODE}" in
    --dry-run|"")
        dry_run
        ;;
    --link)
        link_only
        ;;
    --activate)
        activate
        ;;
    --unload)
        unload
        ;;
    --status)
        status
        ;;
    *)
        echo "usage: $0 [--dry-run|--link|--activate|--unload|--status]" >&2
        exit 2
        ;;
esac
