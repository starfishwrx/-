#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${ROOT_DIR}"

if [[ -x "${ROOT_DIR}/.venv/bin/uvicorn" ]]; then
  exec "${ROOT_DIR}/.venv/bin/uvicorn" fastapi_app:app --host 0.0.0.0 --port 8000
fi

if [[ -x "${ROOT_DIR}/.venv/bin/python" ]]; then
  exec "${ROOT_DIR}/.venv/bin/python" -m uvicorn fastapi_app:app --host 0.0.0.0 --port 8000
fi

exec uvicorn fastapi_app:app --host 0.0.0.0 --port 8000
