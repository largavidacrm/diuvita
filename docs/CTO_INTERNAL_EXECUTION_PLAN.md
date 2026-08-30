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

Operating boundary:

- Before content, product, automation or publication work, check `docs/DIUVITA_LIMITES_OPERATIVOS.md`.
- If a task touches one of those hard limits, stop and ask Daniel with the escalation format in that guide.

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
- Admin evidence cards show field risk and the current rule decision for each claim.
- Admin rollback control from clinic version history, with field-change preview before restore and every restore audited as a new version.
- Candidate reviews now create internal drafts and route Daniel to final validation before publication.
- Candidate reviews now show a three-step publication path so Daniel sees that draft creation is not publication.
- Admin system status shows why auto-publication is or is not mature enough to discuss.
- Admin system status shows the concrete priority review case, not only the generic next-action category.
- Admin system status shows whether source monitoring is fresh or pending.
- Admin system status shows source snapshot retention without enabling cleanup.
- Admin system status shows specialist coverage for visible clinic profiles.
- Admin system status shows visible-profile completeness without editing clinic data.
- Source records can be hydrated with compact hash/excerpt evidence through `scripts/hydrate_source_records.py`.
- Source coverage can be measured per visible clinic before expanding automation, and the safe CTO cycle includes that measurement.
- Compact source snapshot history is stored in `source_snapshots`.
- Source snapshot retention can be measured read-only before any cleanup policy.
- First source-change watcher exists in `scripts/monitor_source_changes.py`.
- Source-change reviews include material hints for contact, team, services, prices and medical claims.
- Open source-change reviews can be processed into separate profile-enrichment proposals without editing public clinic data.
- Saved clinic sources can be processed in batch through shadow extraction/verifier proposals without editing public clinic data.
- Saved-source batches prioritize visible clinics with more measured public fields pending.
- Saved-source batches avoid multiple open enrichment cards for the same clinic by default.
- Safe recurring CTO shadow cycle exists in `scripts/run_cto_shadow_cycle.py`.
- Local safety checks are bundled in `scripts/run_local_checks.py`.
- Daniel-facing review brief exists in `scripts/daniel_review_brief.py`, read-only and suitable for future notifications.
- Review maturity can be measured read-only before considering low-risk auto-publish expansion.
- Published specialist coverage can be measured read-only before creating more team-detail workflows.
- Visible profile completeness can be measured read-only across summary, contact, services, units, specialists and technology, including a next-profile suggestion.
- Stored field claims can be evaluated read-only against publication rules before any policy change.
- Blocking field claims can be routed into internal quality-review cards without editing clinic data.
- Blocking field claims have a read-only Daniel brief so the first manual review target is clearer.
- Shadow discovery path for clinic candidates.
- Duplicate hints for candidates.
- Quality audit workflow for incomplete clinic profiles, including contact, services, units, specialists and technology.
- Internal profile-enrichment review cards for existing clinics.
- Public clinic pages display richer fields with clearer navigation, section counts, fast profile stats, contact-aware search and more scannable lists.
- Production health can be checked read-only for the public site shell, admin shell, sitemap and favicon.
- Safe CTO shadow cycle now includes a Daniel-facing brief in its JSON output and can optionally print only that brief for unattended logs.
- Safe CTO shadow cycle has a backlog guard so safe-apply runs do not keep adding review cards when the inbox is already full.
- Safe CTO shadow cycle can optionally include the read-only production health check.
- Safe CTO shadow cycle can optionally run the strict editorial-limit scan.
- Admin system status shows public website health from lightweight public checks.
- Admin system status and review inbox show duplicated profile-enrichment review pressure.
- Duplicated review pressure has a read-only brief with concrete clinics to start from, and the safe CTO cycle includes that measurement.

Not yet mature:

- Real recurring internet discovery.
- Source snapshots are durable and the watcher now respects monitoring cadence;
  cleanup is still disabled and retention is measured read-only.
- Extraction and verification exist in shadow mode, but they are not yet independent production workers.
- Batch source extraction exists as an operator tool, but should remain manual/supervised until review-card volume is comfortable.
- Deterministic field rules exist locally, but low-risk auto-approval stays disabled until accuracy is measured.
- Doctor, pricing, treatment and SEO workflows.
- Specialist coverage can now be measured, but publication of new professional details still needs manual review.
- Profile completeness can now be measured and shown in `/admin/`, but filling missing fields still needs sourced review cards and Daniel's final validation.
- Daily/weekly digest and notification cadence.
- Rollback controls in the admin UI need operational usage, but the restore path and preview now exist.
- Accuracy measurement needs more human-reviewed volume, but the measurement tool now exists.

## Execution lanes

### Lane 1: Control center

Goal: Daniel supervises the machine without touching technical tools.

