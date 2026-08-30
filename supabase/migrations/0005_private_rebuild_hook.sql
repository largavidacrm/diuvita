begin;

create extension if not exists pg_net with schema extensions;

create schema if not exists private;
revoke all on schema private from public;
revoke all on schema private from anon;
revoke all on schema private from authenticated;

create table if not exists private.app_settings (
  key text primary key,
  value text not null,
  updated_at timestamptz not null default now()
);

create table if not exists private.rebuild_state (
  name text primary key,
  last_requested_at timestamptz not null default now()
);

create or replace function private.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists app_settings_set_updated_at on private.app_settings;
create trigger app_settings_set_updated_at
before update on private.app_settings
for each row execute function private.set_updated_at();

create or replace function private.request_public_site_rebuild()
returns void
language plpgsql
security definer
set search_path = private, net, public
as $$
declare
  hook_url text;
  should_send boolean := false;
begin
  select value
  into hook_url
  from private.app_settings
  where key = 'vitalarga_build_hook_url';

  if hook_url is null or btrim(hook_url) = '' then
    return;
  end if;

  insert into private.rebuild_state (name, last_requested_at)
  values ('public_site', now())
  on conflict (name) do update
    set last_requested_at = excluded.last_requested_at
    where private.rebuild_state.last_requested_at < now() - interval '2 minutes'
  returning true into should_send;

  if coalesce(should_send, false) then
    perform net.http_post(
      url := hook_url,
      body := jsonb_build_object(
        'source', 'supabase',
        'requested_at', now()
      ),
      timeout_milliseconds := 5000
    );
  end if;
end;
$$;

create or replace function private.clinics_request_public_site_rebuild()
returns trigger
language plpgsql
security definer
set search_path = private, public
as $$
begin
  if tg_op = 'INSERT' then
    perform private.request_public_site_rebuild();
    return new;
  end if;

  if new.display_name is distinct from old.display_name
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
  then
    perform private.request_public_site_rebuild();
  end if;

  return new;
end;
$$;

drop trigger if exists clinics_request_public_site_rebuild on public.clinics;
create trigger clinics_request_public_site_rebuild
after insert or update on public.clinics
for each row execute function private.clinics_request_public_site_rebuild();

commit;
