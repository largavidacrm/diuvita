#!/usr/bin/env python3
"""Checks for the read-only specialist reconciliation report."""
from __future__ import annotations

import json

from specialist_review_reconciliation import (
    clean_person_list,
    format_reconciliation,
    load_reconciliation,
    normalize_person_key,
    reconcile_row,
    specialist_reconciliation_next_step,
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
                "professionals": ["Dra. Ana Lopez", "Dr. Luis Pérez - Director médico"],
            }
        ],
        "claim_professionals": ["Dr Luis Perez", "Dra. Carla Ruiz", "Alergología Anestesiología"],
    }
    reconciled = reconcile_row(row)
    output = format_reconciliation({
        "generated_at": "2026-08-31T08:40:00+00:00",
        "query": "Clinic A",
        "writes_data": False,
        "clinics": [reconciled],
    })

    check(normalize_person_key("Dra. Ana López") == normalize_person_key("Ana Lopez"), "person keys should ignore accents and titles")
    check(clean_person_list(["Alergología Anestesiología"]) == [], "specialty menus should not become people")
    check(reconciled["published_count"] == 1, "published count missing")
    check(reconciled["review_professional_count"] == 2, "review professional count missing")
    check(reconciled["claim_professional_count"] == 2, "claim professional count should keep only clear names")
    check(reconciled["pending_professional_count"] == 2, "pending names should exclude already published duplicates")
    check("Dr. Luis Pérez" in reconciled["pending_professionals"], "review-only pending person missing")
    check("Dra. Carla Ruiz" in reconciled["pending_professionals"], "claim-only pending person missing")
    check("Dra. Ana Lopez" in reconciled["already_published_detected"], "already-published detected person missing")
    check("cargar nombres al formulario" in reconciled["next_step"], "next step should route to existing review cards")
    check("# Vitalarga specialist reconciliation" in output, "title missing")
    check("Writes data: no" in output, "read-only marker missing")
    check("Pendientes de decidir: 2" in output, "pending count line missing")
    check("Tarjetas:" in output, "review card breakdown missing")

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
    check("public.review_queue" in sql, "query should read review cards")
    check("public.field_claims" in sql, "query should read internal claims")
    check("professionals.published" in sql, "query should include specialist claim paths")
    check("team.public_professionals" in sql, "query should include team specialist claim paths")
    check("c.status in ('published', 'preliminary')" in sql, "query should stay on visible clinics")
    print("OK specialist reconciliation: report is read-only")


if __name__ == "__main__":
    main()
