begin;

alter table public.clinics
  add column if not exists identity_confirmed_at timestamptz,
  add column if not exists identity_confirmed_by uuid,
  add column if not exists identity_confirmation_note text;

create index if not exists clinics_identity_confirmed_idx
on public.clinics(identity_confirmed_at desc)
where identity_confirmed_at is not null;

create table if not exists public.clinic_claim_requests (
  id uuid primary key default gen_random_uuid(),
  request_kind text not null check (request_kind in ('claim_existing', 'recommend_clinic')),
  clinic_id uuid references public.clinics(id) on delete set null,
  submitted_by uuid,
  clinic_name text not null,
  clinic_website text check (clinic_website is null or clinic_website ~* '^https?://'),
  clinic_city text,
  clinic_country text,
  contact_email text not null check (contact_email ~* '^[^@\s]+@[^@\s]+\.[^@\s]+$'),
  requester_name text not null,
  requester_role text,
  message text,
  source_urls jsonb not null default '[]'::jsonb check (jsonb_typeof(source_urls) = 'array'),
  accepted_manual_review boolean not null default false,
  status text not null default 'pending' check (status in ('pending', 'approved', 'rejected', 'needs_more_info')),
  risk_flags jsonb not null default '[]'::jsonb check (jsonb_typeof(risk_flags) = 'array'),
  review_id uuid references public.review_queue(id) on delete set null,
  reviewed_by text,
  reviewed_at timestamptz,
  resolution_note text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

drop trigger if exists clinic_claim_requests_set_updated_at on public.clinic_claim_requests;
create trigger clinic_claim_requests_set_updated_at
before update on public.clinic_claim_requests
for each row execute function public.set_updated_at();

create table if not exists public.clinic_portal_memberships (
  id uuid primary key default gen_random_uuid(),
  clinic_id uuid not null references public.clinics(id) on delete cascade,
  user_id uuid,
  email text not null check (email ~* '^[^@\s]+@[^@\s]+\.[^@\s]+$'),
  representative_name text,
  representative_role text,
  role text not null default 'owner' check (role in ('owner', 'editor', 'viewer')),
  status text not null default 'active' check (status in ('pending', 'active', 'revoked')),
  claim_request_id uuid references public.clinic_claim_requests(id) on delete set null,
  approved_by text,
  approved_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

drop trigger if exists clinic_portal_memberships_set_updated_at on public.clinic_portal_memberships;
create trigger clinic_portal_memberships_set_updated_at
before update on public.clinic_portal_memberships
for each row execute function public.set_updated_at();

create unique index if not exists clinic_portal_membership_active_email_idx
on public.clinic_portal_memberships (clinic_id, lower(email))
where status = 'active';

create index if not exists clinic_portal_memberships_user_idx
on public.clinic_portal_memberships(user_id, status);

create table if not exists public.clinic_profile_change_requests (
  id uuid primary key default gen_random_uuid(),
  clinic_id uuid not null references public.clinics(id) on delete cascade,
  submitted_by uuid,
  submitted_email text not null check (submitted_email ~* '^[^@\s]+@[^@\s]+\.[^@\s]+$'),
  membership_id uuid references public.clinic_portal_memberships(id) on delete set null,
  proposed_fields jsonb not null check (jsonb_typeof(proposed_fields) = 'object'),
  source_urls jsonb not null default '[]'::jsonb check (jsonb_typeof(source_urls) = 'array'),
  message text,
  status text not null default 'pending' check (status in ('pending', 'approved', 'rejected', 'needs_more_info')),
  risk_flags jsonb not null default '[]'::jsonb check (jsonb_typeof(risk_flags) = 'array'),
  review_id uuid references public.review_queue(id) on delete set null,
  reviewed_by text,
  reviewed_at timestamptz,
  resolution_note text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

drop trigger if exists clinic_profile_change_requests_set_updated_at on public.clinic_profile_change_requests;
create trigger clinic_profile_change_requests_set_updated_at
before update on public.clinic_profile_change_requests
for each row execute function public.set_updated_at();

create index if not exists clinic_profile_change_requests_clinic_status_idx
on public.clinic_profile_change_requests(clinic_id, status, created_at desc);

create index if not exists clinic_claim_requests_status_idx
on public.clinic_claim_requests(status, created_at desc);

alter table public.clinic_claim_requests enable row level security;
alter table public.clinic_portal_memberships enable row level security;
alter table public.clinic_profile_change_requests enable row level security;

grant select, insert, update, delete on public.clinic_claim_requests to authenticated;
grant select, insert, update, delete on public.clinic_portal_memberships to authenticated;
grant select, insert, update, delete on public.clinic_profile_change_requests to authenticated;

drop policy if exists "admin full access" on public.clinic_claim_requests;
create policy "admin full access"
on public.clinic_claim_requests
for all to authenticated
using (public.is_admin())
with check (public.is_admin());

drop policy if exists "admin full access" on public.clinic_portal_memberships;
create policy "admin full access"
on public.clinic_portal_memberships
for all to authenticated
using (public.is_admin())
with check (public.is_admin());

drop policy if exists "admin full access" on public.clinic_profile_change_requests;
create policy "admin full access"
on public.clinic_profile_change_requests
for all to authenticated
using (public.is_admin())
with check (public.is_admin());

drop policy if exists "clinic portal users read own claim requests" on public.clinic_claim_requests;
create policy "clinic portal users read own claim requests"
on public.clinic_claim_requests
for select to authenticated
using (
  submitted_by = auth.uid()
  or lower(contact_email) = lower(coalesce(auth.jwt() ->> 'email', ''))
);

drop policy if exists "clinic portal users read own memberships" on public.clinic_portal_memberships;
create policy "clinic portal users read own memberships"
on public.clinic_portal_memberships
for select to authenticated
using (
  user_id = auth.uid()
  or lower(email) = lower(coalesce(auth.jwt() ->> 'email', ''))
);

drop policy if exists "clinic portal users read own change requests" on public.clinic_profile_change_requests;
create policy "clinic portal users read own change requests"
on public.clinic_profile_change_requests
for select to authenticated
using (
  submitted_by = auth.uid()
  or lower(submitted_email) = lower(coalesce(auth.jwt() ->> 'email', ''))
  or exists (
    select 1
    from public.clinic_portal_memberships m
    where m.clinic_id = clinic_profile_change_requests.clinic_id
      and m.status = 'active'
      and (
        m.user_id = auth.uid()
        or lower(m.email) = lower(coalesce(auth.jwt() ->> 'email', ''))
      )
  )
);

create or replace function public.portal_clean_source_urls(p_source_urls text[] default array[]::text[])
returns jsonb
language sql
immutable
as $$
  select coalesce(jsonb_agg(url order by url), '[]'::jsonb)
  from (
    select distinct btrim(raw_url) as url
    from unnest(coalesce(p_source_urls, array[]::text[])) as input(raw_url)
    where btrim(raw_url) ~* '^https?://'
  ) clean;
$$;

create or replace function public.clinic_portal_risk_flags(
  p_text text default '',
  p_fields jsonb default '{}'::jsonb
)
returns jsonb
language plpgsql
stable
as $$
declare
  haystack text := lower(coalesce(p_text, '') || ' ' || coalesce(p_fields::text, ''));
  flags jsonb := '[]'::jsonb;
begin
  if haystack ~ '(top[[:space:]]*[0-9]|ranking|mejor clinica|mejor clínica|premium|destacad)' then
    flags := flags || jsonb_build_array(jsonb_build_object(
      'code', 'promotional_or_ranking_language',
      'label', 'Lenguaje promocional o comparativo',
      'risk', 'high'
    ));
  end if;

  if haystack ~ '(cura|curar|revierte|revertir|rejuvenece|alarga la vida|garantiza|garantizado)' then
    flags := flags || jsonb_build_array(jsonb_build_object(
      'code', 'medical_claim_language',
      'label', 'Claim medico sensible',
      'risk', 'high'
    ));
  end if;

  if haystack ~ '(paciente|resena|reseña|opinion|opinión|testimonio|antes/despues|antes/después|caso clinico|caso clínico)' then
    flags := flags || jsonb_build_array(jsonb_build_object(
      'code', 'patient_story_language',
      'label', 'Posible contenido de pacientes',
      'risk', 'high'
    ));
  end if;

  if p_fields ? 'pricing_url' or p_fields ? 'public_pricing' then
    flags := flags || jsonb_build_array(jsonb_build_object(
      'code', 'pricing_field',
      'label', 'Dato de precios a revisar',
      'risk', 'high'
    ));
  end if;

  return flags;
end;
$$;

create or replace function public.portal_filter_profile_fields(p_fields jsonb)
returns jsonb
language plpgsql
immutable
as $$
declare
  clean jsonb := '{}'::jsonb;
  supported_keys constant text[] := array[
    'display_name',
    'website',
    'country',
    'city',
    'region',
    'address',
    'locations',
    'maps_url',
    'google_maps_url',
    'google_reviews_url',
    'summary',
    'services',
    'specialties',
    'unidades',
    'profesionales',
    'tech',
    'email',
    'telefono',
    'instagram'
  ];
  field_key text;
  field_value jsonb;
begin
  if p_fields is null or jsonb_typeof(p_fields) <> 'object' then
    return clean;
  end if;

  foreach field_key in array supported_keys
  loop
    if not (p_fields ? field_key) then
      continue;
    end if;

    field_value := p_fields -> field_key;
    if field_value is null or field_value = 'null'::jsonb then
      continue;
    end if;
    if jsonb_typeof(field_value) = 'string' and btrim(field_value #>> '{}') = '' then
      continue;
    end if;
    if jsonb_typeof(field_value) = 'array' and jsonb_array_length(field_value) = 0 then
      continue;
    end if;

    clean := jsonb_set(clean, array[field_key], field_value, true);
  end loop;

  return clean;
end;
$$;

create or replace function public.portal_attach_email_memberships()
returns integer
language plpgsql
security definer
set search_path = public, auth
as $$
declare
  actor_uid uuid := auth.uid();
  actor_email text := lower(coalesce(auth.jwt() ->> 'email', ''));
  attached_count integer := 0;
begin
  if actor_uid is null or actor_email = '' then
    raise exception 'authentication required' using errcode = '42501';
  end if;

  update public.clinic_portal_memberships
  set user_id = actor_uid
  where user_id is null
    and status = 'active'
    and lower(email) = actor_email;

  get diagnostics attached_count = row_count;
  return attached_count;
end;
$$;

create or replace function public.portal_submit_clinic_claim_request(
  p_request_kind text,
  p_clinic_id uuid default null,
  p_clinic_slug text default null,
  p_clinic_name text default null,
  p_clinic_website text default null,
  p_clinic_city text default null,
  p_clinic_country text default null,
  p_contact_email text default null,
  p_requester_name text default null,
  p_requester_role text default null,
  p_message text default null,
  p_source_urls text[] default array[]::text[],
  p_accept_manual_review boolean default false
)
returns jsonb
language plpgsql
security definer
set search_path = public, auth
as $$
declare
  clean_kind text := nullif(btrim(coalesce(p_request_kind, '')), '');
  clean_email text := lower(nullif(btrim(coalesce(p_contact_email, auth.jwt() ->> 'email', '')), ''));
  clean_requester text := nullif(btrim(coalesce(p_requester_name, '')), '');
  clean_role text := nullif(btrim(coalesce(p_requester_role, '')), '');
  clean_message text := nullif(btrim(coalesce(p_message, '')), '');
  clean_name text := nullif(btrim(coalesce(p_clinic_name, '')), '');
  clean_website text := nullif(btrim(coalesce(p_clinic_website, '')), '');
  clean_city text := nullif(btrim(coalesce(p_clinic_city, '')), '');
  clean_country text := nullif(btrim(coalesce(p_clinic_country, 'España')), '');
  actor_uid uuid := auth.uid();
  actor_email text := lower(coalesce(auth.jwt() ->> 'email', ''));
  target_clinic public.clinics%rowtype;
  request_row public.clinic_claim_requests%rowtype;
  created_review_id uuid;
  risk_flags jsonb;
  clean_source_urls jsonb := public.portal_clean_source_urls(p_source_urls);
  source_url text;
  review_title text;
begin
  if clean_kind not in ('claim_existing', 'recommend_clinic') then
    raise exception 'invalid request kind' using errcode = '22023';
  end if;

  if not coalesce(p_accept_manual_review, false) then
    raise exception 'manual review acceptance is required' using errcode = '22023';
  end if;

  if p_clinic_id is not null then
    select * into target_clinic from public.clinics where id = p_clinic_id;
  elsif nullif(btrim(coalesce(p_clinic_slug, '')), '') is not null then
    select * into target_clinic from public.clinics where slug = btrim(p_clinic_slug);
  end if;

  if clean_kind = 'claim_existing' and target_clinic.id is null then
    raise exception 'clinic not found for claim request' using errcode = 'P0002';
  end if;

  if target_clinic.id is not null then
    clean_name := coalesce(clean_name, target_clinic.display_name);
    clean_website := coalesce(clean_website, target_clinic.website);
    clean_city := coalesce(clean_city, target_clinic.city);
    clean_country := coalesce(clean_country, target_clinic.country);
  end if;

  if clean_name is null then
    raise exception 'clinic name is required' using errcode = '22023';
  end if;
  if clean_email is null or clean_email !~* '^[^@\s]+@[^@\s]+\.[^@\s]+$' then
    raise exception 'valid contact email is required' using errcode = '22023';
  end if;
  if clean_requester is null then
    raise exception 'requester name is required' using errcode = '22023';
  end if;
  if clean_website is not null and clean_website !~* '^https?://' then
    raise exception 'clinic website must start with http or https' using errcode = '22023';
  end if;
  if clean_kind = 'recommend_clinic' and (clean_website is null or clean_city is null) then
    raise exception 'recommended clinics need website and city' using errcode = '22023';
  end if;

  source_url := coalesce(clean_source_urls ->> 0, clean_website);
  risk_flags := public.clinic_portal_risk_flags(
    concat_ws(' ', clean_message, clean_name, clean_website, clean_city, clean_country),
    '{}'::jsonb
  );

  insert into public.clinic_claim_requests (
    request_kind,
    clinic_id,
    submitted_by,
    clinic_name,
    clinic_website,
    clinic_city,
    clinic_country,
    contact_email,
    requester_name,
    requester_role,
    message,
    source_urls,
    accepted_manual_review,
    risk_flags
  )
  values (
    clean_kind,
    target_clinic.id,
    actor_uid,
    clean_name,
    clean_website,
    clean_city,
    clean_country,
    clean_email,
    clean_requester,
    clean_role,
    clean_message,
    clean_source_urls,
    true,
    risk_flags
  )
  returning * into request_row;

  if clean_kind = 'recommend_clinic' then
    review_title := 'Recomendar clinica: ' || clean_name;
    insert into public.review_queue (
      review_type,
      title,
      priority,
      status,
      payload
    )
    values (
      'candidate_clinic',
      review_title,
      88,
      'open',
      jsonb_strip_nulls(jsonb_build_object(
        'source', 'clinic_portal',
        'portal_claim_request_id', request_row.id,
        'request_kind', request_row.request_kind,
        'requester_email', clean_email,
        'requester_name', clean_requester,
        'requester_role', clean_role,
        'message', clean_message,
        'source_urls', clean_source_urls,
        'risk_flags', risk_flags,
        'candidate', jsonb_strip_nulls(jsonb_build_object(
          'name', clean_name,
          'website', clean_website,
          'city', clean_city,
          'country', clean_country,
          'source_url', source_url,
          'discovery_confidence', 0.55
        ))
      ))
    )
    returning id into created_review_id;
  else
    review_title := 'Reclamar ficha: ' || clean_name;
    insert into public.review_queue (
      clinic_id,
      review_type,
      title,
      priority,
      status,
      payload
    )
    values (
      target_clinic.id,
      'clinic_claim_request',
      review_title,
      96,
      'open',
      jsonb_strip_nulls(jsonb_build_object(
        'source', 'clinic_portal',
        'portal_claim_request_id', request_row.id,
        'request_kind', request_row.request_kind,
        'clinic_id', target_clinic.id,
        'clinic_name', clean_name,
        'clinic_city', clean_city,
        'clinic_country', clean_country,
        'website', clean_website,
        'requester_email', clean_email,
        'requester_name', clean_requester,
        'requester_role', clean_role,
        'message', clean_message,
        'source_urls', clean_source_urls,
        'risk_flags', risk_flags
      ))
    )
    returning id into created_review_id;
  end if;

  update public.clinic_claim_requests
  set review_id = created_review_id
  where id = request_row.id
  returning * into request_row;

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
    'clinic_portal_claim_submitted',
    case when actor_uid is null then 'public' else 'clinic_user' end,
    coalesce(nullif(actor_email, ''), clean_email),
    'clinic_claim_request',
    request_row.id,
    target_clinic.id,
    jsonb_build_object(
      'request_kind', clean_kind,
      'review_id', created_review_id,
      'risk_flags', risk_flags
    )
  );

  return jsonb_build_object(
    'request_id', request_row.id,
    'review_id', created_review_id,
    'status', request_row.status,
    'message', 'Solicitud recibida. Queda pendiente de revision manual.'
  );
end;
$$;

create or replace function public.portal_submit_profile_change_request(
  p_clinic_id uuid,
  p_proposed_fields jsonb,
  p_source_urls text[] default array[]::text[],
  p_message text default null
)
returns jsonb
language plpgsql
security definer
set search_path = public, auth
as $$
declare
  actor_uid uuid := auth.uid();
  actor_email text := lower(coalesce(auth.jwt() ->> 'email', ''));
  membership_row public.clinic_portal_memberships%rowtype;
  clinic_row public.clinics%rowtype;
  clean_fields jsonb := public.portal_filter_profile_fields(p_proposed_fields);
  clean_message text := nullif(btrim(coalesce(p_message, '')), '');
  clean_source_urls jsonb := public.portal_clean_source_urls(p_source_urls);
  risk_flags jsonb;
  request_row public.clinic_profile_change_requests%rowtype;
  created_review_id uuid;
  field_keys text[];
begin
  if actor_uid is null or actor_email = '' then
    raise exception 'authentication required' using errcode = '42501';
  end if;

  perform public.portal_attach_email_memberships();

  select *
  into clinic_row
  from public.clinics
  where id = p_clinic_id;

  if not found then
    raise exception 'clinic not found' using errcode = 'P0002';
  end if;

  select *
  into membership_row
  from public.clinic_portal_memberships m
  where m.clinic_id = p_clinic_id
    and m.status = 'active'
    and (
      m.user_id = actor_uid
      or lower(m.email) = actor_email
    )
  order by m.approved_at desc nulls last, m.created_at desc
  limit 1;

  if not found then
    raise exception 'clinic access is not approved' using errcode = '42501';
  end if;

  if clean_fields = '{}'::jsonb then
    raise exception 'at least one supported field is required' using errcode = '22023';
  end if;

  risk_flags := public.clinic_portal_risk_flags(clean_message, clean_fields);
  select coalesce(array_agg(key order by key), array[]::text[])
  into field_keys
  from jsonb_object_keys(clean_fields) as fields(key);

  insert into public.clinic_profile_change_requests (
    clinic_id,
    submitted_by,
    submitted_email,
    membership_id,
    proposed_fields,
    source_urls,
    message,
    risk_flags
  )
  values (
    clinic_row.id,
    actor_uid,
    actor_email,
    membership_row.id,
    clean_fields,
    clean_source_urls,
    clean_message,
    risk_flags
  )
  returning * into request_row;

  insert into public.review_queue (
    clinic_id,
    review_type,
    title,
    priority,
    status,
    payload
  )
  values (
    clinic_row.id,
    'clinic_profile_enrichment',
    'Cambio solicitado por clinica: ' || clinic_row.display_name,
    case when jsonb_array_length(risk_flags) > 0 then 94 else 82 end,
    'open',
    jsonb_strip_nulls(jsonb_build_object(
      'source', 'clinic_portal',
      'portal_change_request_id', request_row.id,
      'clinic_id', clinic_row.id,
      'clinic_name', clinic_row.display_name,
      'clinic_city', clinic_row.city,
      'clinic_country', clinic_row.country,
      'website', clinic_row.website,
      'requester_email', actor_email,
      'requester_name', membership_row.representative_name,
      'requester_role', membership_row.representative_role,
      'message', clean_message,
      'source_urls', clean_source_urls,
      'risk_flags', risk_flags,
      'proposed_fields', clean_fields
    ))
  )
  returning id into created_review_id;

  update public.clinic_profile_change_requests
  set review_id = created_review_id
  where id = request_row.id
  returning * into request_row;

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
    'clinic_portal_change_submitted',
    'clinic_user',
    actor_email,
    'clinic_profile_change_request',
    request_row.id,
    clinic_row.id,
    jsonb_build_object(
      'review_id', created_review_id,
      'fields', to_jsonb(field_keys),
      'risk_flags', risk_flags
    )
  );

  return jsonb_build_object(
    'request_id', request_row.id,
    'review_id', created_review_id,
    'status', request_row.status,
    'message', 'Propuesta recibida. Queda pendiente de validacion por Vitalarga.'
  );
end;
$$;

create or replace function public.portal_my_clinic_workspace()
returns jsonb
language plpgsql
security definer
set search_path = public, auth
as $$
declare
  actor_uid uuid := auth.uid();
  actor_email text := lower(coalesce(auth.jwt() ->> 'email', ''));
begin
  if actor_uid is null or actor_email = '' then
    raise exception 'authentication required' using errcode = '42501';
  end if;

  perform public.portal_attach_email_memberships();

  return jsonb_build_object(
    'memberships', (
      select coalesce(jsonb_agg(
        jsonb_build_object(
          'id', m.id,
          'status', m.status,
          'role', m.role,
          'approved_at', m.approved_at,
          'clinic', jsonb_build_object(
            'id', c.id,
            'slug', c.slug,
            'display_name', c.display_name,
            'website', c.website,
            'country', c.country,
            'city', c.city,
            'region', c.region,
            'address', c.address,
            'summary', c.summary,
            'current_data', c.current_data,
            'identity_confirmed_at', c.identity_confirmed_at
          )
        )
        order by c.display_name
      ), '[]'::jsonb)
      from public.clinic_portal_memberships m
      join public.clinics c on c.id = m.clinic_id
      where m.status = 'active'
        and (
          m.user_id = actor_uid
          or lower(m.email) = actor_email
        )
    ),
    'claim_requests', (
      select coalesce(jsonb_agg(
        jsonb_build_object(
          'id', r.id,
          'request_kind', r.request_kind,
          'clinic_id', r.clinic_id,
          'clinic_name', r.clinic_name,
          'clinic_city', r.clinic_city,
          'clinic_country', r.clinic_country,
          'status', r.status,
          'created_at', r.created_at,
          'reviewed_at', r.reviewed_at,
          'resolution_note', r.resolution_note
        )
        order by r.created_at desc
      ), '[]'::jsonb)
      from public.clinic_claim_requests r
      where r.submitted_by = actor_uid
        or lower(r.contact_email) = actor_email
    ),
    'change_requests', (
      select coalesce(jsonb_agg(
        jsonb_build_object(
          'id', cr.id,
          'clinic_id', cr.clinic_id,
          'clinic_name', c.display_name,
          'status', cr.status,
          'proposed_fields', cr.proposed_fields,
          'created_at', cr.created_at,
          'reviewed_at', cr.reviewed_at,
          'resolution_note', cr.resolution_note
        )
        order by cr.created_at desc
      ), '[]'::jsonb)
      from public.clinic_profile_change_requests cr
      join public.clinics c on c.id = cr.clinic_id
      where cr.submitted_by = actor_uid
        or lower(cr.submitted_email) = actor_email
        or exists (
          select 1
          from public.clinic_portal_memberships m
          where m.clinic_id = cr.clinic_id
            and m.status = 'active'
            and (
              m.user_id = actor_uid
              or lower(m.email) = actor_email
            )
        )
    )
  );
end;
$$;

create or replace function public.admin_resolve_clinic_claim_request(
  p_claim_request_id uuid,
  p_status text,
  p_note text default null
)
returns jsonb
language plpgsql
security definer
set search_path = public, auth
as $$
declare
  actor_email text := lower(coalesce(auth.jwt() ->> 'email', ''));
  clean_status text := nullif(btrim(coalesce(p_status, '')), '');
  clean_note text := nullif(btrim(coalesce(p_note, '')), '');
  request_row public.clinic_claim_requests%rowtype;
  updated_request public.clinic_claim_requests%rowtype;
  clinic_row public.clinics%rowtype;
  event_id uuid;
  next_version integer;
  member_user_id uuid;
begin
  if not public.is_admin() then
    raise exception 'not authorized' using errcode = '42501';
  end if;

  if clean_status not in ('approved', 'rejected', 'needs_more_info') then
    raise exception 'invalid claim request status' using errcode = '22023';
  end if;

  select *
  into request_row
  from public.clinic_claim_requests
  where id = p_claim_request_id
  for update;

  if not found then
    raise exception 'claim request not found' using errcode = 'P0002';
  end if;

  if clean_status = 'approved' and request_row.request_kind = 'claim_existing' and request_row.clinic_id is not null then
    select u.id
    into member_user_id
    from auth.users u
    where lower(u.email) = lower(request_row.contact_email)
    order by u.created_at desc
    limit 1;

    insert into public.clinic_portal_memberships (
      clinic_id,
      user_id,
      email,
      representative_name,
      representative_role,
      role,
      status,
      claim_request_id,
      approved_by,
      approved_at
    )
    values (
      request_row.clinic_id,
      coalesce(request_row.submitted_by, member_user_id),
      request_row.contact_email,
      request_row.requester_name,
      request_row.requester_role,
      'owner',
      'active',
      request_row.id,
      actor_email,
      now()
    )
    on conflict (clinic_id, lower(email)) where status = 'active'
    do update set
      user_id = coalesce(excluded.user_id, public.clinic_portal_memberships.user_id),
      representative_name = excluded.representative_name,
      representative_role = excluded.representative_role,
      claim_request_id = excluded.claim_request_id,
      approved_by = excluded.approved_by,
      approved_at = excluded.approved_at,
      updated_at = now();

    update public.clinics
    set
      claimed_by = coalesce(request_row.submitted_by, member_user_id, claimed_by),
      claimed_at = coalesce(claimed_at, now()),
      identity_confirmed_at = now(),
      identity_confirmed_by = coalesce(request_row.submitted_by, member_user_id),
      identity_confirmation_note = clean_note,
      last_verified_at = now()
    where id = request_row.clinic_id
    returning * into clinic_row;

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
      'clinic_identity_confirmed',
      'admin',
      actor_email,
      'clinic',
      clinic_row.id,
      clinic_row.id,
      jsonb_build_object(
        'claim_request_id', request_row.id,
        'contact_email', request_row.contact_email,
        'note', clean_note,
        'label', 'Datos confirmados por el centro'
      )
    )
    returning id into event_id;

    select coalesce(max(version_number), 0) + 1
    into next_version
    from public.entity_versions
    where entity_type = 'clinic'
      and entity_id = clinic_row.id;

    insert into public.entity_versions (
      entity_type,
      entity_id,
      version_number,
      data,
      source_event_id
    )
    values (
      'clinic',
      clinic_row.id,
      next_version,
      to_jsonb(clinic_row),
      event_id
    );
  end if;

  update public.clinic_claim_requests
  set
    status = clean_status,
    reviewed_by = actor_email,
    reviewed_at = now(),
    resolution_note = clean_note
  where id = request_row.id
  returning * into updated_request;

  if request_row.review_id is not null then
    update public.review_queue
    set
      status = case when clean_status = 'rejected' then 'dismissed' else 'resolved' end,
      resolution = jsonb_strip_nulls(jsonb_build_object(
        'action', clean_status,
        'claim_request_id', request_row.id,
        'note', clean_note,
        'actor_email', actor_email
      )),
      resolved_by = actor_email,
      resolved_at = now()
    where id = request_row.review_id;
  end if;

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
    'clinic_claim_request_resolved',
    'admin',
    actor_email,
    'clinic_claim_request',
    request_row.id,
    request_row.clinic_id,
    jsonb_build_object('status', clean_status, 'note', clean_note)
  );

  return jsonb_build_object(
    'request_id', updated_request.id,
    'status', updated_request.status,
    'clinic_id', updated_request.clinic_id
  );
