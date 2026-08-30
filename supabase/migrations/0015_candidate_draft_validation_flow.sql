begin;

create or replace function public.admin_create_draft_clinic_from_review_v2(
  p_review_id uuid,
  p_note text default null
)
returns public.clinics
language plpgsql
security definer
set search_path = public, auth
as $$
declare
  created_row public.clinics%rowtype;
  event_id uuid;
  next_version integer;
  actor_email text := lower(coalesce(auth.jwt() ->> 'email', ''));
begin
  if not public.is_admin() then
    raise exception 'not authorized' using errcode = '42501';
  end if;

  created_row := public.admin_create_draft_clinic_from_review(p_review_id, p_note);

  if created_row.status <> 'draft' then
    update public.clinics
    set
      status = 'draft',
      current_data = jsonb_set(
        coalesce(current_data, '{}'::jsonb),
        '{status}',
        to_jsonb('borrador'::text),
        true
      ),
      updated_at = now()
    where id = created_row.id
    returning * into created_row;

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
      'candidate_draft_status_normalized',
      'admin',
      actor_email,
      'clinic',
      created_row.id,
      created_row.id,
      jsonb_build_object(
        'review_id', p_review_id,
        'status', 'draft',
        'note', 'Candidata creada como borrador interno no publicado.'
      )
    )
    returning id into event_id;

    select coalesce(max(version_number), 0) + 1
    into next_version
    from public.entity_versions
    where entity_type = 'clinic'
      and entity_id = created_row.id;

    insert into public.entity_versions (
      entity_type,
      entity_id,
      version_number,
      data,
      source_event_id
    )
    values (
      'clinic',
      created_row.id,
      next_version,
      to_jsonb(created_row),
      event_id
    );
  end if;

  return created_row;
end;
$$;

grant execute on function public.admin_create_draft_clinic_from_review_v2(uuid, text) to authenticated;

commit;
