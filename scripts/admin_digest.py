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
from submit_blocking_claim_reviews import NON_NOISY_BLOCKING_CLAIM_SQL

SAFE_WRITE_REVIEW_BACKLOG_LIMIT = 50


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
publication_control as (
  select public.admin_publication_control_summary() as data
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
      c.display_name as clinic_name,
      case
        when rq.review_type = 'candidate_clinic' then coalesce(
          case when jsonb_typeof(rq.payload #> '{{candidate,profesionales}}') = 'array'
            then jsonb_array_length(rq.payload #> '{{candidate,profesionales}}') end,
          case when jsonb_typeof(rq.payload #> '{{candidate,professionals}}') = 'array'
            then jsonb_array_length(rq.payload #> '{{candidate,professionals}}') end,
          case when jsonb_typeof(rq.payload -> 'profesionales') = 'array'
            then jsonb_array_length(rq.payload -> 'profesionales') end,
          0
        )
        when rq.review_type = 'clinic_profile_enrichment' then coalesce(
          case when jsonb_typeof(rq.payload #> '{{proposed_fields,profesionales}}') = 'array'
            then jsonb_array_length(rq.payload #> '{{proposed_fields,profesionales}}') end,
          case when jsonb_typeof(rq.payload #> '{{proposed_current_data,profesionales}}') = 'array'
            then jsonb_array_length(rq.payload #> '{{proposed_current_data,profesionales}}') end,
          case when jsonb_typeof(rq.payload #> '{{fields,profesionales}}') = 'array'
            then jsonb_array_length(rq.payload #> '{{fields,profesionales}}') end,
          0
        )
        else 0
      end as professionals_count
    from public.review_queue rq
    left join public.clinics c on c.id = rq.clinic_id
    where rq.status = 'open'
    order by rq.priority desc, rq.created_at asc
    limit {int(limit)}
  ) items
),
enrichment_review_groups as (
  select
    rq.clinic_id,
    c.slug as clinic_slug,
    c.display_name as clinic_name,
    c.city,
    c.status as clinic_status,
    count(*) as open_count,
    max(rq.priority) as max_priority,
    min(rq.created_at) as oldest_created_at
  from public.review_queue rq
  left join public.clinics c on c.id = rq.clinic_id
  where rq.status = 'open'
    and rq.review_type = 'clinic_profile_enrichment'
    and rq.clinic_id is not null
  group by rq.clinic_id, c.slug, c.display_name, c.city, c.status
),
review_backlog_quality as (
  select jsonb_build_object(
    'duplicate_enrichment_clinics', count(*) filter (where open_count > 1),
    'duplicate_enrichment_reviews', coalesce(sum(open_count) filter (where open_count > 1), 0)
  ) as data
  from enrichment_review_groups
),
review_backlog_first_duplicate_target as (
  select coalesce(
    (
      select to_jsonb(items)
      from (
        select
          clinic_slug,
          clinic_name,
          city,
          clinic_status,
          open_count,
          max_priority,
          oldest_created_at
        from enrichment_review_groups
        where open_count > 1
        order by open_count desc, max_priority desc, oldest_created_at asc, clinic_name
        limit 1
      ) items
    ),
    '{{}}'::jsonb
  ) as data
),
review_clinic_workgroups as (
  select
    rq.clinic_id,
    c.slug as clinic_slug,
    c.display_name as clinic_name,
    c.city,
    c.status as clinic_status,
    count(*) as open_count,
    count(*) filter (
      where rq.review_type = 'clinic_quality_audit'
        and rq.payload ->> 'quality_context' = 'blocking_claims'
    ) as blocking_claim_reviews,
    count(*) filter (
      where rq.review_type = 'clinic_quality_audit'
        and coalesce(rq.payload ->> 'quality_context', '') <> 'blocking_claims'
    ) as quality_reviews,
    count(*) filter (where rq.review_type = 'clinic_profile_enrichment') as enrichment_reviews,
    count(*) filter (where rq.review_type = 'source_change_detected') as source_change_reviews,
    count(*) filter (where rq.review_type = 'candidate_clinic') as candidate_reviews,
    max(rq.priority) as max_priority,
    min(rq.created_at) as oldest_created_at
  from public.review_queue rq
  left join public.clinics c on c.id = rq.clinic_id
  where rq.status = 'open'
    and rq.clinic_id is not null
  group by rq.clinic_id, c.slug, c.display_name, c.city, c.status
),
review_first_clinic_workgroup as (
  select coalesce(
    (
      select to_jsonb(items)
      from (
        select
          clinic_slug,
          clinic_name,
          city,
          clinic_status,
          open_count,
          blocking_claim_reviews,
          quality_reviews,
          enrichment_reviews,
          source_change_reviews,
          candidate_reviews,
          max_priority,
          oldest_created_at
        from review_clinic_workgroups
        order by
          blocking_claim_reviews desc,
          open_count desc,
          max_priority desc,
          oldest_created_at asc,
          clinic_name
        limit 1
      ) items
    ),
    '{{}}'::jsonb
  ) as data
),
review_examples_by_type as (
  select coalesce(jsonb_agg(to_jsonb(items) order by items.review_type), '[]'::jsonb) as data
  from (
    select
      id,
      raw_review_type,
      review_type,
      title,
      priority,
      created_at,
      updated_at,
      clinic_slug,
      clinic_name,
      professionals_count
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
        c.display_name as clinic_name,
        case
          when rq.review_type = 'candidate_clinic' then coalesce(
            case when jsonb_typeof(rq.payload #> '{{candidate,profesionales}}') = 'array'
              then jsonb_array_length(rq.payload #> '{{candidate,profesionales}}') end,
            case when jsonb_typeof(rq.payload #> '{{candidate,professionals}}') = 'array'
              then jsonb_array_length(rq.payload #> '{{candidate,professionals}}') end,
            case when jsonb_typeof(rq.payload -> 'profesionales') = 'array'
              then jsonb_array_length(rq.payload -> 'profesionales') end,
            0
          )
          when rq.review_type = 'clinic_profile_enrichment' then coalesce(
            case when jsonb_typeof(rq.payload #> '{{proposed_fields,profesionales}}') = 'array'
              then jsonb_array_length(rq.payload #> '{{proposed_fields,profesionales}}') end,
            case when jsonb_typeof(rq.payload #> '{{proposed_current_data,profesionales}}') = 'array'
              then jsonb_array_length(rq.payload #> '{{proposed_current_data,profesionales}}') end,
            case when jsonb_typeof(rq.payload #> '{{fields,profesionales}}') = 'array'
              then jsonb_array_length(rq.payload #> '{{fields,profesionales}}') end,
            0
          )
          else 0
        end as professionals_count,
        row_number() over (
          partition by case
            when rq.review_type = 'clinic_quality_audit'
              and rq.payload ->> 'quality_context' = 'blocking_claims'
              then 'blocking_claim_review'
            else rq.review_type
          end
          order by rq.priority desc, rq.created_at asc
        ) as review_rank
      from public.review_queue rq
      left join public.clinics c on c.id = rq.clinic_id
      where rq.status = 'open'
    ) ranked
    where review_rank = 1
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
    'conflict', count(*) filter (where fc.verification_status = 'conflict'),
    'rejected', count(*) filter (
      where fc.verification_status = 'rejected'
        and {NON_NOISY_BLOCKING_CLAIM_SQL}
    ),
    'without_source', count(*) filter (where fc.source_record_id is null)
  ) as data
  from public.field_claims fc
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
visible_source_rows as (
  select
    c.id,
    c.slug,
    c.display_name as clinic_name,
    c.city,
    c.status,
    coalesce(sources.source_records, 0) as source_records,
    coalesce(sources.hydrated_source_records, 0) as hydrated_source_records,
    coalesce(sources.source_snapshots, 0) as source_snapshots,
    sources.last_source_at,
    coalesce(claims.total_claims, 0) as total_claims,
    coalesce(claims.claims_with_source, 0) as claims_with_source,
    coalesce(claims.claims_without_source, 0) as claims_without_source,
    coalesce(claims.blocking_claims, 0) as blocking_claims,
    (
      coalesce(sources.source_records, 0) = 0
      or coalesce(sources.hydrated_source_records, 0) = 0
      or coalesce(claims.total_claims, 0) = 0
      or coalesce(claims.claims_without_source, 0) > 0
      or coalesce(claims.blocking_claims, 0) > 0
    ) as needs_source_work
  from public.clinics c
  left join lateral (
    select
      count(distinct sr.id) as source_records,
      count(distinct sr.id) filter (where sr.content_hash is not null) as hydrated_source_records,
      count(ss.id) as source_snapshots,
      max(coalesce(ss.retrieved_at, sr.retrieved_at)) as last_source_at
    from public.source_records sr
    left join public.source_snapshots ss on ss.source_record_id = sr.id
    where sr.clinic_id = c.id
      and sr.entity_type = 'clinic'
  ) sources on true
  left join lateral (
    select
      count(*) as total_claims,
      count(*) filter (where fc.source_record_id is not null) as claims_with_source,
      count(*) filter (where fc.source_record_id is null) as claims_without_source,
      count(*) filter (
        where (
          fc.verification_status = 'conflict'
          or fc.source_record_id is null
        )
        and {NON_NOISY_BLOCKING_CLAIM_SQL}
      ) as blocking_claims
    from public.field_claims fc
    where fc.clinic_id = c.id
      and fc.entity_type = 'clinic'
  ) claims on true
  where c.status in ('published', 'preliminary')
),
source_coverage as (
  select jsonb_build_object(
    'visible_clinics', count(*),
    'clinics_with_sources', count(*) filter (where source_records > 0),
    'clinics_without_sources', count(*) filter (where source_records = 0),
    'clinics_with_hydrated_sources', count(*) filter (where hydrated_source_records > 0),
    'clinics_without_hydrated_sources', count(*) filter (where hydrated_source_records = 0),
    'clinics_with_claims', count(*) filter (where total_claims > 0),
    'clinics_without_claims', count(*) filter (where total_claims = 0),
    'clinics_needing_source_work', count(*) filter (where needs_source_work),
    'claims_with_source', coalesce(sum(claims_with_source), 0),
    'claims_without_source', coalesce(sum(claims_without_source), 0),
    'blocking_claims', coalesce(sum(blocking_claims), 0)
  ) as data
  from visible_source_rows
),
source_next_target as (
  select coalesce(
    (
      select to_jsonb(items)
      from (
        select
          slug,
          clinic_name,
          city,
          status,
          source_records,
          hydrated_source_records,
          source_snapshots,
          last_source_at,
          total_claims,
          claims_with_source,
          claims_without_source,
          blocking_claims
        from visible_source_rows
        where needs_source_work
        order by
          blocking_claims desc,
          case when source_records = 0 then 0 else 1 end,
          case when hydrated_source_records = 0 then 0 else 1 end,
          claims_without_source desc,
          total_claims asc,
          case when status = 'published' then 0 else 1 end,
          clinic_name
        limit 1
      ) items
    ),
    '{{}}'::jsonb
  ) as data
),
visible_specialist_rows as (
  select
    c.id,
    c.slug,
    c.display_name as clinic_name,
    c.city,
    c.status,
    case
      when jsonb_typeof(c.current_data -> 'profesionales') = 'array'
        then jsonb_array_length(c.current_data -> 'profesionales')
      else 0
    end as specialist_entries,
    coalesce(claims.claim_count, 0) as specialist_claims,
    coalesce(reviews.open_review_count, 0) as open_review_count
  from public.clinics c
  left join lateral (
    select count(*) as claim_count
    from public.field_claims fc
    where fc.clinic_id = c.id
      and fc.field_path in ('professionals.published', 'team.public_professionals')
  ) claims on true
  left join lateral (
    select count(*) as open_review_count
    from public.review_queue rq
    where rq.clinic_id = c.id
      and rq.status = 'open'
      and (
        rq.payload ->> 'quality_context' = 'blocking_claims'
        or rq.payload::text ilike '%missing_professionals%'
        or rq.payload::text ilike '%profesionales%'
        or rq.payload::text ilike '%professionals%'
      )
  ) reviews on true
  where c.status in ('published', 'preliminary')
),
specialist_coverage as (
  select jsonb_build_object(
    'visible_clinics', count(*),
    'with_specialists', count(*) filter (where specialist_entries > 0),
    'without_specialists', count(*) filter (where specialist_entries = 0),
    'total_specialist_entries', coalesce(sum(specialist_entries), 0),
    'clinics_with_specialist_claims', count(*) filter (where specialist_claims > 0),
    'clinics_with_open_specialist_reviews', count(*) filter (where open_review_count > 0)
  ) as data
  from visible_specialist_rows
),
specialist_next_target as (
  select coalesce(
    (
      select to_jsonb(items)
      from (
        select slug, clinic_name, city, status, specialist_claims, open_review_count
        from visible_specialist_rows
        where specialist_entries = 0
        order by open_review_count desc, specialist_claims desc, status, clinic_name
        limit 1
      ) items
    ),
    '{{}}'::jsonb
  ) as data
),
visible_profile_base as (
  select
    c.id,
    c.slug,
    c.display_name as clinic_name,
    c.city,
    c.status,
    length(btrim(coalesce(c.summary, c.current_data ->> 'summary', ''))) >= 120 as has_summary,
    nullif(btrim(coalesce(c.website, c.current_data ->> 'web', '')), '') is not null as has_website,
    (
      nullif(btrim(coalesce(c.address, c.current_data ->> 'address', '')), '') is not null
      or exists (
        select 1
        from jsonb_array_elements(
          case
            when jsonb_typeof(c.current_data -> 'locations') = 'array'
              then c.current_data -> 'locations'
            else '[]'::jsonb
          end
        ) as location(value)
        where nullif(btrim(coalesce(
          location.value ->> 'address',
          location.value ->> 'direccion',
          location.value ->> 'dirección',
          case
            when jsonb_typeof(location.value) = 'string'
              then location.value #>> '{{}}'
            else ''
          end
        )), '') is not null
      )
    ) as has_address,
    (
      nullif(btrim(coalesce(c.current_data ->> 'maps_url', c.current_data ->> 'google_maps_url', '')), '') is not null
      or exists (
        select 1
        from jsonb_array_elements(
          case
            when jsonb_typeof(c.current_data -> 'locations') = 'array'
              then c.current_data -> 'locations'
            else '[]'::jsonb
          end
        ) as location(value)
        where nullif(btrim(coalesce(
          location.value ->> 'maps_url',
          location.value ->> 'google_maps_url',
          location.value ->> 'map_url',
          ''
        )), '') is not null
      )
    ) as has_google_maps,
    (
      nullif(btrim(coalesce(c.current_data ->> 'google_reviews_url', c.current_data ->> 'reviews_url', '')), '') is not null
      or exists (
        select 1
        from jsonb_array_elements(
          case
            when jsonb_typeof(c.current_data -> 'locations') = 'array'
              then c.current_data -> 'locations'
            else '[]'::jsonb
          end
        ) as location(value)
        where nullif(btrim(coalesce(
          location.value ->> 'google_reviews_url',
          location.value ->> 'reviews_url',
          location.value ->> 'valoraciones_url',
          ''
        )), '') is not null
      )
    ) as has_google_reviews,
    nullif(btrim(coalesce(c.current_data ->> 'email', '')), '') is not null
      or nullif(btrim(coalesce(c.current_data ->> 'telefono', c.current_data ->> 'phone', c.current_data ->> 'telephone', '')), '') is not null as has_contact,
    case
      when jsonb_typeof(c.current_data -> 'services') = 'array'
        then jsonb_array_length(c.current_data -> 'services')
      else 0
    end > 0 as has_services,
    case
      when jsonb_typeof(c.current_data -> 'specialties') = 'array'
        then jsonb_array_length(c.current_data -> 'specialties')
      else 0
    end > 0 as has_specialties,
    case
      when jsonb_typeof(c.current_data -> 'unidades') = 'array'
        then jsonb_array_length(c.current_data -> 'unidades')
      else 0
    end > 0 as has_units,
    case
      when jsonb_typeof(c.current_data -> 'profesionales') = 'array'
        then jsonb_array_length(c.current_data -> 'profesionales')
      else 0
    end > 0 as has_specialists,
    case
      when jsonb_typeof(c.current_data -> 'tech') = 'array'
        then jsonb_array_length(c.current_data -> 'tech')
      when nullif(btrim(coalesce(c.current_data ->> 'tech', '')), '') is not null
        then 1
      else 0
    end > 0 as has_technology,
    coalesce(reviews.open_quality_reviews, 0) as open_quality_reviews,
    coalesce(reviews.open_profile_reviews, 0) as open_profile_reviews,
    coalesce(reviews.open_source_change_reviews, 0) as open_source_change_reviews,
    coalesce(reviews.open_relevant_reviews, 0) as open_relevant_reviews
  from public.clinics c
  left join lateral (
    select
      count(*) filter (where rq.review_type = 'clinic_quality_audit') as open_quality_reviews,
      count(*) filter (where rq.review_type = 'clinic_profile_enrichment') as open_profile_reviews,
      count(*) filter (where rq.review_type = 'source_change_detected') as open_source_change_reviews,
      count(*) filter (
        where rq.review_type in ('clinic_quality_audit', 'clinic_profile_enrichment', 'source_change_detected')
      ) as open_relevant_reviews
    from public.review_queue rq
    where rq.clinic_id = c.id
      and rq.status = 'open'
  ) reviews on true
  where c.status in ('published', 'preliminary')
),
visible_profile_checks as (
  select
    *,
    array_remove(array[
      case when not has_summary then 'Resumen corto o vacío' end,
      case when not has_website then 'Web oficial' end,
      case when not has_address then 'Dirección' end,
      case when not has_google_maps then 'Google Maps de clínica' end,
      case when not has_google_reviews then 'Valoraciones Google' end,
      case when not has_contact then 'Email o teléfono' end,
      case when not has_services then 'Servicios' end,
      case when not has_specialties then 'Especialidades' end,
      case when not has_units then 'Unidades clínicas' end,
      case when not has_specialists then 'Especialistas publicados' end,
      case when not has_technology then 'Tecnología destacada' end
    ], null) as pending_fields
  from visible_profile_base
),
profile_completeness as (
  select jsonb_build_object(
    'visible_clinics', count(*),
    'without_pending_fields', count(*) filter (
      where has_summary
        and has_website
        and has_address
        and has_google_maps
        and has_google_reviews
        and has_contact
        and has_services
        and has_specialties
        and has_units
        and has_specialists
        and has_technology
    ),
    'with_pending_fields', count(*) filter (
      where not (
        has_summary
        and has_website
        and has_address
        and has_google_maps
        and has_google_reviews
        and has_contact
        and has_services
        and has_specialties
        and has_units
        and has_specialists
        and has_technology
      )
    ),
    'pending_summary', count(*) filter (where not has_summary),
    'pending_website', count(*) filter (where not has_website),
    'pending_address', count(*) filter (where not has_address),
    'pending_google_maps', count(*) filter (where not has_google_maps),
    'pending_google_reviews', count(*) filter (where not has_google_reviews),
    'pending_contact', count(*) filter (where not has_contact),
    'pending_services', count(*) filter (where not has_services),
    'pending_specialties', count(*) filter (where not has_specialties),
    'pending_units', count(*) filter (where not has_units),
    'pending_specialists', count(*) filter (where not has_specialists),
    'pending_technology', count(*) filter (where not has_technology)
  ) as data
  from visible_profile_checks
),
profile_next_target as (
  select coalesce(
    (
      select to_jsonb(items)
      from (
        select
          slug,
          clinic_name,
          city,
          status,
          pending_fields,
          coalesce(array_length(pending_fields, 1), 0) as pending_count,
          pending_fields[1] as next_pending_field,
          open_quality_reviews,
          open_profile_reviews,
          open_source_change_reviews,
          open_relevant_reviews
        from visible_profile_checks
        where coalesce(array_length(pending_fields, 1), 0) > 0
        order by open_relevant_reviews desc,
          coalesce(array_length(pending_fields, 1), 0) desc,
          case when status = 'published' then 0 else 1 end,
          clinic_name
        limit 1
      ) items
    ),
    '{{}}'::jsonb
  ) as data
)
select jsonb_build_object(
  'admin_email', {sql_literal(admin_email)},
  'summary', (select data from summary),
  'publication_control', (select data from publication_control),
  'reviews_by_type', (select data from reviews_by_type),
  'open_reviews', (select data from open_reviews),
  'review_backlog_quality', (select data from review_backlog_quality),
  'review_backlog_first_duplicate_target', (select data from review_backlog_first_duplicate_target),
  'review_first_clinic_workgroup', (select data from review_first_clinic_workgroup),
  'review_examples_by_type', (select data from review_examples_by_type),
  'recent_failed_jobs', (select data from recent_failed_jobs),
  'recent_jobs_by_type', (select data from recent_jobs_by_type),
  'costs', (select data from costs),
  'claim_quality', (select data from claim_quality),
  'source_monitoring', (select data from source_monitoring),
  'source_coverage', (select data from source_coverage),
  'source_next_target', (select data from source_next_target),
  'specialist_coverage', (select data from specialist_coverage),
  'specialist_next_target', (select data from specialist_next_target),
  'profile_completeness', (select data from profile_completeness),
  'profile_next_target', (select data from profile_next_target),
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


def review_professionals_note(item: dict[str, Any]) -> str:
    count = as_int(item.get("professionals_count"))
    if not count:
        return ""
    word = "especialista" if count == 1 else "especialistas"
    return f" · {count} {word}"


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


def publication_control_status(digest: dict[str, Any]) -> str:
    control = digest.get("publication_control") or {}
    if not control.get("rebuild_hook_configured"):
        return "no configurada"
    minutes = as_int(control.get("rebuild_batch_minutes"))
    if minutes > 1:
        return f"agrupada cada {minutes} min"
    return "directa"


PROFILE_COMPLETENESS_FIELDS = [
    ("pending_summary", "Resumen"),
    ("pending_website", "Web oficial"),
    ("pending_address", "Dirección"),
    ("pending_google_maps", "Google Maps"),
    ("pending_google_reviews", "Valoraciones Google"),
    ("pending_contact", "Contacto"),
    ("pending_services", "Servicios"),
    ("pending_specialties", "Especialidades"),
    ("pending_units", "Unidades"),
    ("pending_specialists", "Especialistas"),
    ("pending_technology", "Tecnología"),
]


def top_pending_profile_field(digest: dict[str, Any]) -> str:
    completeness = digest.get("profile_completeness") or {}
    rows = [
        (label, as_int(completeness.get(key)))
        for key, label in PROFILE_COMPLETENESS_FIELDS
        if as_int(completeness.get(key))
    ]
    if not rows:
        return "sin campo pendiente"
    label, count = sorted(rows, key=lambda item: (-item[1], item[0]))[0]
    return f"{label} · {count} fichas"


def plural(value: int, singular: str, plural_text: str) -> str:
    return singular if value == 1 else plural_text


def first_clinic_workgroup(digest: dict[str, Any]) -> str:
    target = digest.get("review_first_clinic_workgroup") or {}
    if not isinstance(target, dict) or not target:
        return "sin grupo por clínica medido"
    name = str(target.get("clinic_name") or target.get("clinic_slug") or "la primera clínica")
    open_count = as_int(target.get("open_count"))
    parts = []
    for key, singular, plural_text in [
        ("blocking_claim_reviews", "claim bloqueante", "claims bloqueantes"),
        ("enrichment_reviews", "mejora", "mejoras"),
        ("source_change_reviews", "cambio de fuente", "cambios de fuente"),
        ("quality_reviews", "auditoría", "auditorías"),
        ("candidate_reviews", "candidata", "candidatas"),
    ]:
        count = as_int(target.get(key))
        if count:
            parts.append(f"{count} {plural(count, singular, plural_text)}")
    detail = " / ".join(parts)
    if detail:
        return f"Trabajar {name}: {open_count} {plural(open_count, 'tarjeta', 'tarjetas')} ({detail})"
    return f"Trabajar {name}: {open_count} {plural(open_count, 'tarjeta', 'tarjetas')}"


def next_specialist_action(digest: dict[str, Any]) -> str:
    target = digest.get("specialist_next_target") or {}
    if not isinstance(target, dict) or not target:
        return "sin ficha pendiente medida"
    name = str(target.get("clinic_name") or target.get("slug") or "la primera ficha pendiente")
    reviews = as_int(target.get("open_review_count"))
    claims = as_int(target.get("specialist_claims"))
    if reviews:
        return f"Revisar {name}: ya tiene {reviews} {plural(reviews, 'revision abierta', 'revisiones abiertas')}"
    if claims:
        return f"Revisar {name}: ya tiene {claims} {plural(claims, 'claim interno', 'claims internos')}"
    return f"Buscar especialistas publicados para {name} solo en fuentes oficiales"


def next_profile_action(digest: dict[str, Any]) -> str:
    target = digest.get("profile_next_target") or {}
    if not isinstance(target, dict) or not target:
        return "sin ficha pendiente medida"
    name = str(target.get("clinic_name") or target.get("slug") or "la primera ficha pendiente")
    reviews = as_int(target.get("open_relevant_reviews"))
    pending = as_int(target.get("pending_count"))
    first_field = str(target.get("next_pending_field") or "").strip()
    if reviews:
        reason = f"ya tiene {reviews} {plural(reviews, 'revision abierta relacionada', 'revisiones abiertas relacionadas')}"
    elif pending:
        reason = f"tiene {pending} {plural(pending, 'campo pendiente', 'campos pendientes')}"
    else:
        reason = "tiene campos pendientes"
    if first_field:
        return f"Revisar {name}: {reason}. Primer campo: {first_field}"
    return f"Revisar {name}: {reason}"


def next_source_action(digest: dict[str, Any]) -> str:
    target = digest.get("source_next_target") or {}
    if not isinstance(target, dict) or not target:
        return "sin hueco de fuentes medido"
    name = str(target.get("clinic_name") or target.get("slug") or "la primera ficha")
    source_records = as_int(target.get("source_records"))
    hydrated = as_int(target.get("hydrated_source_records"))
    total_claims = as_int(target.get("total_claims"))
    without_source = as_int(target.get("claims_without_source"))
    blocking = as_int(target.get("blocking_claims"))
    if not source_records:
        return f"Añadir fuente oficial para {name}"
    if not hydrated:
        return f"Hidratar {source_records} {plural(source_records, 'fuente guardada', 'fuentes guardadas')} de {name}"
    if blocking:
        return f"Revisar {blocking} {plural(blocking, 'claim bloqueante', 'claims bloqueantes')} de {name}"
    if without_source:
        return f"Vincular fuente a {without_source} {plural(without_source, 'claim', 'claims')} de {name}"
    if not total_claims:
        return f"Crear claims internos desde fuentes guardadas para {name}"
    return f"Revisar soporte de fuentes de {name}"


def source_coverage_status(digest: dict[str, Any]) -> str:
    coverage = digest.get("source_coverage") or {}
    visible = as_int(coverage.get("visible_clinics"))
    if not visible:
        return "sin fichas visibles medidas"
    with_sources = as_int(coverage.get("clinics_with_sources"))
    hydrated = as_int(coverage.get("clinics_with_hydrated_sources"))
    without_sources = as_int(coverage.get("clinics_without_sources"))
    needing = as_int(coverage.get("clinics_needing_source_work"))
    return (
        f"{with_sources}/{visible} fichas con fuente; "
        f"{hydrated}/{visible} hidratadas; "
        f"{without_sources} sin fuente; "
        f"{needing} con trabajo pendiente"
    )


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


def review_backlog_guard_status(digest: dict[str, Any], limit: int = SAFE_WRITE_REVIEW_BACKLOG_LIMIT) -> str:
    summary = digest.get("summary") or {}
    reviews = summary.get("reviews") or {}
    open_reviews = as_int(reviews.get("open"))
    if limit <= 0:
        return "sin freno configurado"
    if open_reviews >= limit:
        return f"freno activo: {open_reviews}/{limit} revisiones abiertas"
    remaining = limit - open_reviews
    if remaining <= 5:
        return f"cerca del freno: {open_reviews}/{limit} abiertas"
    return f"normal: {open_reviews}/{limit} abiertas"


def first_backlog_bottleneck(digest: dict[str, Any]) -> str:
    target = digest.get("review_backlog_first_duplicate_target") or {}
    if not isinstance(target, dict) or not target:
        return "sin atascos duplicados medidos"
    name = str(target.get("clinic_name") or target.get("clinic_slug") or "la primera clinica duplicada")
    count = as_int(target.get("open_count"))
    if count:
        return f"Ordenar {name}: {count} {plural(count, 'mejora abierta', 'mejoras abiertas')}"
    return f"Ordenar {name}"


def format_digest(digest: dict[str, Any]) -> str:
    summary = digest.get("summary") or {}
    clinics = summary.get("clinics") or {}
    reviews = summary.get("reviews") or {}
    jobs = summary.get("jobs") or {}
    evidence = summary.get("evidence") or {}
    automation = summary.get("automation") or {}
    costs = digest.get("costs") or {}
    source_monitoring = digest.get("source_monitoring") or {}
    source_coverage = digest.get("source_coverage") or {}
    specialist_coverage = digest.get("specialist_coverage") or {}
    profile_completeness = digest.get("profile_completeness") or {}
    backlog_quality = digest.get("review_backlog_quality") or {}

    output: list[str] = []
    output.append("# Vitalarga CTO digest")
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
        output.append(line("Siguiente especialistas", next_specialist_action(digest)))
    completeness_visible = as_int(profile_completeness.get("visible_clinics"))
    completeness_ready = as_int(profile_completeness.get("without_pending_fields"))
    if completeness_visible:
        output.append(line("Fichas sin campos pendientes medidos", f"{completeness_ready}/{completeness_visible}"))
        output.append(line("Campo mas pendiente", top_pending_profile_field(digest)))
        output.append(line("Siguiente ficha", next_profile_action(digest)))
    output.append("")

    output.append("## Automatizacion")
    auto_publish = bool(automation.get("auto_publish_enabled"))
    output.append(line("Agentes activos", "si" if automation.get("agents_enabled") else "no"))
    output.append(line("Auto-publicacion", "activada" if auto_publish else "desactivada"))
    output.append(line("Modo sombra", "activo" if automation.get("shadow_mode_active") else "inactivo"))
    output.append(line("Publicacion web", publication_control_status(digest)))
    last_rebuild = parse_timestamp((digest.get("publication_control") or {}).get("last_public_site_rebuild_requested_at"))
    if last_rebuild != "-":
        output.append(line("Ultima peticion Netlify", last_rebuild))
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
    output.append(line("Freno bandeja", review_backlog_guard_status(digest)))
    clinic_group = first_clinic_workgroup(digest)
    if clinic_group != "sin grupo por clínica medido":
        output.append(line("Grupo por clinica", clinic_group))
    duplicate_clinics = as_int(backlog_quality.get("duplicate_enrichment_clinics"))
    duplicate_reviews = as_int(backlog_quality.get("duplicate_enrichment_reviews"))
    if duplicate_clinics:
        output.append(
            line(
                "Duplicados mejoras",
                f"{duplicate_clinics} clinicas / {duplicate_reviews} tarjetas",
            )
        )
        output.append(line("Primer atasco", first_backlog_bottleneck(digest)))
    output.append("")

    output.append("## Vigilancia de fuentes")
    due_sources = as_int(source_monitoring.get("due_sources"))
    output.append(line("Fuentes vigilables", as_int(source_monitoring.get("candidate_sources"))))
    due_label = "todo reciente" if due_sources == 0 else f"{due_sources} pendientes"
    output.append(line("Fuentes vencidas ahora", due_label))
    source_visible = as_int(source_coverage.get("visible_clinics"))
    if source_visible:
        output.append(line("Cobertura fuentes", source_coverage_status(digest)))
        output.append(line("Siguiente fuente", next_source_action(digest)))
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
                f"{clinic}: {item.get('title') or '-'}{review_professionals_note(item)}"
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
