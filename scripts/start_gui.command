#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
PYTHON_BIN="${ROOT_DIR}/.venv/bin/python"

if [[ -x "${PYTHON_BIN}" ]]; then
  if "${PYTHON_BIN}" - <<'PY' >/dev/null 2>&1
import tkinter as tk
root = tk.Tk()
root.withdraw()
root.destroy()
print("ok")
PY
  then
    exec "${PYTHON_BIN}" "${ROOT_DIR}/report_launcher_gui.py"
  fi
fi

if command -v /usr/bin/python3 >/dev/null 2>&1; then
  if /usr/bin/python3 - <<'PY' >/dev/null 2>&1
import tkinter as tk
root = tk.Tk()
root.withdraw()
root.destroy()
print("ok")
PY
  then
    exec /usr/bin/python3 "${ROOT_DIR}/report_launcher_gui.py"
  fi
fi

exec python3 "${ROOT_DIR}/report_launcher_gui.py"
