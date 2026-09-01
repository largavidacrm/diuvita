begin;

create or replace function public.public_recommend_clinic(
  p_clinic_name text,
  p_website text default null,
  p_city text default null,
  p_country text default 'España',
  p_requested_info text default 'new_clinic',
  p_note text default null,
  p_honeypot text default null
)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  clean_name text := nullif(left(regexp_replace(btrim(coalesce(p_clinic_name, '')), '[[:cntrl:]]+', ' ', 'g'), 160), '');
  clean_website text := nullif(left(regexp_replace(btrim(coalesce(p_website, '')), '[[:cntrl:][:space:]]+', '', 'g'), 240), '');
  clean_city text := nullif(left(regexp_replace(btrim(coalesce(p_city, '')), '[[:cntrl:]]+', ' ', 'g'), 120), '');
  clean_country text := coalesce(nullif(left(regexp_replace(btrim(coalesce(p_country, '')), '[[:cntrl:]]+', ' ', 'g'), 80), ''), 'España');
  clean_requested text := lower(nullif(left(regexp_replace(btrim(coalesce(p_requested_info, '')), '[[:cntrl:][:space:]]+', '', 'g'), 40), ''));
  clean_note text := nullif(left(regexp_replace(btrim(coalesce(p_note, '')), '[[:cntrl:]]+', ' ', 'g'), 500), '');
  clean_honeypot text := nullif(btrim(coalesce(p_honeypot, '')), '');
  requested_label text;
  query_text text;
  inserted_job public.agent_jobs%rowtype;
begin
  if clean_honeypot is not null then
    return jsonb_build_object('ok', true, 'queued', false);
  end if;

  if clean_name is null or char_length(clean_name) < 2 then
    raise exception 'clinic name is required' using errcode = '22023';
  end if;

  if clean_website is not null and clean_website !~* '^https?://' then
    clean_website := 'https://' || clean_website;
  end if;

  if clean_website is not null and clean_website !~* '^https?://[a-z0-9.-]+(:[0-9]+)?(/.*)?$' then
    raise exception 'official website must be an http or https URL' using errcode = '22023';
  end if;

  if clean_website is null and clean_city is null then
    raise exception 'website or city is required' using errcode = '22023';
  end if;

  if clean_requested is null or clean_requested not in ('new_clinic', 'specialists', 'contact', 'locations', 'services', 'other') then
    clean_requested := 'new_clinic';
  end if;

  requested_label := case clean_requested
    when 'specialists' then 'Especialistas publicados'
    when 'contact' then 'Contacto público'
    when 'locations' then 'Sedes y acceso'
    when 'services' then 'Servicios'
    when 'other' then 'Otro dato claro'
    else 'Añadir clínica nueva'
  end;

  query_text := concat_ws(' ', clean_name, clean_website, clean_city, clean_country, requested_label);

  insert into public.agent_jobs (
    job_type,
    status,
    priority,
    entity_type,
    input,
    model_tier,
    requires_human
  )
  values (
    'DISCOVER_CLINIC',
    'queued',
    120,
    'clinic',
    jsonb_build_object(
      'mode', 'public_recommendation',
      'source', 'public_site_recommend_clinic',
      'clinic_name', clean_name,
      'website', clean_website,
      'web', clean_website,
      'city', clean_city,
      'country', clean_country,
      'requested_info', clean_requested,
      'requested_info_label', requested_label,
      'note', clean_note,
      'query', query_text,
      'max_results', 8,
      'requires_review', true,
      'allowed_output', 'review_queue_proposal_only',
      'instruction', 'Public visitor recommendation. Validate against official sources and create review proposals only. Do not publish or edit clinic profiles automatically.'
    ),
    'cheap',
    false
  )
  returning * into inserted_job;

  insert into public.change_events (
    event_name,
    actor_type,
    entity_type,
    entity_id,
    payload
  )
  values (
    'public_clinic_recommendation_received',
    'public',
    'agent_job',
    inserted_job.id,
    jsonb_build_object(
      'job_type', inserted_job.job_type,
      'clinic_name', clean_name,
      'has_website', clean_website is not null,
      'city', clean_city,
      'country', clean_country,
      'requested_info', clean_requested
    )
  );

  return jsonb_build_object(
    'ok', true,
    'queued', true,
    'job_id', inserted_job.id,
    'status', inserted_job.status
  );
end;
$$;

grant usage on schema public to anon, authenticated;
grant execute on function public.public_recommend_clinic(text, text, text, text, text, text, text) to anon, authenticated;

commit;
