begin;

create or replace function public.capture_candidate_source_record()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  clean_source_url text := nullif(btrim(coalesce(new.payload ->> 'candidate_source_url', '')), '');
  clean_title text := nullif(btrim(coalesce(new.payload ->> 'candidate_name', new.title, '')), '');
  source_id uuid;
begin
  if new.review_type <> 'candidate_clinic' then
    return null;
  end if;

  if clean_source_url is null or clean_source_url !~* '^https?://' then
    return null;
  end if;

  select sr.id
  into source_id
  from public.source_records sr
  where sr.entity_type = 'candidate_clinic'
    and sr.metadata ->> 'review_id' = new.id::text
  order by sr.created_at asc
  limit 1;

  if source_id is null then
    insert into public.source_records (
      entity_type,
      source_url,
      source_title,
      source_type,
      raw_excerpt,
      metadata
    )
    values (
      'candidate_clinic',
      clean_source_url,
      clean_title,
      'discovery',
      left(coalesce(new.payload -> 'candidate' ->> 'summary', new.payload ->> 'note', ''), 1000),
      jsonb_strip_nulls(jsonb_build_object(
        'review_id', new.id,
        'job_id', new.job_id,
        'mode', new.payload ->> 'mode'
      ))
    )
    returning id into source_id;
  end if;

  update public.review_queue
  set payload = jsonb_set(new.payload, '{source_record_id}', to_jsonb(source_id::text), true)
  where id = new.id
    and coalesce(payload ->> 'source_record_id', '') = '';

  return null;
end;
$$;

drop trigger if exists review_queue_capture_candidate_source on public.review_queue;
create trigger review_queue_capture_candidate_source
after insert on public.review_queue
for each row execute function public.capture_candidate_source_record();

with review_sources as (
  select
    rq.id as review_id,
    rq.job_id,
    nullif(btrim(coalesce(rq.payload ->> 'candidate_source_url', '')), '') as source_url,
    nullif(btrim(coalesce(rq.payload ->> 'candidate_name', rq.title, '')), '') as source_title,
    left(coalesce(rq.payload -> 'candidate' ->> 'summary', rq.payload ->> 'note', ''), 1000) as raw_excerpt,
    rq.payload ->> 'mode' as mode
  from public.review_queue rq
  where rq.review_type = 'candidate_clinic'
    and nullif(btrim(coalesce(rq.payload ->> 'candidate_source_url', '')), '') ~* '^https?://'
)
insert into public.source_records (
  entity_type,
  source_url,
  source_title,
  source_type,
  raw_excerpt,
  metadata
)
select
  'candidate_clinic',
  rs.source_url,
  rs.source_title,
  'discovery',
  rs.raw_excerpt,
  jsonb_strip_nulls(jsonb_build_object(
    'review_id', rs.review_id,
    'job_id', rs.job_id,
    'mode', rs.mode,
    'backfilled', true
  ))
from review_sources rs
where not exists (
  select 1
  from public.source_records sr
  where sr.entity_type = 'candidate_clinic'
    and sr.metadata ->> 'review_id' = rs.review_id::text
);

with
all_sources as (
  select sr.id, (sr.metadata ->> 'review_id')::uuid as review_id
  from public.source_records sr
  where sr.entity_type = 'candidate_clinic'
    and sr.metadata ? 'review_id'
    and sr.metadata ->> 'review_id' ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
)
update public.review_queue rq
set payload = jsonb_set(rq.payload, '{source_record_id}', to_jsonb(all_sources.id::text), true)
from all_sources
where rq.id = all_sources.review_id
  and coalesce(rq.payload ->> 'source_record_id', '') = '';

grant execute on function public.capture_candidate_source_record() to authenticated;

commit;
