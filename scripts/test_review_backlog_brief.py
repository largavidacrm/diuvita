#!/usr/bin/env python3
"""Checks for the read-only review backlog brief."""

from review_backlog_brief import (
    backlog_guard,
    compact_lookup_key,
    first_backlog_action,
    format_card_proposal_summary,
    format_backlog,
    format_clinic_workgroup,
    format_workgroup_card,
    proposal_card_summary,
    review_type_label,
    safe_limit,
    workgroup_order,
    workgroup_recommendation,
)


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    report = {
        "generated_at": "2026-08-30T16:10:00+00:00",
        "summary": {
            "open_reviews": 48,
            "open_enrichment_reviews": 16,
            "duplicate_enrichment_clinics": 2,
            "duplicate_enrichment_reviews": 5,
            "safe_write_limit": 50,
        },
        "review_type_summary": [
            {"review_type": "mejoras de ficha", "open_count": 16, "max_priority": 80},
            {"review_type": "clinicas candidatas", "open_count": 8, "max_priority": 90},
            {"review_type": "claims bloqueantes", "open_count": 4, "max_priority": 85},
            {"review_type": "cambios de fuente", "open_count": 1, "max_priority": 70},
        ],
        "clinic_workgroups": [
            {
                "clinic_name": "Sensabell",
                "clinic_slug": "sensabell",
                "city": "Valencia",
                "clinic_status": "published",
                "card_count": 5,
                "blocking_claim_reviews": 1,
                "quality_reviews": 1,
                "enrichment_reviews": 3,
                "source_change_reviews": 0,
                "candidate_reviews": 0,
                "max_priority": 85,
                "oldest_created_at": "2026-08-30T08:30:00+00:00",
                "cards": [
                    {
                        "title": "Revisar Sensabell",
                        "review_type": "clinic_quality_audit",
                        "priority": 85,
                        "created_at": "2026-08-30T08:30:00+00:00",
                    },
                    {
                        "title": "Ampliar ficha: Sensabell",
                        "review_type": "clinic_profile_enrichment",
                        "priority": 80,
                        "created_at": "2026-08-30T09:00:00+00:00",
                    },
                ],
            },
            {
                "clinic_name": "Kairos Longevity Clinic",
                "clinic_slug": "kairos-longevity-clinic",
                "city": "Madrid",
                "clinic_status": "published",
                "card_count": 4,
                "blocking_claim_reviews": 2,
                "quality_reviews": 0,
                "enrichment_reviews": 2,
                "source_change_reviews": 0,
                "candidate_reviews": 0,
                "max_priority": 85,
                "oldest_created_at": "2026-08-30T09:30:00+00:00",
            },
        ],
        "duplicate_enrichment": [
            {
                "clinic_name": "Sensabell",
                "clinic_slug": "sensabell",
                "city": "Valencia",
                "clinic_status": "published",
                "card_count": 3,
                "max_priority": 80,
                "oldest_created_at": "2026-08-30T09:00:00+00:00",
            },
            {
                "clinic_name": "Kairos Longevity Clinic",
                "clinic_slug": "kairos-longevity-clinic",
                "city": "Madrid",
                "clinic_status": "published",
                "card_count": 2,
                "max_priority": 70,
                "oldest_created_at": "2026-08-30T10:00:00+00:00",
            },
        ],
    }
    output = format_backlog(report)
    clinic_output = format_backlog(dict(report, clinic_query="Sensabell", clinic_workgroups=[report["clinic_workgroups"][0]]))

    check(safe_limit(0) == 1, "limit should have a lower bound")
    check(safe_limit(100) == 50, "limit should have an upper bound")
    check(compact_lookup_key("Clínica Sensabell") == "clinicasensabell", "compact query should remove accents and spaces")
    check(review_type_label("clinic_profile_enrichment") == "mejora", "review type label missing")
    check(review_type_label("clinic_claim_request") == "reclamación de ficha", "claim-request label missing")
    check(
        format_workgroup_card(report["clinic_workgroups"][0]["cards"][0])
        == "  - Revisar Sensabell: revisión manual · P85 · creada 2026-08-30 08:30",
        "workgroup card formatting missing",
    )
    check(
        format_workgroup_card(
            {
                "title": "Reclamar ficha: Monarka Clinic",
                "review_type": "clinic_claim_request",
                "priority": 96,
                "created_at": "2026-08-31T13:58:00+00:00",
            }
        )
        == "  - Reclamar ficha: Monarka Clinic: reclamación de ficha · P96 · creada 2026-08-31 13:58",
        "claim-request card formatting missing",
    )
    summarized_card = proposal_card_summary(
        {
            "title": "Revisar extracción shadow: Unidad de Longevidad IMDA",
            "review_type": "clinic_profile_enrichment",
            "priority": 60,
            "created_at": "2026-08-31T12:47:00+00:00",
            "payload": {
                "proposed_fields": {
                    "locations": [{"address": "C/ Goya 5-7", "city": "Madrid"}],
                    "telefono": "676 629 862",
                    "phone_fixed": "91 632 56 59",
                    "profesionales": ["María Ortega", "Laura Ramos"],
                    "services": ["Longevidad"],
                    "email": "info@example.com",
                }
            },
        }
    )
    check("payload" not in summarized_card, "raw payload should not leave the report")
    check(summarized_card["proposed_phone_count"] == 2, "phone proposal count missing")
    check(
        format_card_proposal_summary(summarized_card)
        == "campos: Sedes, Teléfono principal, Teléfono fijo, Especialistas, Servicios +1 · revisar: 1 sede, 2 teléfonos, 2 especialistas",
        "proposal summary should show field names and safe counts",
    )
    check(
        format_workgroup_card(summarized_card)
        == "  - Revisar extracción shadow: Unidad de Longevidad IMDA: mejora · P60 · creada 2026-08-31 12:47 · campos: Sedes, Teléfono principal, Teléfono fijo, Especialistas, Servicios +1 · revisar: 1 sede, 2 teléfonos, 2 especialistas",
        "workgroup card proposal summary missing",
    )
    check(backlog_guard(report["summary"]) == "pausa preventiva: 48/50 abiertas; baja de 45", "guard label missing")
    check(
        backlog_guard({"open_reviews": 43, "safe_write_limit": 50, "safe_write_pause_margin": 5})
        == "margen corto: 43/50 abiertas; quedan 2 propuestas antes de la pausa preventiva",
        "short-margin guard label missing",
    )
    check(
        first_backlog_action(report) == "Revisar Sensabell: 5 tarjetas, empezando por claims bloqueantes",
        "first action should prefer blocking clinic workgroups",
    )
    check(
        workgroup_order(report["clinic_workgroups"][0]) == "claims bloqueantes -> mejoras -> revisión manual",
        "clinic workgroup order missing",
    )
    check(
        workgroup_recommendation(report["clinic_workgroups"][0]) == "primero quitar o corregir datos dudosos",
        "clinic workgroup recommendation missing",
    )
    check(
        format_clinic_workgroup(report["clinic_workgroups"][0])
        == "- Sensabell · Valencia · publicada · 5 tarjetas · 1 claim bloqueante / 3 mejoras / 1 revisión manual · P85 · más antigua 2026-08-30 08:30 · orden: claims bloqueantes -> mejoras -> revisión manual · primero quitar o corregir datos dudosos",
        "clinic workgroup formatting missing",
    )
    claim_group = {
        "clinic_name": "Monarka Clinic",
        "clinic_slug": "monarka-clinic",
        "city": "Madrid",
        "clinic_status": "published",
        "card_count": 2,
        "blocking_claim_reviews": 0,
        "claim_request_reviews": 1,
        "quality_reviews": 0,
        "enrichment_reviews": 0,
        "source_change_reviews": 1,
        "candidate_reviews": 0,
        "max_priority": 96,
        "oldest_created_at": "2026-08-31T13:58:00+00:00",
    }
    check(workgroup_order(claim_group) == "reclamaciones -> fuentes cambiadas", "claim-request order missing")
    check(
        workgroup_recommendation(claim_group) == "escalar a Daniel antes de cambiar datos",
        "claim-request recommendation missing",
    )
    check(
        format_clinic_workgroup(claim_group)
        == "- Monarka Clinic · Madrid · publicada · 2 tarjetas · 1 reclamación / 1 cambio de fuente · P96 · más antigua 2026-08-31 13:58 · orden: reclamaciones -> fuentes cambiadas · escalar a Daniel antes de cambiar datos",
        "claim-request workgroup formatting missing",
    )
    check(
        first_backlog_action(
            {
                "summary": {"open_reviews": 2, "safe_write_limit": 50},
                "clinic_workgroups": [claim_group],
                "duplicate_enrichment": [{"clinic_name": "Neleva", "card_count": 2}],
            }
        )
        == "Revisar Monarka Clinic: reclamación de ficha pendiente; Daniel decide antes de cambiar datos",
        "claim-request action should come before duplicate-only cleanup",
    )
    check("# Vitalarga: atascos de bandeja" in output, "title missing")
    check("Revisiones abiertas: 48" in output, "open count missing")
    check("Mejoras de ficha abiertas: 16" in output, "enrichment count missing")
    check("claims bloqueantes: 4 abiertas; máxima prioridad P85" in output, "blocking claim type missing")
    check("cambios de fuente: 1 abierta; máxima prioridad P70" in output, "singular open label missing")
    check("Clínicas con varias mejoras abiertas: 2" in output, "duplicate clinic count missing")
    check("Tarjetas en grupos duplicados: 5" in output, "duplicate card count missing")
    check("Freno de bandeja: pausa preventiva: 48/50 abiertas; baja de 45" in output, "guard line missing")
    check("Writes data: no" in output, "read-only signal missing")
    check("## Filtrar por clínica" in output, "clinic workgroup section missing")
    check("Sensabell · Valencia · publicada · 5 tarjetas" in output, "clinic workgroup missing")
    check("Kairos Longevity Clinic · Madrid · publicada · 4 tarjetas" in output, "second workgroup missing")
    check("2 claims bloqueantes / 2 mejoras" in output, "workgroup type counts missing")
    check("orden: claims bloqueantes -> mejoras" in output, "workgroup order line missing")
    check("Sensabell · Valencia · publicada · 3 tarjetas · P80" in output, "duplicate group missing")
    check("Consulta: Sensabell" in clinic_output, "clinic query should be shown")
    check("## Tarjetas del caso" in clinic_output, "clinic-specific card section missing")
    check("Revisar Sensabell: revisión manual · P85" in clinic_output, "first case card missing")
    check("Ampliar ficha: Sensabell: mejora · P80" in clinic_output, "second case card missing")
    check("No hay grupos duplicados" not in output, "should not show empty duplicate state")
    check("no descarta ni resuelve tarjetas" in output, "safety note missing")

    empty_report = {
        "summary": {"open_reviews": 0, "safe_write_limit": 50},
        "review_type_summary": [],
        "clinic_workgroups": [],
        "duplicate_enrichment": [],
    }
    check(first_backlog_action(empty_report) == "No hay revisiones abiertas", "empty action missing")
    duplicate_only_report = {
        "summary": {"open_reviews": 3, "safe_write_limit": 50},
        "clinic_workgroups": [
            {
                "clinic_name": "Neleva",
                "card_count": 2,
                "blocking_claim_reviews": 0,
            }
        ],
        "duplicate_enrichment": [
            {
                "clinic_name": "Neleva",
                "card_count": 2,
            }
        ],
    }
    check(
        first_backlog_action(duplicate_only_report) == "Revisar Neleva: tiene 2 mejoras abiertas",
        "duplicate-only action missing",
    )
    check("No hay grupos de revisión por clínica" in format_backlog(empty_report), "empty workgroup state missing")
    check("No hay grupos duplicados" in format_backlog(empty_report), "empty duplicate state missing")
    print("OK review backlog brief: duplicate pressure is readable")


if __name__ == "__main__":
    main()
