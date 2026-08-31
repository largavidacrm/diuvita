#!/usr/bin/env python3
"""Checks public-site rebuild pending control migration markers."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "supabase" / "migrations" / "0023_public_site_rebuild_pending_control.sql"


def check(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")

    for marker in [
        "add column if not exists last_change_at",
        "add column if not exists last_sent_at",
        "private.public_site_rebuild_batch_minutes",
        "private.request_public_site_rebuild",
        "last_change_at = excluded.last_change_at",
        "coalesce(last_sent_at, last_requested_at)",
        "public.admin_publication_control_summary",
        "last_public_site_change_at",
        "pending_public_site_rebuild",
        "can_request_public_site_rebuild_now",
        "public.admin_request_public_site_rebuild_now",
        "public.is_admin()",
        "net.http_post",
        "public_site_rebuild_requested",
        "grant execute on function public.admin_request_public_site_rebuild_now(text) to authenticated",
    ]:
        check(marker in sql, f"missing rebuild control migration marker: {marker}")

    print("OK public-site rebuild control: pending state is tracked")


if __name__ == "__main__":
    main()
