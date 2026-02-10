#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"
source .venv/bin/activate

export SYMBOLS="${SYMBOLS:-BTC/USDT,ETH/USDT}"
export DB_PATH="${DB_PATH:-./data/bot.sqlite}"
export PORT="${PORT:-8000}"

API_PID=""

cleanup() {
  echo "[run] cleanup..."
  if [[ -n "${API_PID}" ]] && kill -0 "${API_PID}" 2>/dev/null; then
    kill "${API_PID}" || true
  fi
}
trap cleanup EXIT

port_free() {
  ! lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1
}

choose_port() {
  local p="${PORT}"
  if port_free "${p}"; then
    echo "${p}"
    return
  fi
  for p in 8001 8002 8003 8004 8005; do
    if port_free "${p}"; then
      echo "${p}"
      return
    fi
  done
  echo ""
}

P="$(choose_port)"
if [[ -z "$P" ]]; then
  echo "[run] WARN: no free port found (8000-8005). API will NOT be started."
else
  echo "[run] Starting API on :$P ..."
  PORT="$P" python -m backend.app &
  API_PID=$!
  sleep 0.3
fi

echo "[run] Starting worker (preview mode controlled by DB) ..."
python -m backend.runtime.worker
