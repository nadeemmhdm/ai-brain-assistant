#!/usr/bin/env bash
set -euo pipefail
REPO="https://github.com/nadeemmhdm/ai-brain-assistant.git"
INSTALL_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/ai-brain-assistant"

command -v git >/dev/null 2>&1 || { echo "git is required. Install git with your OS package manager and rerun."; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "Python 3.10+ is required. Install Python and rerun."; exit 1; }
command -v node >/dev/null 2>&1 || { echo "Node.js 18+ is required. Install Node.js LTS and rerun."; exit 1; }

if [ -d "$INSTALL_DIR/.git" ]; then
  echo "[install] Existing AI Brain installation found."
elif [ -e "$INSTALL_DIR" ]; then
  echo "Install path exists but is not an AI Brain git checkout: $INSTALL_DIR" >&2
  exit 1
else
  echo "[install] Downloading AI Brain..."
  mkdir -p "$(dirname "$INSTALL_DIR")"
  git clone "$REPO" "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"
python3 scripts/bootstrap.py
echo
echo "Installed successfully: $INSTALL_DIR"
echo "Start AI Brain with: $INSTALL_DIR/run.sh"
