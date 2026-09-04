begin;

insert into private.app_settings (key, value)
values ('vitalarga_publication_mode', 'manual')
on conflict (key) do update
set value = excluded.value;

alter table private.rebuild_state
  add column if not exists last_change_at timestamptz,
  add column if not exists last_sent_at timestamptz,
  alter column last_requested_at drop not null;

create or replace function private.mark_public_site_rebuild_pending()
returns void
language plpgsql
security definer
set search_path = private, public
as $$
declare
  change_time timestamptz := now();
begin
  insert into private.rebuild_state (
    name,
    last_requested_at,
    last_change_at,
    last_sent_at
  )
  values ('public_site', null, change_time, null)
  on conflict (name) do update
    set last_change_at = excluded.last_change_at;
end;
$$;

-- Existing clinic triggers call this function. It deliberately records pending
-- public work without contacting Netlify. Only the authenticated admin action
-- below is allowed to consume a production deploy.
create or replace function private.request_public_site_rebuild()
returns void
language plpgsql
security definer
set search_path = private, public
as $$
begin
  perform private.mark_public_site_rebuild_pending();
end;
$$;

create or replace function private.clinics_request_public_site_rebuild()
returns trigger
language plpgsql
security definer
set search_path = private, public
as $$
declare
  was_public boolean := false;
  is_public boolean := false;
begin
  if tg_op = 'INSERT' then
    if new.status in ('published', 'preliminary') then
      perform private.mark_public_site_rebuild_pending();
    end if;
    return new;
  end if;

  was_public := old.status in ('published', 'preliminary');
  is_public := new.status in ('published', 'preliminary');

  if (was_public or is_public)
    and (
      new.display_name is distinct from old.display_name
      or new.website is distinct from old.website
      or new.country is distinct from old.country
      or new.city is distinct from old.city
      or new.region is distinct from old.region
      or new.address is distinct from old.address
      or new.status is distinct from old.status
      or new.summary is distinct from old.summary
      or new.current_data is distinct from old.current_data
      or new.profile_confidence is distinct from old.profile_confidence
      or new.verification_status is distinct from old.verification_status
    )
  then
    perform private.mark_public_site_rebuild_pending();
  end if;

  return new;
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
  has_pending_changes boolean := false;
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

  select
    coalesce(last_change_at, last_requested_at) is not null
    and (
      coalesce(last_sent_at, last_requested_at) is null
      or coalesce(last_change_at, last_requested_at) > coalesce(last_sent_at, last_requested_at)
    )
  into has_pending_changes
  from private.rebuild_state
  where name = 'public_site'
  for update;

  if not coalesce(has_pending_changes, false) then
    return jsonb_build_object(
      'status', 'skipped',
      'reason', 'no_pending_changes',
      'publication_mode', 'manual'
    );
  end if;

  insert into private.rebuild_state (
    name,
    last_requested_at,
    last_change_at,
    last_sent_at
  )
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
      'publication_mode', 'manual'
    )
  );

  return jsonb_build_object(
    'status', 'requested',
    'requested_at', request_time,
    'publication_mode', 'manual'
  );
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
  publication_mode text := 'manual';
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

  select coalesce(lower(nullif(btrim(value), '')), 'manual')
  into publication_mode
  from private.app_settings
  where key = 'vitalarga_publication_mode';

  publication_mode := coalesce(publication_mode, 'manual');

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
    'publication_mode', publication_mode,
    'automatic_rebuild_enabled', false,
    'rebuild_batch_minutes', rebuild_batch_minutes,
    'last_public_site_rebuild_requested_at', last_public_site_rebuild_requested_at,
    'last_public_site_change_at', last_public_site_change_at,
    'pending_public_site_rebuild', pending_public_site_rebuild,
    'can_request_public_site_rebuild_now', rebuild_hook_configured and pending_public_site_rebuild,
    'generated_at', generated
  );
end;
$$;

comment on function private.request_public_site_rebuild() is
  'Marks public-site changes as pending. It never calls the Netlify build hook.';

comment on function private.clinics_request_public_site_rebuild() is
  'Marks pending work only when a visible clinic is added, changed, published, or removed from publication.';

comment on function public.admin_request_public_site_rebuild_now(text) is
  'The only path that requests a paid Netlify production deploy.';

grant execute on function public.admin_request_public_site_rebuild_now(text) to authenticated;

commit;
