#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

CONFIG_PATH="${CONFIG_PATH:-${ROOT_DIR}/config.yaml}"
PYTHON_BIN="${PYTHON_BIN:-${ROOT_DIR}/.venv/bin/python}"
LOG_DIR="${LOG_DIR:-${ROOT_DIR}/output/scheduler_logs}"
LOCK_DIR="${ROOT_DIR}/output/.daily_report_lock"
ENV_FILE="${ENV_FILE:-${ROOT_DIR}/.env.scheduler}"

MAX_RETRIES="${MAX_RETRIES:-3}"
RETRY_DELAY_SECONDS="${RETRY_DELAY_SECONDS:-300}"
DATE_MODE="${DATE_MODE:-today}" # today | yesterday
RUN_AUTH_CHECK="${RUN_AUTH_CHECK:-1}"
VERIFY_FEISHU_CONTENT="${VERIFY_FEISHU_CONTENT:-0}"
DISABLE_FEISHU_PUSH="${DISABLE_FEISHU_PUSH:-0}"

mkdir -p "${LOG_DIR}" "${ROOT_DIR}/output"

if [[ -f "${ENV_FILE}" ]]; then
  # shellcheck disable=SC1090
  set -a
  source "${ENV_FILE}"
  set +a
fi

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "[ERROR] Python not found: ${PYTHON_BIN}" >&2
  exit 1
fi

resolve_yesterday() {
  if date -d "yesterday" +%F >/dev/null 2>&1; then
    date -d "yesterday" +%F
    return
  fi
  if date -v-1d +%F >/dev/null 2>&1; then
    date -v-1d +%F
    return
  fi
  python3 - <<'PY'
from datetime import date, timedelta
print((date.today() - timedelta(days=1)).isoformat())
PY
}

if [[ $# -ge 1 && -n "${1:-}" ]]; then
  REPORT_DATE="$1"
else
  if [[ "${DATE_MODE}" == "yesterday" ]]; then
    REPORT_DATE="$(resolve_yesterday)"
  else
    REPORT_DATE="$(date +%F)"
  fi
fi

LOG_FILE="${LOG_DIR}/daily_$(date +%Y%m%d_%H%M%S).log"
{
  echo "[$(date '+%F %T')] start daily report, date=${REPORT_DATE}"
  echo "[$(date '+%F %T')] root=${ROOT_DIR}"
  echo "[$(date '+%F %T')] config=${CONFIG_PATH}"
} | tee -a "${LOG_FILE}"

if ! mkdir "${LOCK_DIR}" 2>/dev/null; then
  echo "[$(date '+%F %T')] another run is in progress, skip." | tee -a "${LOG_FILE}"
  exit 0
fi
trap 'rm -rf "${LOCK_DIR}"' EXIT

if [[ "${RUN_AUTH_CHECK}" == "1" ]]; then
  AUTH_CMD=(
    "${PYTHON_BIN}" "${ROOT_DIR}/generate_daily_report.py"
    "--config" "${CONFIG_PATH}"
    "--check-extra-auth"
    "--date" "${REPORT_DATE}"
  )
  echo "[$(date '+%F %T')] auth precheck..." | tee -a "${LOG_FILE}"
  set +e
  "${AUTH_CMD[@]}" 2>&1 | tee -a "${LOG_FILE}"
  AUTH_EXIT=${PIPESTATUS[0]}
  set -e
  if [[ ${AUTH_EXIT} -ne 0 ]]; then
    echo "[$(date '+%F %T')] auth precheck failed, stop." | tee -a "${LOG_FILE}"
    exit ${AUTH_EXIT}
  fi
fi

RUN_CMD=(
  "${PYTHON_BIN}" "${ROOT_DIR}/generate_daily_report.py"
  "--config" "${CONFIG_PATH}"
  "--date" "${REPORT_DATE}"
  "--with-extra-metrics"
)
if [[ "${VERIFY_FEISHU_CONTENT}" == "1" ]]; then
  RUN_CMD+=("--verify-feishu-content")
fi
if [[ "${DISABLE_FEISHU_PUSH}" == "1" ]]; then
  RUN_CMD+=("--no-push-feishu-doc")
fi

attempt=1
while [[ ${attempt} -le ${MAX_RETRIES} ]]; do
  echo "[$(date '+%F %T')] run attempt ${attempt}/${MAX_RETRIES}" | tee -a "${LOG_FILE}"
  set +e
  "${RUN_CMD[@]}" 2>&1 | tee -a "${LOG_FILE}"
  RUN_EXIT=${PIPESTATUS[0]}
  set -e
  if [[ ${RUN_EXIT} -eq 0 ]]; then
    echo "[$(date '+%F %T')] success." | tee -a "${LOG_FILE}"
    exit 0
  fi
  if [[ ${attempt} -lt ${MAX_RETRIES} ]]; then
    echo "[$(date '+%F %T')] failed, sleep ${RETRY_DELAY_SECONDS}s then retry." | tee -a "${LOG_FILE}"
    sleep "${RETRY_DELAY_SECONDS}"
  fi
  attempt=$((attempt + 1))
done

echo "[$(date '+%F %T')] all retries failed." | tee -a "${LOG_FILE}"
exit 1
