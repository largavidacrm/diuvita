#!/usr/bin/env python3
"""Checks for the CTO shadow cycle orchestrator."""
from argparse import Namespace

from run_cto_shadow_cycle import (
    DEFAULT_SAFE_WRITE_REVIEW_BACKLOG_STOP,
    build_cycle_brief,
    build_steps,
    clinic_visibility_status,
    compact_summary,
    cycle_next_clicks,
    enrichment_consolidation_status,
    format_cycle_brief,
    google_link_reconciliation_status,
    manual_review_route_status,
    open_review_count_from_digest,
    publication_readiness_status,
    skipped_step,
    specialist_claim_proposal_status,
    specialist_reconciliation_status,
    try_parse_json,
)


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    check(try_parse_json('{"ok": true}')["ok"] is True, "JSON output should parse")
    check(try_parse_json("plain text") is None, "plain text should not parse")
    check(try_parse_json("") is None, "empty output should be None")
    compact = compact_summary("evaluate_claim_rules", {
        "summary": {"actions": {"review": 2}},
        "evaluations": [{"id": "a"}, {"id": "b"}],
    })
    check(compact["evaluations_count"] == 2, "evaluation count should be kept")
    check("evaluations" not in compact, "full evaluations should be removed")
    compact_items = compact_summary("monitor_source_changes", {
        "changed": 0,
        "items": [
            {
                "source_url": "https://a.test",
                "clinic_name": "A",
                "status": "unchanged",
                "snapshot": {"large": True},
            },
            {
                "source_url": "https://b.test",
                "clinic_name": "B",
                "status": "changed",
                "snapshot": {"large": True},
            },
        ],
    })
    check(compact_items["items_count"] == 2, "items count should be kept")
    check("items" not in compact_items, "full item list should be removed")
    compact_manual_routes = compact_summary("manual_review_route_brief", {
        "summary": {
            "reported_packets": 3,
            "manual_field_routes": 2,
            "source_handoff_available": 1,
            "source_only_reviewable": 1,
            "blocked_without_operator_context": 1,
        },
        "items": [
            {
                "title": "Revisión manual: Tiara Health",
                "clinic_name": "Tiara Health",
                "operator_action": "open_manual_field",
                "human_next_step": "Abrir la ficha y editar Especialistas publicados.",
                "manual_primary_target": {
                    "key": "profesionales",
                    "label": "Especialistas publicados",
                    "admin_target_id": "clinicProfessionals",
                },
                "raw_packet": {"large": True},
            }
        ],
    })
    check(compact_manual_routes["items_count"] == 1, "manual route item count should be kept")
    check("items" not in compact_manual_routes, "raw manual route items should be removed")
    check(
        compact_manual_routes["sample_items"][0]["manual_primary_target"]["admin_target_id"] == "clinicProfessionals",
        "manual route sample should keep the admin target",
    )
    check("raw_packet" not in compact_manual_routes["sample_items"][0], "manual route raw packets should be omitted")
    compact_proposals = compact_summary("export_specialist_claim_proposals", {
        "summary": {"proposal_count": 1, "skipped_with_open_cards": 2},
        "proposals": [
            {
                "slug": "clinic-a",
                "title": "Ampliar especialistas: Clinic A",
                "priority": 55,
                "proposed_fields": {"profesionales": ["Dra. Ana López"]},
            }
        ],
    })
    check(compact_proposals["proposals_count"] == 1, "proposal count should be kept")
    check("proposals" not in compact_proposals, "raw proposals should be removed")
    check("proposed_fields" not in compact_proposals["sample_proposals"][0], "proposed names should be hidden")
    compact_publication = compact_summary("clinic_publication_readiness", {
        "summary": {
            "clinics_measured": 24,
            "ready_clinics": 3,
            "clinics_with_missing_fields": 21,
            "clinics_with_blocking_reviews": 1,
            "top_missing_fields": [{"field": "Google Maps de clinica", "count": 20}],
        },
        "matches": [
            {
                "slug": "clinic-a",
                "clinic_name": "Clinic A",
                "city": "Madrid",
                "status": "draft",
                "open_reviews": 2,
                "has_summary": False,
            }
        ],
    })
    check(compact_publication["matches_count"] == 1, "publication matches count should be kept")
    check("matches" not in compact_publication, "raw publication matches should be removed")
    check("has_summary" not in compact_publication["sample_matches"][0], "publication internals should be hidden")
    check("snapshot" not in compact_items["sample_items"][0], "large nested snapshot should be omitted")
    compact_seed_sources = compact_summary("seed_visible_clinic_sources", {
        "mode": "apply",
        "candidates_seen": 2,
        "inserted_count": 1,
        "items": [
            {
                "clinic_name": "Clinic A",
                "city": "Madrid",
                "status": "published",
                "website": "https://clinic-a.example/",
                "source_url": "https://clinic-a.example/",
                "metadata": {"large": True},
            }
        ],
    })
    check(compact_seed_sources["items_count"] == 1, "seed source count should be kept")
    check("metadata" not in compact_seed_sources["sample_items"][0], "large seed metadata should be omitted")
    check("source_url" in compact_seed_sources["sample_items"][0], "seed source URL should be kept")
    compact_team_sources = compact_summary("discover_clinic_team_sources", {
        "mode": "dry_run",
        "team_sources_found": 1,
        "items": [
            {
                "clinic_slug": "arvila-magna",
                "clinic_name": "Clínica Arvila Magna",
                "city": "Barcelona",
                "status": "published",
                "url": "https://arvilamagna.example/equipo/",
                "label": "Equipo",
                "score": 30,
                "already_stored": False,
                "source_type": "official_team_page",
                "metadata": {"large": True},
            }
        ],
    })
    check(compact_team_sources["items_count"] == 1, "team source count should be kept")
    check("metadata" not in compact_team_sources["sample_items"][0], "large team source metadata should be omitted")
    check("url" in compact_team_sources["sample_items"][0], "team source URL should be kept")
    compact_google_links = compact_summary("discover_clinic_google_links", {
        "mode": "dry_run",
        "items": [
            {
                "clinic_slug": "clinic-a",
                "clinic_name": "Clinic A",
                "website": "https://clinic-a.example/",
                "status": "ready",
                "proposed_fields": {"maps_url": "https://www.google.com/maps/place/Clinic+A"},
                "google_link_candidates": [{"large": True}],
            }
        ],
    })
    check(compact_google_links["items_count"] == 1, "Google-link discovery count should be kept")
    check("google_link_candidates" not in compact_google_links["sample_items"][0], "large Google-link candidates should be omitted")
    check("proposed_fields" in compact_google_links["sample_items"][0], "Google-link proposals should be kept")
    compact_google_reconciliation = compact_summary("google_link_review_reconciliation", {
        "summary": {
            "review_cards": 2,
            "cards_with_direct_maps": 1,
            "cards_with_unsafe_maps": 1,
            "cards_with_review_links": 1,
        },
        "review_cards": [
            {
                "clinic_name": "Clinic A",
                "clinic_slug": "clinic-a",
                "title": "Completar enlaces Google: Clinic A",
                "priority": 60,
                "direct_map_count": 1,
                "unsafe_map_count": 0,
                "review_link_count": 1,
                "map_status_counts": {"direct_profile": 1},
                "maps_urls": ["https://www.google.com/maps/place/Clinic+A/"],
                "payload": {"large": True},
                "next_step": "abrir enlace",
            }
        ],
    })
    check(compact_google_reconciliation["review_cards_count"] == 1, "Google reconciliation card count should be kept")
    check("review_cards" not in compact_google_reconciliation, "full Google reconciliation cards should be removed")
    check("maps_urls" not in compact_google_reconciliation["sample_review_cards"][0], "long Google URLs should stay out of cycle output")
    check("payload" not in compact_google_reconciliation["sample_review_cards"][0], "Google payload should stay out of cycle output")
    google_reconciliation_step = {
        "name": "google_link_review_reconciliation",
        "ok": True,
        "summary": compact_google_reconciliation,
    }
    check(
        google_link_reconciliation_status(google_reconciliation_step)
        == "1/2 con Maps que no se debe guardar sin corregir",
        "Google reconciliation status should flag unsafe Maps",
    )
    compact_top_sources = compact_summary("measure_source_snapshot_retention", {
        "summary": {"total_snapshots": 2},
        "top_sources": [
            {"clinic_name": "A", "source_url": "https://a.test", "snapshots": 3, "prunable": 0, "source_record_id": "large"},
            {"clinic_name": "B", "source_url": "https://b.test", "snapshots": 1, "prunable": 0, "source_record_id": "large"},
        ],
    })
    check(compact_top_sources["top_sources_count"] == 2, "top source count should be kept")
    check("top_sources" not in compact_top_sources, "full top source list should be removed")
    check("source_url" in compact_top_sources["sample_top_sources"][0], "source url should distinguish compact top sources")
    check("source_record_id" not in compact_top_sources["sample_top_sources"][0], "large source ids should be omitted")
    compact_source_coverage = compact_summary("measure_source_coverage", {
        "summary": {"visible_clinics": 2},
        "needs_source_work": [
            {
                "clinic_name": "A",
                "slug": "a",
                "status": "published",
                "source_records": 1,
                "hydrated_source_records": 1,
                "total_claims": 4,
                "claims_without_source": 0,
                "blocking_claims": 2,
                "raw": {"large": True},
            }
        ],
    })
    check(compact_source_coverage["needs_source_work_count"] == 1, "source coverage count should be kept")
    check("needs_source_work" not in compact_source_coverage, "full source coverage list should be removed")
    check("blocking_claims" in compact_source_coverage["sample_needs_source_work"][0], "source blockers should be kept")
    check("raw" not in compact_source_coverage["sample_needs_source_work"][0], "large source coverage details should be omitted")
    compact_profiles = compact_summary("measure_profile_completeness", {
        "summary": {"visible_clinics": 2},
        "pending_profiles": [
            {
                "clinic_name": "A",
                "slug": "a",
                "status": "published",
                "pending_count": 3,
                "pending_fields": ["Email o teléfono"],
                "raw": {"large": True},
            }
        ],
    })
    check(compact_profiles["pending_profiles_count"] == 1, "pending profile count should be kept")
    check("pending_profiles" not in compact_profiles, "full pending profile list should be removed")
    check("pending_fields" in compact_profiles["sample_pending_profiles"][0], "pending fields should be kept")
    check("raw" not in compact_profiles["sample_pending_profiles"][0], "large profile details should be omitted")
    compact_backlog = compact_summary("review_backlog_brief", {
        "summary": {"open_reviews": 48},
        "duplicate_enrichment": [
            {
                "clinic_name": "Sensabell",
                "clinic_slug": "sensabell",
                "city": "Valencia",
                "clinic_status": "published",
                "card_count": 3,
                "max_priority": 60,
                "oldest_created_at": "2026-08-30T09:00:00+00:00",
                "cards": [{"id": "large"}],
            }
        ],
        "clinic_workgroups": [
            {
                "clinic_name": "Sensabell",
                "clinic_slug": "sensabell",
                "city": "Valencia",
                "clinic_status": "published",
                "card_count": 5,
                "blocking_claim_reviews": 1,
                "enrichment_reviews": 3,
                "source_change_reviews": 0,
                "quality_reviews": 1,
                "candidate_reviews": 0,
                "max_priority": 85,
                "oldest_created_at": "2026-08-30T08:30:00+00:00",
                "clinic_id": "large",
            }
        ],
    })
    check(compact_backlog["duplicate_enrichment_count"] == 1, "duplicate backlog count should be kept")
    check("duplicate_enrichment" not in compact_backlog, "full duplicate backlog list should be removed")
    check("card_count" in compact_backlog["sample_duplicate_enrichment"][0], "duplicate count should be kept")
    check("cards" not in compact_backlog["sample_duplicate_enrichment"][0], "duplicate card details should be omitted")
    check(compact_backlog["clinic_workgroups_count"] == 1, "clinic workgroup count should be kept")
    check("clinic_workgroups" not in compact_backlog, "full clinic workgroup list should be removed")
    check("blocking_claim_reviews" in compact_backlog["sample_clinic_workgroups"][0], "clinic workgroup counts should be kept")
    check("clinic_id" not in compact_backlog["sample_clinic_workgroups"][0], "large clinic ids should be omitted")
    compact_consolidation = compact_summary("consolidate_profile_enrichment_reviews", {
        "summary": {
            "groups": 1,
            "cards": 3,
            "fields_to_review": 5,
            "conflicts": 1,
        },
        "groups": [
            {
                "clinic_name": "Sensabell",
                "clinic_slug": "sensabell",
                "city": "Valencia",
                "clinic_status": "published",
                "card_count": 3,
                "source_count": 2,
                "merged_field_count": 6,
                "merged_field_counts": {"profesionales": 4},
                "already_present_count": 1,
                "conflict_count": 1,
                "conflict_fields": ["telefono"],
                "weak_phone_count": 1,
                "weak_phone_fields": ["phone_fixed"],
                "merged_fields": {"profesionales": ["Dra. Example"]},
                "source_urls": ["https://sensabell.example/equipo/"],
                "next_step": "resolver conflictos antes de validar propuestas",
            }
        ],
    })
    check(compact_consolidation["groups_count"] == 1, "consolidation group count should be kept")
    check("groups" not in compact_consolidation, "full consolidation groups should be removed")
    check("merged_fields" not in compact_consolidation["sample_groups"][0], "merged field payload should stay out of cycle output")
    check("source_urls" not in compact_consolidation["sample_groups"][0], "consolidation source URLs should stay out of cycle output")
    check("conflict_count" in compact_consolidation["sample_groups"][0], "consolidation conflict count should be kept")
    check("weak_phone_count" in compact_consolidation["sample_groups"][0], "consolidation weak phone count should be kept")
    consolidation_step = {
        "name": "consolidate_profile_enrichment_reviews",
        "ok": True,
        "summary": compact_consolidation,
    }
    check(
        enrichment_consolidation_status(consolidation_step)
        == "1 conflictos en 1 grupos; revisar antes de fusionar",
        "consolidation status should flag conflicts",
    )
    clean_consolidation_step = {
        "name": "consolidate_profile_enrichment_reviews",
        "ok": True,
        "summary": {
            "summary": {
                "groups": 2,
                "cards": 5,
                "fields_to_review": 9,
                "conflicts": 0,
            },
            "groups_count": 2,
        },
    }
    check(
        enrichment_consolidation_status(clean_consolidation_step)
        == "9 campos listos para revisar en 2 grupos (5 tarjetas)",
        "clean consolidation status should show actionable fields",
    )
    weak_phone_consolidation_step = {
        "name": "consolidate_profile_enrichment_reviews",
        "ok": True,
        "summary": {
            "summary": {
                "groups": 2,
                "cards": 5,
                "fields_to_review": 9,
                "conflicts": 0,
                "weak_phone_fields": 1,
            },
            "groups_count": 2,
        },
    }
    check(
        enrichment_consolidation_status(weak_phone_consolidation_step)
        == "1 telefonos dudosos en 2 grupos; revisar antes de fusionar",
        "weak phone consolidation status should be visible",
    )
    manual_route_step = {
        "name": "manual_review_route_brief",
        "ok": True,
        "summary": {
            "summary": {
                "reported_packets": 6,
                "manual_field_routes": 3,
                "source_handoff_available": 2,
                "source_only_reviewable": 1,
                "blocked_without_operator_context": 1,
                "direct_change_reviews": 1,
            },
            "items_count": 6,
        },
    }
    check(
        manual_review_route_status(manual_route_step)
        == "3 abren campo directo; 2 permiten URL oficial; 1 revisables manualmente aunque no listas para LLM; 1 no listas para LLM por fuente sin contexto",
        "manual review route status should summarize operator routes",
    )
    check(
        manual_review_route_status(None) == "no comprobadas en este ciclo",
        "missing manual route step should be explicit",
    )
    compact_digest = compact_summary("admin_digest", {
        "admin_email": "admin@example.test",
        "summary": {"reviews": {"open": 2}},
        "open_reviews": [
            {"title": "A", "review_type": "candidate_clinic", "priority": 90, "professionals_count": 11, "payload": {"large": True}},
            {"title": "B", "review_type": "clinic_quality_audit", "priority": 80, "payload": {"large": True}},
        ],
        "review_examples_by_type": [
            {"title": "A", "review_type": "candidate_clinic", "priority": 90, "professionals_count": 11, "payload": {"large": True}},
            {"title": "B", "review_type": "blocking_claim_review", "priority": 85, "payload": {"large": True}},
        ],
        "review_backlog_quality": {
            "duplicate_enrichment_clinics": 1,
            "duplicate_enrichment_reviews": 2,
            "raw": {"large": True},
        },
    })
    check("admin_email" not in compact_digest, "admin email should be removed from cycle output")
    check(compact_digest["open_reviews_count"] == 2, "open review count should be kept")
    check("payload" not in compact_digest["sample_open_reviews"][0], "review payload should be omitted")
    check(compact_digest["sample_open_reviews"][0]["professionals_count"] == 11, "review professional count should be kept")
    check(compact_digest["review_backlog_quality"]["duplicate_enrichment_clinics"] == 1, "review backlog quality should be kept")
    check("raw" not in compact_digest["review_backlog_quality"], "large review backlog payloads should be omitted")
    check(compact_digest["review_examples_by_type_count"] == 2, "review example count should be kept")
    check("payload" not in compact_digest["sample_review_examples_by_type"][0], "review example payload should be omitted")
    compact_health = compact_summary("check_production_health", {
        "base_url": "https://www.vitalarga.com",
        "ok": True,
        "checks": [
            {
                "name": "home",
                "url": "https://www.vitalarga.com/",
                "status": 200,
                "ok": True,
                "missing_markers": [],
                "body": "large",
            }
        ],
    })
    check(compact_health["checks_count"] == 1, "production health check count should be kept")
    check("checks" not in compact_health, "full production health checks should be removed")
    check("body" not in compact_health["sample_checks"][0], "production response bodies should be omitted")
    compact_freshness = compact_summary("check_public_site_freshness", {
        "base_url": "https://www.vitalarga.com",
        "ok": False,
        "stale_count": 1,
        "checks": [
            {
                "slug": "monarka-clinic",
                "name": "Monarka Clinic",
                "url": "https://www.vitalarga.com/clinica/monarka-clinic/",
                "fresh": False,
                "missing_markers": 18,
                "missing_examples": ["+34 930 490 300", "Dra. Estela Arnal"],
                "page_excerpt": "large",
            }
        ],
    })
    check(compact_freshness["checks_count"] == 1, "public freshness check count should be kept")
    check("checks" not in compact_freshness, "full public freshness checks should be removed")
    check("missing_examples" not in compact_freshness["sample_checks"][0], "public freshness examples should stay out of cycle output")
    check("page_excerpt" not in compact_freshness["sample_checks"][0], "public freshness page excerpts should be omitted")
    compact_visibility = compact_summary("clinic_public_visibility_report", {
        "query": "Monarka",
        "readiness": {
            "matches": [
                {
                    "slug": "monarka-clinic",
                    "clinic_name": "Monarka Clinic",
                    "status": "published",
                    "updated_at": "2026-08-31T06:47:00+00:00",
                    "current_data": {"large": True},
                }
            ]
        },
        "freshness": {
            "ok": False,
            "clinic_count": 1,
            "stale_count": 1,
            "checks": [
                {
                    "slug": "monarka-clinic",
                    "name": "Monarka Clinic",
                    "url": "https://www.vitalarga.com/clinica/monarka-clinic/",
                    "fresh": False,
                    "missing_markers": 18,
                    "missing_examples": ["Dra. Example"],
                }
            ],
        },
    })
    check(compact_visibility["readiness"]["matches_count"] == 1, "visibility readiness count should be kept")
    check("current_data" not in compact_visibility["readiness"]["sample_matches"][0], "visibility clinic data should be omitted")
    check(compact_visibility["freshness"]["stale_count"] == 1, "visibility freshness stale count should be kept")
    check("missing_examples" not in compact_visibility["freshness"]["sample_checks"][0], "visibility freshness examples should be omitted")
    visibility_step = {"name": "clinic_public_visibility_report", "ok": True, "summary": compact_visibility}
    check(clinic_visibility_status(visibility_step) == "1 ficha con desfase", "visibility step status should show stale public page")
    publication_step = {"name": "clinic_publication_readiness", "ok": True, "summary": compact_publication}
    check(
        publication_readiness_status(publication_step)
        == "3/24 sin faltantes; 21 con faltantes; principal: Google Maps de clinica (20); 1 con claims bloqueantes",
        "publication readiness status should summarize blockers",
    )
    compact_specialists = compact_summary("specialist_review_reconciliation", {
        "query": "Kairos",
        "clinics": [
            {
                "clinic_name": "Kairos Longevity Clinic",
                "slug": "kairos-longevity-clinic",
                "city": "Madrid",
                "status": "published",
                "published_count": 0,
                "review_card_count": 2,
                "review_professional_count": 6,
                "claim_professional_count": 6,
                "pending_professional_count": 6,
                "pending_professionals": ["Dra. Example"],
                "review_cards": [{"payload": "large"}],
                "next_step": "abrir tarjetas",
            }
        ],
    })
    check(compact_specialists["clinics_count"] == 1, "specialist reconciliation clinic count should be kept")
    check("clinics" not in compact_specialists, "full specialist reconciliation clinics should be removed")
    check("pending_professionals" not in compact_specialists["sample_clinics"][0], "specialist names should stay out of cycle output")
    check("review_cards" not in compact_specialists["sample_clinics"][0], "specialist card details should stay out of cycle output")
    specialist_step = {"name": "specialist_review_reconciliation", "ok": True, "summary": compact_specialists}
    check(
        specialist_reconciliation_status(specialist_step) == "Kairos Longevity Clinic: 6 pendientes en 2 tarjetas",
        "specialist reconciliation status should be readable",
    )
    aggregate_specialist_step = {
        "name": "specialist_review_reconciliation",
        "ok": True,
        "summary": {
            "summary": {
                "clinics": 5,
                "clinics_with_pending_professionals": 4,
                "review_cards": 7,
                "pending_professionals": 22,
            },
            "clinics_count": 5,
        },
    }
    check(
        specialist_reconciliation_status(aggregate_specialist_step) == "22 pendientes en 7 tarjetas (4/5 fichas)",
        "specialist reconciliation aggregate status should be readable",
    )
    claim_proposal_step = {
        "name": "export_specialist_claim_proposals",
        "ok": True,
        "summary": {
            "summary": {
                "proposal_count": 1,
                "skipped_with_open_cards": 5,
            },
            "proposals_count": 1,
        },
    }
    check(
        specialist_claim_proposal_status(claim_proposal_step)
        == "1 propuesta privada lista; 5 omitidas porque ya tienen tarjeta",
        "specialist claim proposal status should be readable",
    )
    check(
        specialist_claim_proposal_status({"name": "export_specialist_claim_proposals", "ok": True, "summary": {"summary": {"proposal_count": 0, "skipped_with_open_cards": 5}}})
        == "sin propuestas nuevas; 5 ya tienen tarjeta abierta",
        "empty specialist claim proposal status should explain skipped cards",
    )
    compact_source_shadow = compact_summary("submit_source_shadow_reviews", {
        "items": [
            {
                "clinic_slug": "example",
                "clinic_name": "Example",
                "source_url": "https://example.test",
                "status": "ready",
                "proposed_fields": ["email"],
                "verification_summary": {"large": True},
            }
        ],
    })
    check(compact_source_shadow["items_count"] == 1, "source shadow count should be kept")
    check("verification_summary" not in compact_source_shadow["sample_items"][0], "large source shadow details should be omitted")
    check(DEFAULT_SAFE_WRITE_REVIEW_BACKLOG_STOP == 45, "safe CTO writes should stop in the near-full review zone")
    cycle_digest = {
        "summary": {
            "reviews": {"open": 45},
            "jobs": {"failed": 0, "dead_letter": 0},
            "automation": {"auto_publish_enabled": False, "shadow_mode_active": True},
        },
        "reviews_by_type": [{"review_type": "blocking_claim_review", "open_count": 1}],
        "open_reviews": [{"review_type": "blocking_claim_review", "priority": 95}],
        "profile_completeness": {
            "visible_clinics": 19,
            "with_pending_fields": 19,
            "pending_specialists": 17,
            "pending_contact": 6,
        },
        "profile_next_target": {
            "clinic_name": "Sensabell",
            "pending_count": 4,
            "next_pending_field": "Email o teléfono",
            "open_relevant_reviews": 5,
        },
        "source_coverage": {
            "visible_clinics": 19,
            "clinics_with_sources": 11,
            "clinics_without_sources": 8,
            "clinics_with_hydrated_sources": 10,
            "clinics_without_hydrated_sources": 9,
            "clinics_needing_source_work": 11,
        },
        "source_next_target": {
            "clinic_name": "Kairos Longevity Clinic",
            "source_records": 2,
            "hydrated_source_records": 2,
            "total_claims": 8,
            "claims_without_source": 0,
            "blocking_claims": 2,
        },
        "review_first_clinic_workgroup": {
            "clinic_name": "Sensabell",
            "open_count": 5,
        },
        "google_link_reviews": {
            "open_count": 4,
            "first_review": {"title": "Completar enlaces Google: Sensabell"},
        },
        "specialist_reviews": {
            "open_count": 2,
            "professionals_count": 17,
            "first_review": {"title": "Regenera Clinic Medicina de la Longevidad", "professionals_count": 11},
        },
    }
    cycle_brief = build_cycle_brief({
        "mode": "dry_run",
        "ok": True,
        "steps": [{"name": "admin_digest", "ok": True, "summary": cycle_digest}],
    })
    check(cycle_brief["status"] == "ok", "clean cycle should be OK")
    check(cycle_brief["next_action"] == "Revisar claim bloqueante", "Daniel brief should keep next action")
    check(cycle_brief["profile_gap"] == "Especialistas · 17 fichas", "Daniel brief should keep top profile gap")
    check(
        cycle_brief["profile_next"] == "19/19 fichas con campos pendientes; se revisan después de la prioridad actual",
        "Daniel brief should keep secondary profile queue aggregate",
    )
    check("11/19 fichas con fuente" in cycle_brief["source_gap"], "Daniel brief should keep source coverage")
    check("Kairos Longevity Clinic" in cycle_brief["source_next"], "Daniel brief should keep next source target")
    check("crear borrador no publica" in cycle_brief["publication_guard"].lower(), "publication guard should be explicit")
    next_click_text = " ".join(cycle_next_clicks(cycle_digest))
    check("No crear trabajos nuevos" in next_click_text, "cycle brief should show the backlog guard next click")
    check("Pulsa Abrir prioridad" in next_click_text, "cycle brief should show the concrete priority click")
    check("Abrir Especialistas" in next_click_text, "cycle brief should show specialist next click")
    check("Abrir Google Maps" in next_click_text, "cycle brief should show Google Maps next click")
    brief_text = format_cycle_brief(cycle_brief)
    check("# Vitalarga: resumen CTO automatico" in brief_text, "plain brief title missing")
    check("Que mirar primero: Revisar claim bloqueante." in brief_text, "plain brief next action missing")
    check("Proximos clics: No crear trabajos nuevos" in brief_text, "plain brief next clicks missing")
    check(
        "Fichas pendientes: 19/19 fichas con campos pendientes; se revisan después de la prioridad actual" in brief_text,
        "plain brief should keep secondary profile queue aggregate",
    )
    check("Cobertura fuentes: 11/19 fichas con fuente" in brief_text, "plain brief source coverage missing")
    check("Siguiente fuente: Revisar 2 claims bloqueantes de Kairos Longevity Clinic" in brief_text, "plain brief source target missing")
    check("Preparacion publicacion: no comprobada en este ciclo" in brief_text, "plain brief publication readiness line missing")
    check("Visibilidad clinica: no comprobada en este ciclo" in brief_text, "plain brief clinic visibility line missing")
    check("Consolidacion mejoras: no comprobada en este ciclo" in brief_text, "plain brief consolidation line missing")
    check("Rutas revision manual: no comprobadas en este ciclo" in brief_text, "plain brief manual routes line missing")
    check("Conciliacion Google: no comprobada en este ciclo" in brief_text, "plain brief Google reconciliation line missing")
    check("Conciliacion especialistas: no comprobada en este ciclo" in brief_text, "plain brief specialist reconciliation line missing")
    check("Propuestas especialistas: no comprobadas en este ciclo" in brief_text, "plain brief specialist proposal line missing")
    check(open_review_count_from_digest(cycle_digest) == 45, "open review count should be readable for guards")

    compact_priority_digest = {
        "summary": {
            "reviews": {"open": 41},
            "jobs": {"failed": 0, "dead_letter": 0},
            "automation": {"auto_publish_enabled": False, "shadow_mode_active": True},
        },
        "reviews_by_type": [
            {"review_type": "clinic_profile_enrichment", "open_count": 20},
            {"review_type": "clinic_quality_audit", "open_count": 18},
            {"review_type": "candidate_clinic", "open_count": 3},
        ],
        "sample_open_reviews": [
            {
                "title": "Completar ficha: Clínica Benzaquén",
                "review_type": "clinic_quality_audit",
                "priority": 85,
                "clinic_name": "Clínica Benzaquén",
            },
            {
                "title": "Revisar extracción shadow: Sensabell",
                "review_type": "clinic_profile_enrichment",
                "priority": 60,
                "clinic_name": "Sensabell",
            },
        ],
        "review_first_clinic_workgroup": {
            "clinic_name": "Sensabell",
            "open_count": 4,
        },
    }
    compact_priority_brief = build_cycle_brief({
        "mode": "dry_run",
        "ok": True,
        "steps": [{"name": "admin_digest", "ok": True, "summary": compact_priority_digest}],
    })
    compact_priority_clicks = cycle_next_clicks(compact_priority_digest)
    compact_priority_click_text = " ".join(compact_priority_clicks)
    check(compact_priority_brief["next_action"] == "Revisión manual de fichas", "compact cycle should prefer sampled higher-priority audits")
    check(
        compact_priority_clicks[0].startswith("Pulsa Abrir prioridad: Revisión manual: Clínica Benzaquén"),
        "compact cycle should open the sampled priority card before group context",
    )
    check("Sensabell" in compact_priority_click_text, "compact cycle should keep the lower-priority group as context")
    guarded_brief = build_cycle_brief({
        "mode": "apply_safe",
        "ok": True,
        "steps": [
            {"name": "preflight_review_backlog", "ok": True, "summary": cycle_digest},
            skipped_step("monitor_source_changes", "50 revisiones abiertas; limite seguro 50."),
            {"name": "admin_digest", "ok": True, "summary": cycle_digest},
        ],
    })
    check(guarded_brief["status"] == "attention", "skipped review-card writers should be visible")
    check(guarded_brief["skipped_steps"] == 1, "skipped count should be kept")
    check("Pasos omitidos: 1" in format_cycle_brief(guarded_brief), "plain brief should show skipped steps")
    failed_cycle_brief = build_cycle_brief({
        "mode": "dry_run",
        "ok": False,
        "steps": [{"name": "check_operational_limits_strict", "ok": False, "summary": None}],
    })
    check(failed_cycle_brief["status"] == "needs_daniel", "strict limit failures should ask Daniel")
    check("limites operativos" in failed_cycle_brief["attention"], "strict limit attention should be clear")
    stale_cycle_brief = build_cycle_brief({
        "mode": "dry_run",
        "ok": False,
        "steps": [{"name": "check_public_site_freshness", "ok": False, "summary": {"ok": False, "stale_count": 1}}],
    })
    check(stale_cycle_brief["status"] == "attention", "public freshness gaps should be attention items")
    check(stale_cycle_brief["public_freshness"] == "1 con desfase", "public freshness stale count should be readable")
    check("frescura de la web publica" in stale_cycle_brief["headline"], "freshness failure should name the stopped step")
    check("datos guardados" in stale_cycle_brief["attention"], "freshness attention should explain the cause")
    visibility_cycle_brief = build_cycle_brief({
        "mode": "dry_run",
        "ok": True,
        "steps": [
            {"name": "clinic_public_visibility_report", "ok": True, "summary": compact_visibility},
        ],
    })
    check(visibility_cycle_brief["clinic_visibility"] == "1 ficha con desfase", "clinic visibility should enter cycle brief")
    check("Visibilidad clinica: 1 ficha con desfase" in format_cycle_brief(visibility_cycle_brief), "plain brief should show clinic visibility result")
    publication_cycle_brief = build_cycle_brief({
        "mode": "dry_run",
        "ok": True,
        "steps": [
            {"name": "clinic_publication_readiness", "ok": True, "summary": compact_publication},
        ],
    })
    check(
        publication_cycle_brief["publication_readiness"]
        == "3/24 sin faltantes; 21 con faltantes; principal: Google Maps de clinica (20); 1 con claims bloqueantes",
        "publication readiness should enter cycle brief",
    )
    check(
        "Preparacion publicacion: 3/24 sin faltantes; 21 con faltantes; principal: Google Maps de clinica (20); 1 con claims bloqueantes"
        in format_cycle_brief(publication_cycle_brief),
        "plain brief should show publication readiness result",
    )
    specialist_cycle_brief = build_cycle_brief({
        "mode": "dry_run",
        "ok": True,
        "steps": [
            {"name": "specialist_review_reconciliation", "ok": True, "summary": compact_specialists},
        ],
    })
    check(
        specialist_cycle_brief["specialist_reconciliation"] == "Kairos Longevity Clinic: 6 pendientes en 2 tarjetas",
        "specialist reconciliation should enter cycle brief",
    )
    check(
        "Conciliacion especialistas: Kairos Longevity Clinic: 6 pendientes en 2 tarjetas"
        in format_cycle_brief(specialist_cycle_brief),
        "plain brief should show specialist reconciliation result",
    )
    specialist_proposal_cycle_brief = build_cycle_brief({
        "mode": "dry_run",
        "ok": True,
        "steps": [claim_proposal_step],
    })
    check(
        specialist_proposal_cycle_brief["specialist_claim_proposals"]
        == "1 propuesta privada lista; 5 omitidas porque ya tienen tarjeta",
        "specialist proposal export should enter cycle brief",
    )
    check(
        "Propuestas especialistas: 1 propuesta privada lista; 5 omitidas porque ya tienen tarjeta"
        in format_cycle_brief(specialist_proposal_cycle_brief),
        "plain brief should show specialist proposal export result",
    )
    google_link_cycle_brief = build_cycle_brief({
        "mode": "dry_run",
        "ok": True,
        "steps": [
            {
                "name": "google_link_review_reconciliation",
                "ok": True,
                "summary": compact_google_reconciliation,
            },
        ],
    })
    check(
        google_link_cycle_brief["google_link_reconciliation"] == "1/2 con Maps que no se debe guardar sin corregir",
        "Google reconciliation should enter cycle brief",
    )
    check(
        "Conciliacion Google: 1/2 con Maps que no se debe guardar sin corregir"
        in format_cycle_brief(google_link_cycle_brief),
        "plain brief should show Google reconciliation result",
    )
    consolidation_cycle_brief = build_cycle_brief({
        "mode": "dry_run",
        "ok": True,
        "steps": [
            {
                "name": "consolidate_profile_enrichment_reviews",
                "ok": True,
                "summary": clean_consolidation_step["summary"],
            },
        ],
    })
    check(
        consolidation_cycle_brief["enrichment_consolidation"]
        == "9 campos listos para revisar en 2 grupos (5 tarjetas)",
        "consolidation should enter cycle brief",
    )
    check(
        "Consolidacion mejoras: 9 campos listos para revisar en 2 grupos (5 tarjetas)"
        in format_cycle_brief(consolidation_cycle_brief),
        "plain brief should show consolidation result",
    )
    manual_route_cycle_brief = build_cycle_brief({
        "mode": "dry_run",
        "ok": True,
        "steps": [manual_route_step],
    })
    check(
        manual_route_cycle_brief["manual_review_routes"]
        == "3 abren campo directo; 2 permiten URL oficial; 1 revisables manualmente aunque no listas para LLM; 1 no listas para LLM por fuente sin contexto",
        "manual route status should enter cycle brief",
    )
    check(
        "Rutas revision manual: 3 abren campo directo; 2 permiten URL oficial; 1 revisables manualmente aunque no listas para LLM; 1 no listas para LLM por fuente sin contexto"
        in format_cycle_brief(manual_route_cycle_brief),
        "plain brief should show manual route result",
    )
    steps = build_steps(Namespace(
        apply_safe=False,
        review_limit=2,
        seed_source_limit=12,
        team_source_limit=0,
        team_source_clinic_slug=None,
        team_source_max_links=3,
        google_link_limit=0,
        google_link_clinic_slug=None,
        google_link_replace_existing=False,
        google_link_allow_multiple_open_clinic_reviews=False,
        source_limit=3,
        monitor_limit=4,
        source_change_limit=8,
        source_shadow_limit=0,
        source_shadow_clinic_slug=None,
        source_shadow_replace_existing=False,
        extract_profile_job=False,
        extract_profile_job_replace_existing=False,
        extract_profile_job_allow_multiple_open_clinic_reviews=False,
        digest_limit=5,
        claim_limit=6,
        blocking_claim_limit=9,
        snapshot_retention_days=180,
        snapshot_keep_latest=3,
        snapshot_retention_limit=7,
        source_coverage_limit=10,
        profile_completeness_limit=11,
        publication_readiness=False,
        publication_readiness_clinic="",
        publication_readiness_limit=8,
        backlog_brief_limit=4,
        manual_route_limit=6,
        enrichment_consolidation_limit=6,
        enrichment_consolidation_clinic="",
        google_link_reconciliation=False,
        google_link_reconciliation_clinic="",
        google_link_reconciliation_limit=8,
        specialist_reconciliation=False,
        specialist_reconciliation_clinic="",
        specialist_reconciliation_limit=5,
        specialist_claim_proposals=False,
        specialist_claim_proposals_clinic="",
        specialist_claim_proposal_limit=8,
        fetch_timeout=7,
        strict_editorial=False,
        plain_brief=False,
        production_health=False,
        production_base_url="https://www.vitalarga.com",
        production_timeout=7,
        public_freshness=False,
        public_freshness_slug="",
        public_freshness_clinic="",
        public_freshness_missing_limit=8,
        clinic_visibility=False,
        clinic_visibility_clinic="",
        clinic_visibility_missing_limit=30,
    ))
    names = [step[0] for step in steps]
    check("seed_visible_clinic_sources" in names, "official source seeding step missing")
    check("discover_clinic_team_sources" not in names, "team source discovery should be off by default")
    check("discover_clinic_google_links" not in names, "Google-link discovery should be off by default")
    check("process_source_change_reviews" in names, "source-change processing step missing")
    check("submit_source_shadow_reviews" not in names, "source shadow batch should be off by default")
    check("process_extract_clinic_profile_jobs" not in names, "review-supplied source jobs should be off by default")
    check("check_operational_limits_strict" not in names, "strict editorial scan should be off by default")
    check("check_production_health" not in names, "production health should be off by default")
    check("check_public_site_freshness" not in names, "public freshness should be off by default")
    check("clinic_public_visibility_report" not in names, "clinic visibility should be off by default")
    check("clinic_publication_readiness" not in names, "publication readiness should be off by default")
    check("google_link_review_reconciliation" not in names, "Google reconciliation should be off by default")
    check("specialist_review_reconciliation" not in names, "specialist reconciliation should be off by default")
    check("export_specialist_claim_proposals" not in names, "specialist proposal export should be off by default")
    check("consolidate_profile_enrichment_reviews" in names, "duplicate enrichment consolidation step missing")
    check("submit_blocking_claim_reviews" in names, "blocking-claim review step missing")
    check("measure_source_snapshot_retention" in names, "source snapshot retention step missing")
    check("evaluate_claim_rules" in names, "claim rule evaluation step missing")
    seed_step = [step for step in steps if step[0] == "seed_visible_clinic_sources"][0]
    check("--json" in seed_step[1], "source seeding should be machine readable")
    check("12" in seed_step[1], "seed source limit should pass through")
    hydrate_step = [step for step in steps if step[0] == "hydrate_source_records"][0]
    check(steps.index(seed_step) < steps.index(hydrate_step), "source seeding should run before hydration")
    source_change_step = [step for step in steps if step[0] == "process_source_change_reviews"][0]
    check("8" in source_change_step[1], "source-change limit should be passed through")
    blocking_step = [step for step in steps if step[0] == "submit_blocking_claim_reviews"][0]
    check("9" in blocking_step[1], "blocking-claim limit should be passed through")
    retention_step = [step for step in steps if step[0] == "measure_source_snapshot_retention"][0]
    check("--json" in retention_step[1], "retention report should be machine readable")
    check("180" in retention_step[1] and "3" in retention_step[1] and "7" in retention_step[1], "retention settings should pass through")
    source_coverage_step = [step for step in steps if step[0] == "measure_source_coverage"][0]
    check("--json" in source_coverage_step[1], "source coverage should be machine readable")
    check("10" in source_coverage_step[1], "source coverage limit should pass through")
    profile_step = [step for step in steps if step[0] == "measure_profile_completeness"][0]
    check("--json" in profile_step[1], "profile completeness should be machine readable")
    check("11" in profile_step[1], "profile completeness limit should pass through")
    google_steps = build_steps(Namespace(
        apply_safe=True,
        review_limit=2,
        seed_source_limit=12,
        team_source_limit=0,
        team_source_clinic_slug=None,
        team_source_max_links=3,
        google_link_limit=2,
        google_link_clinic_slug="clinic-a",
        google_link_replace_existing=True,
        google_link_allow_multiple_open_clinic_reviews=True,
        source_limit=3,
        monitor_limit=4,
        source_change_limit=8,
        source_shadow_limit=0,
        source_shadow_clinic_slug=None,
        source_shadow_replace_existing=False,
        extract_profile_job=False,
        extract_profile_job_replace_existing=False,
        extract_profile_job_allow_multiple_open_clinic_reviews=False,
        digest_limit=5,
        claim_limit=6,
        blocking_claim_limit=9,
        snapshot_retention_days=180,
        snapshot_keep_latest=3,
        snapshot_retention_limit=7,
        source_coverage_limit=10,
        profile_completeness_limit=11,
        publication_readiness=False,
        publication_readiness_clinic="",
        publication_readiness_limit=8,
        backlog_brief_limit=4,
        manual_route_limit=6,
        enrichment_consolidation_limit=6,
        enrichment_consolidation_clinic="",
        google_link_reconciliation=False,
        google_link_reconciliation_clinic="",
        google_link_reconciliation_limit=8,
        specialist_reconciliation=False,
        specialist_reconciliation_clinic="",
        specialist_reconciliation_limit=5,
        specialist_claim_proposals=False,
        specialist_claim_proposals_clinic="",
        specialist_claim_proposal_limit=8,
        fetch_timeout=7,
        strict_editorial=False,
        plain_brief=False,
        production_health=False,
        production_base_url="https://www.vitalarga.com",
        production_timeout=7,
        public_freshness=False,
        public_freshness_slug="",
        public_freshness_clinic="",
        public_freshness_missing_limit=8,
        clinic_visibility=False,
        clinic_visibility_clinic="",
        clinic_visibility_missing_limit=30,
    ))
    google_step = [step for step in google_steps if step[0] == "discover_clinic_google_links"][0]
    check("--apply" in google_step[1], "Google-link discovery should honor safe apply")
    check("--clinic-slug" in google_step[1] and "clinic-a" in google_step[1], "Google-link clinic slug should pass through")
    check("--replace-existing" in google_step[1], "Google-link replace flag should pass through")
    check("--allow-multiple-open-clinic-reviews" in google_step[1], "Google-link multiple-review flag should pass through")
    backlog_step = [step for step in steps if step[0] == "review_backlog_brief"][0]
    check("--json" in backlog_step[1], "review backlog brief should be machine readable")
    check("4" in backlog_step[1], "review backlog brief limit should pass through")
    manual_route_step_def = [step for step in steps if step[0] == "manual_review_route_brief"][0]
    check("--preserve-order" in manual_route_step_def[1], "manual route brief should keep dashboard queue order")
    check("6" in manual_route_step_def[1], "manual route limit should pass through")
    consolidation_step_def = [step for step in steps if step[0] == "consolidate_profile_enrichment_reviews"][0]
    check("--json" in consolidation_step_def[1], "consolidation should be machine readable")
    check("6" in consolidation_step_def[1], "consolidation limit should pass through")
    check(steps.index(backlog_step) < steps.index(manual_route_step_def), "manual routes should follow backlog brief")
    check(steps.index(manual_route_step_def) < steps.index(consolidation_step_def), "consolidation should follow manual route brief")
    digest_step = [step for step in steps if step[0] == "admin_digest"][0]
    check(steps.index(consolidation_step_def) < steps.index(digest_step), "consolidation should run before admin digest")
    check("--json" in digest_step[1], "admin digest should be machine readable")
    claim_step = [step for step in steps if step[0] == "evaluate_claim_rules"][0]
    check("--json" in claim_step[1], "claim rule evaluation should be machine readable")
    check("6" in claim_step[1], "claim limit should be passed through")
    optional_steps = build_steps(Namespace(
        apply_safe=True,
        review_limit=2,
        seed_source_limit=12,
        team_source_limit=2,
        team_source_clinic_slug="arvila-magna",
        team_source_max_links=5,
        google_link_limit=0,
        google_link_clinic_slug=None,
        google_link_replace_existing=False,
        google_link_allow_multiple_open_clinic_reviews=False,
        source_limit=3,
        monitor_limit=4,
        source_change_limit=8,
        source_shadow_limit=2,
        source_shadow_clinic_slug="sensabell",
        source_shadow_replace_existing=True,
        extract_profile_job=True,
        extract_profile_job_replace_existing=True,
        extract_profile_job_allow_multiple_open_clinic_reviews=True,
        digest_limit=5,
        claim_limit=6,
        blocking_claim_limit=9,
        snapshot_retention_days=180,
        snapshot_keep_latest=3,
        snapshot_retention_limit=7,
        source_coverage_limit=10,
        profile_completeness_limit=11,
        publication_readiness=True,
        publication_readiness_clinic="Monarka",
        publication_readiness_limit=5,
        backlog_brief_limit=4,
        manual_route_limit=6,
        enrichment_consolidation_limit=4,
        enrichment_consolidation_clinic="Sensabell",
        google_link_reconciliation=True,
        google_link_reconciliation_clinic="Arvila",
        google_link_reconciliation_limit=4,
        specialist_reconciliation=True,
        specialist_reconciliation_clinic="Kairos",
        specialist_reconciliation_limit=3,
        specialist_claim_proposals=True,
        specialist_claim_proposals_clinic="Benzaquen",
        specialist_claim_proposal_limit=4,
        fetch_timeout=7,
        strict_editorial=True,
        plain_brief=True,
        production_health=True,
        production_base_url="https://www.vitalarga.com",
        production_timeout=7,
        public_freshness=True,
        public_freshness_slug="monarka-clinic",
        public_freshness_clinic="Monarka",
        public_freshness_missing_limit=5,
        clinic_visibility=True,
        clinic_visibility_clinic="",
        clinic_visibility_missing_limit=30,
    ))
    source_shadow_step = [step for step in optional_steps if step[0] == "submit_source_shadow_reviews"][0]
    extract_job_step = [step for step in optional_steps if step[0] == "process_extract_clinic_profile_jobs"][0]
    seed_apply_step = [step for step in optional_steps if step[0] == "seed_visible_clinic_sources"][0]
    team_source_step = [step for step in optional_steps if step[0] == "discover_clinic_team_sources"][0]
    google_reconciliation_step = [step for step in optional_steps if step[0] == "google_link_review_reconciliation"][0]
    specialist_reconciliation_step = [step for step in optional_steps if step[0] == "specialist_review_reconciliation"][0]
    specialist_claim_proposal_step = [step for step in optional_steps if step[0] == "export_specialist_claim_proposals"][0]
    focused_consolidation_step = [step for step in optional_steps if step[0] == "consolidate_profile_enrichment_reviews"][0]
    check("--apply" in seed_apply_step[1], "source seeding should follow safe apply mode")
    check("--apply" in team_source_step[1], "team source discovery should follow safe apply mode")
    check("--clinic-slug" in team_source_step[1] and "arvila-magna" in team_source_step[1], "team source clinic slug should pass through")
    check("--max-links-per-clinic" in team_source_step[1] and "5" in team_source_step[1], "team source max links should pass through")
    check(optional_steps.index(seed_apply_step) < optional_steps.index(team_source_step), "team source discovery should run after source seeding")
    check(optional_steps.index(team_source_step) < optional_steps.index(source_shadow_step), "team source discovery should run before source shadow reviews")
    check("--apply" in source_shadow_step[1], "source shadow batch should follow safe apply mode")
    check("--clinic-slug" in source_shadow_step[1] and "sensabell" in source_shadow_step[1], "source shadow clinic slug should pass through")
    check("--replace-existing" in source_shadow_step[1], "source shadow replace flag should pass through")
    check("--apply" in extract_job_step[1], "review-supplied source job should follow safe apply mode")
    check("--pick-next" in extract_job_step[1], "review-supplied source job should pick one queued job")
    check("--compact" in extract_job_step[1], "review-supplied source job should stay compact")
    check("--replace-existing" in extract_job_step[1], "review-supplied source job replace flag should pass through")
    check("--allow-multiple-open-clinic-reviews" in extract_job_step[1], "review-supplied source job multiple-review flag should pass through")
    check(optional_steps.index(extract_job_step) < optional_steps.index(source_shadow_step), "review-supplied source jobs should run before saved-source batches")
    check("--json" in google_reconciliation_step[1], "Google reconciliation should be machine readable")
    check("Arvila" in google_reconciliation_step[1], "Google reconciliation clinic should pass through")
    check("4" in google_reconciliation_step[1], "Google reconciliation limit should pass through")
    check(optional_steps.index(google_reconciliation_step) < optional_steps.index([step for step in optional_steps if step[0] == "admin_digest"][0]), "Google reconciliation should run before admin digest")
    check("--json" in specialist_reconciliation_step[1], "specialist reconciliation should be machine readable")
    check("Kairos" in specialist_reconciliation_step[1], "specialist reconciliation clinic should pass through")
    check("3" in specialist_reconciliation_step[1], "specialist reconciliation limit should pass through")
    check(optional_steps.index(specialist_reconciliation_step) < optional_steps.index([step for step in optional_steps if step[0] == "admin_digest"][0]), "specialist reconciliation should run before admin digest")
    check("--json" in specialist_claim_proposal_step[1], "specialist proposal export should be machine readable")
    check("Benzaquen" in specialist_claim_proposal_step[1], "specialist proposal clinic should pass through")
    check("4" in specialist_claim_proposal_step[1], "specialist proposal limit should pass through")
    check(optional_steps.index(specialist_claim_proposal_step) < optional_steps.index([step for step in optional_steps if step[0] == "admin_digest"][0]), "specialist proposal export should run before admin digest")
    check("Sensabell" in focused_consolidation_step[1], "consolidation clinic should pass through")
    check("4" in focused_consolidation_step[1], "focused consolidation limit should pass through")
    strict_step = [step for step in optional_steps if step[0] == "check_operational_limits_strict"][0]
    check("--strict-editorial" in strict_step[1], "strict editorial flag should pass through")
    health_step = [step for step in optional_steps if step[0] == "check_production_health"][0]
    check(optional_steps.index(strict_step) < optional_steps.index(health_step), "strict editorial should run before production health")
    check("--json" in health_step[1], "production health should be machine readable")
    check("https://www.vitalarga.com" in health_step[1], "production health base URL should pass through")
    check("7" in health_step[1], "production health timeout should pass through")
    freshness_step = [step for step in optional_steps if step[0] == "check_public_site_freshness"][0]
    check(optional_steps.index(health_step) < optional_steps.index(freshness_step), "public freshness should run after production health")
    check("--json" in freshness_step[1], "public freshness should be machine readable")
    check("monarka-clinic" in freshness_step[1], "public freshness clinic slug should pass through")
    check("Monarka" in freshness_step[1], "public freshness clinic name should pass through")
    check("5" in freshness_step[1], "public freshness missing limit should pass through")
    visibility_step = [step for step in optional_steps if step[0] == "clinic_public_visibility_report"][0]
    publication_readiness_step = [step for step in optional_steps if step[0] == "clinic_publication_readiness"][0]
    check(optional_steps.index(health_step) < optional_steps.index(visibility_step), "clinic visibility should run after production health")
    check(optional_steps.index(visibility_step) < optional_steps.index(freshness_step), "clinic visibility should run before public freshness can stop the cycle")
    check("--json" in visibility_step[1], "clinic visibility should be machine readable")
    check("Monarka" in visibility_step[1], "clinic visibility should reuse the normal clinic name")
    check("30" in visibility_step[1], "clinic visibility missing limit should pass through")
    check("--json" in publication_readiness_step[1], "publication readiness should be machine readable")
    check("Monarka" in publication_readiness_step[1], "publication readiness clinic should pass through")
    check("5" in publication_readiness_step[1], "publication readiness limit should pass through")
    check(optional_steps.index(publication_readiness_step) < optional_steps.index([step for step in optional_steps if step[0] == "review_backlog_brief"][0]), "publication readiness should run before backlog brief")
    print("OK cycle: CTO shadow orchestration")


if __name__ == "__main__":
    main()
