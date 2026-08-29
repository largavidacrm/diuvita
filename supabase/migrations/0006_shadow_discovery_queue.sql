begin;

create or replace function public.slugify_simple(p_text text)
returns text
language sql
immutable
as $$
  select coalesce(
    nullif(
      trim(
        both '-' from regexp_replace(
          translate(
            lower(coalesce(p_text, '')),
            'áàäâãåéèëêíìïîóòöôõúùüûñç',
            'aaaaaaeeeeiiiiooooouuuunc'
          ),
          '[^a-z0-9]+',
          '-',
          'g'
        )
      ),
      ''
    ),
    'clinica'
  );
$$;

create or replace function public.admin_pick_agent_job(
  p_worker text default 'manual-shadow-worker',
  p_job_type text default null
)
returns jsonb
language plpgsql
security definer
set search_path = public, auth
as $$
declare
  target_job_id uuid;
  picked_job jsonb;
  clean_worker text := nullif(btrim(coalesce(p_worker, '')), '');
begin
  if not public.is_admin() then
    raise exception 'not authorized' using errcode = '42501';
  end if;

  if clean_worker is null then
    raise exception 'worker name is required' using errcode = '22023';
  end if;

  select id
  into target_job_id
  from public.agent_jobs
  where status = 'queued'
    and scheduled_for <= now()
    and (p_job_type is null or job_type = p_job_type)
  order by priority asc, scheduled_for asc, created_at asc
  for update skip locked
  limit 1;

  if target_job_id is null then
    return null;
  end if;

  update public.agent_jobs
  set
    status = 'running',
    attempts = attempts + 1,
    locked_by = clean_worker,
    started_at = now(),
    finished_at = null,
    error_message = null
  where id = target_job_id
  returning to_jsonb(public.agent_jobs.*) into picked_job;

  insert into public.change_events (
    event_name,
    actor_type,
    actor_id,
    entity_type,
    entity_id,
    payload
  )
  values (
    'agent_job_picked',
    'admin',
    lower(coalesce(auth.jwt() ->> 'email', '')),
    'agent_job',
    target_job_id,
    jsonb_build_object('worker', clean_worker)
  );

  return picked_job;
end;
$$;

create or replace function public.admin_complete_discovery_job(
  p_job_id uuid,
  p_candidates jsonb,
  p_note text default null,
  p_confidence numeric default null,
  p_cost_cents integer default 0
)
returns jsonb
language plpgsql
security definer
set search_path = public, auth
as $$
declare
  job_row public.agent_jobs%rowtype;
  candidate jsonb;
  candidate_count integer := 0;
  review_count integer := 0;
  clean_note text := nullif(btrim(coalesce(p_note, '')), '');
  clean_confidence numeric := p_confidence;
  clean_cost integer := coalesce(p_cost_cents, 0);
  candidate_name text;
  candidate_website text;
  candidate_city text;
  candidate_country text;
  candidate_source text;
  candidate_confidence numeric;
  raw_candidate_confidence text;
  item_title text;
  item_priority integer;
  actor_email text := lower(coalesce(auth.jwt() ->> 'email', ''));
