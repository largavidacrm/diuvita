#!/usr/bin/env python3
"""Checks for Daniel's plain-Spanish review brief."""

from daniel_review_brief import format_brief, first_step, review_counts


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def sample_digest():
    return {
        "generated_at": "2026-08-30T15:10:00+00:00",
        "summary": {
            "clinics": {"published": 11, "preliminary": 8},
            "reviews": {"open": 41},
            "jobs": {"failed": 0, "dead_letter": 0},
            "automation": {
                "auto_publish_enabled": False,
                "shadow_mode_active": True,
                "candidate_reviews_completed": 2,
                "shadow_review_target": 200,
            },
        },
        "reviews_by_type": [
            {"review_type": "clinic_profile_enrichment", "open_count": 12},
            {"review_type": "candidate_clinic", "open_count": 8},
            {"review_type": "blocking_claim_review", "open_count": 1},
        ],
        "open_reviews": [
            {
                "review_type": "blocking_claim_review",
                "priority": 85,
                "clinic_name": "Sensabell",
                "title": "Revisar claims bloqueantes: Sensabell",
            }
        ],
        "recent_failed_jobs": [],
        "source_monitoring": {
            "due_sources": 0,
            "next_due_at": "2026-09-29T09:58:00+00:00",
        },
    }


def main():
    digest = sample_digest()
    output = format_brief(digest)
    counts = review_counts(digest)

    check(counts["blocking_claim_review"] == 1, "blocking-claim count missing")
    check(first_step(digest)[0] == "Primero revisa claims bloqueantes.", "blocking claims should be first")
    check("# Diuvita: brief de revisión" in output, "title missing")
    check("Qué mirar primero" in output, "first action section missing")
    check("Caso visible: Revisar claims bloqueantes: Sensabell." in output, "visible case missing")
    check("Acción sugerida por el sistema: Revisar claim bloqueante." in output, "next action missing")
    check("41 revisiones abiertas" in output, "open review count missing")
    check("1 claims bloqueantes pendiente" in output, "blocking count missing")
    check("8 clínicas nuevas pendientes" in output, "candidate count missing")
    check("Auto-publicación: apagada" in output, "auto-publish state missing")
    check("Modo sombra: activo" in output, "shadow mode state missing")
    check("Crear borrador no publica" in output, "draft safety reminder missing")
    check("Fuentes: todo reciente; próxima revisión 2026-09-29 09:58" in output, "source status missing")

    failed_digest = sample_digest()
    failed_digest["recent_failed_jobs"] = [{"job_type": "QUALITY_AUDIT"}]
    failed_digest["summary"]["jobs"] = {"failed": 1, "dead_letter": 0}
    check(first_step(failed_digest)[0] == "Primero revisa fallos técnicos.", "failed jobs should be first")

    hidden_sample_digest = sample_digest()
    hidden_sample_digest["open_reviews"] = []
    check(
        first_step(hidden_sample_digest)[1] == "Caso visible: abre el filtro Claims bloqueantes en el panel.",
        "missing visible sample should route Daniel to the right filter",
    )
    print("OK Daniel brief: review guidance is readable")


if __name__ == "__main__":
    main()
