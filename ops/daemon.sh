#!/usr/bin/env bash
set -euo pipefail

# Daemon launcher — runs scan loop as a background process
# Usage:
#   ./ops/daemon.sh start [--live]   Start daemon (background, nohup)
#   ./ops/daemon.sh stop             Stop daemon
#   ./ops/daemon.sh status           Show daemon status
#   ./ops/daemon.sh logs             Tail latest scan log

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "${REPO_ROOT}"

# Activate venv
if [ -f .venv/bin/activate ]; then
    source .venv/bin/activate
fi

CONFIG="${CONFIG:-ops/configs/live.yaml}"
INTERVAL="${INTERVAL:-120}"
LOG_FILE="logs/daemon.log"

case "${1:-help}" in
    start)
        shift
        mkdir -p logs
        echo "Starting scan daemon (interval=${INTERVAL}s, config=${CONFIG})..."
        nohup python -m engine --config "${CONFIG}" daemon --interval "${INTERVAL}" "$@" \
            > "${LOG_FILE}" 2>&1 &
        DAEMON_PID=$!
        echo "Daemon started (pid ${DAEMON_PID})"
        echo "  Logs: tail -f ${LOG_FILE}"
        echo "  Stop: $0 stop"
        ;;
    stop)
        python -m engine daemon --stop
        ;;
    status)
        python -m engine daemon --status
        ;;
    logs)
        if [ -f "${LOG_FILE}" ]; then
            tail -f "${LOG_FILE}"
        else
            echo "No daemon log found at ${LOG_FILE}"
            # Show latest scan log instead
            LATEST=$(ls -t logs/scan_*.log 2>/dev/null | head -1)
            if [ -n "${LATEST:-}" ]; then
                echo "Latest scan log: ${LATEST}"
                tail -20 "${LATEST}"
            fi
        fi
        ;;
    help|*)
        echo "Usage: $0 {start|stop|status|logs}"
        echo ""
        echo "  start [--live]  Start daemon in background"
        echo "  stop            Stop running daemon"
        echo "  status          Show daemon status"
        echo "  logs            Tail daemon/scan logs"
        echo ""
        echo "Environment:"
        echo "  CONFIG=path     Config file (default: ops/configs/live.yaml)"
        echo "  INTERVAL=secs   Scan interval (default: 120)"
        ;;
esac
