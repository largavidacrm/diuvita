#!/usr/bin/env python3
"""Checks for Daniel's plain-Spanish review brief."""

from daniel_review_brief import (
    action_review_sort_key,
    format_brief,
    first_step,
    next_clicks,
    production_health_status,
    review_counts,
    safe_json_digest,
)


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
        "publication_control": {
            "rebuild_hook_configured": True,
            "rebuild_batch_minutes": 30,
            "last_public_site_rebuild_requested_at": "2026-08-31T06:24:00+00:00",
            "last_public_site_change_at": "2026-08-31T06:47:00+00:00",
            "pending_public_site_rebuild": True,
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
        "google_link_reviews": {
            "open_count": 4,
            "first_review": {
                "review_type": "clinic_profile_enrichment",
                "priority": 60,
                "clinic_name": "Sensabell",
                "title": "Completar enlaces Google: Sensabell",
            },
        },
        "specialist_reviews": {
            "open_count": 2,
            "professionals_count": 17,
            "first_review": {
                "review_type": "candidate_clinic",
                "priority": 90,
                "clinic_name": "",
                "title": "Regenera Clinic Medicina de la Longevidad",
                "professionals_count": 11,
            },
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
        "publication_readiness": {
            "clinics_measured": 24,
            "visible_clinics": 20,
            "ready_clinics": 3,
            "clinics_with_missing_fields": 21,
            "clinics_with_blocking_reviews": 1,
            "top_missing_fields": [
                {"field": "Google Maps de clínica", "count": 20},
            ],
        },
        "publication_next_target": {
            "slug": "longevity-marbella",
            "clinic_name": "Longevity Marbella",
            "city": "Marbella",
            "status": "draft",
            "missing_fields": ["Google Maps de clínica", "Dirección o sede"],
            "missing_count": 2,
            "next_missing_field": "Google Maps de clínica",
            "open_reviews": 1,
            "open_blocking_reviews": 0,
        },
    }


def main():
    tied_reviews = [
        {"id": "b", "review_type": "clinic_quality_audit", "priority": 85, "title": "Revisión manual: MB Wellness Clinic"},
        {"id": "a", "review_type": "clinic_quality_audit", "priority": 85, "title": "Revisión manual: Clínica Benzaquén"},
    ]
    check(
        sorted(tied_reviews, key=action_review_sort_key)[0]["id"] == "a",
        "Daniel brief sort should have a stable title/id tie-break",
    )

    digest = sample_digest()
    output = format_brief(digest)
    counts = review_counts(digest)
    account_digest = dict(digest, admin_email="daniel@example.com")
    safe_digest = safe_json_digest(account_digest)
    raw_digest = safe_json_digest(account_digest, include_account_fields=True)
    check("admin_email" not in safe_digest, "safe JSON should omit admin email by default")
    check(raw_digest["admin_email"] == "daniel@example.com", "debug JSON should keep admin email explicitly")
    check(account_digest["admin_email"] == "daniel@example.com", "safe JSON should not mutate the original digest")

    check(counts["blocking_claim_review"] == 1, "blocking-claim count missing")
    claim_digest = sample_digest()
    claim_digest["summary"]["reviews"]["open"] = 3
    claim_digest["reviews_by_type"] = [
        {"review_type": "clinic_claim_request", "open_count": 1}
    ]
    claim_digest["open_reviews"] = [
        {
            "review_type": "clinic_claim_request",
            "priority": 96,
            "clinic_name": "Monarka Clinic",
            "title": "Reclamar ficha: Monarka Clinic",
        }
    ]
    claim_digest["review_examples_by_type"] = list(claim_digest["open_reviews"])
    claim_digest["review_first_clinic_workgroup"] = {}
    claim_output = format_brief(claim_digest)
    check(first_step(claim_digest)[0] == "Primero revisa reclamaciones de ficha.", "claim-request first step missing")
    check("1 reclamación de ficha pendiente" in claim_output, "claim-request count missing")
    check(
        "No confirma identidad, no da acceso y no cambia datos por sí sola." in claim_output,
        "claim-request safety wording missing",
    )
    check(
        "Atascos de mejoras: 1 clínica con mejoras repetidas; se ordenan después de la prioridad actual" in claim_output,
        "claim-request brief should keep duplicate backlog secondary",
    )
    check("Primer atasco:" not in claim_output, "claim-request brief should avoid old bottleneck wording")
    check(first_step(digest)[0] == "Primero revisa claims bloqueantes.", "priority review should beat clinic groups")
    check("# Vitalarga: brief de revisión" in output, "title missing")
    check("Qué mirar primero" in output, "first action section missing")
    check("Próximos clics" in output, "next-clicks section missing")
    check("No crees trabajos nuevos hasta bajar la bandeja; ahora está pausa preventiva: 48/50 abiertas; baja de 45." in output, "near-limit click guard missing")
    check("Pulsa Abrir prioridad: Revisar claims bloqueantes: Sensabell." in output, "priority review click missing")
    check("Pulsa Especialistas y abre primero la tarjeta con más nombres: Regenera Clinic Medicina de la Longevidad. En total hay 17 especialistas propuestos en la bandeja." in output, "specialist click missing")
    check("Pulsa Google Maps y valida que el enlace abre el perfil real de la clínica: Completar enlaces Google: Sensabell." in output, "Google Maps click missing")
    check("Caso visible: Revisar claims bloqueantes: Sensabell." in output, "visible priority case missing")
    check("Señal automática base: Revisar claim bloqueante." in output, "base next action missing")
    check("48 revisiones abiertas" in output, "open review count missing")
    check("1 claim bloqueante pendiente" in output, "blocking count missing")
    check("8 clínicas nuevas pendientes" in output, "candidate count missing")
    check("1 cambio de fuente pendiente" in output, "source-change singular missing")
    check("Auto-publicación: apagada" in output, "auto-publish state missing")
    check("Modo sombra: activo" in output, "shadow mode state missing")
    check("Publicación web: con cambios pendientes de verse online" in output, "publication control state missing")
    check("Preparación para publicación: 3/24 fichas sin faltantes obligatorios; 21 con faltantes; 1 con claims bloqueantes" in output, "publication readiness state missing")
    check("Principal faltante para publicar: Google Maps de clínica · 20 fichas" in output, "publication top blocker missing")
    check("Siguiente publicación: Revisar Longevity Marbella: primer faltante obligatorio: Google Maps de clínica; 2 faltantes en total" in output, "publication next action missing")
    check("Crear borrador no publica" in output, "draft safety reminder missing")
    check("Completitud de fichas: 0/19 fichas sin campos pendientes medidos; 19 con pendientes" in output, "profile completeness missing")
    check("Campo más pendiente: Google Maps · 19 fichas" in output, "top pending profile field missing")
    check("Google Maps pendientes: 4 tarjetas; primera: Completar enlaces Google: Sensabell" in output, "Google Maps review target missing")
    check(
        "Fichas pendientes: 19/19 fichas con campos pendientes; se revisan después de la prioridad actual" in output,
        "secondary profile queue should not name a non-primary clinic",
    )
    check("Especialistas publicados: 2/19 fichas con especialistas; 17 pendientes" in output, "specialist coverage missing")
    check("Tarjetas con especialistas: 2 tarjetas; 17 especialistas propuestos" in output, "specialist review status missing")
    check("Siguiente especialistas: Revisar Age Reversal: ya tiene 2 revisiones abiertas" in output, "next specialist action missing")
    check("Fuentes: todo reciente; próxima revisión 2026-09-29 09:58" in output, "source status missing")
    check("Cobertura fuentes: 11/19 fichas con fuente; 10/19 hidratadas; 8 sin fuente; 11 con trabajo pendiente" in output, "source coverage missing")
    check("Siguiente fuente: Revisar 2 claims bloqueantes de Kairos Longevity Clinic" in output, "next source missing")
    check("Bandeja: 1 clínica con varias mejoras abiertas; 2 tarjetas" in output, "review backlog quality missing")
    check("Contexto de grupo: Abrir Sensabell: 5 tarjetas" in output, "clinic workgroup missing")
    check("Atascos de mejoras: Ordenar Sensabell: 2 mejoras abiertas" in output, "first backlog bottleneck missing")
    check("Freno de bandeja: pausa preventiva: 48/50 abiertas; baja de 45" in output, "backlog guard status missing")
    check(len(next_clicks(digest)) == 4, "next clicks should stay short")

    audit_priority_digest = sample_digest()
    audit_priority_digest["summary"]["reviews"]["open"] = 22
    audit_priority_digest["reviews_by_type"] = [
        {"review_type": "clinic_profile_enrichment", "open_count": 20},
        {"review_type": "clinic_quality_audit", "open_count": 2},
    ]
    audit_priority_digest["open_reviews"] = [
        {
            "review_type": "clinic_quality_audit",
            "priority": 85,
            "clinic_name": "Clínica Benzaquén",
            "title": "Completar ficha: Clínica Benzaquén",
        },
        {
            "review_type": "clinic_profile_enrichment",
            "priority": 65,
            "clinic_name": "Sensabell",
            "title": "Ampliar ficha: Sensabell",
        },
    ]
    audit_priority_digest["review_examples_by_type"] = list(audit_priority_digest["open_reviews"])
    audit_priority_digest["review_first_clinic_workgroup"] = {
        "clinic_slug": "sensabell",
        "clinic_name": "Sensabell",
        "city": "Valencia",
        "clinic_status": "published",
        "open_count": 4,
        "blocking_claim_reviews": 0,
        "quality_reviews": 1,
        "enrichment_reviews": 3,
        "source_change_reviews": 0,
        "candidate_reviews": 0,
        "max_priority": 65,
        "oldest_created_at": "2026-08-30T08:30:00+00:00",
    }
    audit_priority_output = format_brief(audit_priority_digest)
    check(
        first_step(audit_priority_digest)[1] == "Caso visible: Revisión manual: Clínica Benzaquén.",
        "quality audit should open the concrete higher-priority ficha",
    )
    check(
        "Pulsa Abrir prioridad: Revisión manual: Clínica Benzaquén; veras la ficha y la revision en columnas"
        in audit_priority_output,
        "quality audit next click should point to manual review",
    )
    check(
        "se abrirá directamente el campo pendiente en la ficha" not in audit_priority_output,
        "quality audit next click should not bypass the proposal columns",
    )
    check(
        "Contexto de grupo: Abrir Sensabell: 4 tarjetas" in audit_priority_output,
        "clinic workgroup should remain as secondary context",
    )

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
    hidden_sample_digest["review_first_clinic_workgroup"] = {}
    hidden_sample_digest["summary"]["reviews"] = {"open": 12}
    check(
        first_step(hidden_sample_digest)[1] == "Caso visible: abre el filtro Claims bloqueantes en el panel.",
        "missing visible sample should route Daniel to the right filter",
    )
    example_digest = sample_digest()
    example_digest["open_reviews"] = []
    example_digest["review_first_clinic_workgroup"] = {}
    example_digest["summary"]["reviews"] = {"open": 12}
    check(
        first_step(example_digest)[1] == "Caso visible: Revisar claims bloqueantes: Sensabell.",
        "type-level review example should guide Daniel when priority list is limited",
    )
    candidate_digest = sample_digest()
    candidate_digest["summary"]["reviews"] = {"open": 1}
    candidate_digest["reviews_by_type"] = [{"review_type": "candidate_clinic", "open_count": 1}]
    candidate_digest["review_first_clinic_workgroup"] = {}
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
