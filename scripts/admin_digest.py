#!/usr/bin/env python3
"""Print a compact internal CTO digest from Supabase.

The digest is read-only. It summarizes admin dashboard status, open review
items, recent failed jobs and recorded job cost.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from typing import Any

from submit_discovery_candidates import (
    get_default_admin_email,
    load_env_file,
    run_psql,
    sql_literal,
)


def as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def as_money(cents: Any) -> str:
    return f"{as_int(cents) / 100:.2f}"


def parse_timestamp(value: Any) -> str:
    if not value:
        return "-"
    text = str(value)
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return text[:16]


def load_digest(admin_email: str, limit: int, local_env: dict[str, str]) -> dict[str, Any]:
    sql = f"""
with claims as (
  select set_config(
    'request.jwt.claims',
    jsonb_build_object('email', {sql_literal(admin_email)})::text,
    true
  )
),
summary as (
  select public.admin_dashboard_summary() as data
  from claims
),
typed_reviews as (
  select
    case
      when review_type = 'clinic_quality_audit'
        and payload ->> 'quality_context' = 'blocking_claims'
        then 'blocking_claim_review'
      else review_type
    end as review_type,
    created_at,
    updated_at
  from public.review_queue
  where status = 'open'
),
reviews_by_type as (
  select coalesce(jsonb_agg(to_jsonb(grouped) order by grouped.open_count desc), '[]'::jsonb) as data
  from (
    select
      review_type,
      count(*) as open_count,
      min(created_at) as oldest_created_at,
      max(updated_at) as newest_updated_at
    from typed_reviews
    group by review_type
  ) grouped
),
open_reviews as (
  select coalesce(jsonb_agg(to_jsonb(items) order by items.priority desc, items.created_at asc), '[]'::jsonb) as data
  from (
    select
      rq.id,
      rq.review_type as raw_review_type,
      case
        when rq.review_type = 'clinic_quality_audit'
          and rq.payload ->> 'quality_context' = 'blocking_claims'
          then 'blocking_claim_review'
        else rq.review_type
      end as review_type,
      rq.title,
      rq.priority,
      rq.created_at,
      rq.updated_at,
      c.slug as clinic_slug,
      c.display_name as clinic_name
    from public.review_queue rq
    left join public.clinics c on c.id = rq.clinic_id
    where rq.status = 'open'
    order by rq.priority desc, rq.created_at asc
    limit {int(limit)}
  ) items
),
recent_failed_jobs as (
  select coalesce(jsonb_agg(to_jsonb(items) order by items.updated_at desc), '[]'::jsonb) as data
  from (
    select
      id,
      job_type,
      status,
      attempts,
      error_message,
      updated_at
    from public.agent_jobs
    where status in ('failed', 'dead_letter')
    order by updated_at desc
    limit {int(limit)}
  ) items
),
recent_jobs_by_type as (
  select coalesce(jsonb_agg(to_jsonb(grouped) order by grouped.total desc), '[]'::jsonb) as data
  from (
    select
      job_type,
      count(*) as total,
      count(*) filter (where status = 'queued') as queued,
      count(*) filter (where status = 'running') as running,
      count(*) filter (where status = 'completed') as completed,
      count(*) filter (where status in ('failed', 'dead_letter')) as failed,
      coalesce(sum(cost_cents), 0) as cost_cents
    from public.agent_jobs
    where created_at >= now() - interval '7 days'
    group by job_type
  ) grouped
),
costs as (
  select jsonb_build_object(
    'last_24h_cents', coalesce(sum(cost_cents) filter (where created_at >= now() - interval '24 hours'), 0),
    'last_7d_cents', coalesce(sum(cost_cents) filter (where created_at >= now() - interval '7 days'), 0),
    'all_time_cents', coalesce(sum(cost_cents), 0)
  ) as data
  from public.agent_jobs
),
claim_quality as (
  select jsonb_build_object(
    'conflict', count(*) filter (where verification_status = 'conflict'),
    'rejected', count(*) filter (where verification_status = 'rejected'),
    'without_source', count(*) filter (where source_record_id is null)
  ) as data
  from public.field_claims
),
monitorable_sources as (
  select
    sr.id,
    coalesce(latest.latest_snapshot_at, sr.retrieved_at) as last_checked_at,
    nullif(regexp_replace(coalesce(sr.metadata ->> 'monitor_cadence_days', ''), '[^0-9]', '', 'g'), '')::int as explicit_cadence_days,
    lower(trim(coalesce(sr.metadata ->> 'monitor_tier', ''))) as monitor_tier
  from public.source_records sr
  left join lateral (
    select max(ss.retrieved_at) as latest_snapshot_at
    from public.source_snapshots ss
    where ss.source_record_id = sr.id
  ) latest on true
  where sr.entity_type = 'clinic'
    and sr.content_hash is not null
    and sr.source_url ~* '^https?://'
),
source_cadences as (
  select
    id,
    last_checked_at,
    case
      when explicit_cadence_days is not null then least(90, greatest(7, explicit_cadence_days))
      when monitor_tier in ('weekly', 'high', '7', '7d') then 7
      when monitor_tier in ('slow', 'low', '90', '90d') then 90
      else 30
    end as cadence_days
  from monitorable_sources
),
source_monitoring as (
  select jsonb_build_object(
    'candidate_sources', count(*),
    'due_sources', count(*) filter (
      where last_checked_at is null
        or last_checked_at + make_interval(days => cadence_days) <= now()
    ),
    'never_checked_sources', count(*) filter (where last_checked_at is null),
    'weekly_sources', count(*) filter (where cadence_days = 7),
    'standard_sources', count(*) filter (where cadence_days = 30),
    'slow_sources', count(*) filter (where cadence_days = 90),
    'custom_sources', count(*) filter (where cadence_days not in (7, 30, 90)),
    'oldest_last_checked_at', min(last_checked_at),
    'oldest_due_at', min(last_checked_at + make_interval(days => cadence_days)) filter (
      where last_checked_at is not null
        and last_checked_at + make_interval(days => cadence_days) <= now()
    ),
    'next_due_at', min(last_checked_at + make_interval(days => cadence_days)) filter (
      where last_checked_at is not null
        and last_checked_at + make_interval(days => cadence_days) > now()
    )
  ) as data
  from source_cadences
),
visible_specialist_rows as (
  select
    c.id,
    case
      when jsonb_typeof(c.current_data -> 'profesionales') = 'array'
        then jsonb_array_length(c.current_data -> 'profesionales')
      else 0
    end as specialist_entries
  from public.clinics c
  where c.status in ('published', 'preliminary')
),
specialist_coverage as (
  select jsonb_build_object(
    'visible_clinics', count(*),
    'with_specialists', count(*) filter (where specialist_entries > 0),
    'without_specialists', count(*) filter (where specialist_entries = 0),
    'total_specialist_entries', coalesce(sum(specialist_entries), 0)
  ) as data
  from visible_specialist_rows
)
select jsonb_build_object(
  'admin_email', {sql_literal(admin_email)},
  'summary', (select data from summary),
  'reviews_by_type', (select data from reviews_by_type),
  'open_reviews', (select data from open_reviews),
  'recent_failed_jobs', (select data from recent_failed_jobs),
  'recent_jobs_by_type', (select data from recent_jobs_by_type),
  'costs', (select data from costs),
  'claim_quality', (select data from claim_quality),
  'source_monitoring', (select data from source_monitoring),
  'specialist_coverage', (select data from specialist_coverage),
  'generated_at', now()
);
"""
    return json.loads(run_psql(sql, local_env))


def line(label: str, value: Any) -> str:
    return f"- {label}: {value}"


def format_review_type(review_type: str) -> str:
    labels = {
        "candidate_clinic": "clinicas candidatas",
        "clinic_profile_enrichment": "mejoras de ficha",
        "clinic_quality_audit": "auditorias de calidad",
        "blocking_claim_review": "claims bloqueantes",
        "source_change_detected": "cambios de fuente",
    }
    return labels.get(review_type, review_type.replace("_", " "))


def maturity_blockers(digest: dict[str, Any]) -> list[str]:
    summary = digest.get("summary") or {}
    automation = summary.get("automation") or {}
    jobs = summary.get("jobs") or {}
    claim_quality = digest.get("claim_quality") or {}
    completed = as_int(automation.get("candidate_reviews_completed"))
    target = as_int(automation.get("shadow_review_target")) or 200
    failed_jobs = as_int(jobs.get("failed")) + as_int(jobs.get("dead_letter"))
    conflicts = as_int(claim_quality.get("conflict"))
    rejected = as_int(claim_quality.get("rejected"))
    without_source = as_int(claim_quality.get("without_source"))
    blockers = []
    if completed < target:
        blockers.append(f"muestra humana insuficiente: {completed}/{target} candidatas")
    if failed_jobs:
        blockers.append(f"{failed_jobs} trabajos fallidos")
    if conflicts:
        blockers.append(f"{conflicts} claims en conflicto")
    if rejected:
        blockers.append(f"{rejected} claims rechazados")
    if without_source:
        blockers.append(f"{without_source} claims sin fuente")
    return blockers


def next_action_label(digest: dict[str, Any]) -> str:
    failed = digest.get("recent_failed_jobs") or []
    open_reviews = digest.get("open_reviews") or []
    reviews_by_type = {
        str(item.get("review_type") or ""): as_int(item.get("open_count"))
        for item in digest.get("reviews_by_type") or []
        if isinstance(item, dict)
    }
    if failed:
        return "Revisar fallos recientes"
    if reviews_by_type.get("blocking_claim_review"):
        return "Revisar claim bloqueante"
    if any(item.get("review_type") == "candidate_clinic" and as_int(item.get("priority")) >= 90 for item in open_reviews):
        return "Validar candidatas"
    if reviews_by_type.get("candidate_clinic"):
        return "Validar candidatas"
    if reviews_by_type.get("source_change_detected"):
        return "Revisar cambios de fuente"
    if reviews_by_type.get("clinic_profile_enrichment"):
        return "Mejorar fichas existentes"
    if reviews_by_type.get("clinic_quality_audit"):
        return "Completar fichas"
    return "Sin accion urgente"


def format_digest(digest: dict[str, Any]) -> str:
    summary = digest.get("summary") or {}
    clinics = summary.get("clinics") or {}
    reviews = summary.get("reviews") or {}
    jobs = summary.get("jobs") or {}
    evidence = summary.get("evidence") or {}
    automation = summary.get("automation") or {}
    costs = digest.get("costs") or {}
    source_monitoring = digest.get("source_monitoring") or {}
    specialist_coverage = digest.get("specialist_coverage") or {}

    output: list[str] = []
    output.append("# Diuvita CTO digest")
    output.append("")
    output.append(f"Generado: {parse_timestamp(digest.get('generated_at') or summary.get('generated_at'))}")
    output.append("")

    output.append("## Estado general")
    output.append(line("Clinicas totales", as_int(clinics.get("total"))))
    output.append(line("Publicadas", as_int(clinics.get("published"))))
    output.append(line("Preliminares", as_int(clinics.get("preliminary"))))
    output.append(line("Pendientes de revision", as_int(reviews.get("open"))))
    output.append(line("Fuentes guardadas", as_int(evidence.get("sources"))))
    output.append(line("Capturas guardadas", as_int(evidence.get("snapshots"))))
    output.append(line("Claims guardados", as_int(evidence.get("claims"))))
    specialist_visible = as_int(specialist_coverage.get("visible_clinics"))
    specialist_with = as_int(specialist_coverage.get("with_specialists"))
    if specialist_visible:
        output.append(line("Fichas con especialistas", f"{specialist_with}/{specialist_visible}"))
    output.append("")

    output.append("## Automatizacion")
    auto_publish = bool(automation.get("auto_publish_enabled"))
    output.append(line("Agentes activos", "si" if automation.get("agents_enabled") else "no"))
    output.append(line("Auto-publicacion", "activada" if auto_publish else "desactivada"))
    output.append(line("Modo sombra", "activo" if automation.get("shadow_mode_active") else "inactivo"))
    if automation.get("shadow_review_target") is not None:
        completed = as_int(automation.get("candidate_reviews_completed"))
        target = as_int(automation.get("shadow_review_target"))
        output.append(line("Revision humana inicial", f"{completed}/{target} candidatas"))
    output.append("")

    output.append("## Madurez para auto-publicacion")
    blockers = maturity_blockers(digest)
    output.append(line("Bajo riesgo", "lista" if not blockers else "no lista"))
    if blockers:
        output.append(line("Motivo principal", blockers[0]))
    output.append("")

    output.append("## Trabajo abierto")
    output.append(line("Jobs en cola", as_int(jobs.get("queued"))))
    output.append(line("Jobs corriendo", as_int(jobs.get("running"))))
    output.append(line("Jobs fallidos", as_int(jobs.get("failed"))))
    output.append(line("Dead letter", as_int(jobs.get("dead_letter"))))
    output.append(line("Coste registrado 24h", as_money(costs.get("last_24h_cents"))))
    output.append(line("Coste registrado 7d", as_money(costs.get("last_7d_cents"))))
    output.append(line("Siguiente accion", next_action_label(digest)))
    output.append("")

    output.append("## Vigilancia de fuentes")
    due_sources = as_int(source_monitoring.get("due_sources"))
    output.append(line("Fuentes vigilables", as_int(source_monitoring.get("candidate_sources"))))
    due_label = "todo reciente" if due_sources == 0 else f"{due_sources} pendientes"
    output.append(line("Fuentes vencidas ahora", due_label))
    if due_sources:
        output.append(line("Mas antigua pendiente", parse_timestamp(source_monitoring.get("oldest_due_at"))))
    else:
        output.append(line("Proxima revision prevista", parse_timestamp(source_monitoring.get("next_due_at"))))
    cadence_parts = [
        f"{as_int(source_monitoring.get('weekly_sources'))} semanal",
        f"{as_int(source_monitoring.get('standard_sources'))} estandar",
        f"{as_int(source_monitoring.get('slow_sources'))} lenta",
    ]
    custom_sources = as_int(source_monitoring.get("custom_sources"))
    if custom_sources:
        cadence_parts.append(f"{custom_sources} personalizada")
    output.append(line("Cadencia", " / ".join(cadence_parts)))
    output.append("")

    output.append("## Revisiones por tipo")
    review_types = digest.get("reviews_by_type") or []
    if review_types:
        for item in review_types:
            open_count = as_int(item.get("open_count"))
            open_word = "abierta" if open_count == 1 else "abiertas"
            output.append(
                line(
                    format_review_type(str(item.get("review_type") or "")),
                    f"{open_count} {open_word}; mas antigua {parse_timestamp(item.get('oldest_created_at'))}",
                )
            )
    else:
        output.append("- No hay revisiones abiertas.")
    output.append("")

    output.append("## Prioridad ahora")
    open_reviews = digest.get("open_reviews") or []
    if open_reviews:
        for item in open_reviews:
            clinic = item.get("clinic_name") or item.get("clinic_slug") or "sin clinica"
            output.append(
                f"- P{as_int(item.get('priority'))} | {format_review_type(str(item.get('review_type') or ''))} | "
                f"{clinic}: {item.get('title') or '-'}"
            )
    else:
        output.append("- No hay tarjetas abiertas.")
    output.append("")

    output.append("## Fallos recientes")
    failed = digest.get("recent_failed_jobs") or []
    if failed:
        for item in failed:
            error = (item.get("error_message") or "sin detalle").strip().replace("\n", " ")
            if len(error) > 120:
                error = error[:117] + "..."
            output.append(
                f"- {item.get('job_type') or 'job'} | intentos {as_int(item.get('attempts'))} | {error}"
            )
    else:
        output.append("- No hay fallos recientes.")

    return "\n".join(output) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--admin-email", help="Admin email used to read the protected dashboard summary.")
    parser.add_argument("--limit", type=int, default=8, help="Maximum open reviews and failed jobs to show.")
    parser.add_argument("--json", action="store_true", help="Print raw digest JSON instead of Markdown.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.limit < 1:
        raise SystemExit("--limit must be at least 1.")
    local_env = load_env_file()
    admin_email = args.admin_email or get_default_admin_email(local_env)
    digest = load_digest(admin_email, args.limit, local_env)
    if args.json:
        print(json.dumps(digest, ensure_ascii=False, indent=2))
    else:
        print(format_digest(digest), end="")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
