#!/usr/bin/env python3
"""Checks for read-only Google link review reconciliation."""
from __future__ import annotations

import json

from google_link_review_reconciliation import (
    first_status_label,
    format_compact_reconciliation,
    format_reconciliation,
    google_link_next_step,
    load_reconciliation,
    proposed_links,
    reconcile_row,
    summarize_cards,
)


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    direct_row = {
        "id": "review-1",
        "review_type": "clinic_profile_enrichment",
        "title": "Completar enlaces Google: Clinic A",
        "priority": 60,
        "created_at": "2026-08-31T08:00:00+00:00",
        "clinic_slug": "clinic-a",
        "clinic_name": "Clinic A",
        "city": "Madrid",
        "clinic_status": "published",
        "payload": {
            "source_url": "https://clinic-a.example/contacto/",
            "proposed_fields": {
                "maps_url": "https://www.google.com/maps/place/Clinic+A/",
                "google_reviews_url": "https://www.google.com/maps/place/Clinic+A/reviews",
                "locations": [
                    {
                        "name": "Madrid",
                        "maps_url": "https://www.google.com/maps/place/Clinic+A/",
                        "google_reviews_url": "https://www.google.com/maps/place/Clinic+A/reviews",
                    }
                ],
            },
        },
    }
    unsafe_row = {
        **direct_row,
        "id": "review-2",
        "title": "Completar enlaces Google: Clinic B",
        "clinic_name": "Clinic B",
        "payload": {
            "proposed_fields": {
                "maps_url": "https://www.google.com/maps/place/Calle+Serrano+100,+Madrid",
                "google_reviews_url": "https://www.google.com/maps/place/Clinic+B/reviews",
            }
        },
    }
    review_only_row = {
        **direct_row,
        "id": "review-3",
        "title": "Completar valoraciones: Clinic C",
        "clinic_name": "Clinic C",
        "payload": {"proposed_fields": {"google_reviews_url": "https://www.google.com/maps/place/Clinic+C/reviews"}},
    }

    links = proposed_links(direct_row["payload"])
    check(links["maps"] == ["https://www.google.com/maps/place/Clinic+A/"], "Maps links should be deduped")
    check(links["reviews"] == ["https://www.google.com/maps/place/Clinic+A/reviews"], "review links should be deduped")

    direct = reconcile_row(direct_row)
    unsafe = reconcile_row(unsafe_row)
    review_only = reconcile_row(review_only_row)
    summary = summarize_cards([direct, unsafe, review_only])
    output = format_reconciliation({
        "query": "",
        "generated_at": "2026-08-31T08:40:00+00:00",
        "writes_data": False,
        "summary": summary,
        "review_cards": [direct, unsafe, review_only],
    })
    compact_output = format_compact_reconciliation({
        "query": "",
        "generated_at": "2026-08-31T08:40:00+00:00",
        "writes_data": False,
        "summary": summary,
        "review_cards": [direct, unsafe, review_only],
    })

    check(summary == {
        "review_cards": 3,
        "cards_with_direct_maps": 1,
        "cards_with_unsafe_maps": 1,
        "cards_with_review_links": 3,
        "manual_decision_items": 5,
    }, "summary counts should classify Google review cards")
    check(direct["direct_map_count"] == 1, "direct Maps count missing")
    check(direct["unsafe_map_count"] == 0, "direct Maps should not be unsafe")
    check(direct["manual_decision_count"] == 2, "direct card should expose Maps and reviews decisions")
    check(
        direct["manual_decision_sequence"][1]["depends_on"] == "maps_url",
        "Google reviews decision should depend on the main Maps profile",
    )
    check(direct["fields_to_review"] == ["Google Maps", "Valoraciones Google"], "decision fields missing")
    check(direct["manual_decision_items"][0]["manual_decision"] == "confirm_real_clinic_profile", "direct Maps decision missing")
    check(direct["manual_decision_items"][0]["safe_to_auto_publish"] is False, "direct Maps should still require human review")
    check("confirmar que es la ficha real" in direct["next_step"], "direct Maps next step missing")
    check(unsafe["map_status_counts"]["street_address"] == 1, "street-address Maps status missing")
    check(unsafe["manual_decision_items"][0]["manual_decision"] == "reject_or_replace_with_real_profile", "unsafe Maps decision missing")
    check("no guardar ese Maps" in unsafe["next_step"], "unsafe Maps next step missing")
    check(review_only["review_link_count"] == 1, "review-only link count missing")
    check(review_only["fields_to_review"] == ["Valoraciones Google"], "review-only decision field missing")
    check("completar primero el perfil principal" in review_only["next_step"], "review-only next step missing")
    check("parece perfil directo de clínica: 1" in first_status_label(direct["map_status_counts"]), "direct status label missing")
    check("parece dirección suelta; no guardar: 1" in first_status_label(unsafe["map_status_counts"]), "unsafe status label missing")
    check("# Vitalarga Google link review reconciliation" in output, "title missing")
    check("Writes data: no" in output, "read-only marker missing")
    check("Tarjetas: 3" in output, "summary card count missing")
    check("Estado Maps: parece perfil directo de clínica: 1" in output, "direct output status missing")
    check("Estado Maps: parece dirección suelta; no guardar: 1" in output, "unsafe output status missing")
    check("Decisiones manuales: Google Maps, Valoraciones Google" in output, "decision fields should be printed")
    check("Orden sugerido: 1. Google Maps -> 2. Valoraciones Google tras Google Maps" in output, "decision sequence should be printed")
    check("Con perfil directo: 1" in compact_output, "compact direct count missing")
    check("Con Maps dudoso: 1" in compact_output, "compact unsafe count missing")
    check("Con valoraciones: 3" in compact_output, "compact review count missing")
    check("Decisiones manuales: 5" in compact_output, "compact decision count missing")
    check("campos: Google Maps, Valoraciones Google" in compact_output, "compact field labels missing")
    check("Clinic A: Completar enlaces Google: Clinic A" in compact_output, "compact card label missing")
    check("Nota: salida compacta sin URLs" in compact_output, "compact privacy note missing")
    check("https://www.google.com/maps" not in compact_output, "compact output should not print Google URLs")

    captured = {}

    def fake_run_psql(sql: str, local_env: dict[str, str]) -> str:
        captured["sql"] = sql
        return json.dumps({
            "query": "Clinic",
            "generated_at": "2026-08-31T08:40:00+00:00",
            "writes_data": False,
            "review_cards": [direct_row, unsafe_row],
        })

    original_run_psql = load_reconciliation.__globals__["run_psql"]
    try:
        load_reconciliation.__globals__["run_psql"] = fake_run_psql
        loaded = load_reconciliation("Clinic", 5, {})
    finally:
        load_reconciliation.__globals__["run_psql"] = original_run_psql

    sql = captured.get("sql", "")
    check(loaded["review_cards"][0]["direct_map_count"] == 1, "loaded report should reconcile rows")
    check(loaded["summary"]["review_cards"] == 2, "loaded report should include summary")
    check("public.review_queue" in sql, "query should read review cards")
    check("rq.status = 'open'" in sql, "query should only inspect open reviews")
    check("maps_url" in sql and "google_reviews_url" in sql, "query should find Google fields")
    check("rq.payload" in sql, "query should load payload for local extraction")
    check("rq.title ilike" in sql, "query should allow review title search")
    check("limit 5" in sql, "query should cap result size")

    check(
        "sin enlace útil" in google_link_next_step({"maps_urls": [], "review_urls": []}),
        "empty link cards should stay pending",
    )
    print("OK Google link reconciliation: report is read-only")


if __name__ == "__main__":
    main()
