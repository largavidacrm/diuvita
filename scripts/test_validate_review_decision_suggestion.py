#!/usr/bin/env python3
"""Checks that LLM review suggestions cannot bypass the human decision gate."""
from pathlib import Path

from review_proposal_decision_packets import decision_packet
from validate_review_decision_suggestion import validate_suggestion


ROOT = Path(__file__).resolve().parents[1]


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def sample_packet():
    return decision_packet({
        "id": "review-1",
        "title": "Revisar extracción shadow: Unidad de Longevidad IMDA",
        "review_type": "clinic_profile_enrichment",
        "priority": 60,
        "payload": {
            "source_url": "https://imda.example/contacto",
            "warnings": ["Contrastar https://imda.example/equipo con persona@example.com y +34 600 111 222."],
            "proposed_fields": {
                "maps_url": "https://www.google.com/maps/place/Unidad+de+Longevidad+IMDA/",
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
            "current_data": {"telefono": ""},
        },
    })


def sample_quality_packet(multiple_targets=False):
    issues = [{"code": "missing_professionals", "label": "Faltan especialistas publicados"}]
    if multiple_targets:
        issues.append({"code": "missing_contact", "label": "Falta email o teléfono"})
    return decision_packet({
        "id": "quality-1",
        "title": "Completar ficha: Tiara Health",
        "review_type": "clinic_quality_audit",
        "payload": {"issues": issues},
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
    packet = sample_packet()
    approved = validate_suggestion(packet, {
        "review_id": "review-1",
        "action": "aprobar",
        "reason": "La fuente oficial parece suficiente.",
    })
    check(approved["valid"], "Spanish approve action should be accepted")
    check(approved["action"] == "approve", "Spanish approve action should normalize")
    check(approved["human_required"] is True, "human gate should always remain")
    check(approved["field_change_keys"] == [], "approve should not include field changes")
    check("field_requires_human_attention" in approved["attention_flags"], "sensitive proposed fields should be flagged")
    check("packet_contains_warnings" in approved["attention_flags"], "packet warnings should be flagged")

    modified = validate_suggestion(packet, {
        "review_id": "review-1",
        "action": "modificar",
        "field_changes": {
            "phone": "916 000 000",
        },
        "reason": "Corregir contacto visto en https://imda.example/contacto y +34 600 111 222.",
        "warnings_to_show": ["Confirmar con persona@example.com antes de guardar."],
    })
    check(modified["valid"], "valid modify should pass")
    check(modified["action"] == "modify", "Spanish modify action should normalize")
    check(modified["field_change_keys"] == ["telefono"], "field aliases should normalize")
    check("field_changes" not in modified, "default output should omit raw change values")
    joined = " ".join([modified["reason"], *modified["warnings"]])
    check("https://imda.example/contacto" not in joined, "default suggestion output should redact URLs")
    check("+34 600 111 222" not in joined, "default suggestion output should redact phones")
    check("persona@example.com" not in joined, "default suggestion output should redact emails")

    modified_with_values = validate_suggestion(packet, {
        "review_id": "review-1",
        "action": "modify",
        "field_changes": {"telefono": "916 000 000"},
        "warnings": ["Confirmar con persona@example.com."],
    }, include_values=True)
    check(modified_with_values["field_changes"]["telefono"] == "916 000 000", "explicit value mode should keep changes")
    check("persona@example.com" in " ".join(modified_with_values["warnings"]), "explicit value mode should keep details")

    bad_field = validate_suggestion(packet, {
        "review_id": "review-1",
        "action": "modify",
        "field_changes": {"status": "published"},
    })
    check(not bad_field["valid"], "non-editable status change should be blocked")
    check("field is not editable in this packet: status" in bad_field["errors"], "status block reason missing")

    bad_publish = validate_suggestion(packet, {
        "review_id": "review-1",
        "action": "approve",
        "publish": True,
        "sql": "select admin_update_clinic();",
    })
    check(not bad_publish["valid"], "publish/control suggestions should be blocked")
    check(any("publish" in error for error in bad_publish["errors"]), "publish block missing")
    check(any("sql" in error for error in bad_publish["errors"]), "SQL block missing")

    bad_review = validate_suggestion(packet, {
        "review_id": "another-review",
        "action": "reject",
    })
    check(not bad_review["valid"], "review_id mismatch should be blocked")

    approve_with_changes = validate_suggestion(packet, {
        "review_id": "review-1",
        "action": "approve",
        "field_changes": {"telefono": "916 000 000"},
    })
    check(not approve_with_changes["valid"], "approve should not carry modifications")
    check("field changes are only allowed when action is modify" in approve_with_changes["errors"], "approve/change error missing")

    empty_modify = validate_suggestion(packet, {
        "review_id": "review-1",
        "action": "modify",
    })
    check(not empty_modify["valid"], "modify should require concrete field changes")

    manual_packet = sample_quality_packet()
    manual_modify = validate_suggestion(manual_packet, {
        "review_id": "quality-1",
        "action": "modify",
        "reason": "Abrir revisión manual del campo de especialistas.",
    })
    check(manual_modify["valid"], "single manual target should allow modify without invented values")
    check(manual_modify["manual_review_target_key"] == "profesionales", "single manual target should be selected")
    check(
        manual_modify["manual_review_target"] == {
            "key": "profesionales",
            "label": "Especialistas publicados",
            "admin_target_id": "clinicProfessionals",
        },
        "validated manual route should keep the admin target",
    )
    check(manual_modify["field_change_keys"] == [], "manual review should not carry field changes")

    explicit_manual_modify = validate_suggestion(manual_packet, {
        "review_id": "quality-1",
        "action": "modify",
        "manual_review_target_key": "profesionales",
        "reason": "Revisar el campo manualmente.",
    })
    check(explicit_manual_modify["valid"], "explicit allowed manual target should pass")

    bad_manual_target = validate_suggestion(manual_packet, {
        "review_id": "quality-1",
        "action": "modify",
        "manual_review_target_key": "status",
    })
    check(not bad_manual_target["valid"], "unlisted manual target should be blocked")

    approve_manual_target = validate_suggestion(manual_packet, {
        "review_id": "quality-1",
        "action": "approve",
        "manual_review_target_key": "profesionales",
    })
    check(not approve_manual_target["valid"], "manual target should not travel with approve")

    smuggled_source = validate_suggestion(manual_packet, {
        "review_id": "quality-1",
        "action": "modify",
        "manual_review_target_key": "profesionales",
        "source_url": "https://www.tiarahealth.com/our-team-of-experts/",
    })
    check(not smuggled_source["valid"], "LLM suggestions should not smuggle source-job fields")
    check(
        "unexpected suggestion key is not allowed: source_url" in smuggled_source["errors"],
        "unexpected source URL key should be reported",
    )

    ambiguous_manual = validate_suggestion(sample_quality_packet(multiple_targets=True), {
        "review_id": "quality-1",
        "action": "modify",
    })
    check(not ambiguous_manual["valid"], "multiple manual targets should require one target key")

    bad_phone = validate_suggestion(packet, {
        "review_id": "review-1",
        "action": "modify",
        "field_changes": {"telefono": "ABC-123"},
    })
    check(not bad_phone["valid"], "weak phone suggestions should be blocked")
    check(any("Teléfono dudoso" in error for error in bad_phone["errors"]), "weak phone error missing")

    bad_maps = validate_suggestion(packet, {
        "review_id": "review-1",
        "action": "modify",
        "field_changes": {"maps_url": "https://www.google.com/maps/search/Unidad+de+Longevidad+IMDA"},
    })
    check(not bad_maps["valid"], "weak Google Maps suggestions should be blocked")
    check(any("Google Maps debe ser el perfil real" in error for error in bad_maps["errors"]), "weak Maps error missing")

    source = (ROOT / "scripts" / "validate_review_decision_suggestion.py").read_text(encoding="utf-8")
    check("admin_update_clinic" in source, "forbidden operation list should name risky admin writes")
    check("run_psql" not in source, "suggestion validator should not connect to Supabase")
    check("load_env_file" not in source, "suggestion validator should not read credentials")
    print("OK review suggestion guard: LLM output stays advisory")


if __name__ == "__main__":
    main()
