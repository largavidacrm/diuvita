#!/usr/bin/env python3
"""Run the local Vitalarga safety checks used before commits."""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

TEST_STEPS = [
    ("test: source snapshots", "scripts/test_capture_source_snapshot.py"),
    ("test: durable source rows", "scripts/test_source_snapshot_records.py"),
    ("test: source snapshot retention", "scripts/test_measure_source_snapshot_retention.py"),
    ("test: production health formatter", "scripts/test_check_production_health.py"),
    ("test: public-site freshness formatter", "scripts/test_check_public_site_freshness.py"),
    ("test: local dashboard server", "scripts/test_serve_local_dashboard.py"),
    ("test: clinic public visibility report", "scripts/test_clinic_public_visibility_report.py"),
    ("test: Netlify deploy guard", "scripts/test_netlify_ignore_build.py"),
    ("test: public-site rebuild control", "scripts/test_public_site_rebuild_pending_control.py"),
    ("test: operational limits", "scripts/test_check_operational_limits.py"),
    ("test: publication rules", "scripts/test_vitalarga_rules.py"),
    ("test: claim rule evaluation", "scripts/test_evaluate_claim_rules.py"),
    ("test: shadow extraction", "scripts/test_extract_clinic_profile_shadow.py"),
    ("test: shadow verification", "scripts/test_verify_clinic_profile_shadow.py"),
    ("test: candidate secondary-source enrichment", "scripts/test_enrich_candidate_review_from_url.py"),
    ("test: candidate team-page enrichment", "scripts/test_enrich_candidate_reviews_from_team_pages.py"),
    ("test: review submission", "scripts/test_submit_shadow_extraction_review.py"),
    ("test: manual profile enrichment submission", "scripts/test_submit_profile_enrichment_reviews.py"),
    ("test: source shadow reviews", "scripts/test_submit_source_shadow_reviews.py"),
    ("test: source shadow claim capture", "scripts/test_capture_source_shadow_claims.py"),
    ("test: admin review filters", "scripts/test_admin_review_filters.py"),
    ("test: admin review case panel", "scripts/test_admin_review_case_panel.py"),
    ("test: admin review actions", "scripts/test_admin_review_actions.py"),
    ("test: admin control sidebar", "scripts/test_admin_control_sidebar.py"),
    ("test: admin publication flow", "scripts/test_admin_publication_flow.py"),
    ("test: admin clinic diff", "scripts/test_admin_clinic_diff.py"),
    ("test: admin location transparency", "scripts/test_admin_location_transparency_fields.py"),
    ("test: admin claim rules", "scripts/test_admin_claim_rules.py"),
    ("test: admin blocking claim labels", "scripts/test_admin_blocking_claim_labels.py"),
    ("test: admin maturity status", "scripts/test_admin_maturity_status.py"),
    ("test: admin source monitoring status", "scripts/test_admin_source_monitoring_status.py"),
    ("test: admin source coverage status", "scripts/test_admin_source_coverage_status.py"),
    ("test: admin snapshot retention status", "scripts/test_admin_snapshot_retention_status.py"),
    ("test: admin specialist coverage status", "scripts/test_admin_specialist_coverage_status.py"),
    ("test: admin profile completeness status", "scripts/test_admin_profile_completeness_status.py"),
    ("test: admin public health status", "scripts/test_admin_public_health_status.py"),
    ("test: admin publication control status", "scripts/test_admin_publication_control_status.py"),
    ("test: admin review backlog quality", "scripts/test_admin_review_backlog_quality.py"),
    ("test: admin next action", "scripts/test_admin_next_action.py"),
    ("test: public home simplified", "scripts/test_public_home_simplified.py"),
    ("test: public profile UX", "scripts/test_public_profile_ux.py"),
    ("test: public site assets", "scripts/test_public_site_assets.py"),
    ("test: public legal identity", "scripts/test_public_legal_identity.py"),
    ("test: static data validation", "scripts/test_validate_data.py"),
    ("test: admin digest", "scripts/test_admin_digest.py"),
    ("test: clinic publication readiness", "scripts/test_clinic_publication_readiness.py"),
    ("test: Daniel review brief", "scripts/test_daniel_review_brief.py"),
    ("test: global plan status", "scripts/test_global_plan_status.py"),
    ("test: blocking claim brief", "scripts/test_blocking_claim_brief.py"),
    ("test: review backlog brief", "scripts/test_review_backlog_brief.py"),
    ("test: enrichment consolidation", "scripts/test_consolidate_profile_enrichment_reviews.py"),
    ("test: review maturity", "scripts/test_measure_review_maturity.py"),
    ("test: specialist coverage", "scripts/test_measure_specialist_coverage.py"),
    ("test: specialist reconciliation", "scripts/test_specialist_review_reconciliation.py"),
    ("test: specialist claim proposal export", "scripts/test_export_specialist_claim_proposals.py"),
    ("test: location coverage", "scripts/test_measure_location_coverage.py"),
    ("test: profile completeness", "scripts/test_measure_profile_completeness.py"),
    ("test: source coverage", "scripts/test_measure_source_coverage.py"),
    ("test: visible source seeding", "scripts/test_seed_visible_clinic_sources.py"),
    ("test: team source discovery", "scripts/test_discover_clinic_team_sources.py"),
    ("test: location source discovery", "scripts/test_discover_clinic_location_sources.py"),
    ("test: Google link discovery", "scripts/test_discover_clinic_google_links.py"),
    ("test: Google link reconciliation", "scripts/test_google_link_review_reconciliation.py"),
    ("test: enrichment claims", "scripts/test_capture_enrichment_review_claims.py"),
    ("test: blocking claim reviews", "scripts/test_submit_blocking_claim_reviews.py"),
    ("test: candidate promotion gate", "scripts/test_promote_candidate_reviews.py"),
    ("test: source hydration", "scripts/test_hydrate_source_records.py"),
    ("test: source monitoring", "scripts/test_monitor_source_changes.py"),
    ("test: source change processing", "scripts/test_process_source_change_reviews.py"),
    ("test: Google Maps URL rules", "scripts/test_google_maps_url_rules.py"),
    ("test: CTO shadow cycle", "scripts/test_run_cto_shadow_cycle.py"),
]

