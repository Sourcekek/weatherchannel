#!/usr/bin/env bash
set -euo pipefail

# Cron wrapper for scan pipeline with timestamped logging
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
LOG_DIR="${REPO_ROOT}/logs"
mkdir -p "${LOG_DIR}"

TIMESTAMP=$(date -u +"%Y%m%dT%H%M%SZ")
LOG_FILE="${LOG_DIR}/scan_${TIMESTAMP}.log"

cd "${REPO_ROOT}"
python -m engine scan "$@" 2>&1 | tee "${LOG_FILE}"
