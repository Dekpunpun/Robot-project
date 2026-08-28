#!/usr/bin/env bash
# Build "The Vesper Manifest.app" on macOS (or a plain binary on Linux).
# For a Windows .exe you must run build.bat on a Windows machine — PyInstaller
# does not cross-compile.
set -euo pipefail
cd "$(dirname "$0")"

echo "=== installing dependencies ==="
python3 -m pip install --quiet --upgrade -r requirements.txt

echo "=== generating the icon ==="
python3 rpg/make_icon.py

echo "=== building ==="
python3 -m PyInstaller --noconfirm --clean VesperManifest.spec

echo "=== checking the build actually runs ==="
if [[ "$OSTYPE" == darwin* ]]; then
  BIN="dist/The Vesper Manifest.app/Contents/MacOS/VesperManifest"
else
  BIN="dist/VesperManifest/VesperManifest"
fi
"$BIN" --selftest

cat <<'EOF'

============================================================
 Done.
   macOS   dist/The Vesper Manifest.app   (double-click it)
   Linux   dist/VesperManifest/VesperManifest
 Ship the whole folder/bundle, not just the inner binary.
============================================================
EOF
