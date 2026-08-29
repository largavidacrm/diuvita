#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EMAIL="${1:-}"

if [ -z "$EMAIL" ]; then
  echo "Usage: scripts/add_supabase_admin.sh email@example.com" >&2
  exit 1
fi

TMP_SQL="$(mktemp)"
trap 'rm -f "$TMP_SQL"' EXIT

python3 - "$EMAIL" > "$TMP_SQL" <<'PY'
import sys

email = sys.argv[1].strip().lower()
if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
    raise SystemExit("Use a valid email address.")

safe = email.replace("'", "''")
print("begin;")
print(
    "insert into public.admin_users (email, role, active) "
    f"values ('{safe}', 'owner', true) "
    "on conflict ((lower(email))) do update set active = true, role = 'owner', updated_at = now();"
)
print("commit;")
PY

"$ROOT/scripts/apply_supabase_sql.sh" "$TMP_SQL"
echo "Admin email allowed: $EMAIL"
