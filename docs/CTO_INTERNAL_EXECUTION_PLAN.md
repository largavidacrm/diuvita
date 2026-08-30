# Diuvita internal CTO execution plan

Date: 2026-08-30

## North star

Build Diuvita as a supervised intelligence machine, not as a manually edited directory.

Target flow:

```text
Internet
  -> Discovery agents
  -> Extraction agent
  -> Verification / prosecutor agent
  -> Rules / arbiter
  -> Human review or safe auto-approval
  -> Supabase versioned truth
  -> Netlify public site
  -> digest, undo, monitoring and next jobs
```

Core principle:

```text
AI proposes. AI challenges. Rules decide. Daniel handles exceptions. Everything is reversible.
```

## Current operating state

Already built:

- Public Netlify site at `https://www.diuvita.com`.
- Supabase canonical database for clinics.
- Static build can read live clinic data from Supabase.
- Private `/admin/` panel with Supabase Auth.
- Manual clinic editing from the admin panel.
- Audit events and entity versions for manual edits.
- `agent_jobs`, `review_queue`, `source_records`, `field_claims`, `human_overrides` and related foundation tables.
- Admin visibility for clinic version history, protected fields and internal evidence claims.
- Source records can be hydrated with compact hash/excerpt evidence through `scripts/hydrate_source_records.py`.
- First source-change watcher exists in `scripts/monitor_source_changes.py`.
- Safe recurring CTO shadow cycle exists in `scripts/run_cto_shadow_cycle.py`.
- Shadow discovery path for clinic candidates.
- Duplicate hints for candidates.
- Quality audit workflow for incomplete clinic profiles, including contact, services, units, specialists and technology.
- Internal profile-enrichment review cards for existing clinics.
- Public clinic pages display richer fields: contact, services, specialties, units, tech and published specialists.

Not yet mature:

- Real recurring internet discovery.
- Durable source snapshots.
- Independent extraction and verification agents.
- Deterministic rules engine for field-level publication.
- Doctor, pricing, treatment and SEO workflows.
- Daily/weekly digest.
- Rollback controls in the admin UI.
- Accuracy measurement across 100-200 reviewed items.

## Execution lanes

### Lane 1: Control center

Goal: Daniel supervises the machine without touching technical tools.

Build next:

1. Review inbox filters by type and risk.
2. Clear proposal diff before saving a clinic.
3. One-click dismiss/resolve notes that are understandable.
4. Rollback view from `entity_versions`.
5. Human-lock controls for sensitive fields.
6. Automation status panel: auto-publish off/on, shadow mode, last run, failed jobs.

Definition of done:

- Daniel can review, approve, reject and undo changes from `/admin/`.
- Every sensitive change remains visible before publication.

### Lane 2: Data provenance

Goal: every important fact has a source and a confidence trail.

Build next:

1. Source snapshot table or storage path for fetched pages.
2. Script to capture source title, URL, retrieval date, excerpt and hash.
3. Field claims for contact, services, specialists, technologies and prices.
4. Claim verification statuses: proposed, accepted, rejected, stale, conflict, review.
5. Admin view showing "why we believe this field".

Definition of done:

- A clinic field can be traced back to its source.
- Old values remain available after updates.

### Lane 3: First autonomous clinic loop

Goal: one complete workflow for clinics before adding more agent types.

Build in order:

1. `DISCOVER_CLINIC`: find candidate clinics from search/source input.
2. `DEDUPE_CLINIC`: compare domain, name, city, address, phone, email and semantic similarity.
3. `EXTRACT_CLINIC_PROFILE`: produce structured JSON only.
4. `VERIFY_CLINIC_PROFILE`: adversarially challenge each important claim.
5. `APPLY_PUBLICATION_RULES`: deterministic rules decide accept/review/reject.
6. `PUBLISH_CANDIDATE`: create or update records only after rules allow it.
7. `NOTIFY_DIGEST`: summarize what happened and what needs Daniel.

Initial policy:

- Auto-publish off.
- Auto-create review items on.
- Auto-store sources and field claims on.
- Human review required for all medical, team, pricing and treatment claims.

Definition of done:

- A new clinic can move from discovery to review card with evidence and no manual data entry.
- Candidate review cards can be preflighted for internal draft creation with `scripts/promote_candidate_reviews.py`.

### Lane 4: Monitoring

Goal: once a clinic exists, Diuvita notices meaningful changes.

Build next:

