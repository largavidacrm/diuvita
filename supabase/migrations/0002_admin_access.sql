begin;

create table if not exists public.admin_users (
  id uuid primary key default gen_random_uuid(),
  email text not null,
  role text not null default 'owner' check (role in ('owner', 'operator', 'viewer')),
  active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create unique index if not exists admin_users_email_unique_idx
on public.admin_users (lower(email));

drop trigger if exists admin_users_set_updated_at on public.admin_users;
create trigger admin_users_set_updated_at
before update on public.admin_users
for each row execute function public.set_updated_at();

alter table public.admin_users enable row level security;

create or replace function public.is_admin()
returns boolean
language sql
stable
security definer
set search_path = public, auth
as $$
  select exists (
    select 1
    from public.admin_users au
    where au.active = true
      and lower(au.email) = lower(coalesce(auth.jwt() ->> 'email', ''))
  );
$$;

create or replace function public.admin_dashboard_summary()
returns jsonb
language plpgsql
stable
security definer
set search_path = public, auth
as $$
begin
  if not public.is_admin() then
    raise exception 'not authorized' using errcode = '42501';
  end if;

  return jsonb_build_object(
    'clinics', (
      select jsonb_build_object(
        'total', count(*),
        'published', count(*) filter (where status = 'published'),
        'preliminary', count(*) filter (where status = 'preliminary'),
        'review', count(*) filter (where status = 'review'),
        'draft', count(*) filter (where status = 'draft')
      )
      from public.clinics
    ),
    'reviews', (
      select jsonb_build_object(
        'open', count(*) filter (where status = 'open'),
        'resolved', count(*) filter (where status = 'resolved')
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
        'claims', (select count(*) from public.field_claims)
      )
    ),
    'generated_at', now()
  );
end;
$$;

grant usage on schema public to authenticated;
grant execute on function public.is_admin() to authenticated;
grant execute on function public.admin_dashboard_summary() to authenticated;

grant select, insert, update, delete on public.admin_users to authenticated;
grant select, insert, update, delete on public.clinics to authenticated;
grant select, insert, update, delete on public.professionals to authenticated;
grant select, insert, update, delete on public.clinic_professionals to authenticated;
grant select, insert, update, delete on public.source_records to authenticated;
grant select, insert, update, delete on public.field_claims to authenticated;
grant select, insert, update, delete on public.agent_jobs to authenticated;
grant select, insert, update, delete on public.review_queue to authenticated;
grant select, insert, update, delete on public.change_events to authenticated;
grant select, insert, update, delete on public.entity_versions to authenticated;
grant select, insert, update, delete on public.human_overrides to authenticated;

do $$
declare
  table_name text;
begin
  foreach table_name in array array[
    'admin_users',
    'clinics',
    'professionals',
    'clinic_professionals',
    'source_records',
    'field_claims',
    'agent_jobs',
    'review_queue',
    'change_events',
    'entity_versions',
    'human_overrides'
  ]
  loop
    execute format('drop policy if exists "admin full access" on public.%I', table_name);
    execute format(
      'create policy "admin full access" on public.%I for all to authenticated using (public.is_admin()) with check (public.is_admin())',
      table_name
    );
  end loop;
end;
$$;

commit;
