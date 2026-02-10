#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"
source .venv/bin/activate

export SYMBOLS="${SYMBOLS:-BTC/USDT,ETH/USDT}"
export DB_PATH="${DB_PATH:-./data/bot.sqlite}"

echo "[run] Starting API on :8000 ..."
python -m backend.app &
API_PID=$!

echo "[run] Starting worker (preview mode controlled by DB) ..."
python -m backend.runtime.worker

echo "[run] Worker stopped, stopping API..."
kill $API_PID || true
