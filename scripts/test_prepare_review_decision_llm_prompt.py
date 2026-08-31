#!/usr/bin/env python3
"""Checks that future LLM prompts preserve the one-decision safety contract."""
from pathlib import Path

from prepare_review_decision_llm_prompt import build_prompt
from review_proposal_decision_packets import decision_packet


ROOT = Path(__file__).resolve().parents[1]


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def sample_packet(include_values=False):
    return decision_packet({
        "id": "review-1",
        "title": "Revisar extracción shadow: Unidad de Longevidad IMDA",
        "review_type": "clinic_profile_enrichment",
        "priority": 60,
        "payload": {
            "source_url": "https://imda.example/contacto",
            "warnings": ["Contrastar https://imda.example/equipo con persona@example.com y +34 600 111 222."],
            "proposed_fields": {
                "telefono": "916 000 000",
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
            "current_data": {"telefono": "915 111 111"},
        },
    }, include_values=include_values)


def main():
    full_packet = sample_packet(include_values=True)
    prompt = build_prompt(full_packet)
    dumped = str(prompt)
    check(prompt["schema_version"] == "review_decision_llm_prompt.v1", "prompt schema version missing")
    check(prompt["safe_default"] is True, "prompt should be safe by default")
    check(prompt["human_required"] is True, "prompt must keep human gate")
    check(prompt["write_policy"] == "no_writes", "prompt should not allow writes")
    check(prompt["validation_required"] == "scripts/validate_review_decision_suggestion.py", "validator link missing")
    check(prompt["packet_digest"]["review_id"] == "review-1", "packet digest review id missing")
    check(prompt["packet_digest"]["field_count"] == 2, "packet digest field count missing")
    check(prompt["messages"][0]["role"] == "system", "system message missing")
    check("No publicas" in prompt["messages"][0]["content"], "system safety instruction missing")
    check("Responde solo JSON" in prompt["messages"][0]["content"], "JSON-only instruction missing")
    check("https://imda.example/contacto" not in dumped, "safe prompt should remove full evidence URLs")
    check("persona@example.com" not in dumped, "safe prompt should redact emails")
    check("+34 600 111 222" not in dumped, "safe prompt should redact phones")
    check("'value':" not in dumped and '"value":' not in dumped, "safe prompt should omit raw value keys")

    schema = prompt["expected_response_schema"]
    check(schema["required"] == ["review_id", "action", "reason"], "response schema required fields missing")
    check(schema["properties"]["action"]["enum"] == ["approve", "reject", "modify"], "action enum missing")
    check(
        schema["properties"]["field_changes"]["propertyNames"]["enum"] == ["profesionales", "telefono"],
        "field_changes should be limited to editable fields",
    )

    full_prompt = build_prompt(full_packet, allow_full_values=True)
    full_dumped = str(full_prompt)
    check(full_prompt["safe_default"] is False, "explicit full prompt should mark safety mode")
    check("https://imda.example/contacto" in full_dumped, "explicit full prompt should keep values")
    check('"value":' in full_prompt["messages"][1]["content"], "explicit full prompt should include value keys")

    source = (ROOT / "scripts" / "prepare_review_decision_llm_prompt.py").read_text(encoding="utf-8")
    check("run_psql" not in source, "prompt builder should not connect to Supabase")
    check("load_env_file" not in source, "prompt builder should not read credentials")
    check("admin_update_clinic" not in source, "prompt builder should not contain write hooks")
    print("OK review LLM prompt: one-decision prompts stay safe")


if __name__ == "__main__":
    main()
