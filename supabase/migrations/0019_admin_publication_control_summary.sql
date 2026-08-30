begin;

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
    where key = 'diuvita_build_hook_url'
      and btrim(value) <> ''
  )
  into rebuild_hook_configured;

  select coalesce(
    max(greatest(1, least(1440, nullif(regexp_replace(value, '[^0-9]', '', 'g'), '')::integer))),
    2
  )
  into rebuild_batch_minutes
  from private.app_settings
  where key = 'diuvita_rebuild_batch_minutes';

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
