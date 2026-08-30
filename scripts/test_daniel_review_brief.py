#!/usr/bin/env python3
"""Checks for Daniel's plain-Spanish review brief."""

from daniel_review_brief import format_brief, first_step, production_health_status, review_counts


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def sample_digest():
    return {
        "generated_at": "2026-08-30T15:10:00+00:00",
        "summary": {
            "clinics": {"published": 11, "preliminary": 8},
            "reviews": {"open": 48},
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
            {"review_type": "source_change_detected", "open_count": 1},
        ],
        "open_reviews": [
            {
                "review_type": "blocking_claim_review",
                "priority": 85,
                "clinic_name": "Sensabell",
                "title": "Revisar claims bloqueantes: Sensabell",
            }
        ],
        "review_examples_by_type": [
            {
                "review_type": "blocking_claim_review",
                "priority": 85,
                "clinic_name": "Sensabell",
                "title": "Revisar claims bloqueantes: Sensabell",
            }
        ],
        "review_backlog_quality": {
            "duplicate_enrichment_clinics": 1,
            "duplicate_enrichment_reviews": 2,
        },
        "review_backlog_first_duplicate_target": {
            "clinic_slug": "sensabell",
            "clinic_name": "Sensabell",
            "city": "Valencia",
            "clinic_status": "published",
            "open_count": 2,
            "max_priority": 60,
            "oldest_created_at": "2026-08-30T09:00:00+00:00",
        },
        "review_first_clinic_workgroup": {
            "clinic_slug": "sensabell",
            "clinic_name": "Sensabell",
            "city": "Valencia",
            "clinic_status": "published",
            "open_count": 5,
            "blocking_claim_reviews": 1,
            "quality_reviews": 1,
            "enrichment_reviews": 3,
            "source_change_reviews": 0,
            "candidate_reviews": 0,
            "max_priority": 85,
            "oldest_created_at": "2026-08-30T08:30:00+00:00",
        },
        "recent_failed_jobs": [],
        "source_monitoring": {
            "due_sources": 0,
            "next_due_at": "2026-09-29T09:58:00+00:00",
        },
        "source_coverage": {
            "visible_clinics": 19,
            "clinics_with_sources": 11,
            "clinics_without_sources": 8,
            "clinics_with_hydrated_sources": 10,
            "clinics_without_hydrated_sources": 9,
            "clinics_with_claims": 11,
            "clinics_without_claims": 8,
            "clinics_needing_source_work": 11,
            "claims_with_source": 109,
            "claims_without_source": 0,
            "blocking_claims": 5,
        },
        "source_next_target": {
            "slug": "kairos-longevity-clinic",
            "clinic_name": "Kairos Longevity Clinic",
            "city": "Madrid",
            "status": "published",
            "source_records": 2,
            "hydrated_source_records": 2,
            "source_snapshots": 2,
            "total_claims": 8,
            "claims_with_source": 8,
            "claims_without_source": 0,
            "blocking_claims": 2,
        },
        "specialist_coverage": {
            "visible_clinics": 19,
            "with_specialists": 2,
            "without_specialists": 17,
            "total_specialist_entries": 3,
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
            "without_pending_fields": 0,
            "with_pending_fields": 19,
            "pending_summary": 0,
            "pending_website": 0,
            "pending_address": 0,
            "pending_google_maps": 19,
            "pending_google_reviews": 18,
            "pending_contact": 6,
            "pending_services": 0,
            "pending_specialties": 0,
            "pending_units": 14,
            "pending_specialists": 17,
            "pending_technology": 5,
        },
        "profile_next_target": {
            "slug": "kairos-longevity-clinic",
            "clinic_name": "Kairos Longevity Clinic",
            "city": "Madrid",
            "status": "published",
            "pending_fields": ["Google Maps de clínica", "Especialistas publicados", "Tecnología destacada"],
            "pending_count": 3,
            "next_pending_field": "Google Maps de clínica",
            "open_quality_reviews": 1,
            "open_profile_reviews": 2,
            "open_source_change_reviews": 1,
            "open_relevant_reviews": 4,
        },
    }


