begin;

create extension if not exists pgcrypto;

do $$
begin
  if exists (select 1 from pg_available_extensions where name = 'vector') then
    execute 'create extension if not exists vector';
  end if;
end;
$$;

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create table public.clinics (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique check (slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'),
  canonical_name text not null,
  display_name text not null,
  website text check (website is null or website ~* '^https?://'),
  country text not null,
  city text not null,
  region text,
  address text,
  status text not null default 'draft' check (
    status in ('draft', 'discovered', 'extracted', 'verified', 'review', 'published', 'preliminary', 'archived')
  ),
  summary text,
  current_data jsonb not null default '{}'::jsonb,
  profile_confidence numeric(5,4) not null default 0 check (profile_confidence >= 0 and profile_confidence <= 1),
  verification_status text not null default 'unverified',
  claimed_by uuid,
  claimed_at timestamptz,
  last_verified_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create trigger clinics_set_updated_at
before update on public.clinics
for each row execute function public.set_updated_at();

create table public.professionals (
  id uuid primary key default gen_random_uuid(),
  slug text unique check (slug is null or slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'),
  full_name text not null,
  specialty text,
  credentials text,
  profile_url text check (profile_url is null or profile_url ~* '^https?://'),
  current_data jsonb not null default '{}'::jsonb,
  confidence numeric(5,4) not null default 0 check (confidence >= 0 and confidence <= 1),
  verification_status text not null default 'unverified',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create trigger professionals_set_updated_at
before update on public.professionals
for each row execute function public.set_updated_at();

create table public.source_records (
  id uuid primary key default gen_random_uuid(),
  clinic_id uuid references public.clinics(id) on delete set null,
  entity_type text not null default 'clinic',
  entity_id uuid,
  source_url text not null check (source_url ~* '^https?://'),
  source_title text,
  source_type text not null default 'website',
  source_date date,
  retrieved_at timestamptz not null default now(),
  content_hash text,
  snapshot_storage_path text,
  raw_excerpt text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table public.field_claims (
  id uuid primary key default gen_random_uuid(),
  clinic_id uuid not null references public.clinics(id) on delete cascade,
  entity_type text not null default 'clinic',
  entity_id uuid,
  field_path text not null,
  value jsonb not null,
  normalized_value jsonb,
  source_record_id uuid references public.source_records(id) on delete set null,
  agent_name text,
  agent_version text,
  confidence numeric(5,4) not null default 0 check (confidence >= 0 and confidence <= 1),
  verification_status text not null default 'proposed' check (
    verification_status in ('proposed', 'accepted', 'rejected', 'stale', 'conflict', 'review')
  ),
  human_locked boolean not null default false,
  created_at timestamptz not null default now()
);

create table public.agent_jobs (
  id uuid primary key default gen_random_uuid(),
  job_type text not null,
  status text not null default 'queued' check (
    status in ('queued', 'running', 'completed', 'failed', 'dead_letter', 'cancelled')
  ),
  priority integer not null default 100,
  entity_type text,
  entity_id uuid,
  clinic_id uuid references public.clinics(id) on delete set null,
  input jsonb not null default '{}'::jsonb,
  output jsonb not null default '{}'::jsonb,
  confidence numeric(5,4) check (confidence is null or (confidence >= 0 and confidence <= 1)),
  attempts integer not null default 0 check (attempts >= 0),
  max_attempts integer not null default 3 check (max_attempts > 0),
  requires_human boolean not null default false,
  error_message text,
  model_tier text,
  cost_cents integer not null default 0 check (cost_cents >= 0),
  locked_by text,
  scheduled_for timestamptz not null default now(),
  started_at timestamptz,
  finished_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create trigger agent_jobs_set_updated_at
before update on public.agent_jobs
for each row execute function public.set_updated_at();

create table public.review_queue (
  id uuid primary key default gen_random_uuid(),
  job_id uuid references public.agent_jobs(id) on delete set null,
  clinic_id uuid references public.clinics(id) on delete set null,
  review_type text not null,
  title text not null,
  field_path text,
  priority integer not null default 100,
  status text not null default 'open' check (status in ('open', 'resolved', 'dismissed')),
  payload jsonb not null default '{}'::jsonb,
  resolution jsonb not null default '{}'::jsonb,
  assigned_to text,
  resolved_by text,
  resolved_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create trigger review_queue_set_updated_at
before update on public.review_queue
for each row execute function public.set_updated_at();

create table public.change_events (
  id uuid primary key default gen_random_uuid(),
  event_name text not null,
  actor_type text not null default 'system',
  actor_id text,
  entity_type text,
  entity_id uuid,
  clinic_id uuid references public.clinics(id) on delete set null,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table public.entity_versions (
  id uuid primary key default gen_random_uuid(),
  entity_type text not null,
  entity_id uuid not null,
  version_number integer not null check (version_number > 0),
  data jsonb not null,
  source_event_id uuid references public.change_events(id) on delete set null,
  created_at timestamptz not null default now(),
  unique (entity_type, entity_id, version_number)
);

create table public.human_overrides (
  id uuid primary key default gen_random_uuid(),
  clinic_id uuid references public.clinics(id) on delete cascade,
  entity_type text not null default 'clinic',
  entity_id uuid,
  field_path text not null,
  value jsonb not null,
  reason text,
  locked boolean not null default true,
  expires_at timestamptz,
  created_by text,
  created_at timestamptz not null default now()
);

create table public.clinic_professionals (
  clinic_id uuid not null references public.clinics(id) on delete cascade,
  professional_id uuid not null references public.professionals(id) on delete cascade,
  role text,
  affiliation_status text not null default 'active' check (affiliation_status in ('active', 'ended', 'uncertain')),
  started_at date,
  ended_at date,
  source_record_id uuid references public.source_records(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (clinic_id, professional_id)
);

create trigger clinic_professionals_set_updated_at
before update on public.clinic_professionals
for each row execute function public.set_updated_at();

create index clinics_status_idx on public.clinics(status);
create index clinics_country_city_idx on public.clinics(country, city);
create index source_records_clinic_idx on public.source_records(clinic_id);
create index field_claims_clinic_field_idx on public.field_claims(clinic_id, field_path);
create index field_claims_status_idx on public.field_claims(verification_status);
create index agent_jobs_pick_next_idx on public.agent_jobs(status, scheduled_for, priority, created_at);
create index review_queue_status_priority_idx on public.review_queue(status, priority, created_at);
create index change_events_entity_idx on public.change_events(entity_type, entity_id, created_at desc);
create index entity_versions_entity_idx on public.entity_versions(entity_type, entity_id, version_number desc);
create index human_overrides_lookup_idx on public.human_overrides(clinic_id, field_path, locked);

alter table public.clinics enable row level security;
alter table public.professionals enable row level security;
alter table public.source_records enable row level security;
alter table public.field_claims enable row level security;
alter table public.agent_jobs enable row level security;
alter table public.review_queue enable row level security;
alter table public.change_events enable row level security;
alter table public.entity_versions enable row level security;
alter table public.human_overrides enable row level security;
alter table public.clinic_professionals enable row level security;

commit;
