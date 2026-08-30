#!/usr/bin/env python3
"""Create internal clinic-profile enrichment review cards.

This tool reads data/clinic_profile_enrichment_proposals_2026-08-30.json and
adds review_queue items for existing clinics. It does not update public clinic
profiles; Daniel must review and save each clinic from the admin panel.
"""
import argparse
import json
import os
import sys

from submit_discovery_candidates import (
    get_default_admin_email,
    load_env_file,
    run_psql,
    sql_literal,
)


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_PATH = os.path.join(
    ROOT,
    "data",
    "clinic_profile_enrichment_proposals_2026-08-30.json",
)


def load_batch(path):
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    proposals = data.get("proposals")
    if not isinstance(proposals, list) or not proposals:
        raise SystemExit("Proposal file must contain a non-empty proposals list.")
    clean = []
    for proposal in proposals:
        if not isinstance(proposal, dict):
            continue
        if not proposal.get("slug"):
            raise SystemExit("Every proposal needs a clinic slug.")
        if not isinstance(proposal.get("proposed_fields"), dict) or not proposal["proposed_fields"]:
            raise SystemExit(f"Proposal for {proposal.get('slug')} has no proposed_fields.")
        clean.append(proposal)
    if not clean:
        raise SystemExit("No valid proposals found.")
    return data.get("batch") or "clinic-profile-enrichment", clean


def proposal_field_count(proposal):
    return len(proposal.get("proposed_fields") or {})


def dry_run(batch, proposals):
    print(f"OK dry run: {len(proposals)} internal review proposals in {batch}.")
    for proposal in proposals:
        print(
            "- "
            + proposal["slug"]
            + f": {proposal_field_count(proposal)} campos propuestos"
        )


def clinic_exists(slug, local_env):
    sql = f"""
select count(*)
from public.clinics
where slug = {sql_literal(slug)};
"""
    return int(run_psql(sql, local_env) or "0") > 0


def create_review(batch, proposal, admin_email, local_env):
    title = proposal.get("title") or "Ampliar ficha: " + proposal["slug"]
    priority = int(proposal.get("priority") or 55)
    payload = json.dumps(proposal, ensure_ascii=False)
    sql = f"""
with target as (
  select id, slug, display_name, city, country, website
  from public.clinics
  where slug = {sql_literal(proposal["slug"])}
),
incoming as (
  select {sql_literal(payload)}::jsonb as proposal
),
existing as (
  select rq.id, rq.title
  from public.review_queue rq
  join target t on t.id = rq.clinic_id
  where rq.review_type = 'clinic_profile_enrichment'
    and rq.status = 'open'
    and rq.payload ->> 'proposal_batch' = {sql_literal(batch)}
  limit 1
),
inserted as (
  insert into public.review_queue (
    clinic_id,
    review_type,
    title,
    field_path,
    priority,
    status,
    payload,
    assigned_to
  )
  select
    t.id,
    'clinic_profile_enrichment',
    {sql_literal(title)},
    'current_data',
    {priority},
    'open',
    jsonb_strip_nulls(
      (i.proposal - 'slug' - 'priority' - 'title') ||
      jsonb_build_object(
        'mode', 'shadow',
        'proposal_batch', {sql_literal(batch)},
        'clinic_id', t.id,
        'clinic_slug', t.slug,
        'clinic_name', t.display_name,
        'clinic_city', t.city,
        'clinic_country', t.country,
        'website', t.website
      )
    ),
    {sql_literal(admin_email)}
  from target t
  cross join incoming i
  where not exists (select 1 from existing)
  returning id, title
),
resolved as (
  select 'inserted' as status, id, title from inserted
  union all
  select 'existing' as status, id, title from existing
  where not exists (select 1 from inserted)
)
select coalesce(jsonb_agg(to_jsonb(resolved.*)), '[]'::jsonb)
from resolved;
"""
    output = run_psql(sql, local_env)
    data = json.loads(output or "[]")
    if not data:
        return {"status": "missing", "slug": proposal["slug"]}
    return data[0]


def record_event(batch, inserted, existing, missing, admin_email, local_env):
    payload = json.dumps(
        {
            "proposal_batch": batch,
            "inserted": inserted,
            "existing": existing,
            "missing": missing,
        },
        ensure_ascii=False,
    )
    sql = f"""
insert into public.change_events (
  event_name,
  actor_type,
  actor_id,
  entity_type,
  payload
)
values (
  'clinic_profile_enrichment_proposals_created',
  'admin',
  {sql_literal(admin_email)},
  'review_queue',
  {sql_literal(payload)}::jsonb
);
"""
    run_psql(sql, local_env)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", default=DEFAULT_PATH)
    parser.add_argument("--admin-email", help="Admin email used for assignment/audit.")
    parser.add_argument("--apply", action="store_true", help="Create review cards in Supabase.")
    return parser.parse_args()


def main():
    args = parse_args()
    batch, proposals = load_batch(args.path)
    if not args.apply:
        dry_run(batch, proposals)
        return

    local_env = load_env_file()
    admin_email = args.admin_email or get_default_admin_email(local_env)
    inserted = []
    existing = []
    missing = []

    for proposal in proposals:
        if not clinic_exists(proposal["slug"], local_env):
            missing.append(proposal["slug"])
            continue
        result = create_review(batch, proposal, admin_email, local_env)
        status = result.get("status")
        if status == "inserted":
            inserted.append(proposal["slug"])
        elif status == "existing":
            existing.append(proposal["slug"])
        else:
            missing.append(proposal["slug"])

    record_event(batch, inserted, existing, missing, admin_email, local_env)
    print(json.dumps({
        "batch": batch,
        "inserted": inserted,
        "existing": existing,
        "missing": missing,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
