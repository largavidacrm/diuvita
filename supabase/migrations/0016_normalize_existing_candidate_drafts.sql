begin;

with updated as (
  update public.clinics c
  set
    status = 'draft',
    current_data = jsonb_set(
      coalesce(c.current_data, '{}'::jsonb),
      '{status}',
      to_jsonb('borrador'::text),
      true
    ),
    updated_at = now()
  where c.status = 'discovered'
    and c.verification_status = 'agent_candidate'
  returning c.*
),
events as (
  insert into public.change_events (
    event_name,
    actor_type,
    actor_id,
    entity_type,
    entity_id,
    clinic_id,
    payload
  )
  select
    'candidate_existing_draft_status_normalized',
    'system',
    'migration-0016',
    'clinic',
    u.id,
    u.id,
    jsonb_build_object(
      'status', 'draft',
      'note', 'Existing candidate clinic normalized to internal draft status.'
    )
  from updated u
  returning id, entity_id
),
version_rows as (
  select
    u.*,
    e.id as source_event_id,
    coalesce((
      select max(ev.version_number)
      from public.entity_versions ev
      where ev.entity_type = 'clinic'
        and ev.entity_id = u.id
    ), 0) + 1 as next_version_number
  from updated u
  join events e on e.entity_id = u.id
)
insert into public.entity_versions (
  entity_type,
  entity_id,
  version_number,
  data,
  source_event_id
)
select
  'clinic',
  id,
  next_version_number,
  to_jsonb(version_rows) - 'source_event_id' - 'next_version_number',
  source_event_id
from version_rows;

commit;
