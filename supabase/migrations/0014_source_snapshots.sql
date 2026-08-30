begin;

create table if not exists public.source_snapshots (
  id uuid primary key default gen_random_uuid(),
  source_record_id uuid not null references public.source_records(id) on delete cascade,
  clinic_id uuid references public.clinics(id) on delete set null,
  entity_type text not null default 'clinic',
  entity_id uuid,
  source_url text not null check (source_url ~* '^https?://'),
  final_url text check (final_url is null or final_url ~* '^https?://'),
  source_title text,
  retrieved_at timestamptz not null,
  http_status integer,
  content_type text,
  content_length integer,
  content_hash text not null,
  text_hash text,
  snapshot_storage_path text,
  text_excerpt text,
  snapshot_kind text not null default 'compact' check (snapshot_kind in ('compact')),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists source_snapshots_source_record_idx
on public.source_snapshots(source_record_id, retrieved_at desc);

create index if not exists source_snapshots_clinic_idx
on public.source_snapshots(clinic_id, retrieved_at desc);

create unique index if not exists source_snapshots_record_hash_unique_idx
on public.source_snapshots(source_record_id, content_hash, (coalesce(text_hash, '')));

alter table public.source_snapshots enable row level security;

grant select, insert, update, delete on public.source_snapshots to authenticated;

drop policy if exists "admin full access" on public.source_snapshots;
create policy "admin full access"
on public.source_snapshots
for all to authenticated
using (public.is_admin())
with check (public.is_admin());

create or replace function public.admin_dashboard_summary()
returns jsonb
language plpgsql
stable
security definer
set search_path = public, auth
as $$
declare
  agents_enabled boolean;
  auto_publish_enabled boolean;
  shadow_review_target integer;
begin
  if not public.is_admin() then
    raise exception 'not authorized' using errcode = '42501';
  end if;

  select coalesce(
    (
      select lower(value) in ('true', '1', 'yes', 'on')
      from private.app_settings
      where key = 'diuvita_agents_enabled'
    ),
    true
  )
  into agents_enabled;

  select coalesce(
    (
      select lower(value) in ('true', '1', 'yes', 'on')
      from private.app_settings
      where key = 'diuvita_auto_publish_enabled'
    ),
    false
  )
  into auto_publish_enabled;

  select coalesce(
    (
      select nullif(regexp_replace(value, '[^0-9]', '', 'g'), '')::integer
      from private.app_settings
      where key = 'diuvita_shadow_review_target'
    ),
    200
  )
  into shadow_review_target;

  return jsonb_build_object(
    'clinics', (
      select jsonb_build_object(
        'total', count(*),
        'published', count(*) filter (where status = 'published'),
        'preliminary', count(*) filter (where status = 'preliminary'),
        'review', count(*) filter (where status = 'review'),
        'draft', count(*) filter (where status = 'draft'),
        'discovered', count(*) filter (where status = 'discovered')
      )
      from public.clinics
    ),
    'reviews', (
      select jsonb_build_object(
        'open', count(*) filter (where status = 'open'),
        'resolved', count(*) filter (where status = 'resolved'),
        'candidate_open', count(*) filter (where status = 'open' and review_type = 'candidate_clinic'),
        'quality_open', count(*) filter (where status = 'open' and review_type = 'clinic_quality_audit')
      )
      from public.review_queue
    ),
    'jobs', (
      select jsonb_build_object(
        'queued', count(*) filter (where status = 'queued'),
        'running', count(*) filter (where status = 'running'),
        'failed', count(*) filter (where status = 'failed'),
        'dead_letter', count(*) filter (where status = 'dead_letter'),
        'completed', count(*) filter (where status = 'completed')
      )
      from public.agent_jobs
    ),
    'evidence', (
      select jsonb_build_object(
        'sources', (select count(*) from public.source_records),
        'claims', (select count(*) from public.field_claims),
        'snapshots', (select count(*) from public.source_snapshots)
      )
    ),
    'automation', (
      select jsonb_build_object(
        'agents_enabled', agents_enabled,
        'auto_publish_enabled', auto_publish_enabled,
        'shadow_mode_active', not auto_publish_enabled,
        'shadow_review_target', shadow_review_target,
        'candidate_reviews_completed', (
          select count(*)
          from public.review_queue
          where review_type = 'candidate_clinic'
            and status in ('resolved', 'dismissed')
        )
      )
    ),
    'generated_at', now()
  );
end;
$$;

grant execute on function public.admin_dashboard_summary() to authenticated;

commit;
