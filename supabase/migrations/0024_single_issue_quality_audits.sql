begin;

create or replace function public.admin_complete_quality_audit_job(
  p_job_id uuid,
  p_limit integer default 80
)
returns jsonb
language plpgsql
security definer
set search_path = public, auth
as $$
declare
  job_row public.agent_jobs%rowtype;
  clinic_row public.clinics%rowtype;
  issues jsonb;
  issue_item jsonb;
  issue_code text;
  issue_label text;
  issue_field_path text;
  review_count integer := 0;
  scanned_count integer := 0;
  issue_count integer := 0;
  clean_limit integer := least(greatest(coalesce(p_limit, 80), 1), 250);
  actor_email text := lower(coalesce(auth.jwt() ->> 'email', ''));
begin
  if not public.is_admin() then
    raise exception 'not authorized' using errcode = '42501';
  end if;

  select *
  into job_row
  from public.agent_jobs
  where id = p_job_id
  for update;

  if not found then
    raise exception 'job not found' using errcode = 'P0002';
  end if;

  if job_row.job_type <> 'QUALITY_AUDIT' then
    raise exception 'job is not a quality audit job' using errcode = '22023';
  end if;

  if job_row.status not in ('queued', 'running', 'failed') then
    raise exception 'job cannot be completed from status %', job_row.status using errcode = '22023';
  end if;

  update public.agent_jobs
  set
    status = 'running',
    attempts = attempts + case when status <> 'running' then 1 else 0 end,
    locked_by = 'admin-quality-audit',
    started_at = coalesce(started_at, now()),
    error_message = null
  where id = job_row.id;

  for clinic_row in
    select *
    from public.clinics c
    where c.status in ('published', 'preliminary')
      and (
        nullif(btrim(coalesce(job_row.input ->> 'country', '')), '') is null
        or lower(c.country) = lower(job_row.input ->> 'country')
      )
    order by c.status asc, c.updated_at asc
    limit clean_limit
  loop
    scanned_count := scanned_count + 1;
    issues := '[]'::jsonb;

    if nullif(btrim(coalesce(clinic_row.website, clinic_row.current_data ->> 'web', '')), '') is null then
      issues := issues || jsonb_build_object('code', 'missing_website', 'label', 'Falta web oficial');
    end if;

    if length(btrim(coalesce(clinic_row.summary, clinic_row.current_data ->> 'summary', ''))) < 120 then
      issues := issues || jsonb_build_object('code', 'weak_summary', 'label', 'Resumen corto o vacío');
    end if;

    if (case
      when jsonb_typeof(clinic_row.current_data -> 'services') = 'array'
        then jsonb_array_length(clinic_row.current_data -> 'services')
      else 0
    end) = 0 then
      issues := issues || jsonb_build_object('code', 'missing_services', 'label', 'Faltan servicios');
    end if;

    if (case
      when jsonb_typeof(clinic_row.current_data -> 'specialties') = 'array'
        then jsonb_array_length(clinic_row.current_data -> 'specialties')
      else 0
    end) = 0 then
      issues := issues || jsonb_build_object('code', 'missing_specialties', 'label', 'Faltan especialidades');
    end if;

    if (case
      when jsonb_typeof(clinic_row.current_data -> 'unidades') = 'array'
        then jsonb_array_length(clinic_row.current_data -> 'unidades')
      else 0
    end) = 0 then
      issues := issues || jsonb_build_object('code', 'missing_units', 'label', 'Faltan unidades clínicas');
    end if;

    if (case
      when jsonb_typeof(clinic_row.current_data -> 'profesionales') = 'array'
        then jsonb_array_length(clinic_row.current_data -> 'profesionales')
      else 0
    end) = 0 then
      issues := issues || jsonb_build_object('code', 'missing_professionals', 'label', 'Faltan especialistas publicados');
    end if;

    if (case
      when jsonb_typeof(clinic_row.current_data -> 'tech') = 'array'
        then jsonb_array_length(clinic_row.current_data -> 'tech')
      when nullif(btrim(coalesce(clinic_row.current_data ->> 'tech', '')), '') is not null
        then 1
      else 0
    end) = 0 then
      issues := issues || jsonb_build_object('code', 'missing_technology', 'label', 'Falta tecnología destacada');
    end if;

    if nullif(btrim(coalesce(clinic_row.address, clinic_row.current_data ->> 'address', '')), '') is null then
      issues := issues || jsonb_build_object('code', 'missing_address', 'label', 'Falta dirección');
    end if;

    if nullif(btrim(coalesce(clinic_row.current_data ->> 'email', '')), '') is null
      and nullif(btrim(coalesce(clinic_row.current_data ->> 'telefono', '')), '') is null
      and nullif(btrim(coalesce(clinic_row.current_data ->> 'phone_fixed', '')), '') is null
      and nullif(btrim(coalesce(clinic_row.current_data ->> 'phone_mobile', '')), '') is null
      and nullif(btrim(coalesce(clinic_row.current_data ->> 'phone_whatsapp', '')), '') is null then
      issues := issues || jsonb_build_object('code', 'missing_contact', 'label', 'Falta email o teléfono');
    end if;

    issue_count := issue_count + jsonb_array_length(issues);

    for issue_item in select value from jsonb_array_elements(issues)
    loop
      issue_code := coalesce(issue_item ->> 'code', '');
      issue_label := coalesce(issue_item ->> 'label', issue_code, 'Campo pendiente');
      issue_field_path := case issue_code
        when 'missing_website' then 'profile.website'
        when 'weak_summary' then 'profile.summary'
        when 'missing_services' then 'services.list'
        when 'missing_specialties' then 'specialties.list'
        when 'missing_units' then 'units.list'
        when 'missing_professionals' then 'team.professionals'
        when 'missing_technology' then 'technology.highlighted'
        when 'missing_address' then 'location.locations'
        when 'missing_contact' then 'contact.public'
        else null
      end;

      if not exists (
        select 1
        from public.review_queue rq
        where rq.clinic_id = clinic_row.id
          and rq.review_type = 'clinic_quality_audit'
          and rq.status = 'open'
          and coalesce(rq.payload ->> 'quality_context', '') <> 'blocking_claims'
          and (
            rq.payload ->> 'quality_issue_code' = issue_code
            or rq.payload -> 'issues' @> jsonb_build_array(jsonb_build_object('code', issue_code))
          )
      ) then
        insert into public.review_queue (
          job_id,
          clinic_id,
          review_type,
          title,
          field_path,
          priority,
          status,
          payload
        )
        values (
          job_row.id,
          clinic_row.id,
          'clinic_quality_audit',
          'Revisión manual: ' || clinic_row.display_name || ' · ' || issue_label,
          issue_field_path,
          case when clinic_row.status = 'published' then 65 else 85 end,
          'open',
          jsonb_build_object(
            'mode', 'shadow',
            'single_decision', true,
            'quality_issue_code', issue_code,
            'quality_issue_label', issue_label,
            'clinic_id', clinic_row.id,
            'clinic_slug', clinic_row.slug,
            'clinic_name', clinic_row.display_name,
            'clinic_city', clinic_row.city,
            'clinic_country', clinic_row.country,
            'website', coalesce(clinic_row.website, clinic_row.current_data ->> 'web'),
            'status', clinic_row.status,
            'issues', jsonb_build_array(issue_item),
            'job_input', job_row.input
          )
        );

        review_count := review_count + 1;
      end if;
    end loop;
  end loop;

  update public.agent_jobs
  set
    status = 'completed',
    output = jsonb_build_object(
      'mode', 'shadow',
      'one_decision_reviews', true,
      'clinics_scanned', scanned_count,
      'review_items_created', review_count,
      'issues_found', issue_count
    ),
    confidence = 1,
    requires_human = review_count > 0,
    cost_cents = cost_cents,
    locked_by = null,
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
    'quality_audit_completed',
    'admin',
    actor_email,
    'agent_job',
    job_row.id,
    jsonb_build_object(
      'one_decision_reviews', true,
      'clinics_scanned', scanned_count,
      'review_items_created', review_count,
      'issues_found', issue_count
    )
  );

  return jsonb_build_object(
    'job_id', job_row.id,
    'status', 'completed',
    'mode', 'shadow',
    'one_decision_reviews', true,
    'clinics_scanned', scanned_count,
    'review_items_created', review_count,
    'issues_found', issue_count
  );
end;
$$;

grant execute on function public.admin_complete_quality_audit_job(uuid, integer) to authenticated;

commit;
