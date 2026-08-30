begin;

do $$
declare
  previous_brand text := 'diu' || 'vita';
  current_brand text := 'vitalarga';
  previous_keys text[] := array[
    previous_brand || '_build_hook_url',
    previous_brand || '_rebuild_batch_minutes',
    previous_brand || '_agents_enabled',
    previous_brand || '_auto_publish_enabled',
    previous_brand || '_shadow_review_target'
  ];
begin
  insert into private.app_settings (key, value)
  select replace(key, previous_brand, current_brand), value
  from private.app_settings
  where key = any(previous_keys)
  on conflict (key) do update
    set value = excluded.value;

  delete from private.app_settings
  where key = any(previous_keys);

  update public.field_claims
  set agent_name = replace(agent_name, previous_brand, current_brand)
  where agent_name like previous_brand || '-%';

  update public.source_records
  set metadata = replace(metadata::text, previous_brand, current_brand)::jsonb
  where metadata::text like '%' || previous_brand || '%';

  update public.agent_jobs
  set
    input = replace(input::text, previous_brand, current_brand)::jsonb,
    output = replace(output::text, previous_brand, current_brand)::jsonb
  where input::text like '%' || previous_brand || '%'
     or output::text like '%' || previous_brand || '%';

  update public.review_queue
  set
    payload = replace(payload::text, previous_brand, current_brand)::jsonb,
    resolution = replace(resolution::text, previous_brand, current_brand)::jsonb
  where payload::text like '%' || previous_brand || '%'
     or resolution::text like '%' || previous_brand || '%';

  update public.change_events
  set payload = replace(payload::text, previous_brand, current_brand)::jsonb
  where payload::text like '%' || previous_brand || '%';

  if to_regclass('public.source_snapshots') is not null then
    update public.source_snapshots
    set metadata = replace(metadata::text, previous_brand, current_brand)::jsonb
    where metadata::text like '%' || previous_brand || '%';
  end if;
end;
$$;

insert into private.app_settings (key, value)
values
  ('vitalarga_agents_enabled', 'true'),
  ('vitalarga_auto_publish_enabled', 'false'),
  ('vitalarga_shadow_review_target', '200'),
  ('vitalarga_rebuild_batch_minutes', '30')
on conflict (key) do nothing;

create or replace function private.request_public_site_rebuild()
returns void
language plpgsql
security definer
set search_path = private, net, public
as $$
declare
  hook_url text;
  batch_minutes integer := 30;
  batch_window interval := interval '30 minutes';
  should_send boolean := false;
begin
  select value
  into hook_url
  from private.app_settings
  where key = 'vitalarga_build_hook_url';

  if hook_url is null or btrim(hook_url) = '' then
    return;
  end if;

  select greatest(
    1,
    least(1440, coalesce(nullif(regexp_replace(value, '[^0-9]', '', 'g'), '')::integer, 30))
  )
  into batch_minutes
  from private.app_settings
  where key = 'vitalarga_rebuild_batch_minutes';

  batch_window := interval '1 minute' * coalesce(batch_minutes, 30);

  insert into private.rebuild_state (name, last_requested_at)
  values ('public_site', now())
  on conflict (name) do update
    set last_requested_at = excluded.last_requested_at
    where private.rebuild_state.last_requested_at < now() - batch_window
  returning true into should_send;

  if coalesce(should_send, false) then
    perform net.http_post(
      url := hook_url,
      body := jsonb_build_object(
        'source', 'supabase',
        'requested_at', now(),
        'batch_window_minutes', coalesce(batch_minutes, 30)
      ),
      timeout_milliseconds := 5000
    );
  end if;
end;
$$;

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
      where key = 'vitalarga_agents_enabled'
    ),
    true
  )
  into agents_enabled;

  select coalesce(
    (
      select lower(value) in ('true', '1', 'yes', 'on')
      from private.app_settings
      where key = 'vitalarga_auto_publish_enabled'
    ),
    false
  )
  into auto_publish_enabled;

  select coalesce(
    (
      select nullif(regexp_replace(value, '[^0-9]', '', 'g'), '')::integer
      from private.app_settings
      where key = 'vitalarga_shadow_review_target'
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

create or replace function public.admin_publication_control_summary()
returns jsonb
language plpgsql
stable
security definer
set search_path = public, auth, private
as $$
declare
  rebuild_hook_configured boolean := false;
  rebuild_batch_minutes integer := 2;
  last_public_site_rebuild_requested_at timestamptz;
begin
  if not public.is_admin() then
    raise exception 'not authorized' using errcode = '42501';
  end if;

  select exists (
    select 1
    from private.app_settings
    where key = 'vitalarga_build_hook_url'
      and btrim(value) <> ''
  )
  into rebuild_hook_configured;

  select coalesce(
    max(greatest(1, least(1440, nullif(regexp_replace(value, '[^0-9]', '', 'g'), '')::integer))),
    2
  )
  into rebuild_batch_minutes
  from private.app_settings
  where key = 'vitalarga_rebuild_batch_minutes';

  select last_requested_at
  into last_public_site_rebuild_requested_at
  from private.rebuild_state
  where name = 'public_site';

  return jsonb_build_object(
    'rebuild_hook_configured', rebuild_hook_configured,
    'rebuild_batch_minutes', rebuild_batch_minutes,
    'last_public_site_rebuild_requested_at', last_public_site_rebuild_requested_at,
    'generated_at', now()
  );
end;
$$;

grant execute on function public.admin_publication_control_summary() to authenticated;

commit;
