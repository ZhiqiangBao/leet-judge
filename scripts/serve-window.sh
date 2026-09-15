#!/usr/bin/env bash
set -euo pipefail

# Run the judge in a visible terminal. Closing that window stops the server.
# If systemd local-leet is active, it is stopped first so port 8080 is free.

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export LOCAL_LEET_ROOT="$ROOT"
export PYTHONPATH="$ROOT/backend"

if [[ ! -x "$ROOT/.venv/bin/uvicorn" ]]; then
  echo "未找到 $ROOT/.venv/bin/uvicorn 。请先运行 ./scripts/setup-ubuntu.sh"
  exit 1
fi

if systemctl is-active --quiet local-leet 2>/dev/null; then
  echo "正在停止后台服务 local-leet，改由本窗口托管……"
  sudo systemctl stop local-leet
fi

run_server() {
  cd "$ROOT"
  echo "=============================================="
  echo "  Leet Hub  日志窗口"
  echo "  地址: http://0.0.0.0:8080"
  echo "  关闭本窗口或 Ctrl+C = 停止整个服务"
  echo "=============================================="
  echo
  exec "$ROOT/.venv/bin/uvicorn" app.main:app --host 0.0.0.0 --port 8080 --log-level info
}

# Already in a terminal (SSH or current tab): run here so hangup stops the process.
if [[ -z "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]] || [[ "${1:-}" == "--here" ]]; then
  run_server
fi

CMD=$(printf '%q ' "$ROOT/scripts/serve-window.sh" --here)

if command -v gnome-terminal >/dev/null; then
  exec gnome-terminal --title="Leet Hub" -- bash -lc "$CMD"
fi
if command -v kgx >/dev/null; then
  exec kgx --title="Leet Hub" -e "bash -lc $CMD"
fi
if command -v xfce4-terminal >/dev/null; then
  exec xfce4-terminal --title="Leet Hub" -e "bash -lc $CMD"
fi
if command -v konsole >/dev/null; then
  exec konsole --title "Leet Hub" -e bash -lc "$CMD"
fi
if command -v xterm >/dev/null; then
  exec xterm -T "Leet Hub" -e bash -lc "$CMD"
fi

echo "未找到图形终端，在当前窗口运行。关闭此终端即停止服务。"
run_server
