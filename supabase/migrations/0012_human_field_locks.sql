begin;

create unique index if not exists human_overrides_active_clinic_field_idx
on public.human_overrides (clinic_id, field_path)
where locked = true;

create or replace function public.admin_set_clinic_field_locks(
  p_clinic_id uuid,
  p_field_paths text[] default array[]::text[],
  p_values jsonb default '{}'::jsonb,
  p_reason text default null
)
returns jsonb
language plpgsql
security definer
set search_path = public, auth
as $$
declare
  actor_email text := lower(coalesce(auth.jwt() ->> 'email', ''));
  supported_paths constant text[] := array[
    'profile.name',
    'contact.website',
    'location.country',
    'location.city',
    'location.region',
    'location.address',
    'summary',
    'services.list',
    'specialties.list',
    'units.list',
    'professionals.published',
    'technologies.list',
    'contact.email',
    'contact.phone',
    'contact.instagram'
  ];
  clean_paths text[];
  unlocked_count integer := 0;
  active_count integer := 0;
begin
  if not public.is_admin() then
    raise exception 'not authorized' using errcode = '42501';
  end if;

  if not exists (select 1 from public.clinics where id = p_clinic_id) then
    raise exception 'clinic not found' using errcode = 'P0002';
  end if;

  select coalesce(array_agg(distinct path), array[]::text[])
  into clean_paths
  from unnest(coalesce(p_field_paths, array[]::text[])) as input_path(path)
  where path = any(supported_paths);

  update public.human_overrides
  set locked = false
  where clinic_id = p_clinic_id
    and entity_type = 'clinic'
    and locked = true
    and field_path = any(supported_paths)
    and not (field_path = any(clean_paths));

  get diagnostics unlocked_count = row_count;

  update public.human_overrides ho
  set
    value = coalesce(p_values -> ho.field_path, ho.value),
    reason = nullif(btrim(coalesce(p_reason, '')), ''),
    created_by = actor_email,
    created_at = now()
  where ho.clinic_id = p_clinic_id
    and ho.entity_type = 'clinic'
    and ho.locked = true
    and ho.field_path = any(clean_paths);

  insert into public.human_overrides (
    clinic_id,
    entity_type,
    entity_id,
    field_path,
    value,
    reason,
    locked,
    created_by
  )
  select
    p_clinic_id,
    'clinic',
    p_clinic_id,
    path,
    coalesce(p_values -> path, to_jsonb(true)),
    nullif(btrim(coalesce(p_reason, '')), ''),
    true,
    actor_email
  from unnest(clean_paths) as selected_path(path)
  where not exists (
    select 1
    from public.human_overrides existing
    where existing.clinic_id = p_clinic_id
      and existing.entity_type = 'clinic'
      and existing.field_path = path
      and existing.locked = true
  );

  select count(*)
  into active_count
  from public.human_overrides
  where clinic_id = p_clinic_id
    and entity_type = 'clinic'
    and locked = true
    and field_path = any(supported_paths);

  if cardinality(clean_paths) > 0 or unlocked_count > 0 then
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
      'clinic_field_locks_updated',
      'admin',
      actor_email,
      'clinic',
      p_clinic_id,
      p_clinic_id,
      jsonb_build_object(
        'locked_fields', clean_paths,
        'active_locked_fields', active_count,
        'unlocked_fields_count', unlocked_count,
        'note', nullif(btrim(coalesce(p_reason, '')), '')
      )
    );
  end if;

  return jsonb_build_object(
    'active_locked_fields', active_count,
    'unlocked_fields_count', unlocked_count
  );
end;
$$;

grant execute on function public.admin_set_clinic_field_locks(uuid, text[], jsonb, text) to authenticated;

commit;
