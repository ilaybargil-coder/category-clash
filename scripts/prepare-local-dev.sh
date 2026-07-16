#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"

if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew is required to start PostgreSQL." >&2
  exit 1
fi

echo "Starting PostgreSQL..."
brew services start postgresql@16 >/dev/null

PG_BIN="$(brew --prefix postgresql@16)/bin"

for _ in {1..30}; do
  if "$PG_BIN/pg_isready" -q; then
    break
  fi
  sleep 1
done

if ! "$PG_BIN/pg_isready" -q; then
  echo "PostgreSQL did not become ready within 30 seconds." >&2
  exit 1
fi

echo "Ensuring the local game role and database exist..."
"$PG_BIN/psql" -d postgres -v ON_ERROR_STOP=1 -q -c \
  "DO \$\$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'game') THEN CREATE ROLE game LOGIN PASSWORD 'game'; ELSE ALTER ROLE game WITH LOGIN PASSWORD 'game'; END IF; END \$\$;"

if ! "$PG_BIN/psql" -d postgres -Atq -c \
  "SELECT 1 FROM pg_database WHERE datname = 'game'" | grep -q 1; then
  "$PG_BIN/createdb" -O game game
fi

echo "Running migrations and loading demo data..."
cd "$BACKEND_DIR"
"$BACKEND_DIR/.venv/bin/alembic" upgrade head
"$BACKEND_DIR/.venv/bin/python" -m app.seed

echo "Local services and database are ready."
