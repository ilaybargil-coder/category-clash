#!/usr/bin/env bash

set -euo pipefail

: "${PORT:?Render must provide PORT}"
: "${DATABASE_URL:?DATABASE_URL must point to the Supabase session pooler}"
: "${JWT_SECRET:?JWT_SECRET must be configured as a Render secret}"

python -m alembic upgrade head
python -m app.seed

exec python -m uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "$PORT" \
  --workers 1 \
  --ws-max-size 4096 \
  --ws-ping-interval 25 \
  --ws-ping-timeout 20
