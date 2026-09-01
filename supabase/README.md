# Vitalarga Supabase foundation

This folder contains the first production-data foundation for Vitalarga.

The current public website still builds from `data/clinics.json`. Supabase is the next canonical layer: versioned clinic truth, sources, field claims, agent jobs, review queue, human overrides and audit events.

## First setup

Project URL:

```text
https://twxhcmvzbpnrneywdece.supabase.co
```

Project ref:

```text
twxhcmvzbpnrneywdece
```

1. Generate a single SQL bootstrap file:

```bash
python3 scripts/export_supabase_bootstrap.py > /tmp/vitalarga_supabase_bootstrap.sql
```

2. Review `/tmp/vitalarga_supabase_bootstrap.sql`.
3. Run it in the Supabase SQL editor.

Local apply option:

```bash
scripts/apply_supabase_bootstrap.sh
```

This reads `DATABASE_URL` from `.env`, generates `/tmp/vitalarga_supabase_bootstrap.sql` and applies it with `psql`.

For local use, the easiest option is to set only this value in `.env`:

```text
SUPABASE_DB_PASSWORD=
```

The script will build the safe local connection itself.

Check the imported foundation:

```bash
scripts/check_supabase_foundation.sh
```

Apply a later migration:

```bash
scripts/apply_supabase_sql.sh supabase/migrations/0002_admin_access.sql
scripts/apply_supabase_sql.sh supabase/migrations/0003_admin_clinic_editing.sql
scripts/apply_supabase_sql.sh supabase/migrations/0004_public_site_feed.sql
scripts/apply_supabase_sql.sh supabase/migrations/0005_private_rebuild_hook.sql
scripts/apply_supabase_sql.sh supabase/migrations/0006_shadow_discovery_queue.sql
scripts/apply_supabase_sql.sh supabase/migrations/0007_candidate_duplicate_hints.sql
scripts/apply_supabase_sql.sh supabase/migrations/0008_capture_candidate_sources.sql
scripts/apply_supabase_sql.sh supabase/migrations/0009_promote_candidate_sources_and_claims.sql
scripts/apply_supabase_sql.sh supabase/migrations/0010_quality_audit_workflow.sql
scripts/apply_supabase_sql.sh supabase/migrations/0011_automation_status.sql
scripts/apply_supabase_sql.sh supabase/migrations/0012_human_field_locks.sql
scripts/apply_supabase_sql.sh supabase/migrations/0013_quality_audit_detail_fields.sql
```

Allow a first admin email after creating the Auth user in Supabase:

```bash
scripts/add_supabase_admin.sh daniel@example.com
```

Create and check the Auth user:

```bash
python3 scripts/create_supabase_auth_user.py daniel@example.com
python3 scripts/check_supabase_auth_login.py daniel@example.com
```

If the direct database host does not resolve from this machine, use Supabase's Session pooler from the dashboard's green **Connect** button and set:

```text
SUPABASE_DB_HOST=aws-1-eu-west-1.pooler.supabase.com
SUPABASE_DB_PORT=5432
SUPABASE_DB_NAME=postgres
SUPABASE_DB_USER=postgres.twxhcmvzbpnrneywdece
```

Alternative two-step setup:

1. Run `supabase/migrations/0001_agent_foundation.sql` in the Supabase SQL editor or through the Supabase CLI.
2. Generate the initial clinic import:

```bash
python3 scripts/export_supabase_seed.py > /tmp/vitalarga_seed.sql
```

3. Review `/tmp/vitalarga_seed.sql`, then run it in Supabase.
4. Add future server-side environment variables in Netlify or worker runtime:

```text
SUPABASE_URL=https://twxhcmvzbpnrneywdece.supabase.co
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_PUBLISHABLE_KEY=
SUPABASE_DB_PASSWORD=
OPENAI_API_KEY=
```

`SUPABASE_SERVICE_ROLE_KEY` and the database password must never be exposed in browser code or committed to Git.

Local values can live in `.env`, which is ignored by Git. The publishable key can be used in browser-side code only when row-level security policies are correct.

## Manual clinic editing

