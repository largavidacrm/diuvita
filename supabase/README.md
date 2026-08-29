# Diuvita Supabase foundation

This folder contains the first production-data foundation for Diuvita.

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
python3 scripts/export_supabase_bootstrap.py > /tmp/diuvita_supabase_bootstrap.sql
```

2. Review `/tmp/diuvita_supabase_bootstrap.sql`.
3. Run it in the Supabase SQL editor.

Local apply option:

```bash
scripts/apply_supabase_bootstrap.sh
```

This reads `DATABASE_URL` from `.env`, generates `/tmp/diuvita_supabase_bootstrap.sql` and applies it with `psql`.

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
python3 scripts/export_supabase_seed.py > /tmp/diuvita_seed.sql
```

3. Review `/tmp/diuvita_seed.sql`, then run it in Supabase.
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

## Public site feed

`public.public_clinics_for_site` returns only publishable clinic data (`published` and `preliminary`) for the static site build. In Netlify, set `DIUVITA_DATA_SOURCE=supabase` so `build.py` reads this feed when generating the public pages.

`supabase/migrations/0005_private_rebuild_hook.sql` adds a private Supabase setting and trigger. Once the build hook URL is stored in `private.app_settings`, public clinic changes ask Netlify to rebuild the static site. The hook URL is not committed to Git and is not exposed to the browser.

## Shadow discovery review

`supabase/migrations/0006_shadow_discovery_queue.sql` adds the first safe workflow surface for `DISCOVER_CLINIC`. A discovery job can be picked, completed with candidate clinics and converted into `review_queue` cards. Review cards can then be dismissed or turned into draft clinic records. Drafts are not published on Diuvita until an admin manually edits their status to `published` or `preliminary`.

`supabase/migrations/0007_candidate_duplicate_hints.sql` adds conservative duplicate hints. Candidates with the same website or a very similar name are still sent to review, but the review card shows likely existing matches and blocks draft creation for clear duplicates.

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
