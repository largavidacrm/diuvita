#!/usr/bin/env python3
"""Checks for the internal CTO digest formatter."""

from admin_digest import format_digest


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    digest = {
        "generated_at": "2026-08-30T10:20:00+00:00",
        "summary": {
            "clinics": {"total": 19, "published": 11, "preliminary": 8},
            "reviews": {"open": 12},
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
    }
    output = format_digest(digest)
    check("# Diuvita CTO digest" in output, "title missing")
    check("Clinicas totales: 19" in output, "clinic count missing")
    check("Capturas guardadas: 3" in output, "snapshot count missing")
    check("Auto-publicacion: desactivada" in output, "auto-publish safety missing")
    check("Bajo riesgo: no lista" in output, "maturity signal missing")
    check("muestra humana insuficiente: 13/200 candidatas" in output, "maturity blocker missing")
    check("mejoras de ficha: 11 abiertas" in output, "review type summary missing")
    check("cambios de fuente: 1 abierta" in output, "source change label missing")
    check("claims bloqueantes: 1 abierta" in output, "blocking claim label missing")
    check("Sensabell" in output, "priority item missing")
    check("Coste registrado 24h: 1.25" in output, "cost formatting missing")
    check("## Vigilancia de fuentes" in output, "source monitoring section missing")
    check("Fuentes vigilables: 39" in output, "monitorable source count missing")
    check("Fuentes vencidas ahora: todo reciente" in output, "fresh source status missing")
    check("Proxima revision prevista: 2026-09-05 10:00" in output, "next due date missing")
    check("Cadencia: 4 semanal / 32 estandar / 3 lenta" in output, "cadence mix missing")
    print("OK digest: internal CTO summary")


if __name__ == "__main__":
    main()
