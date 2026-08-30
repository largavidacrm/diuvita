#!/usr/bin/env python3
"""Checks for the CTO shadow cycle orchestrator."""
from argparse import Namespace

from run_cto_shadow_cycle import (
    build_cycle_brief,
    build_steps,
    compact_summary,
    format_cycle_brief,
    open_review_count_from_digest,
    skipped_step,
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
    cycle_digest = {
        "summary": {
            "reviews": {"open": 45},
            "jobs": {"failed": 0, "dead_letter": 0},
            "automation": {"auto_publish_enabled": False, "shadow_mode_active": True},
        },
        "reviews_by_type": [{"review_type": "blocking_claim_review", "open_count": 1}],
        "open_reviews": [{"review_type": "blocking_claim_review", "priority": 95}],
        "profile_completeness": {"pending_specialists": 17, "pending_contact": 6},
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
    }
    cycle_brief = build_cycle_brief({
        "mode": "dry_run",
        "ok": True,
        "steps": [{"name": "admin_digest", "ok": True, "summary": cycle_digest}],
    })
    check(cycle_brief["status"] == "ok", "clean cycle should be OK")
    check(cycle_brief["next_action"] == "Revisar claim bloqueante", "Daniel brief should keep next action")
    check(cycle_brief["profile_gap"] == "Especialistas · 17 fichas", "Daniel brief should keep top profile gap")
    check("Sensabell" in cycle_brief["profile_next"], "Daniel brief should keep next profile target")
    check("11/19 fichas con fuente" in cycle_brief["source_gap"], "Daniel brief should keep source coverage")
    check("Kairos Longevity Clinic" in cycle_brief["source_next"], "Daniel brief should keep next source target")
    check("crear borrador no publica" in cycle_brief["publication_guard"].lower(), "publication guard should be explicit")
    brief_text = format_cycle_brief(cycle_brief)
    check("# Vitalarga: resumen CTO automatico" in brief_text, "plain brief title missing")
    check("Que mirar primero: Revisar claim bloqueante." in brief_text, "plain brief next action missing")
    check("Siguiente ficha: Revisar Sensabell" in brief_text, "plain brief next profile missing")
    check("Cobertura fuentes: 11/19 fichas con fuente" in brief_text, "plain brief source coverage missing")
    check("Siguiente fuente: Revisar 2 claims bloqueantes de Kairos Longevity Clinic" in brief_text, "plain brief source target missing")
    check(open_review_count_from_digest(cycle_digest) == 45, "open review count should be readable for guards")
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
    steps = build_steps(Namespace(
        apply_safe=False,
        review_limit=2,
        seed_source_limit=12,
        team_source_limit=0,
        team_source_clinic_slug=None,
        team_source_max_links=3,
        source_limit=3,
        monitor_limit=4,
        source_change_limit=8,
        source_shadow_limit=0,
        source_shadow_clinic_slug=None,
        source_shadow_replace_existing=False,
        digest_limit=5,
        claim_limit=6,
        blocking_claim_limit=9,
        snapshot_retention_days=180,
        snapshot_keep_latest=3,
        snapshot_retention_limit=7,
        source_coverage_limit=10,
        profile_completeness_limit=11,
        backlog_brief_limit=4,
        fetch_timeout=7,
        strict_editorial=False,
        plain_brief=False,
        production_health=False,
        production_base_url="https://www.vitalarga.com",
        production_timeout=7,
    ))
    names = [step[0] for step in steps]
    check("seed_visible_clinic_sources" in names, "official source seeding step missing")
    check("discover_clinic_team_sources" not in names, "team source discovery should be off by default")
    check("process_source_change_reviews" in names, "source-change processing step missing")
    check("submit_source_shadow_reviews" not in names, "source shadow batch should be off by default")
    check("check_operational_limits_strict" not in names, "strict editorial scan should be off by default")
    check("check_production_health" not in names, "production health should be off by default")
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
    backlog_step = [step for step in steps if step[0] == "review_backlog_brief"][0]
    check("--json" in backlog_step[1], "review backlog brief should be machine readable")
    check("4" in backlog_step[1], "review backlog brief limit should pass through")
    digest_step = [step for step in steps if step[0] == "admin_digest"][0]
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
        source_limit=3,
        monitor_limit=4,
        source_change_limit=8,
        source_shadow_limit=2,
        source_shadow_clinic_slug="sensabell",
        source_shadow_replace_existing=True,
        digest_limit=5,
        claim_limit=6,
        blocking_claim_limit=9,
        snapshot_retention_days=180,
        snapshot_keep_latest=3,
        snapshot_retention_limit=7,
        source_coverage_limit=10,
        profile_completeness_limit=11,
        backlog_brief_limit=4,
        fetch_timeout=7,
        strict_editorial=True,
        plain_brief=True,
        production_health=True,
        production_base_url="https://www.vitalarga.com",
        production_timeout=7,
    ))
    source_shadow_step = [step for step in optional_steps if step[0] == "submit_source_shadow_reviews"][0]
    seed_apply_step = [step for step in optional_steps if step[0] == "seed_visible_clinic_sources"][0]
    team_source_step = [step for step in optional_steps if step[0] == "discover_clinic_team_sources"][0]
    check("--apply" in seed_apply_step[1], "source seeding should follow safe apply mode")
    check("--apply" in team_source_step[1], "team source discovery should follow safe apply mode")
    check("--clinic-slug" in team_source_step[1] and "arvila-magna" in team_source_step[1], "team source clinic slug should pass through")
    check("--max-links-per-clinic" in team_source_step[1] and "5" in team_source_step[1], "team source max links should pass through")
    check(optional_steps.index(seed_apply_step) < optional_steps.index(team_source_step), "team source discovery should run after source seeding")
    check(optional_steps.index(team_source_step) < optional_steps.index(source_shadow_step), "team source discovery should run before source shadow reviews")
    check("--apply" in source_shadow_step[1], "source shadow batch should follow safe apply mode")
    check("--clinic-slug" in source_shadow_step[1] and "sensabell" in source_shadow_step[1], "source shadow clinic slug should pass through")
    check("--replace-existing" in source_shadow_step[1], "source shadow replace flag should pass through")
    strict_step = [step for step in optional_steps if step[0] == "check_operational_limits_strict"][0]
    check("--strict-editorial" in strict_step[1], "strict editorial flag should pass through")
    health_step = [step for step in optional_steps if step[0] == "check_production_health"][0]
    check(optional_steps.index(strict_step) < optional_steps.index(health_step), "strict editorial should run before production health")
    check("--json" in health_step[1], "production health should be machine readable")
    check("https://www.vitalarga.com" in health_step[1], "production health base URL should pass through")
    check("7" in health_step[1], "production health timeout should pass through")
    print("OK cycle: CTO shadow orchestration")


if __name__ == "__main__":
    main()