end;
$$;

create or replace function public.admin_resolve_clinic_profile_change_request(
  p_change_request_id uuid,
  p_status text,
  p_note text default null
)
returns jsonb
language plpgsql
security definer
set search_path = public, auth
as $$
declare
  actor_email text := lower(coalesce(auth.jwt() ->> 'email', ''));
  clean_status text := nullif(btrim(coalesce(p_status, '')), '');
  clean_note text := nullif(btrim(coalesce(p_note, '')), '');
  request_row public.clinic_profile_change_requests%rowtype;
  updated_request public.clinic_profile_change_requests%rowtype;
begin
  if not public.is_admin() then
    raise exception 'not authorized' using errcode = '42501';
  end if;

  if clean_status not in ('approved', 'rejected', 'needs_more_info') then
    raise exception 'invalid change request status' using errcode = '22023';
  end if;

  select *
  into request_row
  from public.clinic_profile_change_requests
  where id = p_change_request_id
  for update;

  if not found then
    raise exception 'change request not found' using errcode = 'P0002';
  end if;

  update public.clinic_profile_change_requests
  set
    status = clean_status,
    reviewed_by = actor_email,
    reviewed_at = now(),
    resolution_note = clean_note
  where id = request_row.id
  returning * into updated_request;

  if request_row.review_id is not null then
    update public.review_queue
    set
      status = case when clean_status = 'rejected' then 'dismissed' else 'resolved' end,
      resolution = jsonb_strip_nulls(jsonb_build_object(
        'action', clean_status,
        'change_request_id', request_row.id,
        'note', clean_note,
        'actor_email', actor_email
      )),
      resolved_by = actor_email,
      resolved_at = now()
    where id = request_row.review_id;
  end if;

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
    'clinic_portal_change_resolved',
    'admin',
    actor_email,
    'clinic_profile_change_request',
    request_row.id,
    request_row.clinic_id,
    jsonb_build_object('status', clean_status, 'note', clean_note)
  );

  return jsonb_build_object(
    'request_id', updated_request.id,
    'status', updated_request.status,
    'clinic_id', updated_request.clinic_id
  );