1. Monitoring cadence per clinic tier: 7, 30 or 90 days.
2. Cheap page hash check before expensive AI.
3. Material-change detector.
4. Change extraction and verification.
5. Review cards for conflicts or important changes.

Definition of done:

- Existing clinics are checked automatically.
- No material change means no expensive AI call.

### Lane 5: Knowledge graph expansion

Goal: move from directory data to proprietary market intelligence.

Build after the clinic loop works:

1. Professionals and affiliations.
2. Diagnostics and technologies.
3. Treatments and evidence claims.
4. Programs and program components.
5. Prices and price history.
6. Locations and international patient support.

Definition of done:

- Diuvita can answer structured questions beyond "which clinics exist".

### Lane 6: Growth workflows

Goal: turn the data machine into growth.

Build after data accuracy is measured:

1. SEO opportunity agent.
2. Programmatic city/treatment pages.
3. Editorial research and fact-checking workflow.
4. Clinic claim portal.
5. Outreach workflow.
6. Analytics and strategy digest.

Definition of done:

- Diuvita creates useful pages and outreach from verified data, not from generic text generation.

## Field-level publication rules

Use different risk thresholds by field type.

Low risk:

- Official website.
- Address.
- City/country.
- Public email.
- Public phone.

Medium risk:

- Services.
- Technologies.
- Programs.
- Specialist names when listed on the clinic website.

High risk:

- Physician credentials.
- Prices.
- Treatment availability.
- Medical/evidence claims.
- Outcomes, guarantees or comparative quality statements.

Default behavior:

- Low-risk fields can eventually auto-accept after strong source match.
- Medium-risk fields go to review until measured accuracy is high.
- High-risk fields always require stricter verification or Daniel/human approval.
- Any conflict with a human-locked value goes to review and never overwrites automatically.

## Nightly autonomous priority order

When working unattended, pick the first safe task available in this order:

1. Fix broken checks, build failures or production regressions.
2. Improve admin review and rollback safety.
3. Add provenance and source-capture infrastructure.
4. Create internal review proposals for incomplete published profiles.
5. Build or improve job scripts/workers in shadow mode.
6. Add deterministic rules before any publishing expansion.
7. Improve validation and quality audit coverage.
8. Improve documentation only when it unlocks future execution.

Avoid:

- Direct publication of new medical/contact/team data without explicit approval.
- Paid services or new subscriptions without Daniel.
- Uploading local private proposal payloads to GitHub.
- Large rewrites of the public site before the data machine is stable.

## Immediate next build sequence

Next 10 technical steps:

1. Add review inbox filters and clearer counts in `/admin/`.
2. Add a proposal diff view before saving clinic changes.
3. Add rollback view using `entity_versions`. Done as a read-only version history in `/admin/`; restoring an old version remains intentionally gated.
4. Add human-lock controls for fields Daniel corrects manually. Done locally in `supabase/migrations/0012_human_field_locks.sql` and `/admin/`.
5. Add source snapshot capture for reviewed proposals. Done locally in `scripts/capture_source_snapshot.py`; enrichment review URLs can now be linked into Supabase `source_records` with `scripts/capture_enrichment_review_claims.py`.
6. Convert enrichment proposals into `field_claims`, not only review payloads. Done for existing review payloads with `scripts/capture_enrichment_review_claims.py`.
7. Add a deterministic rules module for field risk. Done locally in `scripts/diuvita_rules.py`; next step is integrating it with extraction and verification jobs.
8. Build a shadow `EXTRACT_CLINIC_PROFILE` script for one clinic URL. Done locally in `scripts/extract_clinic_profile_shadow.py`; next step is adding an independent verifier.
9. Build a shadow `VERIFY_CLINIC_PROFILE` script for extracted claims. Done locally in `scripts/verify_clinic_profile_shadow.py`; review-card wiring exists in `scripts/submit_shadow_extraction_review.py`.
10. Add a daily digest card/report for open reviews, failed jobs and costs. Done locally in `scripts/admin_digest.py`; next step is turning it into a scheduled notification when Daniel chooses the channel.

## Daniel decision checkpoints

Ask Daniel only when needed for:

- Search/crawler provider choice or account.
- OpenAI/API production key.
- Email notification sender.
- Whether/when to enable any auto-publish category.
- Brand/editorial policy for how much team/pricing/treatment detail Diuvita should display.
- Business decisions around clinic claim portal and outreach tone.

Everything else should be advanced directly and reported afterwards.
