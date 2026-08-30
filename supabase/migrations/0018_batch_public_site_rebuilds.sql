begin;

insert into private.app_settings (key, value)
values ('diuvita_rebuild_batch_minutes', '30')
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
  where key = 'diuvita_build_hook_url';

  if hook_url is null or btrim(hook_url) = '' then
    return;
  end if;

  select greatest(
    1,
    least(1440, coalesce(nullif(regexp_replace(value, '[^0-9]', '', 'g'), '')::integer, 30))
  )
  into batch_minutes
  from private.app_settings
  where key = 'diuvita_rebuild_batch_minutes';

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

commit;
