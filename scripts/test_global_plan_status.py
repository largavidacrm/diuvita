#!/usr/bin/env python3
"""Checks for the Daniel-readable global plan status."""

from global_plan_status import (
    automation_status,
    codex_can_continue_status,
    daniel_now_status,
    format_global_plan_status,
    location_status,
    llm_review_readiness_blocker,
    not_ready_status,
    plan_phase,
    review_backlog_needs_care,
    source_monitoring_status,
    source_origin_audit_status,
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
        "review_source_origin_audit": {
            "cards": 22,
            "context_ready": 4,
            "recoverable_from_job": 3,
            "source_without_context": 15,
            "no_source_context": 0,
        },
        "profile_completeness": {
            "visible_clinics": 19,
            "with_pending_fields": 19,
            "without_pending_fields": 0,
            "pending_google_maps": 19,
            "pending_google_reviews": 18,
            "pending_specialists": 17,
            "pending_contact": 6,
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
            "clinic_name": "Sensabell",
            "pending_count": 4,
            "next_pending_field": "Email o teléfono",
            "open_relevant_reviews": 5,
        },
        "publication_readiness": {
            "clinics_measured": 24,
            "visible_clinics": 19,
            "ready_clinics": 3,
            "clinics_with_missing_fields": 21,
            "clinics_with_blocking_reviews": 1,
            "top_missing_fields": [
                {"field": "Google Maps de clínica", "count": 20},
            ],
        },
        "publication_next_target": {
            "clinic_name": "Longevity Marbella",
            "slug": "longevity-marbella",
            "status": "draft",
            "missing_fields": ["Google Maps de clínica", "Dirección o sede"],
            "missing_count": 2,
            "next_missing_field": "Google Maps de clínica",
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
    check(location_status(digest) == "3 sedes explícitas; 1 clínica multisede; 2 propuestas en bandeja; 3 internas detectadas; 2 sin Maps de clínica; 3 sin valoraciones; 0 sin dirección", "location status missing")
    check(source_monitoring_status(digest) == "todo reciente; próxima revisión 2026-09-29 09:58", "source monitoring missing")
    check(
        daniel_now_status(digest) == "Abrir prioridad: abre el filtro Claims bloqueantes en el panel",
        "Daniel next step should open the concrete priority review",
    )
    check(codex_can_continue_status(digest) == "mejorar panel, extractores y checks sin crear tarjetas nuevas", "Codex safe next step missing")
    check(
        llm_review_readiness_blocker(digest)
        == "preparación LLM de propuestas con fuente incompleta: 4/22 listas para LLM; 3 recuperables desde trabajo; 15 solo fuente: revisión manual",
        "LLM readiness blocker missing",
    )
    check(
        not_ready_status(digest)
        == "muestra humana insuficiente: 2/200 candidatas; preparación LLM de propuestas con fuente incompleta: 4/22 listas para LLM; 3 recuperables desde trabajo; 15 solo fuente: revisión manual",
        "not-ready reason missing",
    )
    check(source_origin_audit_status(digest) == "4/22 listas para LLM; 3 recuperables desde trabajo; 15 solo fuente: revisión manual", "LLM source-origin status missing")
    check("# Vitalarga: estado del plan global" in output, "title missing")
    check("Git: main · abc123 Test commit" in output, "git label missing")
    check("## Lectura rápida" in output, "quick-read section missing")
    check("Daniel ahora: Abrir prioridad: abre el filtro Claims bloqueantes en el panel" in output, "Daniel quick action missing")
    check("Codex puede seguir con: mejorar panel, extractores y checks sin crear tarjetas nuevas" in output, "Codex safe work missing")
    check(
        "No activar todavía: muestra humana insuficiente: 2/200 candidatas; preparación LLM de propuestas con fuente incompleta: 4/22 listas para LLM; 3 recuperables desde trabajo; 15 solo fuente: revisión manual"
        in output,
        "not-ready quick line missing",
    )
    check("## Siguiente en el panel" in output, "panel next-click section missing")
    check("No crees trabajos nuevos hasta bajar la bandeja; ahora está pausa preventiva: 48/50 abiertas; baja de 45." in output, "panel backlog guard missing")
    check("Pulsa Abrir prioridad: abre el filtro Claims bloqueantes en el panel." in output, "panel priority click missing")
    check("Pulsa Especialistas y abre primero la tarjeta con más nombres: Regenera Clinic Medicina de la Longevidad." in output, "panel specialist click missing")
    check("Pulsa Google Maps y valida que el enlace abre el perfil real de la clínica: Completar enlaces Google: Sensabell." in output, "panel Google Maps click missing")
    check("Fase activa: centro de control y reducción de bandeja" in output, "phase line missing")
    check("Web pública: 11 publicadas y 8 preliminares" in output, "public website line missing")
    check("Bandeja: 48 revisiones abiertas; pausa preventiva: 48/50 abiertas; baja de 45" in output, "backlog line missing")
    check("Trazabilidad de fuentes: 11/19 fichas con fuente" in output, "source coverage line missing")
    check("Sedes y ubicaciones: 3 sedes explícitas; 1 clínica multisede; 2 propuestas en bandeja; 3 internas detectadas" in output, "location coverage line missing")
    check("Ciclo autónomo: activo en sombra; señal automática base" in output, "shadow cycle line missing")
    check("Preparación LLM de propuestas con fuente: 4/22 listas para LLM; 3 recuperables desde trabajo; 15 solo fuente: revisión manual" in output, "LLM review preparation line missing")
    check("Coste Netlify: publicación agrupada cada 30 min" in output, "netlify cost line missing")
    check("Preparación para publicación: 3/24 fichas sin faltantes obligatorios; 21 con faltantes; 1 con claims bloqueantes" in output, "publication readiness line missing")
    check("Principal faltante para publicar: Google Maps de clínica · 20 fichas" in output, "top publication blocker missing")
    check("Contexto de grupo: Abrir Sensabell: 5 tarjetas" in output, "clinic workgroup missing")
    check("Señal automática base: Revisar claim bloqueante" in output, "base review signal missing")
    check("Google Maps propuestos: 4 tarjetas; primera: Completar enlaces Google: Sensabell" in output, "Google Maps proposed line missing")
    check("Especialistas propuestos: 2 tarjetas; 17 especialistas propuestos" in output, "specialist proposed line missing")
    check("Siguiente publicación: Revisar Longevity Marbella: primer faltante obligatorio: Google Maps de clínica; 2 faltantes en total" in output, "next publication line missing")
    check("Siguiente fuente: Revisar 2 claims bloqueantes de Kairos Longevity Clinic" in output, "next source missing")
    check(
        "Fichas pendientes: 19/19 fichas con campos pendientes; se revisan después de la prioridad actual" in output,
        "secondary profile queue should not name a non-primary clinic",
    )
    check("Campo más pendiente: Google Maps · 19 fichas" in output, "top pending field missing")
    check("muestra humana insuficiente: 2/200 candidatas" in output, "maturity blocker missing")
    check("no publica, no edita clínicas" in output, "read-only note missing")

    failed = sample_digest()
    failed["summary"]["jobs"] = {"failed": 1, "dead_letter": 0}
    check(plan_phase(failed) == "estabilización técnica", "failed jobs should change phase")
    specialist_queue = sample_digest()
    specialist_queue["summary"]["reviews"] = {"open": 20}
    specialist_queue["source_coverage"]["clinics_needing_source_work"] = 0
    check(
        codex_can_continue_status(specialist_queue) == "mejorar revisión de Google Maps de clínica sin publicar",
        "Codex should improve publication blockers before specialist-review tooling",
    )
    margin_short = sample_digest()
    margin_short["summary"]["reviews"] = {"open": 43}
    margin_short["source_coverage"]["clinics_needing_source_work"] = 0
    check(review_backlog_needs_care(margin_short), "short backlog margin should count as work needing care")
    check(
        plan_phase(margin_short) == "centro de control y reducción de bandeja",
        "short backlog margin should move the plan phase to review reduction",
    )
    check(
        codex_can_continue_status(margin_short) == "mejorar panel, extractores y checks sin crear tarjetas nuevas",
        "Codex should avoid new review-card work when only a few safe slots remain",
    )
    specialist_only = sample_digest()
    specialist_only["summary"]["reviews"] = {"open": 20}
    specialist_only["source_coverage"]["clinics_needing_source_work"] = 0
    specialist_only["publication_readiness"] = {"clinics_measured": 24, "clinics_with_missing_fields": 0}
    check(
        codex_can_continue_status(specialist_only) == "mejorar revisión de especialistas propuestos sin publicarlos",
        "Codex should still improve specialist-review tooling when publication blockers are clear",
    )

    audit_priority = sample_digest()
    audit_priority["summary"]["reviews"] = {"open": 22}
    audit_priority["reviews_by_type"] = [
        {"review_type": "clinic_profile_enrichment", "open_count": 20},
        {"review_type": "clinic_quality_audit", "open_count": 2},
    ]
    audit_priority["open_reviews"] = [
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
    audit_priority["review_first_clinic_workgroup"] = {
        "clinic_name": "Sensabell",
        "open_count": 4,
        "enrichment_reviews": 3,
        "quality_reviews": 1,
        "max_priority": 65,
    }
    audit_output = format_global_plan_status(audit_priority, "main · audit")
    check(
        daniel_now_status(audit_priority) == "Abrir prioridad: Revisión manual: Clínica Benzaquén",
        "Daniel should see the concrete higher-priority audit before the group",
    )
    check(
        "Pulsa Abrir prioridad: Revisión manual: Clínica Benzaquén; se abrirá directamente el campo pendiente en la ficha."
        in audit_output,
        "global status should send Daniel to manual review for quality-audit fields",
    )
    check(
        "Contexto de grupo: Abrir Sensabell: 4 tarjetas" in audit_output,
        "global status should keep clinic groups as secondary context",
    )
    print("OK global plan status: roadmap snapshot is readable")


if __name__ == "__main__":
    main()
