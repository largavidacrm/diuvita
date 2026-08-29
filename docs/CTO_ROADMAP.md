# Diuvita CTO roadmap

Date: 2026-08-29

## Current state

Diuvita is currently a small static Netlify site:

- `data/clinics.json` is the editorial database.
- `build.py` renders `dist/`.
- `pendientes/` is the manual human-review holding area.
- Netlify runs data validation and then `python3 build.py`.
- Git is connected to `https://github.com/largavidacrm/diuvita`.
- Supabase project exists at `https://twxhcmvzbpnrneywdece.supabase.co`.

This is a good starting point. The next technical goal is not to rebuild the site. The next goal is to make Diuvita agent-ready while keeping the public site stable.

## Product principle

AI proposes. AI challenges. Rules decide whether AI may publish. Humans handle exceptions. Everything is reversible.

That means:

- Agents never edit production pages directly.
- The database stores structured facts, source evidence and confidence.
- Every important field has provenance.
- Human-locked fields always win over AI updates.
- Every autonomous action creates an event.
- Publishing can be disabled instantly without disabling research.

## Target architecture

Short term:

```text
Netlify static frontend
        |
        v
data/clinics.json today
        |
        v
Supabase Postgres as canonical truth
        |
        v
agent_jobs + review_queue + source_records
```

Medium term:

```text
Discovery worker
  -> Extraction worker
  -> Verification worker
  -> Rules engine
  -> Review queue or publish queue
  -> Netlify frontend
```

Long term:

```text
Supabase/Postgres
  + durable workflow engine
  + crawler/search providers
  + model-tier abstraction
  + admin control center
  + clinic claim portal
  + AI navigator
```

## Phase 1: foundation

Goal: create the data and operational backbone without enabling autonomous publishing.

Done in this repo now:

- Add data validation before the static build.
- Add a Supabase foundation migration.
- Apply the Supabase foundation to the live project.
- Add admin access controls in Supabase.
- Add the first static `/admin` control center.
- Add manual clinic editing in `/admin` with audit events and entity versions.
- Add a public Supabase feed for the static site build.
- Add an admin-triggered Netlify rebuild path after manual edits.
- Add a seed exporter for the current clinic JSON.
- Add this CTO roadmap.
- Protect local secrets and generated files in `.gitignore`.
- Configure the canonical public domain as `https://www.diuvita.com`.

Next implementation steps:

1. Push the admin foundation commit to GitHub once Daniel explicitly approves.
2. Confirm `.deploy/`, `.env*`, ZIPs and generated `dist/` are not committed.
3. Set Netlify environment variables for Supabase build reads and the rebuild hook.
4. Publish the Supabase-to-public-site sync.
5. Add the first shadow-mode workflow worker: `DISCOVER_CLINIC`.

## Phase 2: first autonomous loop

Build one complete clinic workflow before adding more agent types.

```text
DISCOVER_CLINIC
  -> DEDUPE_CLINIC
  -> EXTRACT_CLINIC_PROFILE
  -> VERIFY_CLINIC_PROFILE
  -> APPLY_PUBLICATION_RULES
  -> REVIEW_QUEUE or PUBLISH_CANDIDATE
  -> NOTIFY_DIGEST
```

Initial autonomy level:

- Auto-publish: off.
- Auto-create review items: on.
- Auto-store sources and extracted claims: on.
- Auto-generate proposed clinic profile: on.
- Human review: required for all first 100-200 candidates.

Only after measured accuracy should auto-publish be enabled for low-risk fields.

## Phase 3: expand the machine

After the clinic loop works reliably:

1. Monitoring agent: rechecks existing clinics.
2. Doctor agent: creates and updates professional entities.
3. Pricing agent: extracts consultation, program and package prices.
4. SEO agent: proposes programmatic location/treatment pages.
5. Outreach agent: invites clinics to claim profiles.
6. Quality controller: audits published profiles and pauses automation if quality drops.

## Rules engine

Business rules must live outside prompts.

Examples:

- Address can auto-accept at lower risk than medical claims.
- Treatments require stronger evidence than contact details.
- Medical or evidence claims require the highest confidence or human review.
- A field with a matching active `human_overrides` record cannot be overwritten.
- Conflicting extractor/verifier outputs create a `review_queue` item.

The AI creates structured facts. The rules engine decides actions.

## Admin control center

Do not publish a public admin page until authentication exists.

The first private admin should show:

- Agents running.
- Jobs today.
- Auto-approved count.
- Human-review count.
- Failed jobs.
- Estimated AI cost.
- Review inbox.
- Recent autonomous changes.
- Rollback links.
- Human-lock controls.

This is where Daniel supervises the machine, corrects clinic data manually, approves exceptions and protects fields the AI should not overwrite.

## Access needed from Daniel

These are the only things that require Daniel or account access:

- GitHub repository destination.
- Supabase database password or service role key.
- Netlify environment variable access.
- OpenAI API key for production workers.
- Search/crawler provider choice when web discovery begins.
- Email notification provider or account.

Everything else should be built by Codex step by step.
