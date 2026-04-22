#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════
#  tool/anima_cli/man_install.bash — install/uninstall anima(1) man page
#
#  PURPOSE
#    Thin wrapper around `cp`/`rm` that installs docs/man/anima.1 into the
#    platform's MANPATH. No Python. No hardcoded paths (raw#15).
#
#  USAGE
#    man_install.bash --install       # copy anima.1 into $MAN_PREFIX/man/man1/
#    man_install.bash --uninstall     # remove the installed copy
#    man_install.bash --lint          # run mandoc -Tlint on the source
#    man_install.bash --help          # print usage
#
#  ENV
#    MAN_PREFIX   override install root (default: /opt/homebrew/share on
#                 Apple Silicon, /usr/local/share elsewhere)
#    SUDO         command prefix for writes (default: sudo if not root)
# ═══════════════════════════════════════════════════════════════════════════
set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
readonly MAN_SRC="${REPO_ROOT}/docs/man/anima.1"
readonly MAN_NAME="anima.1"

_default_prefix() {
  if [[ "$(uname -s)" == "Darwin" && "$(uname -m)" == "arm64" ]]; then
    printf '%s\n' '/opt/homebrew/share'
  else
    printf '%s\n' '/usr/local/share'
  fi
}

MAN_PREFIX="${MAN_PREFIX:-$(_default_prefix)}"
readonly MAN_DIR="${MAN_PREFIX}/man/man1"
readonly MAN_DST="${MAN_DIR}/${MAN_NAME}"

if [[ -z "${SUDO+x}" ]]; then
  if [[ "$(id -u)" -eq 0 ]]; then
    SUDO=''
  else
    SUDO='sudo'
  fi
fi

usage() {
  cat <<EOF
usage: man_install.bash [--install | --uninstall | --lint | --help]

  --install     copy ${MAN_NAME} into ${MAN_DIR}/
  --uninstall   remove ${MAN_DST}
  --lint        run 'mandoc -Tlint' on ${MAN_SRC}
  --help        show this help

env:
  MAN_PREFIX    install root (current: ${MAN_PREFIX})
  SUDO          write-command prefix (current: '${SUDO}')
EOF
}

do_install() {
  if [[ ! -f "${MAN_SRC}" ]]; then
    printf 'error: man source not found: %s\n' "${MAN_SRC}" >&2
    exit 1
  fi
  printf 'installing %s -> %s\n' "${MAN_NAME}" "${MAN_DST}"
  ${SUDO} mkdir -p "${MAN_DIR}"
  ${SUDO} cp "${MAN_SRC}" "${MAN_DST}"
  ${SUDO} chmod 0644 "${MAN_DST}"
  if command -v mandb >/dev/null 2>&1; then
    ${SUDO} mandb -q >/dev/null 2>&1 || true
  fi
  printf 'ok: run `man anima` to view.\n'
}

do_uninstall() {
  if [[ -e "${MAN_DST}" ]]; then
    printf 'removing %s\n' "${MAN_DST}"
    ${SUDO} rm -f "${MAN_DST}"
    printf 'ok\n'
  else
    printf 'nothing to remove at %s\n' "${MAN_DST}"
  fi
}

do_lint() {
  if ! command -v mandoc >/dev/null 2>&1; then
    printf 'warn: mandoc not available; skipping lint\n' >&2
    exit 0
  fi
  mandoc -Tlint "${MAN_SRC}"
  printf 'lint: PASS\n'
}

main() {
  local action="${1:---help}"
  case "${action}" in
    --install)   do_install ;;
    --uninstall) do_uninstall ;;
    --lint)      do_lint ;;
    -h|--help)   usage ;;
    *)           usage; exit 2 ;;
  esac
}

main "$@"
