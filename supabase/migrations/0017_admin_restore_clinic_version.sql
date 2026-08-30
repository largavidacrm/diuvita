begin;

create or replace function public.admin_restore_clinic_version(
  p_clinic_id uuid,
  p_version_id uuid,
  p_note text default null
)
returns public.clinics
language plpgsql
security definer
set search_path = public, auth
as $$
declare
  before_row public.clinics%rowtype;
  after_row public.clinics%rowtype;
  version_row public.entity_versions%rowtype;
  version_data jsonb;
  clean_current_data jsonb;
  clean_status text;
  actor_email text := lower(coalesce(auth.jwt() ->> 'email', ''));
  event_id uuid;
  next_version integer;
begin
  if not public.is_admin() then
    raise exception 'not authorized' using errcode = '42501';
  end if;

  select *
  into before_row
  from public.clinics
  where id = p_clinic_id
  for update;

  if not found then
    raise exception 'clinic not found' using errcode = 'P0002';
  end if;

  select *
  into version_row
  from public.entity_versions
  where id = p_version_id
    and entity_type = 'clinic'
    and entity_id = p_clinic_id;

  if not found then
    raise exception 'version not found' using errcode = 'P0002';
  end if;

  version_data := coalesce(version_row.data, '{}'::jsonb);
  clean_status := nullif(btrim(coalesce(version_data ->> 'status', '')), '');

  if clean_status is null or clean_status not in (
    'draft',
    'discovered',
    'extracted',
    'verified',
    'review',
    'published',
    'preliminary',
    'archived'
  ) then
    raise exception 'invalid version status' using errcode = '22023';
  end if;

  clean_current_data := coalesce(version_data -> 'current_data', '{}'::jsonb);
  if jsonb_typeof(clean_current_data) <> 'object' then
    clean_current_data := '{}'::jsonb;
  end if;

  clean_current_data := jsonb_set(
    clean_current_data,
    '{status}',
    to_jsonb(case clean_status
      when 'published' then 'publicada'
      when 'preliminary' then 'preliminar'
      when 'review' then 'revision'
      when 'verified' then 'verificada'
      when 'extracted' then 'extraida'
      when 'discovered' then 'descubierta'
      when 'draft' then 'borrador'
      when 'archived' then 'archivada'
      else clean_status
    end),
    true
  );

  update public.clinics
  set
    canonical_name = coalesce(nullif(btrim(coalesce(version_data ->> 'canonical_name', '')), ''), before_row.canonical_name),
    display_name = coalesce(nullif(btrim(coalesce(version_data ->> 'display_name', '')), ''), before_row.display_name),
    website = nullif(btrim(coalesce(version_data ->> 'website', '')), ''),
    country = coalesce(nullif(btrim(coalesce(version_data ->> 'country', '')), ''), before_row.country),
    city = coalesce(nullif(btrim(coalesce(version_data ->> 'city', '')), ''), before_row.city),
    region = nullif(btrim(coalesce(version_data ->> 'region', '')), ''),
    address = nullif(btrim(coalesce(version_data ->> 'address', '')), ''),
    status = clean_status,
    summary = nullif(btrim(coalesce(version_data ->> 'summary', '')), ''),
    current_data = clean_current_data,
    profile_confidence = coalesce(nullif(version_data ->> 'profile_confidence', '')::numeric, before_row.profile_confidence),
    verification_status = coalesce(nullif(btrim(coalesce(version_data ->> 'verification_status', '')), ''), before_row.verification_status),
    last_verified_at = coalesce(nullif(version_data ->> 'last_verified_at', '')::timestamptz, before_row.last_verified_at)
  where id = p_clinic_id
  returning * into after_row;

  insert into public.change_events (
    event_name,
    actor_type,
    actor_id,
    entity_type,
    entity_id,
    clinic_id,
    payload
  )
  values (
    'clinic_version_restored',
    'admin',
    actor_email,
    'clinic',
    after_row.id,
    after_row.id,
    jsonb_build_object(
      'source', 'admin_panel',
      'note', nullif(btrim(coalesce(p_note, '')), ''),
      'restored_version_id', version_row.id,
      'restored_version_number', version_row.version_number,
      'before', to_jsonb(before_row),
      'after', to_jsonb(after_row)
    )
  )
  returning id into event_id;

  select coalesce(max(version_number), 0) + 1
  into next_version
  from public.entity_versions
  where entity_type = 'clinic'
    and entity_id = after_row.id;

  insert into public.entity_versions (
    entity_type,
    entity_id,
    version_number,
    data,
    source_event_id
  )
  values (
    'clinic',
    after_row.id,
    next_version,
    to_jsonb(after_row),
    event_id
  );

  return after_row;
end;
$$;

grant execute on function public.admin_restore_clinic_version(uuid, uuid, text) to authenticated;

commit;