end;
$$;

create or replace function public.public_clinics_for_site()
returns jsonb
language sql
stable
security definer
set search_path = public
as $$
  select coalesce(
    jsonb_agg(
      jsonb_strip_nulls(
        jsonb_build_object(
          'id', c.id,
          'slug', c.slug,
          'name', c.display_name,
          'city', c.city,
          'country', c.country,
          'region', c.region,
          'address', c.address,
          'web', c.website,
          'summary', c.summary,
          'services', case
            when jsonb_typeof(c.current_data -> 'services') = 'array'
              then c.current_data -> 'services'
            else '[]'::jsonb
          end,
          'specialties', case
            when jsonb_typeof(c.current_data -> 'specialties') = 'array'
              then c.current_data -> 'specialties'
            else '[]'::jsonb
          end,
          'cities_extra', case
            when jsonb_typeof(c.current_data -> 'cities_extra') = 'array'
              then c.current_data -> 'cities_extra'
            else null
          end,
          'locations', case
            when jsonb_typeof(c.current_data -> 'locations') = 'array'
              then c.current_data -> 'locations'
            else null
          end,
          'maps_url', nullif(c.current_data ->> 'maps_url', ''),
          'google_maps_url', nullif(c.current_data ->> 'google_maps_url', ''),
          'google_reviews_url', nullif(c.current_data ->> 'google_reviews_url', ''),
          'reviews_url', nullif(c.current_data ->> 'reviews_url', ''),
          'profesionales', case
            when jsonb_typeof(c.current_data -> 'profesionales') = 'array'
              then c.current_data -> 'profesionales'
            else null
          end,
          'unidades', case
            when jsonb_typeof(c.current_data -> 'unidades') = 'array'
              then c.current_data -> 'unidades'
            else null
          end,
          'years_in_practice', nullif(c.current_data ->> 'years_in_practice', ''),
          'specialists_count', c.current_data -> 'specialists_count',
          'team_credentialing_visible', nullif(c.current_data ->> 'team_credentialing_visible', ''),
          'public_pricing', nullif(c.current_data ->> 'public_pricing', ''),
          'pricing_url', nullif(c.current_data ->> 'pricing_url', ''),
          'identity_confirmed_at', c.identity_confirmed_at,
          'tech', nullif(c.current_data ->> 'tech', ''),
          'email', nullif(c.current_data ->> 'email', ''),
          'telefono', nullif(c.current_data ->> 'telefono', ''),
          'instagram', nullif(c.current_data ->> 'instagram', ''),
          'status', case c.status
            when 'published' then 'publicada'
            when 'preliminary' then 'preliminar'
            else c.status
          end
        )
      )
      order by c.display_name
    ),
    '[]'::jsonb
  )
  from public.clinics c
  where c.status in ('published', 'preliminary');
