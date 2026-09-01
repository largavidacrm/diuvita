#!/usr/bin/env python3
"""Checks that future LLM prompts preserve the one-decision safety contract."""
from pathlib import Path

from prepare_review_decision_llm_prompt import build_prompt, require_llm_ready
from review_proposal_decision_packets import decision_packet


ROOT = Path(__file__).resolve().parents[1]


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def exits_with_message(func, *args):
    try:
        func(*args)
    except SystemExit as exc:
        return str(exc)
    return ""


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
            "operator_requested_field_keys": ["profesionales", "telefono"],
            "operator_requested_field_labels": ["Especialistas publicados", "Teléfono principal"],
            "operator_requested_field_summary": "especialistas publicados, teléfono principal",
            "target_scope": "primary_target_first",
            "ui_route": "manual_review_banner_source_handoff",
            "allowed_output": "review_queue_proposal_only",
            "llm_boundary": "respect_source_job_context_scope",
            "proposed_fields": {
                "maps_url": "https://www.google.com/maps/search/Unidad+de+Longevidad+IMDA",
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


def sample_reviews_packet():
    return decision_packet({
        "id": "reviews-1",
        "title": "Revisar valoraciones Google: Clinic",
        "review_type": "clinic_profile_enrichment",
        "payload": {
            "source_url": "https://clinic.example/contacto",
            "proposed_fields": {
                "google_reviews_url": "https://www.google.com/maps/place/Clinic/reviews",
            },
        },
        "clinic": {"display_name": "Clinic", "current_data": {}},
    }, include_values=True)


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
    check(prompt["packet_digest"]["field_count"] == 3, "packet digest field count missing")
    maps_digest = prompt["packet_digest"]["fields"][0]["google_maps_review"]
    check(maps_digest["overall_status"] == "needs_correction_before_approval", "prompt digest should keep Maps review status")
    check(maps_digest["safe_to_auto_publish"] is False, "prompt digest should keep Maps human gate")
    source_context = prompt["packet_digest"]["source_job_context"]
    check(source_context["human_supplied_source"] is True, "prompt digest should keep Daniel-supplied source signal")
    check(source_context["source_host"] == "imda.example", "prompt digest should keep source host")
    check(source_context["ui_route"] == "manual_review_banner_source_handoff", "prompt digest should keep source UI route")
    check(source_context["target_scope"] == "primary_target_first", "prompt digest should keep source scope")
    check(source_context["primary_requested_fields"] == ["profesionales"], "prompt digest should keep primary requested source fields")
    check(source_context["requested_field_labels"] == ["Especialistas publicados", "Teléfono principal"], "prompt digest should keep source field labels")
    check(source_context["primary_requested_field_labels"] == ["Especialistas publicados"], "prompt digest should keep primary source field labels")
    check(source_context["operator_requested_field_keys"] == ["profesionales", "telefono"], "prompt digest should keep operator-requested fields")
    check(
        source_context["operator_requested_field_summary"] == "especialistas publicados, teléfono principal",
        "prompt digest should keep operator field summary",
    )
    check(source_context["llm_boundary"] == "respect_source_job_context_scope", "prompt digest should keep LLM boundary")
    source_origin = prompt["packet_digest"]["source_origin_status"]
    check(source_origin["status"] == "context_ready", "prompt digest should keep source origin status")
    check(source_origin["source_host"] == "imda.example", "prompt digest should keep source origin host")
    manual_profile = prompt["packet_digest"]["manual_profile_edit_context"]
    check(manual_profile["available"] is True, "prompt digest should expose side-panel edit availability")
    check(manual_profile["ui_label"] == "Editar ficha", "prompt digest should keep side-panel edit label")
    check(manual_profile["human_only"] is True, "prompt digest should mark side-panel edits human-only")
    check(manual_profile["write_policy"] == "human_decision_only", "prompt digest side-panel write policy missing")
    check(manual_profile["allowed_actions_to_persist"] == ["approve", "modify"], "prompt digest persistence actions missing")
    check(manual_profile["reject_discards"] is True, "prompt digest should say reject discards manual edits")
    check(manual_profile["safe_to_auto_publish"] is False, "prompt digest should keep manual edits non-publishable")
    check(
        any(item["key"] == "summary" and item["review_input_id"] == "reviewClinicEditSummary" for item in manual_profile["fields"]),
        "prompt digest should include editable side-panel clinic fields",
    )
    check(
        any(item["key"] == "internal_contact" and item["review_input_id"] == "reviewClinicEditInternalContactName" for item in manual_profile["fields"]),
        "prompt digest should include the private internal-contact side-panel field",
    )
    check("value" not in str(manual_profile), "prompt digest should not expose side-panel raw values")
    check(prompt["messages"][0]["role"] == "system", "system message missing")
    check("No publicas" in prompt["messages"][0]["content"], "system safety instruction missing")
    check("manual_profile_edit_context" in prompt["messages"][0]["content"], "system prompt should bound side-panel context")
    check("Responde solo JSON" in prompt["messages"][0]["content"], "JSON-only instruction missing")
    check("https://imda.example/contacto" not in dumped, "safe prompt should remove full evidence URLs")
    check("persona@example.com" not in dumped, "safe prompt should redact emails")
    check("+34 600 111 222" not in dumped, "safe prompt should redact phones")
    check("'value':" not in dumped and '"value":' not in dumped, "safe prompt should omit raw value keys")

    schema = prompt["expected_response_schema"]
    check(schema["required"] == ["review_id", "action", "reason"], "response schema required fields missing")
    check(schema["properties"]["action"]["enum"] == ["approve", "reject", "modify"], "action enum missing")
    check(
        schema["properties"]["field_changes"]["propertyNames"]["enum"] == ["maps_url", "profesionales", "telefono"],
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
        quality_prompt["packet_digest"]["manual_review_context"]["after_save"]
        == "resolve_current_review_then_return_to_review_list",
        "prompt digest should keep return-to-list behavior",
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

    reviews_prompt = build_prompt(sample_reviews_packet())
    reviews_field = reviews_prompt["packet_digest"]["fields"][0]["google_reviews_review"]
    check(
        reviews_field["approval_dependency"]["satisfied"] is False,
        "prompt digest should keep missing Google Reviews dependency",
    )
    check(
        reviews_prompt["packet_digest"]["source_origin_status"]["status"] == "source_without_context",
        "prompt digest should warn about source-only cards without operator context",
    )
    reviews_dumped = str(reviews_prompt)
    check("https://clinic.example/contacto" not in reviews_dumped, "safe reviews prompt should redact source URLs")
    require_llm_ready(full_packet)
    blocked_message = exits_with_message(require_llm_ready, sample_reviews_packet())
    check("not LLM-ready" in blocked_message, "strict prompt mode should block source-only packets")

    full_prompt = build_prompt(full_packet, allow_full_values=True)
    full_dumped = str(full_prompt)
    check(full_prompt["safe_default"] is False, "explicit full prompt should mark safety mode")
    check("https://imda.example/contacto" in full_dumped, "explicit full prompt should keep values")
    check('"value":' in full_prompt["messages"][1]["content"], "explicit full prompt should include value keys")

    source = (ROOT / "scripts" / "prepare_review_decision_llm_prompt.py").read_text(encoding="utf-8")
    check("--require-llm-ready" in source, "strict LLM-ready CLI flag missing")
    check("run_psql" not in source, "prompt builder should not connect to Supabase")
    check("load_env_file" not in source, "prompt builder should not read credentials")
    check("admin_update_clinic" not in source, "prompt builder should not contain write hooks")
    print("OK review LLM prompt: one-decision prompts stay safe")


if __name__ == "__main__":
    main()
