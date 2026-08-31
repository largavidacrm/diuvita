#!/usr/bin/env python3
"""Checks the clinic portal activation readiness report."""

from check_clinic_portal_activation import build_checks, format_report, readiness, report_payload


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    pending_checks = build_checks()
    pending_payload = report_payload(pending_checks)
    pending_output = format_report(pending_payload)

    check(readiness(pending_checks) == "listo técnicamente; pendiente de decisión/manual", "default readiness should wait for Daniel")
    check(pending_payload["counts"]["blocked"] == 0, "local portal wiring should not be technically blocked")
    check(pending_payload["counts"]["manual"] == 5, "manual activation checkpoints should be explicit")
    check("Resultado: listo técnicamente; pendiente de decisión/manual" in pending_output, "readiness headline missing")
    check("Revisión legal y privacidad" in pending_output, "legal/privacy checkpoint missing")
    check("Migración Supabase" in pending_output, "Supabase migration checkpoint missing")
    check("Supabase Auth" in pending_output, "Supabase Auth checkpoint missing")
    check("Prueba real controlada" in pending_output, "manual test checkpoint missing")
    check("Aprobación de publicación" in pending_output, "production approval checkpoint missing")
    check("no activa Supabase, Netlify ni producción" in pending_output, "safety note missing")

    approved_checks = build_checks(
        {
            "legal_privacy_review": True,
            "supabase_migration": True,
            "supabase_auth": True,
            "manual_flow_test": True,
            "production_approval": True,
        }
    )
    approved_payload = report_payload(approved_checks)
    approved_output = format_report(approved_payload)
    check(readiness(approved_checks) == "listo para activar cuando Daniel lo ordene", "approved readiness missing")
    check(approved_payload["counts"]["manual"] == 0, "approved report should have no manual checkpoints")
    check("## Bloqueos técnicos" not in approved_output, "approved report should not show technical blockers")
    check("Ruta pública del portal" in approved_output, "ready checks should still be shown")
    print("OK clinic portal activation: readiness report is safe and readable")


if __name__ == "__main__":
    main()