Build next:

1. Review inbox filters by type and risk.
2. Clear proposal diff before saving a clinic.
3. One-click dismiss/resolve notes that are understandable.
4. Rollback view and restore control from `entity_versions`.
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

1. Monitoring cadence per clinic tier: 7, 30 or 90 days. Done locally in
   `scripts/monitor_source_changes.py`, using the latest stored snapshot date.
2. Cheap page hash check before expensive AI. Done locally in the watcher.
3. Material-change detector. Done locally with conservative internal hints.
4. Change extraction and verification. Initial bridge exists in
   `scripts/process_source_change_reviews.py`.
5. Review cards for conflicts or important changes. Done for source changes.

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
- Clinical units.
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

1. Add review inbox filters and clearer counts in `/admin/`. Done locally with quick filters by type, priority and repeated enrichment proposals, visible counts and a clear-filters control.
2. Add a proposal diff view before saving clinic changes. Done locally with a live before/after panel for manual edits and loaded proposals.
3. Add rollback view using `entity_versions`. Done in `/admin/` with version history, restore confirmation and field-change preview; restoring an old version remains intentionally gated.
4. Add human-lock controls for fields Daniel corrects manually. Done locally in `supabase/migrations/0012_human_field_locks.sql` and `/admin/`.
5. Add source snapshot capture for reviewed proposals. Done locally in `scripts/capture_source_snapshot.py`; enrichment review URLs can now be linked into Supabase `source_records` with `scripts/capture_enrichment_review_claims.py`.
6. Convert enrichment proposals into `field_claims`, not only review payloads. Done for existing review payloads with `scripts/capture_enrichment_review_claims.py`.
7. Add a deterministic rules module for field risk. Done locally in `scripts/diuvita_rules.py`; stored claims can now be evaluated read-only with `scripts/evaluate_claim_rules.py`.
8. Build a shadow `EXTRACT_CLINIC_PROFILE` script for one clinic URL. Done locally in `scripts/extract_clinic_profile_shadow.py`; next step is adding an independent verifier.
9. Build a shadow `VERIFY_CLINIC_PROFILE` script for extracted claims. Done locally in `scripts/verify_clinic_profile_shadow.py`; review-card wiring exists in `scripts/submit_shadow_extraction_review.py`.
10. Add a daily digest card/report for open reviews, failed jobs and costs. Done locally in `scripts/admin_digest.py`; a simpler Daniel-facing brief exists in `scripts/daniel_review_brief.py`, and the safe CTO cycle now embeds a Daniel-facing summary. Next step is turning it into a scheduled notification when Daniel chooses the channel.
11. Add a read-only review maturity measurement before any auto-publish expansion. Done locally in `scripts/measure_review_maturity.py`; the signal now appears in the admin status and digest.
12. Process source-change review cards into profile-enrichment proposals. Done locally in `scripts/process_source_change_reviews.py`; it never edits or publishes clinic data.
13. Add source-monitoring cadence so the watcher checks due sources instead of repeatedly scanning the same fresh sources. Done locally in `scripts/monitor_source_changes.py`; use `--force` for manual spot checks.
14. Show source-monitoring freshness in the admin control center. Done locally in `/admin/`, using source records and latest snapshots.
15. Turn rejected/conflict/source-less claims into internal quality-review cards. Done locally in `scripts/submit_blocking_claim_reviews.py` and included in the safe CTO shadow cycle; `scripts/blocking_claim_brief.py` summarizes those blockers for Daniel without writing data.
16. Add a read-only source snapshot retention report. Done locally in `scripts/measure_source_snapshot_retention.py` and surfaced in `/admin/`; no cleanup/deletion path is enabled.
17. Add a read-only visible-profile completeness report. Done locally in `scripts/measure_profile_completeness.py`, included in the digest/brief and surfaced in `/admin/` with a next-profile suggestion.
18. Improve public clinic profile UX so collected fields are easier to scan. Done locally with card-level field signals, top-of-profile stats, section counts, a clear "En esta ficha" jump area and lighter profile lists.
19. Include profile completeness in the safe CTO shadow cycle. Done locally as a read-only cycle step.
20. Add a production smoke check. Done locally in `scripts/check_production_health.py`; it reads public URLs only and is separate from local checks.

## Daniel decision checkpoints

Ask Daniel only when needed for:

- Search/crawler provider choice or account.
- OpenAI/API production key.
- Email notification sender.
- Whether/when to enable any auto-publish category.
- Brand/editorial policy for how much team/pricing/treatment detail Diuvita should display.
- Business decisions around clinic claim portal and outreach tone.
- Any hard limit listed in `docs/DIUVITA_LIMITES_OPERATIVOS.md`.

Everything else should be advanced directly and reported afterwards.