def main():
    digest = sample_digest()
    output = format_brief(digest)
    counts = review_counts(digest)

    check(counts["blocking_claim_review"] == 1, "blocking-claim count missing")
    check(first_step(digest)[0] == "Primero revisa claims bloqueantes.", "blocking claims should be first")
    check("# Vitalarga: brief de revisión" in output, "title missing")
    check("Qué mirar primero" in output, "first action section missing")
    check("Caso visible: Revisar claims bloqueantes: Sensabell." in output, "visible case missing")
    check("Acción sugerida por el sistema: Revisar claim bloqueante." in output, "next action missing")
    check("48 revisiones abiertas" in output, "open review count missing")
    check("1 claim bloqueante pendiente" in output, "blocking count missing")
    check("8 clínicas nuevas pendientes" in output, "candidate count missing")
    check("1 cambio de fuente pendiente" in output, "source-change singular missing")
    check("Auto-publicación: apagada" in output, "auto-publish state missing")
    check("Modo sombra: activo" in output, "shadow mode state missing")
    check("Crear borrador no publica" in output, "draft safety reminder missing")
    check("Completitud de fichas: 0/19 fichas sin campos pendientes medidos; 19 con pendientes" in output, "profile completeness missing")
    check("Campo más pendiente: Google Maps · 19 fichas" in output, "top pending profile field missing")
    check("Siguiente ficha: Revisar Kairos Longevity Clinic" in output, "next profile action missing")
    check("Especialistas publicados: 2/19 fichas con especialistas; 17 pendientes" in output, "specialist coverage missing")
    check("Siguiente especialistas: Revisar Age Reversal: ya tiene 2 revisiones abiertas" in output, "next specialist action missing")
    check("Fuentes: todo reciente; próxima revisión 2026-09-29 09:58" in output, "source status missing")
    check("Cobertura fuentes: 11/19 fichas con fuente; 10/19 hidratadas; 8 sin fuente; 11 con trabajo pendiente" in output, "source coverage missing")
    check("Siguiente fuente: Revisar 2 claims bloqueantes de Kairos Longevity Clinic" in output, "next source missing")
    check("Bandeja: 1 clínica con varias mejoras abiertas; 2 tarjetas" in output, "review backlog quality missing")
    check("Grupo por clínica: Trabajar Sensabell: 5 tarjetas" in output, "clinic workgroup missing")
    check("Primer atasco: Ordenar Sensabell: 2 mejoras abiertas" in output, "first backlog bottleneck missing")
    check("Freno de bandeja: cerca del freno: 48/50 abiertas" in output, "backlog guard status missing")

    production_report = {
        "ok": True,
        "checks": [{"name": "home", "ok": True}, {"name": "admin_shell", "ok": True}],
    }
    output_with_health = format_brief(digest, production_report)
    check("Web pública: OK en 2 comprobaciones públicas" in output_with_health, "production health line missing")
    attention_report = {
        "ok": False,
        "checks": [{"name": "home", "ok": True}, {"name": "sitemap", "ok": False}],
    }
    check(
        production_health_status(attention_report) == "atención en 1 comprobación: sitemap",
        "production health attention summary missing",
    )

    failed_digest = sample_digest()
    failed_digest["recent_failed_jobs"] = [{"job_type": "QUALITY_AUDIT"}]
    failed_digest["summary"]["jobs"] = {"failed": 1, "dead_letter": 0}
    check(first_step(failed_digest)[0] == "Primero revisa fallos técnicos.", "failed jobs should be first")

    hidden_sample_digest = sample_digest()
    hidden_sample_digest["open_reviews"] = []
    hidden_sample_digest["review_examples_by_type"] = []
    check(
        first_step(hidden_sample_digest)[1] == "Caso visible: abre el filtro Claims bloqueantes en el panel.",
        "missing visible sample should route Daniel to the right filter",
    )
    example_digest = sample_digest()
    example_digest["open_reviews"] = []
    check(
        first_step(example_digest)[1] == "Caso visible: Revisar claims bloqueantes: Sensabell.",
        "type-level review example should guide Daniel when priority list is limited",
    )
    candidate_digest = sample_digest()
    candidate_digest["reviews_by_type"] = [{"review_type": "candidate_clinic", "open_count": 1}]
    candidate_digest["open_reviews"] = [
        {
            "review_type": "candidate_clinic",
            "priority": 90,
            "clinic_name": "",
            "title": "Regenera Clinic Medicina de la Longevidad",
            "professionals_count": 11,
        }
    ]
    candidate_digest["review_examples_by_type"] = []
    check(
        first_step(candidate_digest)[1]
        == "Caso visible: Regenera Clinic Medicina de la Longevidad. Trae 11 especialistas recogidos.",
        "candidate reviews should show collected professionals",
    )
    print("OK Daniel brief: review guidance is readable")


if __name__ == "__main__":
    main()
