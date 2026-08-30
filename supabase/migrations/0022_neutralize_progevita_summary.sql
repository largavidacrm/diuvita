begin;

do $$
declare
  before_row public.clinics%rowtype;
  after_row public.clinics%rowtype;
  event_id uuid;
  next_version integer;
  clean_summary text := 'Centro de longevidad dirigido por el Dr. Miguel Ángel Fernández Torán (más de 30 años de experiencia). Programas residenciales en entorno natural con seguimiento por biomarcadores, desde ~1.470€.';
begin
  select *
  into before_row
  from public.clinics
  where slug = 'progevita'
  for update;

  if not found then
    raise notice 'Progevita clinic row not found; skipping summary neutralization.';
    return;
  end if;

  if before_row.summary is not distinct from clean_summary
    and not (
      before_row.current_data ? 'summary'
      and before_row.current_data ->> 'summary' is distinct from clean_summary
    )
  then
    raise notice 'Progevita summary already neutralized; skipping.';
    return;
  end if;

  update public.clinics
  set
    summary = clean_summary,
    current_data = case
      when current_data ? 'summary'
        then jsonb_set(current_data, '{summary}', to_jsonb(clean_summary), true)
      else current_data
    end,
    verification_status = coalesce(nullif(verification_status, ''), 'human_curated'),
    last_verified_at = now()
  where id = before_row.id
  returning * into after_row;

  update public.field_claims
  set
    value = to_jsonb(clean_summary),
    normalized_value = to_jsonb(clean_summary),
    verification_status = case
      when verification_status = 'accepted' then 'review'
      else verification_status
    end
  where clinic_id = before_row.id
    and field_path in ('summary', 'profile.summary')
    and (
      value::text ilike '%world longevity clinics%'
      or value::text ilike '%calidad-precio%'
      or value::text ilike '%clasificado%'
    );

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
    'clinic_editorial_neutralization',
    'system',
    'codex',
    'clinic',
    after_row.id,
    after_row.id,
    jsonb_build_object(
      'reason', 'Remove ranking and quality-price claim before Vitalarga domain migration',
      'field_path', 'summary',
      'before_summary', before_row.summary,
      'after_summary', after_row.summary
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
end;
$$;

commit;
