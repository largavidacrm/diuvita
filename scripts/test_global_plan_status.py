#!/usr/bin/env python3
"""Checks for the Daniel-readable global plan status."""

from global_plan_status import (
    automation_status,
    format_global_plan_status,
    plan_phase,
    source_monitoring_status,
    specialist_status,
    visible_clinic_status,
)


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def sample_digest():
    return {
        "generated_at": "2026-08-30T17:05:00+00:00",
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
            "last_public_site_rebuild_requested_at": "2026-08-30T10:35:11+00:00",
        },
        "reviews_by_type": [{"review_type": "blocking_claim_review", "open_count": 4}],
        "open_reviews": [{"review_type": "blocking_claim_review", "priority": 95}],
        "recent_failed_jobs": [],
        "claim_quality": {"conflict": 0, "rejected": 0, "without_source": 0},
        "source_monitoring": {
            "due_sources": 0,
            "next_due_at": "2026-09-29T09:58:00+00:00",
        },
        "source_coverage": {
            "visible_clinics": 19,
            "clinics_with_sources": 11,
            "clinics_without_sources": 8,
            "clinics_with_hydrated_sources": 11,
            "clinics_needing_source_work": 11,
        },
        "source_next_target": {
            "clinic_name": "Kairos Longevity Clinic",
            "source_records": 2,
            "hydrated_source_records": 2,
            "total_claims": 8,
            "claims_without_source": 0,
            "blocking_claims": 2,
        },
        "review_first_clinic_workgroup": {
            "clinic_name": "Sensabell",
            "open_count": 5,
            "blocking_claim_reviews": 1,
            "quality_reviews": 1,
            "enrichment_reviews": 3,
            "source_change_reviews": 0,
            "candidate_reviews": 0,
        },
        "profile_completeness": {
            "visible_clinics": 19,
            "pending_specialists": 17,
            "pending_contact": 6,
        },
        "profile_next_target": {
            "clinic_name": "Sensabell",
            "pending_count": 4,
            "next_pending_field": "Email o teléfono",
            "open_relevant_reviews": 5,
        },
        "specialist_coverage": {
            "visible_clinics": 19,
            "with_specialists": 2,
            "without_specialists": 17,
        },
        "specialist_next_target": {
            "clinic_name": "Kairos Longevity Clinic",
            "open_review_count": 4,
            "specialist_claims": 1,
        },
    }


def main():
    digest = sample_digest()
    output = format_global_plan_status(digest, "main · abc123 Test commit")

    check(plan_phase(digest) == "centro de control y reducción de bandeja", "phase should reflect review pressure")
    check(visible_clinic_status(digest) == "11 publicadas y 8 preliminares", "visible clinic status missing")
    check(automation_status(digest) == "modo sombra activo; auto-publicación apagada", "automation status missing")
    check(specialist_status(digest) == "2/19 fichas con especialistas; 17 pendientes", "specialist status missing")
    check(source_monitoring_status(digest) == "todo reciente; próxima revisión 2026-09-29 09:58", "source monitoring missing")
    check("# Diuvita: estado del plan global" in output, "title missing")
    check("Git: main · abc123 Test commit" in output, "git label missing")
    check("Fase activa: centro de control y reducción de bandeja" in output, "phase line missing")
    check("Web pública: 11 publicadas y 8 preliminares" in output, "public website line missing")
    check("Bandeja: 48 revisiones abiertas; cerca del freno: 48/50 abiertas" in output, "backlog line missing")
    check("Trazabilidad de fuentes: 11/19 fichas con fuente" in output, "source coverage line missing")
    check("Ciclo autónomo: activo en sombra" in output, "shadow cycle line missing")
    check("Coste Netlify: publicación agrupada cada 30 min" in output, "netlify cost line missing")
    check("Grupo por clínica: Trabajar Sensabell: 5 tarjetas" in output, "clinic workgroup missing")
    check("Siguiente fuente: Revisar 2 claims bloqueantes de Kairos Longevity Clinic" in output, "next source missing")
    check("Siguiente ficha: Revisar Sensabell" in output, "next profile missing")
    check("Campo más pendiente: Especialistas · 17 fichas" in output, "top pending field missing")
    check("muestra humana insuficiente: 2/200 candidatas" in output, "maturity blocker missing")
    check("no publica, no edita clínicas" in output, "read-only note missing")

    failed = sample_digest()
    failed["summary"]["jobs"] = {"failed": 1, "dead_letter": 0}
    check(plan_phase(failed) == "estabilización técnica", "failed jobs should change phase")
    print("OK global plan status: roadmap snapshot is readable")


if __name__ == "__main__":
    main()
