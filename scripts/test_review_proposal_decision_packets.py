#!/usr/bin/env python3
"""Checks read-only single-decision packets for future LLM assistance."""

from pathlib import Path

from review_proposal_decision_packets import build_report, decision_packet


ROOT = Path(__file__).resolve().parents[1]


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def sample_enrichment_row():
    return {
        "id": "review-1",
        "title": "Revisar extracción shadow: Unidad de Longevidad IMDA",
        "review_type": "clinic_profile_enrichment",
        "priority": 60,
        "created_at": "2026-08-31T12:47:16+00:00",
        "payload": {
            "source_url": "https://imda.example/contacto",
            "warnings": ["Contrastar https://imda.example/equipo con persona@example.com y +34 600 111 222."],
            "proposed_fields": {
                "maps_url": "https://www.google.com/maps/search/Unidad+de+Longevidad+IMDA",
                "telefono": "ABC-123",
                "profesionales": ["Dra. Example"],
            },
        },
        "clinic": {
            "id": "clinic-1",
            "slug": "unidad-de-longevidad-imda",
            "display_name": "Unidad de Longevidad IMDA",
            "city": "Madrid",
            "country": "España",
            "status": "preliminary",
            "website": "https://imda.example",
            "current_data": {
                "telefono": "916325659",
                "profesionales": [],
            },
        },
    }


def main():
    safe_packet = decision_packet(sample_enrichment_row())
    check(safe_packet["schema_version"] == "review_decision_packet.v1", "schema version missing")
    check(safe_packet["decision_scope"] == "single_review_item", "packet should represent one review card")
    check(safe_packet["allowed_actions"] == ["approve", "reject", "modify"], "decision actions missing")
    check(safe_packet["automation_contract"]["write_policy"] == "read_only_packet", "LLM contract should stay read-only")
    check(safe_packet["proposal_type"] == "Mejora de ficha", "proposal type label missing")
    check(safe_packet["clinic"]["name"] == "Unidad de Longevidad IMDA", "clinic identity missing")
    check(len(safe_packet["proposed_change"]) == 3, "proposed field count missing")
    check(safe_packet["proposed_change"][0]["label"] == "Google Maps", "field ordering should make Maps visible")
    check(
        [item["key"] for item in safe_packet["editable_fields"]] == ["maps_url", "profesionales", "telefono"],
        "modify should be limited to proposed fields",
    )
    check(
        any(item["label"] == "Teléfono principal" for item in safe_packet["current_relevant"]),
        "current relevant field missing",
    )
    check("value" not in safe_packet["proposed_change"][0]["proposed"], "safe default should omit proposed values")
    check("value" not in safe_packet["current_relevant"][0]["current"], "safe default should omit current values")
    check(safe_packet["evidence"][0]["host"] == "imda.example", "safe evidence should keep host")
    check("value" not in safe_packet["evidence"][0], "safe default should omit evidence URLs")
    check(
        "Google Maps debe ser el perfil real de la clínica" in " ".join(safe_packet["warnings"]),
        "weak Maps warning missing",
    )
    check(
        "Teléfono dudoso" in " ".join(safe_packet["warnings"]),
        "weak phone warning missing",
    )
    check(
        "Especialistas requiere revisión humana antes de uso público." in safe_packet["warnings"],
        "specialist human-review warning missing",
    )
    joined_safe_warnings = " ".join(safe_packet["warnings"])
    check("https://imda.example/equipo" not in joined_safe_warnings, "safe warnings should redact full URLs")
    check("persona@example.com" not in joined_safe_warnings, "safe warnings should redact email addresses")
    check("+34 600 111 222" not in joined_safe_warnings, "safe warnings should redact phone numbers")

    valued_report = build_report([sample_enrichment_row()], include_values=True)
    valued_packet = valued_report["packets"][0]
    check(valued_report["writes_data"] is False, "packet report must be read-only")
    check(valued_report["decision_scope"] == "one_card_one_decision", "report scope missing")
    check(
        valued_packet["proposed_change"][0]["proposed"]["value"].startswith("https://www.google.com/maps/search/"),
        "explicit value mode should include proposed values",
    )
    check(
        valued_packet["evidence"][0]["value"] == "https://imda.example/contacto",
        "explicit value mode should include evidence URLs",
    )
    check(
        "persona@example.com" in " ".join(valued_packet["warnings"]),
        "explicit value mode should preserve local warning detail",
    )

    claim_packet = decision_packet({
        "id": "claim-1",
        "title": "Reclamar ficha: Example Clinic",
        "review_type": "clinic_claim_request",
        "payload": {
            "clinic_name": "Example Clinic",
            "requester_name": "Persona",
            "requester_email": "persona@example.com",
            "message": "Quiero cambiar datos.",
        },
        "clinic": {"display_name": "Example Clinic", "status": "published"},
    })
    check(claim_packet["proposed_change"][0]["synthetic"], "claim request should be synthetic")
    check(not claim_packet["current_relevant"], "synthetic claim should not pretend to edit fields")
    check(
        "no confirma identidad" in " ".join(claim_packet["warnings"]),
        "claim-request safety warning missing",
    )

    candidate_packet = decision_packet({
        "id": "candidate-1",
        "title": "Nueva candidata",
        "review_type": "candidate_clinic",
        "payload": {
            "candidate": {
                "name": "Longevity Example",
                "website": "https://longevity.example",
                "city": "Madrid",
                "country": "España",
                "professionals": ["Dra. Example"],
            }
        },
        "clinic": {},
    })
    check(
        any(item["key"] == "profesionales" for item in candidate_packet["proposed_change"]),
        "candidate fallback should keep professionals proposals",
    )

    source = (ROOT / "scripts" / "review_proposal_decision_packets.py").read_text(encoding="utf-8")
    lowered = source.lower()
    check("from public.review_queue rq" in source, "script should read review_queue")
    check("left join public.clinics c" in source, "script should attach current clinic data")
    for forbidden in ["insert into", " update ", " delete from", "admin_update_clinic", "admin_resolve_review_item"]:
        check(forbidden not in lowered, f"packet builder should not write data: {forbidden}")

    print("OK review proposal packets: LLM-ready decisions stay read-only")


if __name__ == "__main__":
    main()
