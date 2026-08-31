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
            "from_review_id": "quality-previous",
            "human_supplied_source": True,
            "requested_fields": ["profesionales", "telefono"],
            "requested_field_labels": ["Especialistas publicados", "Teléfono principal"],
            "primary_requested_fields": ["profesionales"],
            "primary_requested_field_labels": ["Especialistas publicados"],
            "target_scope": "primary_target_first",
            "ui_route": "manual_review_banner_source_handoff",
            "allowed_output": "review_queue_proposal_only",
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


def sample_quality_packet():
    return decision_packet({
        "id": "quality-1",
        "title": "Completar ficha: Tiara Health",
        "review_type": "clinic_quality_audit",
        "payload": {
            "issues": [
                {"code": "missing_professionals", "label": "Faltan especialistas publicados"},
            ],
        },
        "clinic": {
            "id": "clinic-tiara",
            "slug": "tiara-health",
            "display_name": "Tiara Health",
            "city": "Marbella",
            "country": "España",
            "status": "preliminary",
            "current_data": {},
        },
    })


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
    source_context = prompt["packet_digest"]["source_job_context"]
    check(source_context["human_supplied_source"] is True, "prompt digest should keep Daniel-supplied source signal")
    check(source_context["source_host"] == "imda.example", "prompt digest should keep source host")
    check(source_context["ui_route"] == "manual_review_banner_source_handoff", "prompt digest should keep source UI route")
    check(source_context["target_scope"] == "primary_target_first", "prompt digest should keep source scope")
    check(source_context["primary_requested_fields"] == ["profesionales"], "prompt digest should keep primary requested source fields")
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

    quality_prompt = build_prompt(sample_quality_packet())
    check(
        quality_prompt["packet_digest"]["manual_review_targets"] == [{"key": "profesionales", "label": "Especialistas publicados"}],
        "prompt digest should keep manual review targets",
    )
    check(
        quality_prompt["packet_digest"]["display_title"] == "Revisión manual: Tiara Health",
        "prompt digest should keep the readable manual review title",
    )
    check(
        quality_prompt["packet_digest"]["manual_review_context"]["operator_action"]
        == "open_admin_target_edit_field_then_save_clinic",
        "prompt digest should keep the manual operator route",
    )
    check(
        quality_prompt["packet_digest"]["manual_review_context"]["source_handoff"]["target_scope"]
        == "primary_target_first",
        "prompt digest should keep the scoped source handoff",
    )
    check(
        quality_prompt["packet_digest"]["source_job_request"]["ui_route"] == "manual_review_banner_source_handoff"
        and quality_prompt["packet_digest"]["source_job_request"]["primary_requested_fields"] == ["profesionales"],
        "prompt digest should keep the primary source-job target",
    )
    check(
        quality_prompt["packet_digest"]["manual_review_context"]["llm_boundary"]
        == "do_not_invent_values_or_write_field_changes",
        "prompt digest should keep the no-invention boundary",
    )
    check(
        quality_prompt["expected_response_schema"]["properties"]["manual_review_target_key"]["enum"] == ["profesionales"],
        "prompt schema should limit manual review targets",
    )
    check(
        "manual_review_targets" in quality_prompt["messages"][1]["content"],
        "safe prompt should include manual target metadata",
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
