#!/usr/bin/env python3
"""Checks for the read-only pre-SEO readiness report."""

from pre_seo_readiness_report import (
    build_gates,
    build_pre_seo_report,
    format_pre_seo_report,
    next_pre_seo_review_action,
    programmatic_seo_status,
    review_open_count,
    source_coverage_line,
)


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def sample_digest():
    return {
        "generated_at": "2026-09-01T15:22:00+00:00",
        "summary": {
            "reviews": {"open": 8},
            "automation": {"auto_publish_enabled": False},
        },
        "publication_readiness": {
            "clinics_measured": 26,
            "ready_clinics": 11,
            "clinics_with_missing_fields": 15,
            "clinics_with_blocking_reviews": 1,
            "top_missing_fields": [
                {"field": "Google Maps de clinica", "count": 12},
                {"field": "Contacto publico", "count": 5},
            ],
        },
        "source_coverage": {
            "visible_clinics": 19,
            "clinics_with_sources": 14,
            "clinics_with_hydrated_sources": 12,
            "clinics_without_sources": 5,
            "clinics_needing_source_work": 7,
        },
        "review_source_origin_audit": {
            "cards": 8,
            "context_ready": 5,
            "recoverable_from_job": 1,
            "source_without_context": 2,
            "no_source_context": 0,
        },
    }


def sample_backlog():
    return {
        "generated_at": "2026-09-01T15:22:00+00:00",
        "summary": {
            "open_reviews": 8,
            "duplicate_enrichment_reviews": 0,
            "safe_write_limit": 50,
            "safe_write_pause_margin": 5,
            "safe_write_pause_at": 45,
        },
        "review_type_summary": [
            {"review_type": "mejoras de ficha", "open_count": 8, "max_priority": 50},
        ],
        "clinic_workgroups": [
            {
                "clinic_name": "Sensabell",
                "clinic_slug": "sensabell",
                "city": "Valencia",
                "clinic_status": "published",
                "card_count": 1,
                "blocking_claim_reviews": 0,
                "claim_request_reviews": 0,
                "quality_reviews": 0,
                "enrichment_reviews": 1,
                "source_change_reviews": 0,
                "candidate_reviews": 0,
                "max_priority": 50,
                "oldest_created_at": "2026-09-01T11:00:00+00:00",
            }
        ],
    }


def main():
    digest = sample_digest()
    backlog = sample_backlog()
    report = build_pre_seo_report(digest, backlog, review_target=25, limit=8)
    output = format_pre_seo_report(report)
    gates = build_gates(digest, backlog, 25)

    check(review_open_count(backlog, digest) == 8, "review count should prefer backlog")
    check(
        next_pre_seo_review_action(backlog) == "Revisar Sensabell: 1 tarjeta, empezando por mejoras de ficha",
        "next review action should name the first clinic workgroup",
    )
    check("14/19 fichas con fuente; 12/19 hidratadas; 5 sin fuente; 7 con trabajo pendiente" in source_coverage_line(digest), "source coverage line missing")
    check(programmatic_seo_status(gates).startswith("esperar:"), "programmatic SEO should wait while fields and traceability are pending")
    check("# Vitalarga: cierre pre-SEO" in output, "title missing")
    check("Bandeja: 8 abiertas; objetivo <=25 cumplido" in output, "target status missing")
    check("SEO tecnico: puede seguir en local" in output, "technical SEO status missing")
    check("SEO programatico: esperar: Campos base publicables; Trazabilidad suficiente" in output, "programmatic blockers missing")
    check("Writes data: no" in output, "write safety line missing")
    check("Push/deploy: no" in output, "deployment safety line missing")
    check("OK · Bandeja <= 25" in output, "backlog gate missing")
    check("PENDIENTE · Campos base publicables" in output, "base-fields gate missing")
    check("PENDIENTE · Trazabilidad suficiente" in output, "traceability gate missing")
    check("mejoras de ficha: 8 abiertas, max P50" in output, "review type summary missing")
    check("Siguiente revision humana: Revisar Sensabell" in output, "next review action missing")
    check("no publica, no edita clinicas" in output, "read-only note missing")

    ready_digest = sample_digest()
    ready_digest["publication_readiness"] = {
        "clinics_measured": 26,
        "ready_clinics": 26,
        "clinics_with_missing_fields": 0,
        "clinics_with_blocking_reviews": 0,
        "top_missing_fields": [],
    }
    ready_digest["source_coverage"] = {
        "visible_clinics": 26,
        "clinics_with_sources": 26,
        "clinics_with_hydrated_sources": 26,
        "clinics_without_sources": 0,
        "clinics_needing_source_work": 0,
    }
    ready_digest["review_source_origin_audit"] = {
        "cards": 4,
        "context_ready": 4,
        "recoverable_from_job": 0,
        "source_without_context": 0,
        "no_source_context": 0,
    }
    ready_gates = build_gates(ready_digest, backlog, 25)
    check(
        programmatic_seo_status(ready_gates)
        == "preparado para plantear SEO programatico con aprobacion de Daniel",
        "ready state should still require Daniel approval",
    )


if __name__ == "__main__":
    main()
