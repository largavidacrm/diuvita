#!/usr/bin/env python3
"""Checks for the internal CTO digest formatter."""
from pathlib import Path

from admin_digest import (
    action_review_sort_key,
    display_review_title,
    first_clinic_workgroup,
    first_backlog_bottleneck,
    format_digest,
    format_review_type,
    google_link_review_status,
    location_coverage_status,
    next_action_label,
    next_publication_action,
    next_profile_action,
    next_portal_action,
    next_source_action,
    next_specialist_action,
    publication_control_status,
    publication_readiness_status,
    portal_status,
    review_backlog_guard_status,
    source_origin_audit_status,
    source_coverage_status,
    specialist_review_status,
    top_publication_missing_field,
    top_pending_profile_field,
)


ROOT = Path(__file__).resolve().parents[1]


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    tied_reviews = [
        {"id": "b", "review_type": "clinic_quality_audit", "priority": 85, "title": "Revisión manual: MB Wellness Clinic"},
        {"id": "a", "review_type": "clinic_quality_audit", "priority": 85, "title": "Revisión manual: Clínica Benzaquén"},
    ]
    check(
        sorted(tied_reviews, key=action_review_sort_key)[0]["id"] == "a",
        "action review sort should have a stable title/id tie-break",
    )

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
        "publication_control": {
            "rebuild_hook_configured": True,
            "rebuild_batch_minutes": 30,
            "last_public_site_rebuild_requested_at": "2026-08-30T10:35:11+00:00",
            "last_public_site_change_at": "2026-08-30T10:35:11+00:00",
            "pending_public_site_rebuild": False,
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
            },
            {
                "review_type": "candidate_clinic",
                "priority": 90,
                "clinic_name": "",
                "title": "Regenera Clinic Medicina de la Longevidad",
                "professionals_count": 11,
            },
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
                "professionals_count": 11,
            },
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
            "direct_maps_count": 2,
            "weak_maps_count": 1,
            "reviews_without_maps_count": 0,
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
        "review_source_origin_audit": {
            "cards": 22,
            "context_ready": 4,
            "recoverable_from_job": 3,
            "source_without_context": 15,
            "no_source_context": 0,
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
            "without_pending_fields": 0,
            "with_pending_fields": 19,
            "pending_summary": 0,
            "pending_website": 0,
            "pending_address": 0,
            "pending_google_maps": 19,
            "pending_contact": 6,
            "pending_services": 0,
            "pending_specialties": 0,
            "pending_units": 14,
            "pending_specialists": 17,
            "pending_technology": 5,
            "pending_years_in_practice": 19,
            "pending_specialists_count": 19,
            "pending_team_credentialing_visible": 19,
            "pending_public_pricing": 19,
        },
        "location_coverage": {
            "clinics_with_locations": 2,
            "multi_location_clinics": 1,
            "total_locations": 3,
            "locations_missing_address": 0,
            "locations_missing_google_maps_profile": 2,
            "clinics_with_location_proposals": 1,
            "proposed_location_rows": 2,
            "clinics_with_location_claims": 2,
            "internal_location_rows": 3,
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
                {"field": "Dirección o sede", "count": 3},
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
    output = format_digest(digest)
    check(next_action_label(digest) == "Revisar claim bloqueante", "next action should prefer blocking claims")
    claim_request_digest = dict(digest)
    claim_request_digest["reviews_by_type"] = [
        {"review_type": "clinic_claim_request", "open_count": 1}
    ]
    claim_request_digest["open_reviews"] = [
        {
            "review_type": "clinic_claim_request",
            "priority": 96,
            "clinic_name": "Monarka Clinic",
            "title": "Reclamar ficha: Monarka Clinic",
        }
    ]
    claim_request_digest["review_first_clinic_workgroup"] = {
        "clinic_name": "Monarka Clinic",
        "open_count": 1,
        "blocking_claim_reviews": 0,
        "claim_request_reviews": 1,
        "quality_reviews": 0,
        "enrichment_reviews": 0,
        "source_change_reviews": 0,
        "candidate_reviews": 0,
    }
    check(format_review_type("clinic_claim_request") == "reclamaciones de ficha", "claim-request label missing")
    check(format_review_type("clinic_quality_audit") == "revisiones manuales", "quality-audit label should be manual review")
    check(next_action_label(claim_request_digest) == "Revisar reclamación de ficha", "claim request should be next before candidates")
    check(
        first_clinic_workgroup(claim_request_digest)
        == "Abrir Monarka Clinic: 1 tarjeta (1 reclamación de ficha)",
        "claim request should be visible in clinic workgroup detail",
    )
    check(next_specialist_action(digest) == "Revisar Age Reversal: ya tiene 2 revisiones abiertas", "next specialist action missing")
    claim_only_digest = dict(digest)
    claim_only_digest["specialist_next_target"] = dict(digest["specialist_next_target"], open_review_count=0)
    check(
        next_specialist_action(claim_only_digest) == "Revisar Age Reversal: ya tiene 1 nombre detectado",
        "next specialist action should use detected-name wording",
    )
    check(
        next_profile_action(digest) == "Revisar Kairos Longevity Clinic: ya tiene 4 revisiones abiertas relacionadas. Primer campo: Google Maps de clínica",
        "next profile action missing",
    )
    check(
        publication_readiness_status(digest) == "3/24 fichas sin faltantes obligatorios; 21 con faltantes; 1 con claims bloqueantes",
        "publication readiness status missing",
    )
    check(top_publication_missing_field(digest) == "Google Maps de clínica · 20 fichas", "top publication blocker missing")
    check(
        next_publication_action(digest)
        == "Revisar Longevity Marbella: primer faltante obligatorio: Google Maps de clínica; 2 faltantes en total",
        "next publication action missing",
    )
    check(next_source_action(digest) == "Revisar 2 claims bloqueantes de Kairos Longevity Clinic", "next source action missing")
    check(
        first_clinic_workgroup(digest) == "Abrir Sensabell: 5 tarjetas (1 claim bloqueante / 3 mejoras / 1 revisión manual)",
        "first clinic workgroup missing",
    )
    check(
        source_coverage_status(digest) == "11/19 fichas con fuente; 10/19 hidratadas; 8 sin fuente; 11 con trabajo pendiente",
        "source coverage status missing",
    )
    check(first_backlog_bottleneck(digest) == "Ordenar Sensabell: 2 mejoras abiertas", "first backlog bottleneck missing")
    check(review_backlog_guard_status(digest) == "pausa preventiva: 48/50 abiertas; baja de 45", "review backlog guard missing")
    margin_digest = {"summary": {"reviews": {"open": 43}}}
    check(
        review_backlog_guard_status(margin_digest) == "margen corto: 43/50 abiertas; quedan 2 propuestas antes de la pausa preventiva",
        "preventive backlog margin should be visible before the pause",
    )
    check(top_pending_profile_field(digest) == "Google Maps · 19 fichas", "top pending profile field missing")
    check(
        location_coverage_status(digest) == "3 sedes explícitas; 1 clínica multisede; 2 propuestas en bandeja; 3 internas detectadas; 2 sedes explícitas sin Maps de clínica; 0 sedes explícitas sin dirección",
        "location coverage status missing",
    )
    check(
        google_link_review_status(digest) == "4 tarjetas; 2 parecen perfil directo; 1 dudosa; primera: Completar enlaces Google: Sensabell",
        "Google link review status missing",
    )
    source = (ROOT / "scripts" / "admin_digest.py").read_text(encoding="utf-8")
    check(
        'proposed_google_maps_check = "btrim(proposed.value) ~* \'^https?://\'"' in source
        and 'location_maps_check = f"btrim({location_maps_value}) ~* \'^https?://\'"' in source,
        "Google link digest should count any proposed Maps URL, including weak links for review",
    )
    check(
        specialist_review_status(digest) == "2 tarjetas; 17 especialistas propuestos; primera: Regenera Clinic Medicina de la Longevidad · 11 especialistas",
        "specialist review status missing",
    )
    check(
        source_origin_audit_status(digest) == "19/22 preparables para ayuda IA; 4 con contexto completo; 3 recuperables desde trabajo; 15 acotadas a campos propuestos",
        "source origin audit status missing",
    )
    candidate_url_review = {
        "review_type": "candidate_clinic",
        "priority": 90,
        "clinic_name": "",
        "title": "https://eternalgroup.es/",
    }
    check(
        display_review_title(candidate_url_review) == "Recomendar clínica: eternalgroup.es",
        "candidate URL review titles should become recommendation labels",
    )
    check(
        display_review_title({
            "review_type": "clinic_quality_audit",
            "title": "Completar ficha: Clínica Benzaquén",
        }) == "Revisión manual: Clínica Benzaquén",
        "quality audit titles should use manual review wording",
    )
    candidate_url_digest = dict(digest)
    candidate_url_digest["reviews_by_type"] = [{"review_type": "candidate_clinic", "open_count": 1}]
    candidate_url_digest["open_reviews"] = [candidate_url_review]
    check(
        "sin clinica: Recomendar clínica: eternalgroup.es" in format_digest(candidate_url_digest),
        "candidate URL review should be readable in formatted digest",
    )
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
    check("# Vitalarga CTO digest" in output, "title missing")
    check("Clinicas totales: 19" in output, "clinic count missing")
    check("Capturas guardadas: 3" in output, "snapshot count missing")
    check("Fichas con especialistas: 2/19" in output, "specialist coverage missing")
    check("Tarjetas con especialistas: 2 tarjetas; 17 especialistas propuestos" in output, "specialist review status line missing")
    check("Siguiente especialistas: Revisar Age Reversal: ya tiene 2 revisiones abiertas" in output, "next specialist line missing")
    check("Fichas sin campos pendientes medidos: 0/19" in output, "profile completeness missing")
    check("Campo mas pendiente: Google Maps · 19 fichas" in output, "top pending profile field line missing")
    check(top_pending_profile_field(digest) == "Google Maps · 19 fichas", "top pending field should use operational priority on ties")
    check("Fichas pendientes:" in output, "profile queue line missing")
    check("Fichas listas para publicar: 3/24 fichas sin faltantes obligatorios; 21 con faltantes; 1 con claims bloqueantes" in output, "publication readiness line missing")
    check("Principal faltante publicacion: Google Maps de clínica · 20 fichas" in output, "publication blocker line missing")
    check("Siguiente publicacion: Revisar Longevity Marbella: primer faltante obligatorio: Google Maps de clínica; 2 faltantes en total" in output, "next publication line missing")
    check("Sedes: 3 sedes explícitas; 1 clínica multisede; 2 propuestas en bandeja; 3 internas detectadas" in output, "location coverage line missing")
    check("Auto-publicacion: desactivada" in output, "auto-publish safety missing")
    check("Publicacion web: manual" in output, "manual publication status missing")
    check("Ultimo cambio guardado: 2026-08-30 10:35" in output, "last public change missing")
    check("Ultima peticion Netlify: 2026-08-30 10:35" in output, "last rebuild request missing")
    check("Bajo riesgo: no lista" in output, "maturity signal missing")
    check("muestra humana insuficiente: 13/200 candidatas" in output, "maturity blocker missing")
    check("mejoras de ficha: 11 abiertas" in output, "review type summary missing")
    check("cambios de fuente: 1 abierta" in output, "source change label missing")
    check("claims bloqueantes: 1 abierta" in output, "blocking claim label missing")
    check("Sensabell" in output, "priority item missing")
    check("Regenera Clinic Medicina de la Longevidad · 11 especialistas" in output, "professional-count note missing")
    check("review_examples_by_type" not in output, "raw example key should not appear in formatted digest")
    check("Coste registrado 24h: 1.25" in output, "cost formatting missing")
    check("Siguiente accion: Revisar claim bloqueante" in output, "next action missing")

    pending_digest = dict(digest)
    pending_digest["publication_control"] = dict(digest["publication_control"])
    pending_digest["publication_control"]["last_public_site_change_at"] = "2026-08-30T11:05:00+00:00"
    pending_digest["publication_control"]["pending_public_site_rebuild"] = True
    pending_output = format_digest(pending_digest)
    check(
        publication_control_status(pending_digest) == "manual, con cambios pendientes",
        "pending publication status should be explicit",
    )
    check("Publicacion web: manual, con cambios pendientes" in pending_output, "pending publication line missing")
    check("Freno bandeja: pausa preventiva: 48/50 abiertas; baja de 45" in output, "backlog guard line missing")
    check("Google Maps pendientes: 4 tarjetas; 2 parecen perfil directo; 1 dudosa; primera: Completar enlaces Google: Sensabell" in output, "Google Maps pending line missing")
    check("'direct_maps_count', count(*) filter (where direct_maps_proposed)" in source, "Google Maps digest should count direct-looking profiles")
    check("'weak_maps_count', count(*) filter (where weak_maps_proposed)" in source, "Google Maps digest should count weak proposals")
    check("'reviews_without_maps_count', 0" in source, "Google reviews should no longer be counted as an operational Google link review")
    check("Ayuda IA revisiones: 19/22 preparables para ayuda IA; 4 con contexto completo; 3 recuperables desde trabajo; 15 acotadas a campos propuestos" in output, "source origin audit line missing")
    source = (ROOT / "scripts" / "admin_digest.py").read_text(encoding="utf-8")
    check(
        'proposed_google_maps_check = "btrim(proposed.value) ~* \'^https?://\'"' in source,
        "review digest should count weak proposed Maps URLs for human review",
    )
    check("proposed.key in ('maps_url', 'google_maps_url')" in source, "review digest should detect proposed Maps fields")
    check("proposed.key in ('google_reviews_url', 'reviews_url')" not in source, "review digest should no longer include Google review links")
    check(
        'location_maps_check = f"btrim({location_maps_value}) ~* \'^https?://\'"' in source,
        "review digest should count weak location Maps URLs for human review",
    )
    check("publication_readiness_base as (" in source, "digest should calculate publication readiness")
    check("'publication_readiness', (select data from publication_readiness)" in source, "digest should expose publication readiness")
    check("review_source_origin_audit as (" in source, "digest should calculate source-origin audit")
    check("'review_source_origin_audit', (select data from review_source_origin_audit)" in source, "digest should expose source-origin audit")
    check("items.title asc, items.id asc" in source, "digest open-review aggregation should have a stable tie-break")
    check("rq.title asc, rq.id asc" in source, "digest open-review queries should have a stable tie-break")
    check("Especialistas pendientes: 2 tarjetas; 17 especialistas propuestos" in output, "specialist pending line missing")
    check("Grupo por clinica: Abrir Sensabell: 5 tarjetas" in output, "clinic workgroup line missing")
    check("Duplicados mejoras: 1 clinicas / 2 tarjetas" in output, "duplicate enrichment signal missing")
    check("Primer atasco: Ordenar Sensabell: 2 mejoras abiertas" in output, "first backlog bottleneck line missing")
    check("## Vigilancia de fuentes" in output, "source monitoring section missing")
    check("Fuentes vigilables: 39" in output, "monitorable source count missing")
    check("Fuentes vencidas ahora: todo reciente" in output, "fresh source status missing")
    check("Cobertura fuentes: 11/19 fichas con fuente; 10/19 hidratadas; 8 sin fuente; 11 con trabajo pendiente" in output, "source coverage line missing")
    check("Cobertura sedes: 3 sedes explícitas; 1 clínica multisede; 2 propuestas en bandeja; 3 internas detectadas" in output, "source location coverage line missing")
    check("Siguiente fuente: Revisar 2 claims bloqueantes de Kairos Longevity Clinic" in output, "next source line missing")
    check("Proxima revision prevista: 2026-09-05 10:00" in output, "next due date missing")
    check("Cadencia: 4 semanal / 32 estandar / 3 lenta" in output, "cadence mix missing")

    portal_digest = {
        "summary": {
            "clinics": {"total": 19, "published": 11, "preliminary": 8},
            "reviews": {"open": 3},
            "jobs": {"queued": 0, "running": 0, "failed": 0, "dead_letter": 0},
            "evidence": {},
            "automation": {
                "agents_enabled": True,
                "auto_publish_enabled": False,
                "shadow_mode_active": True,
                "shadow_review_target": 200,
                "candidate_reviews_completed": 13,
            },
            "portal": {
                "claim_requests_pending": 2,
                "change_requests_pending": 1,
                "active_memberships": 4,
                "identity_confirmed": 2,
            },
        },
        "portal_reviews": {
            "claim_access_open": 1,
            "recommended_clinic_open": 1,
            "profile_change_open": 1,
            "open_total": 3,
        },
        "reviews_by_type": [
            {"review_type": "clinic_claim_request", "open_count": 1},
            {"review_type": "portal_recommended_clinic", "open_count": 1},
            {"review_type": "portal_profile_change", "open_count": 1},
        ],
        "open_reviews": [],
        "review_examples_by_type": [],
        "recent_failed_jobs": [],
    }
    portal_output = format_digest(portal_digest)
    check(next_action_label(portal_digest) == "Revisar reclamación de ficha", "portal claim should be prioritized as a ficha claim")
    check(next_portal_action(portal_digest) == "Revisar 1 reclamación de ficha", "next portal action missing")
    check(
        portal_status(portal_digest) == "3 pendientes: 1 reclamación de ficha, 1 sugerencia, 1 cambio; 2 fichas con datos confirmados por el centro",
        "portal status missing",
    )
    check("## Portal clinicas" in portal_output, "portal section missing")
    check("Estado: 3 pendientes: 1 reclamación de ficha, 1 sugerencia, 1 cambio" in portal_output, "portal status line missing")
    check("Siguiente portal: Revisar 1 reclamación de ficha" in portal_output, "portal next action line missing")
    print("OK digest: internal CTO summary")


if __name__ == "__main__":
    main()
