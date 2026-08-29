begin;

create or replace function public.admin_update_clinic(
  p_clinic_id uuid,
  p_display_name text,
  p_website text,
  p_country text,
  p_city text,
  p_region text,
  p_address text,
  p_status text,
  p_summary text,
  p_current_data jsonb,
  p_profile_confidence numeric,
  p_verification_status text,
  p_change_note text default null
)
returns public.clinics
language plpgsql
security definer
set search_path = public, auth
as $$
declare
  before_row public.clinics%rowtype;
  after_row public.clinics%rowtype;
  actor_email text := lower(coalesce(auth.jwt() ->> 'email', ''));
  event_id uuid;
  next_version integer;
  clean_display_name text := nullif(btrim(coalesce(p_display_name, '')), '');
  clean_country text := nullif(btrim(coalesce(p_country, '')), '');
  clean_city text := nullif(btrim(coalesce(p_city, '')), '');
  clean_status text := nullif(btrim(coalesce(p_status, '')), '');
  clean_confidence numeric := coalesce(p_profile_confidence, 0);
begin
  if not public.is_admin() then
    raise exception 'not authorized' using errcode = '42501';
  end if;

  if clean_display_name is null then
    raise exception 'display name is required' using errcode = '22023';
  end if;

  if clean_country is null then
    raise exception 'country is required' using errcode = '22023';
  end if;

  if clean_city is null then
    raise exception 'city is required' using errcode = '22023';
  end if;

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
    raise exception 'invalid status' using errcode = '22023';
  end if;

  if clean_confidence < 0 or clean_confidence > 1 then
    raise exception 'confidence must be between 0 and 1' using errcode = '22023';
  end if;

  select *
  into before_row
  from public.clinics
  where id = p_clinic_id
  for update;

  if not found then
    raise exception 'clinic not found' using errcode = 'P0002';
  end if;

  update public.clinics
  set
    canonical_name = clean_display_name,
    display_name = clean_display_name,
    website = nullif(btrim(coalesce(p_website, '')), ''),
    country = clean_country,
    city = clean_city,
    region = nullif(btrim(coalesce(p_region, '')), ''),
    address = nullif(btrim(coalesce(p_address, '')), ''),
    status = clean_status,
    summary = nullif(btrim(coalesce(p_summary, '')), ''),
    current_data = coalesce(p_current_data, '{}'::jsonb),
    profile_confidence = clean_confidence,
    verification_status = coalesce(nullif(btrim(coalesce(p_verification_status, '')), ''), 'human_curated'),
    last_verified_at = now()
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
    'clinic_manual_update',
    'admin',
    actor_email,
    'clinic',
    after_row.id,
    after_row.id,
    jsonb_build_object(
      'source', 'admin_panel',
      'note', nullif(btrim(coalesce(p_change_note, '')), ''),
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

grant execute on function public.admin_update_clinic(
  uuid,
  text,
  text,
  text,
  text,
  text,
  text,
  text,
  text,
  jsonb,
  numeric,
  text,
  text
) to authenticated;

commit;
