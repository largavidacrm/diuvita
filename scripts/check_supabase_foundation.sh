#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT/.env"

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
  -c "select count(*) as allowed_admin_emails from public.admin_users where active = true;" \
  -c "select lower(u.email) as admin_email, u.email_confirmed_at is not null as email_confirmed from auth.users u join public.admin_users au on lower(au.email) = lower(u.email) where au.active = true order by admin_email;" \
  -c "select count(*) as admin_clinic_edit_function from pg_proc p join pg_namespace n on n.oid = p.pronamespace where n.nspname = 'public' and p.proname = 'admin_update_clinic';" \
  -c "select count(*) as public_site_feed_function from pg_proc p join pg_namespace n on n.oid = p.pronamespace where n.nspname = 'public' and p.proname = 'public_clinics_for_site';" \
  -c "select status, count(*) from public.clinics group by status order by status;" \
  -c "select count(*) as open_review_items from public.review_queue where status = 'open';" \
  -c "select count(*) as queued_jobs from public.agent_jobs where status = 'queued';"
