#!/usr/bin/env python3
"""Read-only audit for review proposals missing source-job context."""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any
from urllib.parse import urlparse

from admin_digest import parse_timestamp
from review_backlog_brief import compact_lookup_key
from submit_discovery_candidates import load_env_file, run_psql, sql_literal


CONTEXT_KEYS = (
    "from_review_id",
    "human_supplied_source",
    "requested_fields",
    "requested_field_labels",
    "primary_requested_fields",
    "primary_requested_field_labels",
    "operator_requested_field_keys",
    "operator_requested_field_labels",
    "operator_requested_field_summary",
    "target_scope",
    "ui_route",
    "allowed_output",
    "llm_boundary",
    "operator_intent",
)

STATUS_LABELS = {
    "context_ready": "listo para LLM",
    "recoverable_from_job": "recuperable desde trabajo",
    "source_without_context": "solo revisión manual",
    "no_source_context": "sin contexto de fuente",
}


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def clean_str(value: Any) -> str:
    return str(value or "").strip()


def compact_url(value: Any, limit: int = 96) -> str:
    clean = clean_str(value)
    return clean if len(clean) <= limit else clean[: limit - 1].rstrip() + "…"


def source_url(payload: dict[str, Any]) -> str:
    url = clean_str(payload.get("source_url"))
    if url:
        return url
    urls = as_list(payload.get("source_urls"))
    return clean_str(urls[0]) if urls else ""


def source_host(value: Any) -> str:
    clean = clean_str(value)
    return urlparse(clean).netloc if clean else ""


def has_context(value: dict[str, Any]) -> bool:
    return any(value.get(key) not in (None, "", [], {}) for key in CONTEXT_KEYS)


def context_subset(value: dict[str, Any]) -> dict[str, Any]:
    return {key: value.get(key) for key in CONTEXT_KEYS if value.get(key) not in (None, "", [], {})}


def status_label(value: Any) -> str:
    clean = clean_str(value)
    return STATUS_LABELS.get(clean, clean or "sin estado")


def audit_row(row: dict[str, Any]) -> dict[str, Any]:
    payload = as_dict(row.get("payload"))
    job_input = as_dict(row.get("job_input"))
    url = source_url(payload) or source_url(job_input)
    payload_has_context = has_context(payload)
    job_has_context = has_context(job_input)
    if payload_has_context:
        status = "context_ready"
        next_step = "la tarjeta ya conserva el contexto de origen para LLM"
    elif job_has_context:
        status = "recoverable_from_job"
        next_step = "puede recuperarse desde agent_jobs antes de pedir ayuda LLM"
    elif url:
        status = "source_without_context"
        next_step = "revisar manualmente; no inferir intención original solo por la URL"
    else:
        status = "no_source_context"
        next_step = "usar la revisión humana normal"
    return {
        "review_id": row.get("id"),
        "title": row.get("title"),
        "clinic_name": row.get("clinic_name") or row.get("clinic_slug"),
        "clinic_slug": row.get("clinic_slug"),
        "created_at": row.get("created_at"),
        "source_host": source_host(url),
        "has_payload_context": payload_has_context,
        "has_job_context": job_has_context,
        "status": status,
        "payload_context": context_subset(payload),
        "job_context": context_subset(job_input),
        "next_step": next_step,
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, int]:
    summary = {
        "cards": len(rows),
        "context_ready": 0,
        "recoverable_from_job": 0,
        "source_without_context": 0,
        "no_source_context": 0,
    }
    for row in rows:
        status = clean_str(row.get("status"))
        if status in summary:
            summary[status] += 1
    return summary


