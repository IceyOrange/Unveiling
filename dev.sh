#!/usr/bin/env bash
# dev.sh — one command to start open-websearch daemon + Unveiling
#
# Usage:
#   ./dev.sh            # web mode (Flask on :5001)
#   ./dev.sh cli "AI 时代的焦虑"  # CLI mode
#
# Requires: npx, python venv at .venv/

set -euo pipefail
cd "$(dirname "$0")"

# ── colors ──
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; DIM='\033[2m'; RST='\033[0m'

log()  { echo -e "${GREEN}[dev]${RST} $*"; }
warn() { echo -e "${YELLOW}[dev]${RST} $*"; }
die()  { echo -e "${RED}[dev]${RST} $*" >&2; exit 1; }

# ── config ──
DAEMON_URL="${WEBSEARCH_DAEMON_URL:-http://localhost:3000}"
DAEMON_CMD="${WEBSEARCH_CMD:-npx open-websearch@latest}"
ENGINE="${WEBSEARCH_ENGINE:-duckduckgo}"
MODE="${1:-web}"

# ── cleanup trap ──
CHILD_PIDS=()
cleanup() {
    echo ""
    log "shutting down (${#CHILD_PIDS[@]} process(es))..."
    for pid in "${CHILD_PIDS[@]}"; do
        kill "$pid" 2>/dev/null || true
    done
    wait 2>/dev/null
    log "done."
}
trap cleanup EXIT INT TERM

# ── start daemon ──
start_daemon() {
    log "starting open-websearch daemon ($ENGINE)..."
    WEBSEARCH_ENGINE="$ENGINE" $DAEMON_CMD &
    CHILD_PIDS+=($!)

    # wait until healthy (up to 30s)
    local i=0
    while [ $i -lt 30 ]; do
        if curl -sf --max-time 2 "${DAEMON_URL}/health" >/dev/null 2>&1; then
            log "daemon ready at $DAEMON_URL"
            return 0
        fi
        sleep 1
        i=$((i + 1))
    done
    warn "daemon not healthy after 30s — Unveiling will fall back to Serper"
}

# ── start unvealing ──
source .venv/bin/activate

start_daemon

case "$MODE" in
    web)
        log "starting Unveiling web (Flask :5001)..."
        python frontend/app.py &
        CHILD_PIDS+=($!)
        ;;
    cli)
        shift || true
        [ $# -eq 0 ] && die "cli mode needs a question: ./dev.sh cli \"你的问题\""
        log "starting Unveiling CLI..."
        python main.py "$@"
        # CLI exits on its own — skip wait
        exit 0
        ;;
    *)
        die "unknown mode '$MODE' — use 'web' or 'cli'"
        ;;
esac

log "all services running. Ctrl+C to stop."
wait
