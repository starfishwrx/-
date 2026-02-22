#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${ROOT_DIR}"

STAMP="$(date +%Y%m%d_%H%M%S)"
RELEASE_DIR="${ROOT_DIR}/dist/releases/${STAMP}"
mkdir -p "${RELEASE_DIR}"

echo "[1/3] Build CLI package..."
uv run --python .venv/bin/python --with pyinstaller pyinstaller \
  --noconfirm --clean \
  --name autodatareport-cli \
  generate_daily_report.py \
  --add-data templates:templates \
  --add-data config.example.yaml:. \
  --add-data hosts_870.example.yaml:. \
  --add-data hosts_505.example.yaml:. \
  --add-data extra_auth.example.json:.

echo "[2/3] Build GUI package..."
uv run --python .venv/bin/python --with pyinstaller pyinstaller \
  --noconfirm --clean \
  --windowed \
  --name autodatareport-gui \
  report_launcher_gui.py \
  --add-data config.example.yaml:. \
  --add-data scripts:scripts

echo "[3/3] Assemble release artifacts..."
cp -R "${ROOT_DIR}/dist/autodatareport-cli" "${RELEASE_DIR}/"
cp -R "${ROOT_DIR}/dist/autodatareport-gui.app" "${RELEASE_DIR}/"
cp "${ROOT_DIR}/scripts/start_gui.command" "${RELEASE_DIR}/"
chmod +x "${RELEASE_DIR}/start_gui.command"

(cd "${ROOT_DIR}/dist" && zip -qr "releases/${STAMP}/autodatareport-cli-macos.zip" "autodatareport-cli")
(cd "${ROOT_DIR}/dist" && zip -qr "releases/${STAMP}/autodatareport-gui-macos.zip" "autodatareport-gui.app")

echo "Release ready at: ${RELEASE_DIR}"
echo " - autodatareport-cli-macos.zip"
echo " - autodatareport-gui-macos.zip"