begin
  if not public.is_admin() then
    raise exception 'not authorized' using errcode = '42501';
  end if;

  if p_candidates is null or jsonb_typeof(p_candidates) <> 'array' then
    raise exception 'candidates must be a json array' using errcode = '22023';
  end if;

  candidate_count := jsonb_array_length(p_candidates);
  if candidate_count > 50 then
    raise exception 'too many candidates for one review batch' using errcode = '22023';
  end if;

  if clean_confidence is not null and (clean_confidence < 0 or clean_confidence > 1) then
    raise exception 'confidence must be between 0 and 1' using errcode = '22023';
  end if;

  if clean_cost < 0 then
    raise exception 'cost cannot be negative' using errcode = '22023';
  end if;

  select *
  into job_row
  from public.agent_jobs
  where id = p_job_id
  for update;

  if not found then
    raise exception 'job not found' using errcode = 'P0002';
  end if;

  if job_row.job_type <> 'DISCOVER_CLINIC' then
    raise exception 'job is not a discovery job' using errcode = '22023';
  end if;

  if job_row.status not in ('queued', 'running', 'failed') then
    raise exception 'job cannot be completed from status %', job_row.status using errcode = '22023';
  end if;

  for candidate in select value from jsonb_array_elements(p_candidates)
  loop
    if jsonb_typeof(candidate) <> 'object' then
      continue;
    end if;

    candidate_name := nullif(btrim(coalesce(candidate ->> 'name', candidate ->> 'clinic_name', '')), '');
    candidate_website := nullif(btrim(coalesce(candidate ->> 'website', candidate ->> 'web', '')), '');
    candidate_city := nullif(btrim(coalesce(candidate ->> 'city', '')), '');
    candidate_country := nullif(btrim(coalesce(candidate ->> 'country', job_row.input ->> 'country', '')), '');
    candidate_source := nullif(btrim(coalesce(candidate ->> 'source_url', candidate_website, '')), '');

    if candidate_name is null and candidate_website is null and candidate_source is null then
      continue;
    end if;

    raw_candidate_confidence := nullif(btrim(coalesce(candidate ->> 'discovery_confidence', candidate ->> 'confidence', '')), '');
    candidate_confidence := null;
    if raw_candidate_confidence ~ '^[0-9]+(\.[0-9]+)?$' then
      candidate_confidence := least(1, greatest(0, raw_candidate_confidence::numeric));
    end if;

    item_priority := case
      when candidate_confidence is null then 100
      when candidate_confidence >= 0.80 then 70
      when candidate_confidence >= 0.55 then 90
      else 115
    end;

    item_title := coalesce(candidate_name, candidate_website, candidate_source, 'Clínica candidata');
    if candidate_city is not null then
      item_title := item_title || ' · ' || candidate_city;
    end if;

    insert into public.review_queue (
      job_id,
      review_type,
      title,
      priority,
      status,
      payload
    )
    values (
      job_row.id,
      'candidate_clinic',
      item_title,
      item_priority,
      'open',
      jsonb_strip_nulls(jsonb_build_object(
        'mode', 'shadow',
        'candidate', candidate,
        'job_input', job_row.input,
        'note', clean_note,
        'candidate_name', candidate_name,
        'candidate_website', candidate_website,
        'candidate_city', candidate_city,
        'candidate_country', candidate_country,
        'candidate_source_url', candidate_source
      ))
    );

    review_count := review_count + 1;
  end loop;

  update public.agent_jobs
  set
    status = 'completed',
    output = jsonb_strip_nulls(jsonb_build_object(
      'mode', 'shadow',
      'candidates', p_candidates,
      'review_items_created', review_count,
      'note', clean_note,
      'completed_by', actor_email
    )),
    confidence = clean_confidence,
    requires_human = true,
    cost_cents = cost_cents + clean_cost,
    locked_by = null,
    started_at = coalesce(started_at, now()),
    finished_at = now(),
    error_message = null
  where id = job_row.id;

  insert into public.change_events (
    event_name,
    actor_type,
    actor_id,
    entity_type,
    entity_id,
    payload
  )
  values (
    'discovery_shadow_completed',
    'admin',
    actor_email,
    'agent_job',
    job_row.id,
    jsonb_build_object(
      'review_items_created', review_count,
      'candidate_count', candidate_count
    )
  );

  return jsonb_build_object(
    'job_id', job_row.id,
    'status', 'completed',
    'mode', 'shadow',
    'candidate_count', candidate_count,
    'review_items_created', review_count
  );
end;
$$;

create or replace function public.admin_fail_agent_job(
  p_job_id uuid,
  p_error text
)
returns public.agent_jobs
language plpgsql
security definer
set search_path = public, auth
as $$
declare
  job_row public.agent_jobs%rowtype;
  failed_row public.agent_jobs%rowtype;
  clean_error text := nullif(btrim(coalesce(p_error, '')), '');
  actor_email text := lower(coalesce(auth.jwt() ->> 'email', ''));
