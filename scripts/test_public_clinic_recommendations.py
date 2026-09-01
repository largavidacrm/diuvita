#!/usr/bin/env python3
"""Checks that public clinic recommendations become safe internal jobs."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def check(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    source = (ROOT / "build.py").read_text(encoding="utf-8")
    sql = (ROOT / "supabase" / "migrations" / "0025_public_clinic_recommendations.sql").read_text(encoding="utf-8")
    admin = (ROOT / "admin" / "index.html").read_text(encoding="utf-8")

    for marker in [
        'href="/#recomendar-clinica"',
        'id="recomendar-clinica"',
        "Recomendar Clínica",
        'id="recommendToggle"',
        'id="recommendClinicForm"',
        'id="recommendClinicName"',
        'id="recommendClinicWebsite"',
        'id="recommendClinicRequest"',
        'id="recommendStatus"',
        "Nada se publica automáticamente.",
        "window.VITALARGA_PUBLIC_CONFIG",
        "supabasePublishableKey",
        "/rest/v1/rpc/public_recommend_clinic",
        "p_clinic_name:name",
        "p_website:website",
        "p_requested_info:requested",
        "p_honeypot:trap",
        "Recibido. Queda como trabajo pendiente para revisión interna.",
        ".recommend{max-width:1180px",
        ".recommend-form{display:grid",
        ".recommend-status.error",
    ]:
        check(marker in source, f"missing public recommendation marker: {marker}")

    for marker in [
        "create or replace function public.public_recommend_clinic",
        "security definer",
        "insert into public.agent_jobs",
        "'DISCOVER_CLINIC'",
        "'queued'",
        "'source', 'public_site_recommend_clinic'",
        "'allowed_output', 'review_queue_proposal_only'",
        "'public_clinic_recommendation_received'",
        "grant usage on schema public to anon, authenticated",
        "grant execute on function public.public_recommend_clinic(text, text, text, text, text, text, text) to anon, authenticated",
    ]:
        check(marker in sql, f"missing public recommendation SQL marker: {marker}")

    check("grant insert on public.agent_jobs to anon" not in sql.lower(), "migration must not grant direct anon insert to agent_jobs")
    check("insert into public.clinics" not in sql.lower(), "public recommendation must not create clinics directly")
    check("insert into public.review_queue" not in sql.lower(), "public recommendation should create jobs, not review cards directly")

    check(
        "public_site_recommend_clinic" in admin
        and "Recomendación pública · " in admin
        and "Recomendar clínica: " in admin,
        "admin jobs table should make public recommendations visible",
    )

    print("OK public recommendations: public form creates safe internal jobs")


if __name__ == "__main__":
    main()