`/admin/` lets an authorized admin open a clinic, edit the main public fields, list the specialists published by that clinic and save the result to Supabase. The save path uses `public.admin_update_clinic`, which checks admin access, updates the clinic and records the change in `change_events` and `entity_versions`.

Daniel's non-technical panel guide lives in `docs/DANIEL_ADMIN_GUIDE.md`.

## Public site feed

`public.public_clinics_for_site` returns only publishable clinic data (`published` and `preliminary`) for the static site build. In Netlify, set `VITALARGA_DATA_SOURCE=supabase` so `build.py` reads this feed when generating the public pages.

`supabase/migrations/0020_location_transparency_public_feed.sql` extends that
feed with optional multi-location data, Google Maps links, Google review links
and transparency fields. The fields live in `clinics.current_data`, so existing
clinic rows keep working while richer profiles can be edited from `/admin/`.

`supabase/migrations/0005_private_rebuild_hook.sql` adds a private Supabase setting and trigger. Once the build hook URL is stored in `private.app_settings`, public clinic changes ask Netlify to rebuild the static site. The hook URL is not committed to Git and is not exposed to the browser.

`supabase/migrations/0018_batch_public_site_rebuilds.sql` updates that rebuild request so public-site rebuilds can be batched. The default window is 30 minutes and can be adjusted through `private.app_settings` with the key `vitalarga_rebuild_batch_minutes`.

`supabase/migrations/0019_admin_publication_control_summary.sql` exposes the rebuild batching status to authorized admins without returning the private Netlify build hook URL.

## Shadow discovery review

`supabase/migrations/0006_shadow_discovery_queue.sql` adds the first safe workflow surface for `DISCOVER_CLINIC`. A discovery job can be picked, completed with candidate clinics and converted into `review_queue` cards. Review cards can then be dismissed or turned into draft clinic records. Drafts are not published on Vitalarga until an admin manually edits their status to `published` or `preliminary`.

`supabase/migrations/0007_candidate_duplicate_hints.sql` adds conservative duplicate hints. Candidates with the same website or a very similar name are still sent to review, but the review card shows likely existing matches and blocks draft creation for clear duplicates.

`supabase/migrations/0008_capture_candidate_sources.sql` captures candidate source URLs as `source_records`, so every review proposal keeps an auditable evidence trail before it becomes a clinic draft.

`supabase/migrations/0009_promote_candidate_sources_and_claims.sql` promotes that source when a review becomes a draft clinic and stores the candidate's main facts as `field_claims` with `verification_status = 'review'`.

`supabase/migrations/0010_quality_audit_workflow.sql` adds a zero-cost quality audit for visible clinic profiles. It creates review cards for missing or weak public fields and never edits the public profile directly.

`supabase/migrations/0011_automation_status.sql` stores safe defaults for automation: agents enabled, auto-publish disabled and a target of 200 reviewed candidates before considering higher autonomy.

`supabase/migrations/0012_human_field_locks.sql` adds admin field locks. When Daniel protects a field from `/admin/`, future agents can still propose evidence but should not overwrite that field automatically.

`supabase/migrations/0013_quality_audit_detail_fields.sql` expands the quality audit so it also flags missing units and highlighted technology.

`supabase/migrations/0024_single_issue_quality_audits.sql` updates the quality audit workflow so future manual-review cards are single-decision: one missing field per card, with `quality_issue_code` and `field_path` preserved for traceability. Apply only after Daniel approves changing the live Supabase function.

Local candidate batches can be submitted with:

```bash
python3 scripts/submit_discovery_candidates.py --create-job "longevity clinic Spain" --candidates /path/to/candidates.json
```

The JSON file can be either a list or an object with a `candidates` list. Each item may include `name`, `website`, `city`, `country`, `summary`, `source_url`, `discovery_confidence`, `services`, `specialties` and `profesionales`.

## Runtime principle

Codex builds and maintains the system. Supabase, workers and APIs run the production agents.

The first production workflow should run in shadow mode:

1. Discover a candidate clinic.
2. Extract structured fields with sources.
3. Verify the fields adversarially.
4. Apply deterministic rules.
5. Send anything ambiguous to `review_queue`.
6. Do not auto-publish until enough examples have been reviewed.
