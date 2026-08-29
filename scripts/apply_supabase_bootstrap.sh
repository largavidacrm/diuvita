#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT/.env"
BOOTSTRAP_SQL="/tmp/diuvita_supabase_bootstrap.sql"

if [ ! -f "$ENV_FILE" ]; then
  echo "Missing .env. Copy .env.example to .env and set SUPABASE_DB_PASSWORD." >&2
  exit 1
fi

env_value() {
  awk -v key="$1" '
    $0 ~ "^" key "=" {
    sub(/^[^=]*=/, "")
    gsub(/^'\''|'\''$/, "")
    gsub(/^"|"$/, "")
    print
    exit
  }
' "$ENV_FILE"
}

env_or_file() {
  local key="$1"
  local default_value="${2:-}"
  local value="${!key-}"
  if [ -z "$value" ]; then
    value="$(env_value "$key")"
  fi
  if [ -z "$value" ]; then
    value="$default_value"
  fi
  printf '%s' "$value"
}

SUPABASE_DB_PASSWORD="$(env_or_file SUPABASE_DB_PASSWORD)"
DATABASE_URL="$(env_or_file DATABASE_URL)"
SUPABASE_DB_HOST="$(env_or_file SUPABASE_DB_HOST db.twxhcmvzbpnrneywdece.supabase.co)"
SUPABASE_DB_PORT="$(env_or_file SUPABASE_DB_PORT 5432)"
SUPABASE_DB_NAME="$(env_or_file SUPABASE_DB_NAME postgres)"
SUPABASE_DB_USER="$(env_or_file SUPABASE_DB_USER postgres)"

if [ -n "${DATABASE_URL:-}" ] && printf '%s' "$DATABASE_URL" | grep -q '\[YOUR-PASSWORD\]'; then
  DATABASE_URL=""
fi

if [ -n "${SUPABASE_DB_PASSWORD:-}" ]; then
  DATABASE_URL=""
fi

if [ -z "${SUPABASE_DB_PASSWORD:-}" ] && [ -z "${DATABASE_URL:-}" ]; then
  echo "Set SUPABASE_DB_PASSWORD in .env, or set DATABASE_URL with the real password." >&2
  exit 1
fi

PSQL="${PSQL:-}"
if [ -z "$PSQL" ]; then
  if command -v psql >/dev/null 2>&1; then
    PSQL="$(command -v psql)"
  elif [ -x /opt/homebrew/opt/libpq/bin/psql ]; then
    PSQL="/opt/homebrew/opt/libpq/bin/psql"
  else
    echo "psql was not found. Install libpq or PostgreSQL client tools first." >&2
    exit 1
  fi
fi

if [ -n "${DATABASE_URL:-}" ]; then
  if printf '%s' "$DATABASE_URL" | grep -q '?'; then
    CONNECTION_URL="${DATABASE_URL}&sslmode=require"
  else
    CONNECTION_URL="${DATABASE_URL}?sslmode=require"
  fi
  PSQL_ARGS=("$CONNECTION_URL")
else
  export PGPASSWORD="$SUPABASE_DB_PASSWORD"
  export PGSSLMODE=require
  PSQL_ARGS=(
    -h "$SUPABASE_DB_HOST"
    -p "$SUPABASE_DB_PORT"
    -d "$SUPABASE_DB_NAME"
    -U "$SUPABASE_DB_USER"
  )
fi

python3 "$ROOT/scripts/export_supabase_bootstrap.py" > "$BOOTSTRAP_SQL"
"$PSQL" "${PSQL_ARGS[@]}" -v ON_ERROR_STOP=1 -f "$BOOTSTRAP_SQL"

echo "Supabase bootstrap applied successfully."
