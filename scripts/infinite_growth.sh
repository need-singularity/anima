#!/usr/bin/env bash
set -euo pipefail
GROWTH_NAME="anima"
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DOMAIN="consciousness"

# 공통 라이브러리 (shared/loop/anima.json에서 interval/max_cycles 자동 로드)
COMMON="${NEXUS:-$HOME/Dev/nexus}/scripts/lib/growth_common.sh"
source "$COMMON"
MAX_CYCLES=${1:-${MAX_CYCLES:-999}}
INTERVAL=${2:-${INTERVAL:-999}}

# 프로젝트별 phases
domain_phases() {
    local cycle="$1" load="$2"

    # 1. 학습 체크포인트 스캔
    log_info "Phase: 학습 체크포인트 스캔"
    local py_count
    py_count=$(find "$PROJECT_ROOT/src" -name '*.py' 2>/dev/null | wc -l | tr -d ' ')
    log_info "  src/ Python 파일: ${py_count}개"
    if [ -d "$PROJECT_ROOT/checkpoints" ]; then
        local ckpt_count
        ckpt_count=$(ls "$PROJECT_ROOT/checkpoints" 2>/dev/null | wc -l | tr -d ' ')
        log_info "  checkpoints/: ${ckpt_count}개 항목"
        write_growth_bus "checkpoint_scan" "ok" "py=${py_count},ckpt=${ckpt_count}"
    else
        log_info "  checkpoints/ 디렉토리 없음"
        write_growth_bus "checkpoint_scan" "warn" "no_checkpoints_dir"
    fi

    # 2. 의식 법칙 검증
    log_info "Phase: 의식 법칙 검증"
    local laws_file="$PROJECT_ROOT/.shared/consciousness_laws.json"
    if [ -f "$laws_file" ]; then
        local laws_count
        laws_count=$(python3 -c "import json; print(len(json.load(open('$laws_file'))))" 2>/dev/null || echo "?")
        log_info "  consciousness_laws.json: ${laws_count} 항목"
        write_growth_bus "consciousness_laws" "ok" "count=${laws_count}"
    else
        log_info "  consciousness_laws.json 없음"
        write_growth_bus "consciousness_laws" "skip" "not_found"
    fi

    # 3. 빌드 상태
    log_info "Phase: 빌드 상태 확인"
    if python3 -c "import anima" 2>/dev/null; then
        log_info "  import anima: OK"
        write_growth_bus "build" "ok" "import_success"
    else
        log_info "  import anima: FAIL"
        write_growth_bus "build" "warn" "import_fail"
    fi

    # 4. 성장 스캔
    log_info "Phase: 성장 스캔"
    local scan_script="$PROJECT_ROOT/.growth/scan.py"
    if [ -f "$scan_script" ]; then
        python3 "$scan_script" 2>/dev/null | tail -5 | while IFS= read -r line; do
            log_info "  $line"
        done
        write_growth_bus "growth_scan" "ok" ""
    else
        log_info "  .growth/scan.py 없음 — skip"
        write_growth_bus "growth_scan" "skip" "no_script"
    fi
}

run_growth_loop "domain_phases"
