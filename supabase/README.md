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
OPENAI_API_KEY=
```

`SUPABASE_SERVICE_ROLE_KEY` and the database password must never be exposed in browser code or committed to Git.

Local values can live in `.env`, which is ignored by Git. The publishable key can be used in browser-side code only when row-level security policies are correct.

## Runtime principle

Codex builds and maintains the system. Supabase, workers and APIs run the production agents.

The first production workflow should run in shadow mode:

1. Discover a candidate clinic.
2. Extract structured fields with sources.
3. Verify the fields adversarially.
4. Apply deterministic rules.
5. Send anything ambiguous to `review_queue`.
6. Do not auto-publish until enough examples have been reviewed.
