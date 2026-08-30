#!/usr/bin/env python3
"""Evaluate stored field claims through the deterministic rules engine.

This report is read-only. It shows what the current publication rules would do
with claims already stored in Supabase.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from typing import Any

from diuvita_rules import RiskPolicy, decide_claim
from submit_discovery_candidates import (
    get_default_admin_email,
    load_env_file,
    run_psql,
    sql_literal,
)


ALLOWED_STATUSES = {"proposed", "accepted", "rejected", "stale", "conflict", "review"}
DEFAULT_LIMIT = 100


def as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "si", "sí", "on"}
    return bool(value)


def pct(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "0%"
    return f"{round(max(0.0, min(1.0, number)) * 100)}%"


def safe_limit(raw_limit: int) -> int:
    return max(1, min(1000, int(raw_limit or DEFAULT_LIMIT)))


def load_automation(admin_email: str, local_env: dict[str, str]) -> dict[str, Any]:
    sql = f"""
with claims as (
  select set_config(
    'request.jwt.claims',
    jsonb_build_object('email', {sql_literal(admin_email)})::text,
    true
  )
)
select public.admin_dashboard_summary() -> 'automation'
from claims;
"""
    return json.loads(run_psql(sql, local_env))


def load_claim_rows(
    admin_email: str,
    local_env: dict[str, str],
    *,
    limit: int,
    status: str | None = None,
    clinic_slug: str | None = None,
) -> list[dict[str, Any]]:
    status_filter = ""
    if status:
        status_filter = f"and fc.verification_status = {sql_literal(status)}"
    slug_filter = ""
    if clinic_slug:
        slug_filter = f"and c.slug = {sql_literal(clinic_slug)}"
    sql = f"""
with claims as (
  select set_config(
    'request.jwt.claims',
    jsonb_build_object('email', {sql_literal(admin_email)})::text,
    true
  )
),
rows as (
  select
    fc.id,
    fc.clinic_id,
    c.slug as clinic_slug,
    c.display_name as clinic_name,
    fc.field_path,
    fc.value,
    fc.source_record_id,
    fc.agent_name,
    fc.agent_version,
    fc.confidence,
    fc.verification_status,
    fc.human_locked,
    fc.created_at
  from public.field_claims fc
  join public.clinics c on c.id = fc.clinic_id
  where true
    {status_filter}
    {slug_filter}
  order by fc.created_at desc
  limit {safe_limit(limit)}
)
select coalesce(jsonb_agg(to_jsonb(rows)), '[]'::jsonb)
from rows;
"""
    return json.loads(run_psql(sql, local_env))


def policy_from_automation(automation: dict[str, Any], preview_low_risk_autopublish: bool) -> RiskPolicy:
    return RiskPolicy(
        auto_publish_enabled=preview_low_risk_autopublish or as_bool(automation.get("auto_publish_enabled")),
        low_auto_publish_enabled=True,
        medium_auto_publish_enabled=False,
        high_auto_publish_enabled=False,
    )


def claim_input(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "field_path": row.get("field_path"),
        "value": row.get("value"),
        "confidence": row.get("confidence"),
        "verification_status": row.get("verification_status"),
        "human_locked": row.get("human_locked"),
        "source_count": 1 if row.get("source_record_id") else 0,
    }


def evaluate_rows(rows: list[dict[str, Any]], policy: RiskPolicy) -> list[dict[str, Any]]:
    evaluations = []
    for row in rows:
        decision = decide_claim(claim_input(row), policy)
        evaluations.append({
            "claim_id": row.get("id"),
            "clinic_slug": row.get("clinic_slug"),
            "clinic_name": row.get("clinic_name"),
            "field_path": row.get("field_path"),
            "verification_status": row.get("verification_status"),
            "source_record_id": row.get("source_record_id"),
            "agent_name": row.get("agent_name"),
            "decision": decision,
        })
    return evaluations


def summarize(evaluations: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    actions = Counter(str(item.get("decision", {}).get("action") or "review") for item in evaluations)
    risks = Counter(str(item.get("decision", {}).get("risk") or "high") for item in evaluations)
    reasons = Counter(str(item.get("decision", {}).get("reason") or "unknown") for item in evaluations)
    return {
        "actions": dict(actions),
        "risks": dict(risks),
        "reasons": dict(reasons),
    }


def format_report(evaluations: list[dict[str, Any]], mode: str) -> str:
    summary = summarize(evaluations)
    lines = [
        "# Diuvita claim rule evaluation",
        f"- Mode: {mode}",
        "- Database writes: none",
        "- Public changes: none",
        f"- Claims evaluated: {len(evaluations)}",
        "## Actions",
    ]
    for action in ["auto_accept", "review", "reject"]:
        lines.append(f"- {action}: {summary['actions'].get(action, 0)}")
    lines.append("## Risk tiers")
    for risk in ["low", "medium", "high"]:
        lines.append(f"- {risk}: {summary['risks'].get(risk, 0)}")
    lines.append("## Main blockers")
    for reason, count in Counter(summary["reasons"]).most_common(5):
        lines.append(f"- {count}x {reason}")
    if not evaluations:
        lines.append("- No claims matched the selected filters.")
    else:
        lines.append("## Sample decisions")
        for item in evaluations[:15]:
            decision = item["decision"]
            clinic = item.get("clinic_name") or item.get("clinic_slug") or "clinic"
            lines.append(
                f"- {decision['action']} · {decision['risk']} · {pct(decision['confidence'])} · "
                f"{clinic} · {item.get('field_path')} · {decision['reason']}"
            )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--admin-email", help="Admin email used for protected read-only queries.")
    parser.add_argument("--clinic-slug", help="Limit evaluation to one clinic.")
    parser.add_argument("--status", choices=sorted(ALLOWED_STATUSES), help="Limit evaluation to one claim status.")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="Maximum claims to evaluate.")
    parser.add_argument(
        "--preview-low-risk-autopublish",
        action="store_true",
        help="Simulate low-risk auto-publish being enabled without writing anything.",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    local_env = load_env_file()
    admin_email = args.admin_email or get_default_admin_email(local_env)
    automation = load_automation(admin_email, local_env)
    policy = policy_from_automation(automation, args.preview_low_risk_autopublish)
    rows = load_claim_rows(
        admin_email,
        local_env,
        limit=args.limit,
        status=args.status,
        clinic_slug=args.clinic_slug,
    )
    evaluations = evaluate_rows(rows, policy)
    mode = "low-risk auto-publish preview" if args.preview_low_risk_autopublish else "current Supabase policy"
    payload = {
        "mode": mode,
        "summary": summarize(evaluations),
        "evaluations": evaluations,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(format_report(evaluations, mode))
    return 0


if __name__ == "__main__":
    sys.exit(main())
