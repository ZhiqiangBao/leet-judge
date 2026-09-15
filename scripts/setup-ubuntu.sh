#!/usr/bin/env bash
set -euo pipefail

# First-time install on the Ubuntu judge host.
# To start a stopped service later:  sudo systemctl start local-leet
# Do not re-run this script just to start it (apt zig 0.14 can overwrite 0.16).

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "This setup script is for the Ubuntu server, not the development PC."
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
USER_NAME="${SUDO_USER:-$USER}"
SERVICE_SRC="$ROOT/scripts/local-leet.service"
UNIT="/etc/systemd/system/local-leet.service"
REINSTALL=0
if [[ "${1:-}" == "--reinstall" ]]; then
  REINSTALL=1
fi

start_unit() {
  sudo systemctl daemon-reload
  sudo systemctl enable --now local-leet.service
  echo
  echo "local-leet started. Open http://127.0.0.1:8080"
  systemctl --no-pager --full status local-leet || true
}

if [[ -f "$UNIT" && "$REINSTALL" -eq 0 ]]; then
  echo "Already installed. Starting local-leet (not a full reinstall)."
  echo "Service was stopped? That is:  sudo systemctl start local-leet"
  echo "Need to reinstall packages?    $0 --reinstall"
  start_unit
  exit 0
fi

export DEBIAN_FRONTEND=noninteractive
sudo apt-get update

PKGS=(python3 python3-venv python3-pip g++ gcc nodejs npm golang-go rustc)
if command -v zig >/dev/null 2>&1; then
  echo "Keeping existing zig $(zig version 2>/dev/null || echo unknown); not apt-installing zig 0.14."
else
  PKGS+=(zig)
fi
sudo apt-get install -y "${PKGS[@]}"

cd "$ROOT"
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r backend/requirements.txt

if command -v npm >/dev/null; then
  (cd frontend && npm install && npm run build)
  sudo npm install -g typescript
else
  echo "npm not found; install Node.js and run: cd frontend && npm install && npm run build"
  exit 1
fi

sed \
  -e "s|@ROOT@|$ROOT|g" \
  -e "s|@USER@|$USER_NAME|g" \
  "$SERVICE_SRC" | sudo tee "$UNIT" >/dev/null

start_unit
echo "If ufw is enabled: sudo ufw allow 8080/tcp"
echo "Register admin on this machine only: http://127.0.0.1:8081"
echo "Later, import a problem zip in the admin 题库 page."
echo "Later, update judge code: ./scripts/update-from-github.sh"
echo "Later, start a stopped service: sudo systemctl start local-leet"
