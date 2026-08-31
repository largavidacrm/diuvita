#!/usr/bin/env python3
"""Checks for the internal CTO digest formatter."""
from pathlib import Path

from admin_digest import (
    first_clinic_workgroup,
    first_backlog_bottleneck,
    format_digest,
    google_link_review_status,
    location_coverage_status,
    next_action_label,
    next_profile_action,
    next_portal_action,
    next_source_action,
    next_specialist_action,
    publication_control_status,
    portal_status,
    review_backlog_guard_status,
    source_coverage_status,
    specialist_review_status,
    top_pending_profile_field,
)


ROOT = Path(__file__).resolve().parents[1]


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
            "pending_google_reviews": 18,
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
            "locations_missing_google_reviews": 3,
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
    }
    output = format_digest(digest)
    check(next_action_label(digest) == "Revisar claim bloqueante", "next action should prefer blocking claims")
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
    check(next_source_action(digest) == "Revisar 2 claims bloqueantes de Kairos Longevity Clinic", "next source action missing")
    check(
        first_clinic_workgroup(digest) == "Trabajar Sensabell: 5 tarjetas (1 claim bloqueante / 3 mejoras / 1 auditoría)",
        "first clinic workgroup missing",
    )
    check(
        source_coverage_status(digest) == "11/19 fichas con fuente; 10/19 hidratadas; 8 sin fuente; 11 con trabajo pendiente",
        "source coverage status missing",
    )
    check(first_backlog_bottleneck(digest) == "Ordenar Sensabell: 2 mejoras abiertas", "first backlog bottleneck missing")
    check(review_backlog_guard_status(digest) == "cerca del freno: 48/50 abiertas", "review backlog guard missing")
    check(top_pending_profile_field(digest) == "Google Maps · 19 fichas", "top pending profile field missing")
    check(
        location_coverage_status(digest) == "3 sedes explícitas; 1 clínica multisede; 2 propuestas en bandeja; 3 internas detectadas; 2 sin Maps de clínica; 3 sin valoraciones; 0 sin dirección",
        "location coverage status missing",
    )
    check(
        google_link_review_status(digest) == "4 tarjetas; primera: Completar enlaces Google: Sensabell",
        "Google link review status missing",
    )
    check(
        specialist_review_status(digest) == "2 tarjetas; 17 especialistas propuestos; primera: Regenera Clinic Medicina de la Longevidad · 11 especialistas",
        "specialist review status missing",
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
    check("Siguiente ficha: Revisar Kairos Longevity Clinic" in output, "next profile line missing")
    check("Sedes: 3 sedes explícitas; 1 clínica multisede; 2 propuestas en bandeja; 3 internas detectadas" in output, "location coverage line missing")
    check("Auto-publicacion: desactivada" in output, "auto-publish safety missing")
    check("Publicacion web: agrupada cada 30 min" in output, "publication batching missing")
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
        publication_control_status(pending_digest) == "con cambios pendientes de verse online",
        "pending publication status should be explicit",
    )
    check("Publicacion web: con cambios pendientes de verse online" in pending_output, "pending publication line missing")
    check("Freno bandeja: cerca del freno: 48/50 abiertas" in output, "backlog guard line missing")
    check("Google Maps pendientes: 4 tarjetas; primera: Completar enlaces Google: Sensabell" in output, "Google Maps pending line missing")
    source = (ROOT / "scripts" / "admin_digest.py").read_text(encoding="utf-8")
    check("proposed_google_maps_check = google_maps_profile_url_sql(\"proposed.value\")" in source, "review digest should use direct-only Maps SQL")
    check("proposed.key in ('maps_url', 'google_maps_url')" in source, "review digest should detect proposed Maps fields")
    check("proposed.key in ('google_reviews_url', 'reviews_url')" in source, "review digest should still include Google review links")
    check("where {location_maps_check}" in source, "review digest should use direct-only location Maps SQL")
    check("Especialistas pendientes: 2 tarjetas; 17 especialistas propuestos" in output, "specialist pending line missing")
    check("Grupo por clinica: Trabajar Sensabell: 5 tarjetas" in output, "clinic workgroup line missing")
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
    check(next_action_label(portal_digest) == "Revisar accesos del portal", "portal access should be prioritized")
    check(next_portal_action(portal_digest) == "Revisar 1 solicitud de acceso", "next portal action missing")
    check(
        portal_status(portal_digest) == "3 pendientes: 1 acceso, 1 sugerencia, 1 cambio; 2 fichas con datos confirmados por el centro",
        "portal status missing",
    )
    check("## Portal clinicas" in portal_output, "portal section missing")
    check("Estado: 3 pendientes: 1 acceso, 1 sugerencia, 1 cambio" in portal_output, "portal status line missing")
    check("Siguiente portal: Revisar 1 solicitud de acceso" in portal_output, "portal next action line missing")
    print("OK digest: internal CTO summary")


if __name__ == "__main__":
    main()
