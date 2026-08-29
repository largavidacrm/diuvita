#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT/.env"
SQL_FILE="${1:-}"

if [ -z "$SQL_FILE" ] || [ ! -f "$SQL_FILE" ]; then
  echo "Usage: scripts/apply_supabase_sql.sh path/to/file.sql" >&2
  exit 1
fi

if [ ! -f "$ENV_FILE" ]; then
  echo "Missing .env." >&2
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
SUPABASE_DB_HOST="$(env_or_file SUPABASE_DB_HOST db.twxhcmvzbpnrneywdece.supabase.co)"
SUPABASE_DB_PORT="$(env_or_file SUPABASE_DB_PORT 5432)"
SUPABASE_DB_NAME="$(env_or_file SUPABASE_DB_NAME postgres)"
SUPABASE_DB_USER="$(env_or_file SUPABASE_DB_USER postgres)"

if [ -z "${SUPABASE_DB_PASSWORD:-}" ]; then
  echo "Set SUPABASE_DB_PASSWORD in .env first." >&2
  exit 1
fi

PSQL="${PSQL:-}"
if [ -z "$PSQL" ]; then
  if command -v psql >/dev/null 2>&1; then
    PSQL="$(command -v psql)"
  elif [ -x /opt/homebrew/opt/libpq/bin/psql ]; then
    PSQL="/opt/homebrew/opt/libpq/bin/psql"
  else
    echo "psql was not found." >&2
    exit 1
  fi
fi

export PGPASSWORD="$SUPABASE_DB_PASSWORD"
export PGSSLMODE=require

"$PSQL" \
  -h "$SUPABASE_DB_HOST" \
  -p "$SUPABASE_DB_PORT" \
  -d "$SUPABASE_DB_NAME" \
  -U "$SUPABASE_DB_USER" \
  -v ON_ERROR_STOP=1 \
  -f "$SQL_FILE"
