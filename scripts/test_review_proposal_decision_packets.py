#!/usr/bin/env python3
"""Checks read-only single-decision packets for future LLM assistance."""

from pathlib import Path

from review_proposal_decision_packets import (
    build_report,
    decision_packet,
    packet_is_llm_ready,
    packet_llm_readiness_status,
)


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
            "operator_intent": "Daniel indica que esta URL oficial contiene especialistas y contacto.",
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


def sample_quality_audit_row():
    return {
        "id": "quality-1",
        "title": "Completar ficha: Tiara Health",
        "review_type": "clinic_quality_audit",
        "priority": 85,
        "created_at": "2026-08-31T12:47:16+00:00",
        "payload": {
            "issues": [
                {"code": "missing_professionals", "label": "Faltan especialistas publicados"},
                {"code": "missing_contact", "label": "Falta email o teléfono"},
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
    }


def sample_unsourced_specialist_row():
    return {
        "id": "specialist-source-1",
        "title": "Revisar especialistas: Tiara Health",
        "review_type": "clinic_profile_enrichment",
        "priority": 85,
        "created_at": "2026-08-31T12:47:16+00:00",
        "payload": {
            "proposed_fields": {
                "profesionales": ["Dra. Example", "Dr. Example"],
            },
        },
        "clinic": {
            "id": "clinic-tiara",
            "slug": "tiara-health",
            "display_name": "Tiara Health",
            "city": "Marbella",
            "country": "España",
            "status": "preliminary",
            "current_data": {"profesionales": []},
        },
    }


def sample_dirty_specialist_row():
    return {
        "id": "dirty-specialist-1",
        "title": "Revisar especialistas: Eternal Group",
        "review_type": "clinic_profile_enrichment",
        "priority": 85,
        "created_at": "2026-09-01T10:47:16+00:00",
        "payload": {
            "source_url": "https://eternal.example/equipo",
            "proposed_fields": {
                "profesionales": [
                    "Dr. Ibáñez European Society Calorimetry Respirometry ESCAR",
                    "Infantil Psiquiatría CARLA BUIXEDA",
                    "Dra. Laura Muntaner",
                    "Dr. Miguel Ángel Palos COLABORADORES Aviso Legal",
                ],
            },
        },
        "clinic": {
            "id": "clinic-eternal",
            "slug": "eternal-group",
            "display_name": "Eternal Group",
            "city": "Madrid",
            "country": "España",
            "status": "draft",
            "current_data": {"profesionales": []},
        },
    }


def main():
    safe_packet = decision_packet(sample_enrichment_row())
    check(safe_packet["schema_version"] == "review_decision_packet.v1", "schema version missing")
    check(safe_packet["decision_scope"] == "single_review_item", "packet should represent one review card")
    check(safe_packet["allowed_actions"] == ["approve", "reject", "modify"], "decision actions missing")
    check(safe_packet["automation_contract"]["write_policy"] == "read_only_packet", "LLM contract should stay read-only")
    check(
        safe_packet["automation_contract"]["after_decision"] == "resolve_current_review_then_return_to_review_list",
        "review decisions should return Daniel to the list",
    )
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
    profile_context = safe_packet["manual_profile_edit_context"]
    check(profile_context["ui_label"] == "Editar ficha", "side-panel edit label missing")
    check(profile_context["human_only"] is True, "side-panel edits must stay human-only")
    check(profile_context["write_policy"] == "human_decision_only", "side-panel write policy missing")
    check(profile_context["allowed_actions_to_persist"] == ["approve", "modify"], "side-panel persistence actions missing")
    check(profile_context["reject_discards"] is True, "reject should discard side-panel edits")
    check(profile_context["safe_to_auto_publish"] is False, "side-panel edits should never auto-publish")
    check(profile_context["field_count"] >= 20, "side-panel editable field count missing")
    profile_keys = [item["key"] for item in profile_context["fields"]]
    check(
        all(key in profile_keys for key in ["display_name", "summary", "website", "profesionales", "telefono", "internal_contact"]),
        "side-panel editable fields should include core clinic fields",
    )
    check("value" not in profile_context["fields"][0]["current"], "safe side-panel context should omit raw values")
    check("value" not in safe_packet["proposed_change"][0]["proposed"], "safe default should omit proposed values")
    maps_context = safe_packet["proposed_change"][0]["google_maps_review"]
    check(maps_context["kind"] == "google_maps_profile_link", "Maps review context kind missing")
    check(maps_context["overall_status"] == "needs_correction_before_approval", "unsafe Maps status should be explicit")
    check(maps_context["status_counts"]["search_or_route"] == 1, "Maps status counts should identify search URLs")
    check(maps_context["safe_to_auto_publish"] is False, "Maps proposals should never become auto-publishable")
    reviews_packet = decision_packet({
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
    })
    reviews_context = reviews_packet["proposed_change"][0]["google_reviews_review"]
    check(reviews_context["kind"] == "google_reviews_link", "Google reviews context kind missing")
    check(
        reviews_context["overall_status"] == "reviews_link_needs_main_profile_confirmation",
        "Google reviews links should depend on the main profile confirmation",
    )
    check(
        reviews_context["approval_dependency"]["satisfied"] is False,
        "Google reviews should expose a missing Maps dependency",
    )
    check(
        reviews_context["next_step"] == "confirm_main_google_maps_profile_before_approval",
        "Google reviews without Maps should ask for the main profile first",
    )
    check(reviews_context["safe_to_auto_publish"] is False, "Google reviews should stay human-gated")
    reviews_origin = reviews_packet["source_origin_status"]
    check(reviews_origin["status"] == "source_without_context", "legacy source-only cards should expose missing source context")
    check(reviews_origin["source_host"] == "clinic.example", "legacy source context should keep only the host by default")
    check(reviews_origin["prompt_policy"] == "bounded_legacy_source_only", "legacy source policy should stay bounded")
    check(reviews_origin["target_scope"] == "explicit_proposed_fields_only", "legacy source scope should only cover proposed fields")
    check(reviews_origin["write_policy"] == "read_only_packet", "legacy source policy should stay read-only")
    check(
        reviews_origin["llm_boundary"] == "do_not_infer_operator_intent_or_expand_beyond_proposed_fields",
        "legacy source boundary should prevent broadening",
    )
    check("source_url" not in reviews_origin, "legacy source context should not expose full URL by default")
    check(packet_is_llm_ready(safe_packet) is True, "context-ready packets should be available for LLM help")
    check(packet_llm_readiness_status(safe_packet) == "strict_prompt_ready", "context-ready packet status missing")
    check(packet_is_llm_ready(reviews_packet) is True, "legacy source packets with explicit fields should be LLM-ready with limits")
    check(packet_llm_readiness_status(reviews_packet) == "legacy_source_prompt_ready", "legacy source status missing")
    reviews_with_maps_packet = decision_packet({
        "id": "reviews-2",
        "title": "Revisar valoraciones Google: Clinic",
        "review_type": "clinic_profile_enrichment",
        "payload": {
            "source_url": "https://clinic.example/contacto",
            "proposed_fields": {
                "google_reviews_url": "https://www.google.com/maps/place/Clinic/reviews",
            },
        },
        "clinic": {
            "display_name": "Clinic",
            "current_data": {"maps_url": "https://www.google.com/maps/place/Clinic/"},
        },
    })
    reviews_with_maps_context = reviews_with_maps_packet["proposed_change"][0]["google_reviews_review"]
    check(
        reviews_with_maps_context["approval_dependency"]["satisfied"] is True,
        "Google reviews should detect an existing direct Maps profile",
    )
    check(
        reviews_with_maps_context["next_step"] == "confirm_reviews_match_confirmed_google_maps_profile",
        "Google reviews with Maps should ask Daniel to match the same profile",
    )
    check("value" not in safe_packet["current_relevant"][0]["current"], "safe default should omit current values")
    check(safe_packet["evidence"][0]["host"] == "imda.example", "safe evidence should keep host")
    check("value" not in safe_packet["evidence"][0], "safe default should omit evidence URLs")
    source_context = safe_packet["source_job_context"]
    check(source_context["mode"] == "operator_supplied_source_review", "source job context mode missing")
    check(source_context["human_supplied_source"] is True, "source job context should mark Daniel-supplied sources")
    check(source_context["source_host"] == "imda.example", "source job context should keep source host")
    check(source_context["requested_fields"] == ["profesionales", "telefono"], "source job context should keep requested fields")
    check(source_context["primary_requested_fields"] == ["profesionales"], "source job context should keep primary requested fields")
    check(
        source_context["operator_requested_field_summary"] == "especialistas publicados, teléfono principal",
        "source job context should keep Daniel's field summary",
    )
    check(source_context["target_scope"] == "primary_target_first", "source job context should keep primary target scope")
    check(source_context["ui_route"] == "manual_review_banner_source_handoff", "source job context should keep UI route")
    check(source_context["allowed_output"] == "review_queue_proposal_only", "source job context should keep proposal-only output")
    check(source_context["llm_boundary"] == "respect_source_job_context_scope", "source job context should keep LLM boundary")
    check("source_url" not in source_context, "safe source job context should omit full source URL")
    origin_status = safe_packet["source_origin_status"]
    check(origin_status["status"] == "context_ready", "source origin should detect ready operator context")
    check(origin_status["source_host"] == "imda.example", "source origin should keep the safe source host")
    check(origin_status["llm_boundary"] == "respect_source_job_context_scope", "source origin should keep LLM scope")
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
        valued_packet["source_job_context"]["source_url"] == "https://imda.example/contacto",
        "explicit value mode should include source-job URL",
    )
    check(
        valued_packet["source_origin_status"]["source_url"] == "https://imda.example/contacto",
        "explicit value mode should include source origin URL",
    )
    valued_phone = [
        item for item in valued_packet["manual_profile_edit_context"]["fields"]
        if item["key"] == "telefono"
    ][0]
    check(
        valued_phone["current"]["value"] == "916325659",
        "explicit value mode should include manual profile current values",
    )
    check(
        "persona@example.com" in " ".join(valued_packet["warnings"]),
        "explicit value mode should preserve local warning detail",
    )

    quality_packet = decision_packet(sample_quality_audit_row())
    check(quality_packet["proposal_type"] == "Revisión manual", "quality proposal type should be manual review")
    check(
        quality_packet["display_title"] == "Revisión manual: Tiara Health · Faltan especialistas publicados",
        "quality title should name the active manual field",
    )
    check(not quality_packet["editable_fields"], "quality audit issues should not become direct LLM-editable fields")
    check(packet_is_llm_ready(quality_packet) is True, "manual target packets should allow LLM navigation help")
    check(
        packet_llm_readiness_status(quality_packet) == "manual_target_prompt_ready",
        "manual target readiness status missing",
    )
    check(
        quality_packet["proposed_change"][0]["manual_review_target"]["key"] == "profesionales",
        "professional quality issue should point to the manual specialists field",
    )
    check(
        [target["key"] for target in quality_packet["manual_review_targets"]] == ["profesionales", "email", "telefono"],
        "quality audit should expose safe manual review targets",
    )
    check(
        quality_packet["source_job_request"]["requested_fields"] == ["profesionales", "email", "telefono"],
        "quality audit packet should describe bounded source-job fields",
    )
    check(
        quality_packet["source_job_request"]["requested_field_labels"] == [
            "Especialistas publicados",
            "Contacto público",
            "Teléfono principal",
        ],
        "quality audit packet should keep human-readable source-job labels",
    )
    check(
        quality_packet["source_job_request"]["primary_requested_fields"] == ["profesionales"],
        "quality audit packet should identify the primary source-job field",
    )
    check(
        quality_packet["source_job_request"]["primary_requested_field_labels"] == ["Especialistas publicados"],
        "quality audit packet should identify the primary source-job label",
    )
    check(
        quality_packet["source_job_request"]["ui_route"] == "manual_review_banner_source_handoff"
        and quality_packet["source_job_request"]["target_scope"] == "primary_target_first",
        "source-job bridge should match the manual-review banner route",
    )
    check(
        quality_packet["source_job_request"]["write_policy"] == "creates_review_proposal_only",
        "source-job bridge should stay review-only",
    )
    check(
        quality_packet["source_job_request"]["allowed_output"] == "review_queue_proposal_only",
        "source-job bridge should forbid direct profile writes",
    )
    manual_context = quality_packet["manual_review_context"]
    check(manual_context["mode"] == "manual_admin_field_review", "manual context mode missing")
    check(
        manual_context["after_save"] == "resolve_current_review_then_return_to_review_list",
        "manual save should return Daniel to the review list",
    )
    check(
        manual_context["primary_target"]["admin_target_id"] == "clinicProfessionals",
        "manual context should keep the admin field to open",
    )
    check(
        manual_context["issues"][0]["issue_label"] == "Faltan especialistas publicados",
        "manual context should keep the pending issue label",
    )
    check(
        manual_context["operator_action"] == "open_admin_target_edit_field_then_save_clinic",
        "manual context should describe the manual operator route",
    )
    check(
        manual_context["source_handoff"]["ui_label"] == "Pasar URL al agente"
        and manual_context["source_handoff"]["target_scope"] == "primary_target_first",
        "manual context should expose the scoped source handoff",
    )
    check(
        manual_context["llm_boundary"] == "do_not_invent_values_or_write_field_changes",
        "manual context should keep the LLM boundary explicit",
    )
    filtered_report = build_report([
        sample_enrichment_row(),
        sample_quality_audit_row(),
        {
            "id": "source-only-1",
            "title": "Revisar valoraciones Google: Clinic",
            "review_type": "clinic_profile_enrichment",
            "payload": {
                "source_url": "https://clinic.example/contacto",
                "proposed_fields": {"google_reviews_url": "https://www.google.com/maps/place/Clinic/reviews"},
            },
            "clinic": {"display_name": "Clinic", "current_data": {}},
        },
    ], llm_ready_only=True)
    check(filtered_report["llm_ready_only"] is True, "LLM-ready report flag missing")
    check(filtered_report["packet_count"] == 3, "LLM-ready batches should include bounded legacy source packets")
    check(filtered_report["excluded_source_without_context"] == 0, "LLM-ready report should not exclude bounded legacy source packets")

    unsourced_specialist_packet = decision_packet(sample_unsourced_specialist_row())
    source_request = unsourced_specialist_packet["source_job_request"]
    check(
        source_request["ui_route"] == "review_card_specialist_source_handoff"
        and source_request["target_scope"] == "specialist_source_only",
        "unsourced specialist cards should ask for a specialist-only source handoff",
    )
    check(
        source_request["requested_fields"] == ["profesionales"]
        and source_request["allowed_output"] == "review_queue_proposal_only",
        "specialist source handoff should stay bounded and review-only",
    )
    dirty_specialist_packet = decision_packet(sample_dirty_specialist_row())
    dirty_warnings = " ".join(dirty_specialist_packet["warnings"])
    check(
        "Especialistas contiene entradas sospechosas. Usa Modificar" in dirty_warnings,
        "dirty specialist proposals should warn Daniel before approval",
    )
    dirty_specialist_item = next(
        item for item in dirty_specialist_packet["proposed_change"] if item["key"] == "profesionales"
    )
    quality_review = dirty_specialist_item["specialist_quality_review"]
    check(
        quality_review["overall_status"] == "needs_manual_correction_before_approval"
        and quality_review["safe_to_auto_publish"] is False,
        "dirty specialist proposals should be marked unsafe for automation",
    )
    check("examples" not in quality_review, "safe packet should omit dirty specialist raw examples")
    valued_dirty_packet = decision_packet(sample_dirty_specialist_row(), include_values=True)
    valued_quality_review = next(
        item for item in valued_dirty_packet["proposed_change"] if item["key"] == "profesionales"
    )["specialist_quality_review"]
    check(
        "Aviso Legal" in " ".join(valued_quality_review["examples"]),
        "explicit value mode should include dirty specialist examples for debugging",
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
    check("rq.title asc, rq.id asc" in source, "review packet query should have a stable tie-break")
    check("title asc, id asc" in source, "review packet JSON aggregation should have a stable tie-break")
    for forbidden in ["insert into", " update ", " delete from", "admin_update_clinic", "admin_resolve_review_item"]:
        check(forbidden not in lowered, f"packet builder should not write data: {forbidden}")

    print("OK review proposal packets: LLM-ready decisions stay read-only")


if __name__ == "__main__":
    main()
