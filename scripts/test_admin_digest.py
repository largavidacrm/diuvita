#!/usr/bin/env python3
"""Checks for the internal CTO digest formatter."""

from admin_digest import (
    format_digest,
    next_action_label,
    next_specialist_action,
    review_backlog_guard_status,
    top_pending_profile_field,
)


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    digest = {
        "generated_at": "2026-08-30T10:20:00+00:00",
        "summary": {
            "clinics": {"total": 19, "published": 11, "preliminary": 8},
            "reviews": {"open": 48},
            "jobs": {"queued": 2, "running": 1, "failed": 0, "dead_letter": 0},
            "evidence": {"sources": 7, "snapshots": 3, "claims": 31},
            "automation": {
                "agents_enabled": True,
                "auto_publish_enabled": False,
                "shadow_mode_active": True,
                "shadow_review_target": 200,
                "candidate_reviews_completed": 13,
            },
        },
        "reviews_by_type": [
            {
                "review_type": "clinic_profile_enrichment",
                "open_count": 11,
                "oldest_created_at": "2026-08-29T22:00:00+00:00",
            },
            {
                "review_type": "source_change_detected",
                "open_count": 1,
                "oldest_created_at": "2026-08-30T10:00:00+00:00",
            },
            {
                "review_type": "blocking_claim_review",
                "open_count": 1,
                "oldest_created_at": "2026-08-30T11:00:00+00:00",
            }
        ],
        "open_reviews": [
            {
                "review_type": "blocking_claim_review",
                "raw_review_type": "clinic_quality_audit",
                "priority": 85,
                "clinic_name": "Sensabell",
                "title": "Revisar claims bloqueantes: Sensabell",
            }
        ],
        "review_examples_by_type": [
            {
                "review_type": "blocking_claim_review",
                "raw_review_type": "clinic_quality_audit",
                "priority": 85,
                "clinic_name": "Sensabell",
                "title": "Revisar claims bloqueantes: Sensabell",
            },
            {
                "review_type": "candidate_clinic",
                "priority": 90,
                "clinic_name": "",
                "title": "Candidata visible",
            },
        ],
        "review_backlog_quality": {
            "duplicate_enrichment_clinics": 1,
            "duplicate_enrichment_reviews": 2,
        },
        "recent_failed_jobs": [],
        "claim_quality": {
            "conflict": 0,
            "rejected": 0,
            "without_source": 0,
        },
        "costs": {
            "last_24h_cents": 125,
            "last_7d_cents": 456,
        },
        "source_monitoring": {
            "candidate_sources": 39,
            "due_sources": 0,
            "never_checked_sources": 0,
            "weekly_sources": 4,
            "standard_sources": 32,
            "slow_sources": 3,
            "custom_sources": 0,
            "oldest_last_checked_at": "2026-08-29T10:00:00+00:00",
            "oldest_due_at": None,
            "next_due_at": "2026-09-05T10:00:00+00:00",
        },
        "specialist_coverage": {
            "visible_clinics": 19,
            "with_specialists": 2,
            "without_specialists": 17,
            "total_specialist_entries": 3,
            "clinics_with_specialist_claims": 11,
            "clinics_with_open_specialist_reviews": 18,
        },
        "specialist_next_target": {
            "slug": "age-reversal",
            "clinic_name": "Age Reversal",
            "city": "Barcelona",
            "status": "published",
            "specialist_claims": 1,
            "open_review_count": 2,
        },
        "profile_completeness": {
            "visible_clinics": 19,
            "without_pending_fields": 1,
            "with_pending_fields": 18,
            "pending_summary": 0,
            "pending_website": 0,
            "pending_address": 0,
            "pending_contact": 6,
            "pending_services": 0,
            "pending_specialties": 0,
            "pending_units": 14,
            "pending_specialists": 17,
            "pending_technology": 5,
        },
    }
    output = format_digest(digest)
    check(next_action_label(digest) == "Revisar claim bloqueante", "next action should prefer blocking claims")
    check(next_specialist_action(digest) == "Revisar Age Reversal: ya tiene 2 revisiones abiertas", "next specialist action missing")
    check(review_backlog_guard_status(digest) == "cerca del freno: 48/50 abiertas", "review backlog guard missing")
    check(top_pending_profile_field(digest) == "Especialistas · 17 fichas", "top pending profile field missing")
    limited_digest = dict(digest)
    limited_digest["open_reviews"] = [
        {
            "review_type": "candidate_clinic",
            "priority": 90,
            "clinic_name": "",
            "title": "Candidata visible",
        }
    ]
    check(
        next_action_label(limited_digest) == "Revisar claim bloqueante",
        "next action should use full review-type summary, not only visible cards",
    )
    check("# Diuvita CTO digest" in output, "title missing")
    check("Clinicas totales: 19" in output, "clinic count missing")
    check("Capturas guardadas: 3" in output, "snapshot count missing")
    check("Fichas con especialistas: 2/19" in output, "specialist coverage missing")
    check("Siguiente especialistas: Revisar Age Reversal: ya tiene 2 revisiones abiertas" in output, "next specialist line missing")
    check("Fichas sin campos pendientes medidos: 1/19" in output, "profile completeness missing")
    check("Campo mas pendiente: Especialistas · 17 fichas" in output, "top pending profile field line missing")
    check("Auto-publicacion: desactivada" in output, "auto-publish safety missing")
    check("Bajo riesgo: no lista" in output, "maturity signal missing")
    check("muestra humana insuficiente: 13/200 candidatas" in output, "maturity blocker missing")
    check("mejoras de ficha: 11 abiertas" in output, "review type summary missing")
    check("cambios de fuente: 1 abierta" in output, "source change label missing")
    check("claims bloqueantes: 1 abierta" in output, "blocking claim label missing")
    check("Sensabell" in output, "priority item missing")
    check("review_examples_by_type" not in output, "raw example key should not appear in formatted digest")
    check("Coste registrado 24h: 1.25" in output, "cost formatting missing")
    check("Siguiente accion: Revisar claim bloqueante" in output, "next action missing")
    check("Freno bandeja: cerca del freno: 48/50 abiertas" in output, "backlog guard line missing")
    check("Duplicados mejoras: 1 clinicas / 2 tarjetas" in output, "duplicate enrichment signal missing")
    check("## Vigilancia de fuentes" in output, "source monitoring section missing")
    check("Fuentes vigilables: 39" in output, "monitorable source count missing")
    check("Fuentes vencidas ahora: todo reciente" in output, "fresh source status missing")
    check("Proxima revision prevista: 2026-09-05 10:00" in output, "next due date missing")
    check("Cadencia: 4 semanal / 32 estandar / 3 lenta" in output, "cadence mix missing")
    print("OK digest: internal CTO summary")


if __name__ == "__main__":
    main()
