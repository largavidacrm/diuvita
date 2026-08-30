#!/usr/bin/env python3
"""Read-only source snapshot retention report for Diuvita."""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any
from urllib.parse import urlparse

from admin_digest import as_int, parse_timestamp
from submit_discovery_candidates import load_env_file, run_psql


DEFAULT_RETENTION_DAYS = 180
DEFAULT_KEEP_LATEST = 3


def load_retention_report(
    retention_days: int,
    keep_latest: int,
    limit: int,
    local_env: dict[str, str],
) -> dict[str, Any]:
    sql = f"""
with ranked as (
  select
    ss.id,
    ss.source_record_id,
    ss.clinic_id,
    ss.source_url,
    ss.retrieved_at,
    ss.created_at,
    c.slug as clinic_slug,
    c.display_name as clinic_name,
    row_number() over (
      partition by ss.source_record_id
      order by ss.retrieved_at desc, ss.created_at desc, ss.id desc
    ) as source_rank
  from public.source_snapshots ss
  left join public.clinics c on c.id = ss.clinic_id
),
policy as (
  select
    *,
    retrieved_at < now() - make_interval(days => {int(retention_days)}) as older_than_retention,
    source_rank > {int(keep_latest)} as beyond_keep_latest
  from ranked
),
source_counts as (
  select
    source_record_id,
    max(source_url) as source_url,
    max(clinic_slug) as clinic_slug,
    max(clinic_name) as clinic_name,
    count(*) as snapshots,
    min(retrieved_at) as oldest_snapshot_at,
    max(retrieved_at) as newest_snapshot_at,
    count(*) filter (where older_than_retention and beyond_keep_latest) as prunable
  from policy
  group by source_record_id
),
summary as (
  select jsonb_build_object(
    'retention_days', {int(retention_days)},
    'keep_latest', {int(keep_latest)},
    'total_snapshots', count(*),
    'sources_with_snapshots', count(distinct source_record_id),
    'older_than_retention', count(*) filter (where older_than_retention),
    'protected_latest', count(*) filter (where older_than_retention and not beyond_keep_latest),
    'prunable_snapshots', count(*) filter (where older_than_retention and beyond_keep_latest),
    'oldest_snapshot_at', min(retrieved_at),
    'newest_snapshot_at', max(retrieved_at)
  ) as data
  from policy
),
top_sources as (
  select coalesce(jsonb_agg(to_jsonb(items) order by items.snapshots desc, items.clinic_name), '[]'::jsonb) as data
  from (
    select *
    from source_counts
    order by snapshots desc, clinic_name
    limit {int(limit)}
  ) items
)
select jsonb_build_object(
  'summary', (select data from summary),
  'top_sources', (select data from top_sources),
  'generated_at', now()
);
"""
    return json.loads(run_psql(sql, local_env))


def source_label(row: dict[str, Any]) -> str:
    clinic = str(row.get("clinic_name") or row.get("clinic_slug") or "sin clinica")
    url = str(row.get("source_url") or "").strip()
    if not url:
        return clinic
    parsed = urlparse(url)
    host = parsed.netloc.replace("www.", "")
    path = parsed.path.rstrip("/")
    short_path = path if len(path) <= 38 else path[:35].rstrip("/") + "..."
    source = host + short_path if host else url[:60]
    return clinic + " | " + source


def plural_count(value: Any, singular: str, plural: str) -> str:
    count = as_int(value)
    return f"{count} {singular if count == 1 else plural}"


def format_retention_report(report: dict[str, Any]) -> str:
    summary = report.get("summary") or {}
    top_sources = report.get("top_sources") or []
    retention_days = as_int(summary.get("retention_days")) or DEFAULT_RETENTION_DAYS
    keep_latest = as_int(summary.get("keep_latest")) or DEFAULT_KEEP_LATEST

    lines = [
        "# Diuvita source snapshot retention",
        "",
        f"Generated: {parse_timestamp(report.get('generated_at'))}",
        "",
        "## Policy preview",
        f"- Keep at least latest snapshots per source: {keep_latest}",
        f"- Consider cleanup only after days: {retention_days}",
        "- Writes data: no",
        "",
        "## Snapshot inventory",
        f"- Total snapshots: {as_int(summary.get('total_snapshots'))}",
        f"- Sources with snapshots: {as_int(summary.get('sources_with_snapshots'))}",
        f"- Older than policy: {as_int(summary.get('older_than_retention'))}",
        f"- Protected as latest evidence: {as_int(summary.get('protected_latest'))}",
        f"- Cleanup candidates: {as_int(summary.get('prunable_snapshots'))}",
        f"- Oldest snapshot: {parse_timestamp(summary.get('oldest_snapshot_at'))}",
        f"- Newest snapshot: {parse_timestamp(summary.get('newest_snapshot_at'))}",
        "",
        "## Sources with most snapshots",
    ]
    if not top_sources:
        lines.append("- No snapshots recorded yet.")
    for row in top_sources:
        lines.append(
            f"- {source_label(row)}: {plural_count(row.get('snapshots'), 'snapshot', 'snapshots')}, "
            f"{plural_count(row.get('prunable'), 'cleanup candidate', 'cleanup candidates')}"
        )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--retention-days", type=int, default=DEFAULT_RETENTION_DAYS)
    parser.add_argument("--keep-latest", type=int, default=DEFAULT_KEEP_LATEST)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--json", action="store_true", help="Print raw JSON.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.retention_days < 30 or args.retention_days > 730:
        raise SystemExit("--retention-days must be between 30 and 730.")
    if args.keep_latest < 1 or args.keep_latest > 20:
        raise SystemExit("--keep-latest must be between 1 and 20.")
    if args.limit < 1:
        raise SystemExit("--limit must be at least 1.")

    report = load_retention_report(
        retention_days=args.retention_days,
        keep_latest=args.keep_latest,
        limit=args.limit,
        local_env=load_env_file(),
    )
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(format_retention_report(report), end="")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
