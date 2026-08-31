begin;

insert into private.app_settings (key, value)
values ('vitalarga_rebuild_batch_minutes', '30')
on conflict (key) do nothing;

alter table private.rebuild_state
  add column if not exists last_change_at timestamptz,
  add column if not exists last_sent_at timestamptz;

update private.rebuild_state
set
  last_change_at = coalesce(last_change_at, last_requested_at),
  last_sent_at = coalesce(last_sent_at, last_requested_at)
where name = 'public_site';

create or replace function private.public_site_rebuild_batch_minutes()
returns integer
language sql
stable
security definer
set search_path = private
as $$
  select coalesce(
    max(greatest(1, least(1440, nullif(regexp_replace(value, '[^0-9]', '', 'g'), '')::integer))),
    30
  )
  from private.app_settings
  where key = 'vitalarga_rebuild_batch_minutes';
$$;

create or replace function private.request_public_site_rebuild()
returns void
language plpgsql
security definer
set search_path = private, net, public
as $$
declare
  hook_url text;
  batch_minutes integer := private.public_site_rebuild_batch_minutes();
  batch_window interval := interval '1 minute' * private.public_site_rebuild_batch_minutes();
  request_time timestamptz := now();
  last_sent timestamptz;
  should_send boolean := false;
begin
  insert into private.rebuild_state (name, last_requested_at, last_change_at, last_sent_at)
  values ('public_site', request_time - batch_window - interval '1 second', request_time, null)
  on conflict (name) do update
    set last_change_at = excluded.last_change_at;

  select value
  into hook_url
  from private.app_settings
  where key = 'vitalarga_build_hook_url';

  if hook_url is null or btrim(hook_url) = '' then
    return;
  end if;

  select coalesce(last_sent_at, last_requested_at)
  into last_sent
  from private.rebuild_state
  where name = 'public_site'
  for update;

  if last_sent is null or last_sent < request_time - batch_window then
    should_send := true;
  end if;

  if should_send then
    update private.rebuild_state
    set
      last_requested_at = request_time,
      last_sent_at = request_time
    where name = 'public_site';

    perform net.http_post(
      url := hook_url,
      body := jsonb_build_object(
        'source', 'supabase',
        'requested_at', request_time,
        'batch_window_minutes', batch_minutes
      ),
      timeout_milliseconds := 5000
    );
  end if;
end;
$$;

create or replace function public.admin_publication_control_summary()
returns jsonb
language plpgsql
stable
security definer
set search_path = public, auth, private
as $$
declare
  rebuild_hook_configured boolean := false;
  rebuild_batch_minutes integer := private.public_site_rebuild_batch_minutes();
  last_public_site_rebuild_requested_at timestamptz;
  last_public_site_change_at timestamptz;
  pending_public_site_rebuild boolean := false;
  generated timestamptz := now();
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

  select
    coalesce(last_sent_at, last_requested_at),
    coalesce(last_change_at, last_requested_at)
  into
    last_public_site_rebuild_requested_at,
    last_public_site_change_at
  from private.rebuild_state
  where name = 'public_site';

  pending_public_site_rebuild :=
    last_public_site_change_at is not null
    and (
      last_public_site_rebuild_requested_at is null
      or last_public_site_change_at > last_public_site_rebuild_requested_at
    );

  return jsonb_build_object(
    'rebuild_hook_configured', rebuild_hook_configured,
    'rebuild_batch_minutes', rebuild_batch_minutes,
    'last_public_site_rebuild_requested_at', last_public_site_rebuild_requested_at,
    'last_public_site_change_at', last_public_site_change_at,
    'pending_public_site_rebuild', pending_public_site_rebuild,
    'can_request_public_site_rebuild_now', rebuild_hook_configured and pending_public_site_rebuild,
    'generated_at', generated
  );
end;
$$;

create or replace function public.admin_request_public_site_rebuild_now(p_note text default null)
returns jsonb
language plpgsql
security definer
set search_path = public, auth, private, net
as $$
declare
  hook_url text;
  request_time timestamptz := now();
  actor_email text := lower(coalesce(auth.jwt() ->> 'email', ''));
  batch_minutes integer := private.public_site_rebuild_batch_minutes();
begin
  if not public.is_admin() then
    raise exception 'not authorized' using errcode = '42501';
  end if;

  select value
  into hook_url
  from private.app_settings
  where key = 'vitalarga_build_hook_url';

  if hook_url is null or btrim(hook_url) = '' then
    raise exception 'public build hook is not configured' using errcode = '22023';
  end if;

  insert into private.rebuild_state (name, last_requested_at, last_change_at, last_sent_at)
  values ('public_site', request_time, request_time, request_time)
  on conflict (name) do update
    set
      last_requested_at = excluded.last_requested_at,
      last_sent_at = excluded.last_sent_at,
      last_change_at = greatest(
        coalesce(private.rebuild_state.last_change_at, excluded.last_change_at),
        excluded.last_change_at
      );

  perform net.http_post(
    url := hook_url,
    body := jsonb_build_object(
      'source', 'admin_manual',
      'requested_at', request_time,
      'batch_window_minutes', batch_minutes,
      'note', nullif(btrim(coalesce(p_note, '')), '')
    ),
    timeout_milliseconds := 5000
  );

  insert into public.change_events (
    event_name,
    actor_type,
    actor_id,
    entity_type,
    payload
  )
  values (
    'public_site_rebuild_requested',
    'admin',
    actor_email,
    'public_site',
    jsonb_build_object(
      'source', 'admin_panel',
      'note', nullif(btrim(coalesce(p_note, '')), ''),
      'requested_at', request_time,
      'batch_window_minutes', batch_minutes
    )
  );

  return jsonb_build_object(
    'status', 'requested',
    'requested_at', request_time,
    'batch_window_minutes', batch_minutes
  );
end;
$$;

grant execute on function public.admin_publication_control_summary() to authenticated;
grant execute on function public.admin_request_public_site_rebuild_now(text) to authenticated;

commit;
