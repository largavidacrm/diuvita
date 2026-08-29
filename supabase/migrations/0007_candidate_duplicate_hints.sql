begin;

create or replace function public.normalized_url_host(p_url text)
returns text
language sql
immutable
as $$
  select nullif(
    regexp_replace(
      regexp_replace(
        regexp_replace(
          lower(btrim(coalesce(p_url, ''))),
          '^https?://',
          ''
        ),
        '^www\.',
        ''
      ),
      '[/?#:].*$',
      ''
    ),
    ''
  );
$$;

create or replace function public.admin_candidate_duplicate_matches(
  p_candidate jsonb,
  p_country text default null
)
returns jsonb
language plpgsql
stable
security definer
set search_path = public, auth
as $$
declare
  clean_name text := nullif(btrim(coalesce(p_candidate ->> 'name', p_candidate ->> 'clinic_name', '')), '');
  clean_city text := nullif(btrim(coalesce(p_candidate ->> 'city', '')), '');
  clean_country text := nullif(btrim(coalesce(p_candidate ->> 'country', p_country, '')), '');
  candidate_host text := public.normalized_url_host(coalesce(p_candidate ->> 'website', p_candidate ->> 'web'));
  clean_name_slug text := public.slugify_simple(coalesce(p_candidate ->> 'name', p_candidate ->> 'clinic_name', ''));
  matches jsonb;
begin
  if not public.is_admin() then
    raise exception 'not authorized' using errcode = '42501';
  end if;

  if clean_name is null and candidate_host is null then
    return '[]'::jsonb;
  end if;

  select coalesce(
    jsonb_agg(
      jsonb_build_object(
        'id', scored.id,
        'slug', scored.slug,
        'name', scored.display_name,
        'website', scored.website,
        'city', scored.city,
        'country', scored.country,
        'status', scored.status,
        'reason', scored.reason,
        'duplicate_probability', scored.duplicate_probability
      )
      order by scored.duplicate_probability desc, scored.display_name asc
    ),
    '[]'::jsonb
  )
  into matches
  from (
    select *
    from (
      select
        c.id,
        c.slug,
        c.display_name,
        coalesce(c.website, c.current_data ->> 'web') as website,
        c.city,
        c.country,
        c.status,
        case
          when candidate_host is not null
            and public.normalized_url_host(coalesce(c.website, c.current_data ->> 'web')) = candidate_host
            then 'same_website'
          when clean_name is not null
            and public.slugify_simple(c.display_name) = clean_name_slug
            and clean_city is not null
            and lower(c.city) = lower(clean_city)
            and clean_country is not null
            and lower(c.country) = lower(clean_country)
            then 'same_name_city'
          when clean_name is not null
            and public.slugify_simple(c.display_name) = clean_name_slug
            and clean_country is not null
            and lower(c.country) = lower(clean_country)
            then 'same_name_country'
          when clean_name is not null
            and replace(public.slugify_simple(c.display_name), '-', '') = replace(clean_name_slug, '-', '')
            then 'same_name_slug'
          else null
        end as reason,
        case
          when candidate_host is not null
            and public.normalized_url_host(coalesce(c.website, c.current_data ->> 'web')) = candidate_host
            then 0.98
          when clean_name is not null
            and public.slugify_simple(c.display_name) = clean_name_slug
            and clean_city is not null
            and lower(c.city) = lower(clean_city)
            and clean_country is not null
            and lower(c.country) = lower(clean_country)
            then 0.94
          when clean_name is not null
            and public.slugify_simple(c.display_name) = clean_name_slug
            and clean_country is not null
            and lower(c.country) = lower(clean_country)
            then 0.82
          when clean_name is not null
            and replace(public.slugify_simple(c.display_name), '-', '') = replace(clean_name_slug, '-', '')
            then 0.76
          else 0
        end as duplicate_probability
      from public.clinics c
    ) scored_candidates
    where duplicate_probability > 0
    order by duplicate_probability desc, display_name asc
    limit 5
  ) scored;

  return matches;
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
  duplicate_review_count integer := 0;
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
  duplicate_matches jsonb;
  duplicate_probability numeric;
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

    duplicate_matches := public.admin_candidate_duplicate_matches(candidate, candidate_country);
    select coalesce(max((match_item.value ->> 'duplicate_probability')::numeric), 0)
    into duplicate_probability
    from jsonb_array_elements(duplicate_matches) as match_item(value);

    item_title := coalesce(candidate_name, candidate_website, candidate_source, 'Clínica candidata');
    if candidate_city is not null then
      item_title := item_title || ' · ' || candidate_city;
    end if;

    if duplicate_probability >= 0.90 then
      item_title := 'Posible duplicado: ' || item_title;
      item_priority := least(item_priority, 55);
      duplicate_review_count := duplicate_review_count + 1;
    elsif duplicate_probability >= 0.75 then
      item_title := 'Revisar parecido: ' || item_title;
      item_priority := least(item_priority, 80);
      duplicate_review_count := duplicate_review_count + 1;
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
        'candidate_source_url', candidate_source,
        'duplicate_probability', duplicate_probability,
        'duplicate_matches', duplicate_matches
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
      'duplicate_review_items_created', duplicate_review_count,
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
      'duplicate_review_items_created', duplicate_review_count,
      'candidate_count', candidate_count
    )
  );

  return jsonb_build_object(
    'job_id', job_row.id,
    'status', 'completed',
    'mode', 'shadow',
    'candidate_count', candidate_count,
    'review_items_created', review_count,
    'duplicate_review_items_created', duplicate_review_count
  );
end;
$$;

grant execute on function public.normalized_url_host(text) to authenticated, anon;
grant execute on function public.admin_candidate_duplicate_matches(jsonb, text) to authenticated;
grant execute on function public.admin_complete_discovery_job(uuid, jsonb, text, numeric, integer) to authenticated;

commit;