PYTHON_SCRIPTS = sorted(str(path.relative_to(ROOT)) for path in (ROOT / "scripts").glob("*.py"))

ADMIN_JS_CHECK = r"""
const fs = require('fs');
const vm = require('vm');
const h = fs.readFileSync('admin/index.html', 'utf8');
const scripts = [...h.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)]
  .map(m => m[1])
  .filter(s => s.includes('(function ()'));
for (const s of scripts) new vm.Script(s);
console.log('OK admin JS syntax');
"""


@dataclass(frozen=True)
class CheckStep:
    label: str
    command: list[str]
    timeout: int


def print_output(title: str, text: str) -> None:
    clean = text.strip()
    if not clean:
        return
    print(f"{title}:")
    for line in clean.splitlines()[-80:]:
        print(f"  {line}")


def run_step(step: CheckStep) -> bool:
    started = time.time()
    print(f"RUN {step.label}", flush=True)
    result = subprocess.run(
        step.command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=step.timeout,
        check=False,
    )
    duration = round(time.time() - started, 2)
    if result.returncode == 0:
        print(f"OK  {step.label} ({duration}s)")
        return True
    print(f"FAIL {step.label} ({duration}s, exit {result.returncode})")
    print_output("stdout", result.stdout)
    print_output("stderr", result.stderr)
    return False


def build_steps(skip_build: bool) -> list[CheckStep]:
    steps: list[CheckStep] = [
        CheckStep("python syntax", [sys.executable, "-m", "py_compile", *PYTHON_SCRIPTS], 60),
    ]
    steps.extend(CheckStep(label, [sys.executable, script], 60) for label, script in TEST_STEPS)
    steps.append(CheckStep("operational limits scan", [sys.executable, "scripts/check_operational_limits.py"], 60))
    steps.append(CheckStep("clinic data validation", [sys.executable, "scripts/validate_data.py"], 60))
    if not skip_build:
        steps.append(CheckStep("static site build", [sys.executable, "build.py"], 120))
        steps.append(CheckStep("built-site public profile UX", [sys.executable, "scripts/check_built_public_profile_ux.py"], 60))
        steps.append(CheckStep("built-site operational limits scan", [sys.executable, "scripts/check_operational_limits.py", "--built-site"], 60))
    steps.append(CheckStep("admin JavaScript syntax", ["node", "-e", ADMIN_JS_CHECK], 60))
    steps.append(CheckStep("whitespace check", ["git", "diff", "--check"], 60))
    return steps


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-build", action="store_true", help="Skip static site build.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    steps = build_steps(args.skip_build)
    for step in steps:
        if not run_step(step):
            return 1
    print(f"OK local checks: {len(steps)} checks passed")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
