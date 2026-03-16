#!/bin/zsh

set -euo pipefail

if [[ "${OSTYPE}" != darwin* ]]; then
  echo "This script must be run on macOS." >&2
  exit 1
fi

if ! python3 -m pip show pyinstaller >/dev/null 2>&1; then
  echo "PyInstaller is not installed. Run: pip install -e \".[build]\"" >&2
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BUILD_DIR="${ROOT_DIR}/build"
DIST_DIR="${ROOT_DIR}/dist"
ICON_NAME="ShunYaku"
APP_PATH="${DIST_DIR}/${ICON_NAME}.app"
ZIP_PATH="${DIST_DIR}/${ICON_NAME}-mac.zip"
PYINSTALLER_CONFIG_DIR="${BUILD_DIR}/pyinstaller-config"

mkdir -p "${BUILD_DIR}" "${DIST_DIR}"

cd "${ROOT_DIR}"
PYINSTALLER_CONFIG_DIR="${PYINSTALLER_CONFIG_DIR}" \
  pyinstaller \
  --noconfirm \
  --distpath "${DIST_DIR}" \
  --workpath "${BUILD_DIR}/pyinstaller" \
  ShunYaku.spec

if [[ ! -d "${APP_PATH}" ]]; then
  echo "App bundle was not created: ${APP_PATH}" >&2
  exit 1
fi

if [[ -n "${CODESIGN_IDENTITY:-}" ]]; then
  codesign --force --deep --options runtime --timestamp --sign "${CODESIGN_IDENTITY}" "${APP_PATH}"
fi

ditto -c -k --keepParent "${APP_PATH}" "${ZIP_PATH}"

if [[ -n "${APPLE_NOTARY_PROFILE:-}" ]]; then
  xcrun notarytool submit "${ZIP_PATH}" --keychain-profile "${APPLE_NOTARY_PROFILE}" --wait
  xcrun stapler staple "${APP_PATH}"
  ditto -c -k --keepParent "${APP_PATH}" "${ZIP_PATH}"
fi

echo "Built app: ${APP_PATH}"
echo "Built archive: ${ZIP_PATH}"
