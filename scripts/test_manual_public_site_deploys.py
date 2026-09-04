#!/usr/bin/env python3
"""Checks that automatic clinic changes cannot consume a Netlify deploy."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "supabase" / "migrations" / "0026_manual_public_site_deploys.sql"


def check(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def function_body(sql: str, signature: str) -> str:
    marker = f"create or replace function {signature}"
    check(marker in sql, f"missing function: {signature}")
    return sql.split(marker, 1)[1].split("$$;", 1)[0]


def main() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")
    automatic_path = function_body(sql, "private.request_public_site_rebuild()")
    clinic_trigger_path = function_body(sql, "private.clinics_request_public_site_rebuild()")

    for marker in [
        "vitalarga_publication_mode",
        "'manual'",
        "private.mark_public_site_rebuild_pending()",
        "last_change_at = excluded.last_change_at",
        "'automatic_rebuild_enabled', false",
        "'publication_mode', publication_mode",
    ]:
        check(marker in sql, f"missing manual publication marker: {marker}")

    check(
        "private.mark_public_site_rebuild_pending()" in automatic_path,
        "automatic trigger path must only mark changes as pending",
    )
    check(
        "net.http_post" not in automatic_path,
        "automatic trigger path must never call Netlify",
    )
    check(
        "new.status in ('published', 'preliminary')" in clinic_trigger_path,
        "new draft clinics must not create public deploy work",
    )
    check(
        "was_public or is_public" in clinic_trigger_path,
        "only visible-status updates should create public deploy work",
    )
    check(
        "net.http_post" not in clinic_trigger_path,
        "clinic trigger must never call Netlify",
    )

    manual_path = function_body(
        sql,
        "public.admin_request_public_site_rebuild_now(p_note text default null)",
    )
    check("public.is_admin()" in manual_path, "manual deploy must require an admin")
    check("has_pending_changes" in manual_path, "manual deploy must require pending public changes")
    check("'status', 'skipped'" in manual_path, "empty manual requests must be skipped")
    check("net.http_post" in manual_path, "manual admin action must call the Netlify hook")

    admin = (ROOT / "admin" / "index.html").read_text(encoding="utf-8")
    for marker in [
        "data.publication_mode",
        'control.publicationMode === "manual"',
        "Manual · pendiente",
        "Netlify solo se ejecutará al pulsar Actualizar web ahora",
        "Queda pendiente hasta que pulses Actualizar web ahora",
        "No había cambios públicos pendientes. Netlify no se ha ejecutado.",
    ]:
        check(marker in admin, f"missing manual admin guidance: {marker}")

    print("OK manual public deploys: only the explicit admin action can call Netlify")


if __name__ == "__main__":
    main()
