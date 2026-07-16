#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

"$PROJECT_DIR/scripts/prepare-local-dev.sh"

cd "$PROJECT_DIR/backend"
exec "$PROJECT_DIR/backend/.venv/bin/python" -m uvicorn \
  app.main:app --reload --port 8000 --ws-max-size 4096