def clinic_lookup_filter(query: str) -> str:
    clean = query.strip()
    if not clean:
        return ""
    literal = sql_literal(clean)
    like = sql_literal(f"%{clean}%")
    compact = sql_literal(f"%{compact_lookup_key(clean)}%")
    return f"""
    and (
      lower(coalesce(c.slug, '')) = lower({literal})
      or c.slug ilike {like}
      or c.display_name ilike {like}
      or rq.title ilike {like}
      or regexp_replace(translate(lower(coalesce(c.slug, '')), 'áéíóúüñ', 'aeiouun'), '[^a-z0-9]+', '', 'g') like {compact}
      or regexp_replace(translate(lower(coalesce(c.display_name, '')), 'áéíóúüñ', 'aeiouun'), '[^a-z0-9]+', '', 'g') like {compact}
    )
"""


def load_audit(query: str, limit: int, local_env: dict[str, str]) -> dict[str, Any]:
    capped_limit = max(1, min(100, int(limit)))
    query_filter = clinic_lookup_filter(query)
    sql = f"""
select jsonb_build_object(
  'query', {sql_literal(query.strip())},
  'generated_at', now(),
  'writes_data', false,
  'items',
  coalesce(jsonb_agg(to_jsonb(items) order by items.created_at desc), '[]'::jsonb)
)
from (
  select
    rq.id,
    rq.title,
    rq.created_at,
    c.slug as clinic_slug,
    c.display_name as clinic_name,
    rq.payload,
    aj.input as job_input
  from public.review_queue rq
  left join public.clinics c on c.id = rq.clinic_id
  left join public.agent_jobs aj on aj.id::text = coalesce(rq.payload ->> 'job_id', '')
  where rq.status = 'open'
    and rq.review_type = 'clinic_profile_enrichment'
    and (
      rq.payload ? 'source_url'
      or rq.payload ? 'source_urls'
      or rq.payload ? 'job_id'
    )
    {query_filter}
  order by rq.created_at desc
  limit {capped_limit}
) items;
"""
    raw = json.loads(run_psql(sql, local_env))
    rows = [audit_row(row) for row in raw.get("items") or [] if isinstance(row, dict)]
    raw["items"] = rows
    raw["summary"] = summarize(rows)
    return raw


def format_report(report: dict[str, Any], compact: bool = False) -> str:
    summary = report.get("summary") or {}
    rows = [row for row in report.get("items") or [] if isinstance(row, dict)]
    lines = [
        "# Vitalarga: contexto de origen para revisiones",
        "",
        f"Generado: {parse_timestamp(report.get('generated_at'))}",
        f"Consulta: {report.get('query') or 'todas las mejoras abiertas'}",
        "- Writes data: no",
        f"- Tarjetas revisadas: {summary.get('cards', 0)}",
        f"- Contexto listo: {summary.get('context_ready', 0)}",
        f"- Recuperable desde trabajo: {summary.get('recoverable_from_job', 0)}",
        f"- Fuente sin contexto: {summary.get('source_without_context', 0)}",
        "",
    ]
    if not rows:
        lines.append("- No hay mejoras abiertas con fuente o trabajo asociado.")
        return "\n".join(lines) + "\n"
    lines.append("## Tarjetas")
    for row in rows[:10 if compact else len(rows)]:
        clinic = row.get("clinic_name") or row.get("clinic_slug") or "sin clínica"
        host = row.get("source_host") or "sin host"
        lines.append(
            f"- {clinic}: {status_label(row.get('status'))} · {host} · {row.get('next_step')}"
        )
        if not compact:
            lines.append(f"  Tarjeta: {row.get('title') or row.get('review_id')}")
    if compact:
        lines.append("")
        lines.append("Nota: salida compacta sin URLs completas ni payloads.")
    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--clinic", default="", help="Clinic name, slug or review-title fragment.")
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--json", action="store_true", help="Print raw JSON.")
    parser.add_argument("--compact", action="store_true", help="Hide card details and long payload context.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.limit < 1:
        raise SystemExit("--limit must be at least 1.")
    report = load_audit(args.clinic, args.limit, load_env_file())
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(format_report(report, compact=args.compact), end="")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
