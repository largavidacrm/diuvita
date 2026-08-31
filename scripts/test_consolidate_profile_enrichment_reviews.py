#!/usr/bin/env python3
"""Checks for read-only consolidation of duplicate enrichment reviews."""

from consolidate_profile_enrichment_reviews import (
    build_report,
    canonical_field,
    consolidated_group,
    field_already_present,
    format_report,
    merge_fields,
    source_urls,
    split_spanish_phones,
    value_key,
)


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def sample_group():
    return {
        "clinic_id": "clinic-1",
        "clinic_slug": "sensabell",
        "clinic_name": "Sensabell",
        "city": "Valencia",
        "clinic_status": "published",
        "website": "https://sensabell.example/",
        "current_data": {
            "services": ["Medicina preventiva"],
            "telefono": "961 111 222",
        },
        "cards": [
            {
                "id": "review-1",
                "title": "Ampliar ficha: Sensabell",
                "payload": {
                    "source_url": "https://sensabell.example/longevidad/",
                    "source_urls": ["https://sensabell.example/longevidad/"],
                    "proposed_fields": {
                        "services": ["Medicina preventiva", "Nutricion"],
                        "professionals": ["Dra. Ana Lopez"],
                        "phone": "961 111 222",
                    },
                },
            },
            {
                "id": "review-2",
                "title": "Revisar extraccion shadow: Sensabell",
                "payload": {
                    "source_urls": [
                        "https://sensabell.example/equipo/",
                        "https://sensabell.example/longevidad/",
                    ],
                    "proposed_fields": {
                        "services": ["Nutricion", "Medicina del sueno"],
                        "profesionales": ["Dra. Ana Lopez", "Dr. Luis Perez"],
                        "telefono": "962 333 444",
                        "phone_fixed": "08-29679-5",
                        "locations": [
                            {
                                "address": "Calle Colon 1, 46004 Valencia",
                                "city": "Valencia",
                            },
                            {
                                "address": "Calle Colon 1, 46004 Valencia",
                                "city": "Valencia",
                            },
                        ],
                    },
                },
            },
        ],
    }


def main():
    group = sample_group()
    merged, conflicts, field_sources = merge_fields(group["cards"])
    consolidated = consolidated_group(group)
    report = build_report([group])
    output = format_report(report)

    check(canonical_field("professionals") == "profesionales", "professionals alias missing")
    check(canonical_field("phone") == "telefono", "phone alias missing")
    check(value_key("Dra. Ana López") == value_key("dra ana lopez"), "value keys should ignore accents and case")
    check(source_urls(group["cards"][0]["payload"]) == ["https://sensabell.example/longevidad/"], "source URL cleanup failed")
    check(merged["services"] == ["Medicina preventiva", "Nutricion", "Medicina del sueno"], "list fields should merge in order")
    check(merged["profesionales"] == ["Dra. Ana Lopez", "Dr. Luis Perez"], "professional aliases should merge")
    check(len(merged["locations"]) == 1, "locations should deduplicate by address and city")
    check(conflicts[0]["field"] == "telefono", "scalar conflict should be detected")
    check(conflicts[0]["variant_count"] == 2, "conflict should count variants")
    check(field_sources["profesionales"] == ["review-1", "review-2"], "field source review ids missing")
    check(field_already_present(group, "telefono", "961111222"), "profile phone comparison should ignore spacing")
    check("telefono" not in consolidated["review_fields"], "already-present scalar should not need review")
    check("services" in consolidated["review_fields"], "partially new list should need review")
    check(consolidated["already_present_fields"] == ["telefono"], "already-present field list missing")
    check(consolidated["conflict_count"] == 1, "conflict count missing")
    check(consolidated["weak_phone_fields"] == ["phone_fixed"], "weak phone field should be flagged")
    check(consolidated["source_count"] == 2, "source dedupe count missing")
    check(consolidated["next_step"] == "resolver conflictos antes de validar propuestas", "conflict next step missing")
    check(report["summary"]["groups"] == 1, "group summary missing")
    check(report["summary"]["cards"] == 2, "card summary missing")
    check(report["summary"]["groups_with_conflicts"] == 1, "conflict group summary missing")
    check("Writes data: no" in output, "read-only safety line missing")
    check("Sensabell: 2 tarjetas ->" in output, "group row missing")
    check("conflictos: Telefono principal" in output, "conflict labels missing")
    check("telefonos dudosos: Telefono fijo" in output, "weak phone label missing")
    check("ya en ficha: Telefono principal" in output, "already-present labels missing")

    clean = sample_group()
    clean["cards"][1]["payload"]["proposed_fields"]["telefono"] = "961 111 222"
    clean["cards"][1]["payload"]["proposed_fields"]["phone_fixed"] = "963 333 444"
    clean_report = build_report([clean])
    check(clean_report["groups"][0]["conflict_count"] == 0, "matching scalars should not conflict")
    check(
        clean_report["groups"][0]["next_step"] == "abrir el caso y resolver una propuesta cada vez",
        "clean groups should point to sequential review",
    )
    multi_phone_group = {
        "clinic_id": "clinic-2",
        "clinic_slug": "phone-case",
        "clinic_name": "Phone Case",
        "city": "Madrid",
        "clinic_status": "review",
        "current_data": {},
        "cards": [
            {
                "id": "review-phone",
                "title": "Ampliar ficha: Phone Case",
                "payload": {
                    "proposed_fields": {
                        "telefono": "960 05 61 65 / 695 567 297",
                    },
                },
            }
        ],
    }
    multi_phone = consolidated_group(multi_phone_group)
    check(split_spanish_phones("960 05 61 65 / 695 567 297") == ["960056165", "695567297"], "multi-phone split missing")
    check(multi_phone["merged_fields"]["telefono"] == "960056165", "primary split phone missing")
    check(multi_phone["merged_fields"]["phone_mobile"] == "695567297", "mobile split phone missing")
    check(multi_phone["weak_phone_count"] == 0, "clear split phones should not be weak")
    check(
        multi_phone["next_step"] == "abrir el caso y resolver una propuesta cada vez",
        "clear split phones should be actionable",
    )

    empty_report = build_report([])
    check("No hay mejoras duplicadas abiertas." in format_report(empty_report), "empty state missing")

    print("OK enrichment consolidation: duplicate review groups")


if __name__ == "__main__":
    main()