$$;

create or replace function public.admin_dashboard_summary()
returns jsonb
language plpgsql
stable
security definer
set search_path = public, auth
as $$
declare
  agents_enabled boolean;
  auto_publish_enabled boolean;
  shadow_review_target integer;
begin
  if not public.is_admin() then
    raise exception 'not authorized' using errcode = '42501';
  end if;

  select coalesce(
    (
      select lower(value) in ('true', '1', 'yes', 'on')
      from private.app_settings
      where key = 'vitalarga_agents_enabled'
    ),
    true
  )
  into agents_enabled;

  select coalesce(
    (
      select lower(value) in ('true', '1', 'yes', 'on')
      from private.app_settings
      where key = 'vitalarga_auto_publish_enabled'
    ),
    false
  )
  into auto_publish_enabled;

  select coalesce(
    (
      select nullif(regexp_replace(value, '[^0-9]', '', 'g'), '')::integer
      from private.app_settings
      where key = 'vitalarga_shadow_review_target'
    ),
    200
  )
  into shadow_review_target;

  return jsonb_build_object(
    'clinics', (
      select jsonb_build_object(
        'total', count(*),
        'published', count(*) filter (where status = 'published'),
        'preliminary', count(*) filter (where status = 'preliminary'),
        'review', count(*) filter (where status = 'review'),
        'draft', count(*) filter (where status = 'draft'),
        'discovered', count(*) filter (where status = 'discovered'),
        'identity_confirmed', count(*) filter (where identity_confirmed_at is not null)
      )
      from public.clinics
    ),
    'reviews', (
      select jsonb_build_object(
        'open', count(*) filter (where status = 'open'),
        'resolved', count(*) filter (where status = 'resolved'),
        'candidate_open', count(*) filter (where status = 'open' and review_type = 'candidate_clinic'),
        'quality_open', count(*) filter (where status = 'open' and review_type = 'clinic_quality_audit'),
        'clinic_claim_open', count(*) filter (where status = 'open' and review_type = 'clinic_claim_request')
      )
      from public.review_queue
    ),
    'jobs', (
      select jsonb_build_object(
        'queued', count(*) filter (where status = 'queued'),
        'running', count(*) filter (where status = 'running'),
        'failed', count(*) filter (where status = 'failed'),
        'dead_letter', count(*) filter (where status = 'dead_letter'),
        'completed', count(*) filter (where status = 'completed')
      )
      from public.agent_jobs
    ),
    'evidence', (
      select jsonb_build_object(
        'sources', (select count(*) from public.source_records),
        'claims', (select count(*) from public.field_claims),
        'snapshots', (select count(*) from public.source_snapshots)
      )
    ),
    'portal', (
      select jsonb_build_object(
        'claim_requests_pending', (select count(*) from public.clinic_claim_requests where status = 'pending'),
        'change_requests_pending', (select count(*) from public.clinic_profile_change_requests where status = 'pending'),
        'active_memberships', (select count(*) from public.clinic_portal_memberships where status = 'active'),
        'identity_confirmed', (select count(*) from public.clinics where identity_confirmed_at is not null)
      )
    ),
    'automation', (
      select jsonb_build_object(
        'agents_enabled', agents_enabled,
        'auto_publish_enabled', auto_publish_enabled,
        'shadow_mode_active', not auto_publish_enabled,
        'shadow_review_target', shadow_review_target,
        'candidate_reviews_completed', (
          select count(*)
          from public.review_queue
          where review_type = 'candidate_clinic'
            and status in ('resolved', 'dismissed')
        )
      )
    ),
    'generated_at', now()
  );
end;
$$;

grant execute on function public.portal_clean_source_urls(text[]) to anon, authenticated;
grant execute on function public.clinic_portal_risk_flags(text, jsonb) to anon, authenticated;
grant execute on function public.portal_filter_profile_fields(jsonb) to authenticated;
grant execute on function public.portal_attach_email_memberships() to authenticated;
grant execute on function public.portal_submit_clinic_claim_request(
  text,
  uuid,
  text,
  text,
  text,
  text,
  text,
  text,
  text,
  text,
  text,
  text[],
  boolean
) to anon, authenticated;
grant execute on function public.portal_submit_profile_change_request(uuid, jsonb, text[], text) to authenticated;
grant execute on function public.portal_my_clinic_workspace() to authenticated;
grant execute on function public.admin_resolve_clinic_claim_request(uuid, text, text) to authenticated;
grant execute on function public.admin_resolve_clinic_profile_change_request(uuid, text, text) to authenticated;
grant execute on function public.public_clinics_for_site() to anon, authenticated;
grant execute on function public.admin_dashboard_summary() to authenticated;

commit;