begin
  if not public.is_admin() then
    raise exception 'not authorized' using errcode = '42501';
  end if;

  if clean_error is null then
    raise exception 'error message is required' using errcode = '22023';
  end if;

  select *
  into job_row
  from public.agent_jobs
  where id = p_job_id
  for update;

  if not found then
    raise exception 'job not found' using errcode = 'P0002';
  end if;

  update public.agent_jobs
  set
    status = case when attempts >= max_attempts then 'dead_letter' else 'failed' end,
    error_message = clean_error,
    locked_by = null,
    finished_at = now()
  where id = job_row.id
  returning * into failed_row;

  insert into public.change_events (
    event_name,
    actor_type,
    actor_id,
    entity_type,
    entity_id,
    payload
  )
  values (
    'agent_job_failed',
    'admin',
    actor_email,
    'agent_job',
    job_row.id,
    jsonb_build_object('error', clean_error, 'status', failed_row.status)
  );

  return failed_row;
end;
$$;

create or replace function public.admin_resolve_review_item(
  p_review_id uuid,
  p_status text,
  p_note text default null
)
returns public.review_queue
language plpgsql
security definer
set search_path = public, auth
as $$
declare
  review_row public.review_queue%rowtype;
  updated_row public.review_queue%rowtype;
  clean_status text := nullif(btrim(coalesce(p_status, '')), '');
  clean_note text := nullif(btrim(coalesce(p_note, '')), '');
  actor_email text := lower(coalesce(auth.jwt() ->> 'email', ''));
begin
  if not public.is_admin() then
    raise exception 'not authorized' using errcode = '42501';
  end if;

  if clean_status not in ('open', 'resolved', 'dismissed') then
    raise exception 'invalid review status' using errcode = '22023';
  end if;

  select *
  into review_row
  from public.review_queue
  where id = p_review_id
  for update;

  if not found then
    raise exception 'review item not found' using errcode = 'P0002';
  end if;

  update public.review_queue
  set
    status = clean_status,
    resolution = case
      when clean_status = 'open' then '{}'::jsonb
      else jsonb_strip_nulls(jsonb_build_object(
        'action', clean_status,
        'note', clean_note,
        'actor_email', actor_email
      ))
    end,
    resolved_by = case when clean_status = 'open' then null else actor_email end,
    resolved_at = case when clean_status = 'open' then null else now() end
  where id = review_row.id
  returning * into updated_row;

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
    'review_item_status_changed',
    'admin',
    actor_email,
    'review_queue',
    review_row.id,
    review_row.clinic_id,
    jsonb_build_object('from', review_row.status, 'to', clean_status, 'note', clean_note)
  );

  return updated_row;
end;
$$;

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
  event_id uuid;
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
    where regexp_replace(lower(coalesce(c.website, '')), '/+$', '') = regexp_replace(lower(clean_website), '/+$', '')
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

  if source_url is not null then
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

  update public.review_queue
  set
    status = 'resolved',
    clinic_id = inserted_row.id,
    resolution = jsonb_strip_nulls(jsonb_build_object(
      'action', 'draft_created',
      'clinic_id', inserted_row.id,
      'clinic_slug', inserted_row.slug,
      'source_record_id', source_id,
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
      'source_record_id', source_id
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

grant execute on function public.slugify_simple(text) to authenticated, anon;
grant execute on function public.admin_pick_agent_job(text, text) to authenticated;
grant execute on function public.admin_complete_discovery_job(uuid, jsonb, text, numeric, integer) to authenticated;
grant execute on function public.admin_fail_agent_job(uuid, text) to authenticated;
grant execute on function public.admin_resolve_review_item(uuid, text, text) to authenticated;
grant execute on function public.admin_create_draft_clinic_from_review(uuid, text) to authenticated;

commit;
