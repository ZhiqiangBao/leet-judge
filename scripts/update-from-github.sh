#!/usr/bin/env bash
set -euo pipefail

# Pull judge code (not a problem bank) from GitHub onto the Ubuntu host.
if [[ "$(uname -s)" != "Linux" ]]; then
  echo "Run this on the Ubuntu server."
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -d .git ]]; then
  echo "This directory is not a git clone. Clone the GitHub repo first."
  exit 1
fi

BEFORE="$(git rev-parse HEAD)"
git pull --ff-only
AFTER="$(git rev-parse HEAD)"

changed() {
  git diff --name-only "$BEFORE" "$AFTER" | grep -q "$1"
}

if [[ "$BEFORE" == "$AFTER" ]]; then
  echo "Already up to date."
else
  if changed '^backend/requirements.txt'; then
    "$ROOT/.venv/bin/pip" install -r backend/requirements.txt
  fi
  if changed '^frontend/'; then
    (cd frontend && npm install && npm run build)
  fi
fi

if systemctl is-enabled local-leet >/dev/null 2>&1; then
  sudo systemctl restart local-leet
  echo "Pulled and restarted local-leet."
else
  echo "Pulled. Restart the server yourself (./scripts/run-ubuntu.sh)."
fi
