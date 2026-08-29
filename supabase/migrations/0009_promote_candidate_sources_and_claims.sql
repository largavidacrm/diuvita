begin;

create or replace function public.admin_create_draft_clinic_from_review(
  p_review_id uuid,
  p_note text default null
)
returns public.clinics
language plpgsql
security definer
set search_path = public, auth
as $$
declare
  review_row public.review_queue%rowtype;
  candidate jsonb;
  inserted_row public.clinics%rowtype;
  source_id uuid;
  review_source_id uuid;
  event_id uuid;
  inserted_claim_count integer := 0;
  actor_email text := lower(coalesce(auth.jwt() ->> 'email', ''));
  clean_note text := nullif(btrim(coalesce(p_note, '')), '');
  clean_name text;
  clean_website text;
  clean_country text;
  clean_city text;
  clean_summary text;
  source_url text;
  base_slug text;
  final_slug text;
  suffix integer := 2;
  raw_confidence text;
  clean_confidence numeric := 0.4;
begin
  if not public.is_admin() then
    raise exception 'not authorized' using errcode = '42501';
  end if;

  select *
  into review_row
  from public.review_queue
  where id = p_review_id
  for update;

  if not found then
    raise exception 'review item not found' using errcode = 'P0002';
  end if;

  if review_row.status <> 'open' then
    raise exception 'review item is not open' using errcode = '22023';
  end if;

  if review_row.review_type <> 'candidate_clinic' then
    raise exception 'review item is not a clinic candidate' using errcode = '22023';
  end if;

  candidate := coalesce(review_row.payload -> 'candidate', review_row.payload);
  if candidate is null or jsonb_typeof(candidate) <> 'object' then
    raise exception 'candidate payload is invalid' using errcode = '22023';
  end if;

  clean_name := nullif(btrim(coalesce(candidate ->> 'name', candidate ->> 'clinic_name', '')), '');
  clean_website := nullif(btrim(coalesce(candidate ->> 'website', candidate ->> 'web', '')), '');
  clean_country := nullif(btrim(coalesce(candidate ->> 'country', review_row.payload -> 'job_input' ->> 'country', 'España')), '');
  clean_city := nullif(btrim(coalesce(candidate ->> 'city', 'Por verificar')), '');
  clean_summary := nullif(btrim(coalesce(candidate ->> 'summary', '')), '');
  source_url := nullif(btrim(coalesce(candidate ->> 'source_url', clean_website, '')), '');
  raw_confidence := nullif(btrim(coalesce(candidate ->> 'discovery_confidence', candidate ->> 'confidence', '')), '');

  if review_row.payload ->> 'source_record_id' ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' then
    review_source_id := (review_row.payload ->> 'source_record_id')::uuid;
  end if;

  if clean_name is null then
    raise exception 'candidate name is required' using errcode = '22023';
  end if;

  if clean_website is not null and clean_website !~* '^https?://' then
    raise exception 'candidate website must start with http or https' using errcode = '22023';
  end if;

  if source_url is not null and source_url !~* '^https?://' then
    source_url := clean_website;
  end if;

  if raw_confidence ~ '^[0-9]+(\.[0-9]+)?$' then
    clean_confidence := least(1, greatest(0, raw_confidence::numeric));
  end if;

  if clean_website is not null and exists (
    select 1
    from public.clinics c
    where public.normalized_url_host(coalesce(c.website, c.current_data ->> 'web')) = public.normalized_url_host(clean_website)
  ) then
    raise exception 'a clinic with this website already exists' using errcode = '23505';
  end if;

  if exists (
    select 1
    from public.clinics c
    where lower(c.display_name) = lower(clean_name)
      and lower(c.city) = lower(clean_city)
      and lower(c.country) = lower(clean_country)
  ) then
    raise exception 'a clinic with this name and city already exists' using errcode = '23505';
  end if;

  base_slug := public.slugify_simple(clean_name);
  final_slug := base_slug;

  while exists (select 1 from public.clinics where slug = final_slug)
  loop
    final_slug := base_slug || '-' || suffix::text;
    suffix := suffix + 1;
  end loop;

  insert into public.clinics (
    slug,
    canonical_name,
    display_name,
    website,
    country,
    city,
    status,
    summary,
    current_data,
    profile_confidence,
    verification_status
  )
  values (
    final_slug,
    clean_name,
    clean_name,
    clean_website,
    clean_country,
    clean_city,
    'discovered',
    clean_summary,
    jsonb_strip_nulls(jsonb_build_object(
      'slug', final_slug,
      'name', clean_name,
      'web', clean_website,
      'country', clean_country,
      'city', clean_city,
      'status', 'descubierta',
      'summary', clean_summary,
      'services', coalesce(candidate -> 'services', '[]'::jsonb),
      'specialties', coalesce(candidate -> 'specialties', '[]'::jsonb),
      'profesionales', coalesce(candidate -> 'profesionales', candidate -> 'professionals', '[]'::jsonb),
      'source_url', source_url
    )),
    clean_confidence,
    'agent_candidate'
  )
  returning * into inserted_row;

  if review_source_id is not null then
    update public.source_records
    set
      clinic_id = inserted_row.id,
      entity_type = 'clinic',
      entity_id = inserted_row.id,
      source_title = coalesce(source_title, clean_name),
      metadata = metadata || jsonb_build_object(
        'promoted_from_review_id', review_row.id,
        'promoted_clinic_id', inserted_row.id
      )
    where id = review_source_id
    returning id into source_id;
  end if;

  if source_id is null and source_url is not null then
    insert into public.source_records (
      clinic_id,
      entity_type,
      entity_id,
      source_url,
      source_title,
      source_type,
      metadata
    )
    values (
      inserted_row.id,
      'clinic',
      inserted_row.id,
      source_url,
      clean_name,
      'discovery',
      jsonb_build_object('review_id', review_row.id, 'job_id', review_row.job_id)
    )
    returning id into source_id;
  end if;

  insert into public.field_claims (
    clinic_id,
    entity_type,
    entity_id,
    field_path,
    value,
    source_record_id,
    agent_name,
    agent_version,
    confidence,
    verification_status
  )
  select
    inserted_row.id,
    'clinic',
    inserted_row.id,
    claim.field_path,
    claim.value,
    source_id,
    'diuvita-shadow-discovery',
    '2026-08-29',
    clean_confidence,
    'review'
  from (
    values
      ('identity.canonical_name', to_jsonb(clean_name::text)),
      ('contact.website', to_jsonb(clean_website::text)),
      ('location.country', to_jsonb(clean_country::text)),
      ('location.city', to_jsonb(clean_city::text)),
      ('profile.summary', to_jsonb(clean_summary::text)),
      ('services.list', case when jsonb_typeof(candidate -> 'services') = 'array' then candidate -> 'services' else null end),
      ('specialties.list', case when jsonb_typeof(candidate -> 'specialties') = 'array' then candidate -> 'specialties' else null end),
      ('team.public_professionals', case
        when jsonb_typeof(candidate -> 'profesionales') = 'array' then candidate -> 'profesionales'
        when jsonb_typeof(candidate -> 'professionals') = 'array' then candidate -> 'professionals'
        else null
      end)
  ) as claim(field_path, value)
  where claim.value is not null
    and claim.value <> '[]'::jsonb
    and claim.value <> 'null'::jsonb;

  get diagnostics inserted_claim_count = row_count;

  update public.review_queue
  set
    status = 'resolved',
    clinic_id = inserted_row.id,
    resolution = jsonb_strip_nulls(jsonb_build_object(
      'action', 'draft_created',
      'clinic_id', inserted_row.id,
      'clinic_slug', inserted_row.slug,
      'source_record_id', source_id,
      'field_claims_created', inserted_claim_count,
      'note', clean_note,
      'actor_email', actor_email
    )),
    resolved_by = actor_email,
    resolved_at = now()
  where id = review_row.id;

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
    'candidate_review_draft_created',
    'admin',
    actor_email,
    'clinic',
    inserted_row.id,
    inserted_row.id,
    jsonb_build_object(
      'review_id', review_row.id,
      'job_id', review_row.job_id,
      'source_record_id', source_id,
      'field_claims_created', inserted_claim_count
    )
  )
  returning id into event_id;

  insert into public.entity_versions (
    entity_type,
    entity_id,
    version_number,
    data,
    source_event_id
  )
  values (
    'clinic',
    inserted_row.id,
    1,
    to_jsonb(inserted_row),
    event_id
  );

  return inserted_row;
end;
$$;

grant execute on function public.admin_create_draft_clinic_from_review(uuid, text) to authenticated;

commit;
