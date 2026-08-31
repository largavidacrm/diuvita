#!/usr/bin/env python3
"""Checks for the read-only specialist reconciliation report."""
from __future__ import annotations

import json

from specialist_review_reconciliation import (
    annotated_review_cards,
    clean_person_list,
    format_reconciliation,
    format_review_cards,
    load_reconciliation,
    normalize_person_key,
    reconcile_row,
    specialist_reconciliation_next_step,
    summarize_clinics,
)


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    row = {
        "slug": "clinic-a",
        "clinic_name": "Clinic A",
        "city": "Madrid",
        "status": "published",
        "published_professionals": ["Dra. Ana López"],
        "review_cards": [
            {
                "id": "review-1",
                "title": "Ampliar ficha: Clinic A",
                "priority": 60,
                "created_at": "2026-08-30T10:00:00+00:00",
                "source_url": "https://clinic-a.example/equipo-medico/",
                "professionals": ["Dra. Ana Lopez", "Dr. Luis Pérez - Director médico"],
            }
        ],
        "claim_professionals": ["Dr Luis Perez", "Dra. Carla Ruiz", "Alergología Anestesiología"],
    }
    reconciled = reconcile_row(row)
    summary = summarize_clinics([reconciled])
    output = format_reconciliation({
        "generated_at": "2026-08-31T08:40:00+00:00",
        "query": "Clinic A",
        "writes_data": False,
        "summary": summary,
        "clinics": [reconciled],
    })

    check(normalize_person_key("Dra. Ana López") == normalize_person_key("Ana Lopez"), "person keys should ignore accents and titles")
    check(clean_person_list(["Alergología Anestesiología"]) == [], "specialty menus should not become people")
    annotated = annotated_review_cards(row["review_cards"], {normalize_person_key("Dra. Ana López")})
    check(annotated[0]["professional_count"] == 2, "annotated cards should count professionals")
    check(annotated[0]["pending_professional_count"] == 1, "annotated cards should count new names")
    check(annotated[0]["already_published_count"] == 1, "annotated cards should count represented names")
    check(annotated[0]["has_source_url"] is True, "annotated cards should mark source availability")
    check(reconciled["published_count"] == 1, "published count missing")
    check(reconciled["review_professional_count"] == 2, "review professional count missing")
    check(reconciled["claim_professional_count"] == 2, "claim professional count should keep only clear names")
    check(reconciled["pending_professional_count"] == 2, "pending names should exclude already published duplicates")
    check("Dr. Luis Pérez" in reconciled["pending_professionals"], "review-only pending person missing")
    check("Dra. Carla Ruiz" in reconciled["pending_professionals"], "claim-only pending person missing")
    check("Dra. Ana Lopez" in reconciled["already_published_detected"], "already-published detected person missing")
    check(summary["pending_professionals"] == 2, "summary should count pending names")
    check(summary["review_cards"] == 1, "summary should count review cards")
    check(summary["review_cards_with_source"] == 1, "summary should count cards with source")
    check(summary["review_cards_without_source"] == 0, "summary should count cards without source")
    check(summary["review_cards_with_pending_professionals"] == 1, "summary should count cards with pending people")
    check(summary["review_cards_already_represented"] == 0, "summary should count fully represented cards")
    check("cargar nombres al formulario" in reconciled["next_step"], "next step should route to existing review cards")
    check("# Vitalarga specialist reconciliation" in output, "title missing")
    check("Writes data: no" in output, "read-only marker missing")
    check("Clínicas medidas: 1" in output, "summary clinic count missing")
    check("Pendientes de decidir: 2" in output, "pending count line missing")
    check("Tarjetas con fuente clara: 1/1" in output, "source-card summary missing")
    check("Tarjetas con nombres nuevos: 1" in output, "new-name card summary missing")
    check("Tarjetas:" in output, "review card breakdown missing")
    check("nuevos: 1; ya en ficha: 1" in output, "card pending/already counts missing")
    check("fuente: https://clinic-a.example/equipo-medico/" in output, "review source URL missing")
    no_source_card = dict(row["review_cards"][0], source_url="")
    no_source_lines = format_review_cards(annotated_review_cards([no_source_card], set()))
    check("fuente: pendiente" in no_source_lines[0], "cards without source should be explicit")

    check(
        "preparar una propuesta revisable" in specialist_reconciliation_next_step({
            "pending_professional_count": 2,
            "review_card_count": 0,
            "claim_professional_count": 2,
        }),
        "internal-only pending names should stay in proposal mode",
    )

    captured = {}

    def fake_run_psql(sql: str, local_env: dict[str, str]) -> str:
        captured["sql"] = sql
        return json.dumps({
            "query": "Clinic A",
            "generated_at": "2026-08-31T08:40:00+00:00",
            "writes_data": False,
            "clinics": [row],
        })

    original_run_psql = load_reconciliation.__globals__["run_psql"]
    try:
        load_reconciliation.__globals__["run_psql"] = fake_run_psql
        loaded = load_reconciliation("Clinic A", 5, {})
    finally:
        load_reconciliation.__globals__["run_psql"] = original_run_psql

    sql = captured.get("sql", "")
    check(loaded["clinics"][0]["pending_professional_count"] == 2, "loaded report should reconcile rows")
    check(loaded["summary"]["pending_professionals"] == 2, "loaded report should include summary")
    check("public.review_queue" in sql, "query should read review cards")
    check("public.field_claims" in sql, "query should read internal claims")
    check("professionals.published" in sql, "query should include specialist claim paths")
    check("team.public_professionals" in sql, "query should include team specialist claim paths")
    check("source_url" in sql, "query should carry review card source context")
    check("c.status in ('published', 'preliminary')" in sql, "query should stay on visible clinics")
    print("OK specialist reconciliation: report is read-only")


if __name__ == "__main__":
    main()
