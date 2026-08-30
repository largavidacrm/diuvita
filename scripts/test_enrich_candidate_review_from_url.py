#!/usr/bin/env python3
"""Checks candidate-review enrichment from secondary official URLs."""
from enrich_candidate_review_from_url import extracted_professionals, first_json_line, patched_payload


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    extraction = {
        "candidate_profile": {
            "professionals": [
                "Dra. Délia Vilá",
                "Xavier Carretero",
                "Dra. Délia Vilá",
                "Neli Martínez",
            ]
        }
    }
    payload = {
        "candidate_source_url": "https://regeneraclinic.com/longevidad",
        "candidate": {
            "name": "Regenera Clinic Medicina de la Longevidad",
            "source_url": "https://regeneraclinic.com/longevidad",
            "profesionales": ["Dr. Existing"],
        },
    }

    professionals = extracted_professionals(extraction)
    check(professionals == ["Dra. Délia Vilá", "Xavier Carretero", "Neli Martínez"], "professionals should dedupe")

    patched, summary = patched_payload(payload, extraction, "https://regeneraclinic.com/quienes-somos")
    merged = patched["candidate"]["profesionales"]
    sources = patched["candidate"]["source_urls"]

    check(summary["status"] == "patched", "payload should be patched")
    check(merged == ["Dr. Existing", "Dra. Délia Vilá", "Xavier Carretero", "Neli Martínez"], "professionals should merge")
    check(
        sources == [
            "https://regeneraclinic.com/longevidad",
            "https://regeneraclinic.com/quienes-somos",
        ],
        "sources should merge without duplicates",
    )
    check(payload["candidate"]["profesionales"] == ["Dr. Existing"], "input payload should not be mutated")
    check("warnings" in patched, "review warning should be added")
    patched_again, _ = patched_payload(patched, extraction, "https://regeneraclinic.com/quienes-somos")
    check(len(patched_again["shadow_enrichments"]) == 1, "same enrichment should not duplicate")
    check(
        first_json_line("INSERT 0 0\n{\"status\":\"updated\"}\nUPDATE 1") == {"status": "updated"},
        "psql output parser should find JSON rows",
    )
    print("OK candidate enrichment: secondary source merge")


if __name__ == "__main__":
    main()
