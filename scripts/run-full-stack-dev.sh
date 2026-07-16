#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_PID=""

cleanup() {
  if [[ -n "$BACKEND_PID" ]]; then
    kill "$BACKEND_PID" >/dev/null 2>&1 || true
    wait "$BACKEND_PID" 2>/dev/null || true
  fi
}

trap cleanup EXIT INT TERM

"$PROJECT_DIR/scripts/prepare-local-dev.sh"

echo "Starting Backend on http://localhost:8000..."
cd "$PROJECT_DIR/backend"
"$PROJECT_DIR/backend/.venv/bin/python" -m uvicorn \
  app.main:app --reload --port 8000 --ws-max-size 4096 &
BACKEND_PID=$!

echo "Starting Frontend on http://localhost:3000..."
cd "$PROJECT_DIR/frontend"
npm run dev
