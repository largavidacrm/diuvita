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
            }
        ],
        "open_reviews": [
            {
                "review_type": "clinic_profile_enrichment",
                "priority": 60,
                "clinic_name": "Monarka Clinic",
                "title": "Revisar extraccion shadow: Monarka Clinic",
            }
        ],
        "recent_failed_jobs": [],
        "costs": {
            "last_24h_cents": 125,
            "last_7d_cents": 456,
        },
    }
    output = format_digest(digest)
    check("# Diuvita CTO digest" in output, "title missing")
    check("Clinicas totales: 19" in output, "clinic count missing")
    check("Capturas guardadas: 3" in output, "snapshot count missing")
    check("Auto-publicacion: desactivada" in output, "auto-publish safety missing")
    check("mejoras de ficha: 11 abiertas" in output, "review type summary missing")
    check("cambios de fuente: 1 abierta" in output, "source change label missing")
    check("Monarka Clinic" in output, "priority item missing")
    check("Coste registrado 24h: 1.25" in output, "cost formatting missing")
    print("OK digest: internal CTO summary")


if __name__ == "__main__":
    main()
