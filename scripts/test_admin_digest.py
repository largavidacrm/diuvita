#!/usr/bin/env python3
"""Checks for the internal CTO digest formatter."""

from admin_digest import (
    first_clinic_workgroup,
    first_backlog_bottleneck,
    format_digest,
    next_action_label,
    next_profile_action,
    next_source_action,
    next_specialist_action,
    review_backlog_guard_status,
    source_coverage_status,
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
        "publication_control": {
            "rebuild_hook_configured": True,
            "rebuild_batch_minutes": 30,
            "last_public_site_rebuild_requested_at": "2026-08-30T10:35:11+00:00",
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
        "profile_next_target": {
            "slug": "kairos-longevity-clinic",
            "clinic_name": "Kairos Longevity Clinic",
            "city": "Madrid",
            "status": "published",
            "pending_fields": ["Especialistas publicados", "Tecnología destacada"],
            "pending_count": 2,
            "next_pending_field": "Especialistas publicados",
            "open_quality_reviews": 1,
            "open_profile_reviews": 2,
            "open_source_change_reviews": 1,
            "open_relevant_reviews": 4,
        },
    }
    output = format_digest(digest)
    check(next_action_label(digest) == "Revisar claim bloqueante", "next action should prefer blocking claims")
    check(next_specialist_action(digest) == "Revisar Age Reversal: ya tiene 2 revisiones abiertas", "next specialist action missing")
    check(
        next_profile_action(digest) == "Revisar Kairos Longevity Clinic: ya tiene 4 revisiones abiertas relacionadas. Primer campo: Especialistas publicados",
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
    check("# Vitalarga CTO digest" in output, "title missing")
    check("Clinicas totales: 19" in output, "clinic count missing")
    check("Capturas guardadas: 3" in output, "snapshot count missing")
    check("Fichas con especialistas: 2/19" in output, "specialist coverage missing")
    check("Siguiente especialistas: Revisar Age Reversal: ya tiene 2 revisiones abiertas" in output, "next specialist line missing")
    check("Fichas sin campos pendientes medidos: 1/19" in output, "profile completeness missing")
    check("Campo mas pendiente: Especialistas · 17 fichas" in output, "top pending profile field line missing")
    check("Siguiente ficha: Revisar Kairos Longevity Clinic" in output, "next profile line missing")
    check("Auto-publicacion: desactivada" in output, "auto-publish safety missing")
    check("Publicacion web: agrupada cada 30 min" in output, "publication batching missing")
    check("Ultima peticion Netlify: 2026-08-30 10:35" in output, "last rebuild request missing")
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
    check("Grupo por clinica: Trabajar Sensabell: 5 tarjetas" in output, "clinic workgroup line missing")
    check("Duplicados mejoras: 1 clinicas / 2 tarjetas" in output, "duplicate enrichment signal missing")
    check("Primer atasco: Ordenar Sensabell: 2 mejoras abiertas" in output, "first backlog bottleneck line missing")
    check("## Vigilancia de fuentes" in output, "source monitoring section missing")
    check("Fuentes vigilables: 39" in output, "monitorable source count missing")
    check("Fuentes vencidas ahora: todo reciente" in output, "fresh source status missing")
    check("Cobertura fuentes: 11/19 fichas con fuente; 10/19 hidratadas; 8 sin fuente; 11 con trabajo pendiente" in output, "source coverage line missing")
    check("Siguiente fuente: Revisar 2 claims bloqueantes de Kairos Longevity Clinic" in output, "next source line missing")
    check("Proxima revision prevista: 2026-09-05 10:00" in output, "next due date missing")
    check("Cadencia: 4 semanal / 32 estandar / 3 lenta" in output, "cadence mix missing")
    print("OK digest: internal CTO summary")


if __name__ == "__main__":
    main()
