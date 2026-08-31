# Vitalarga internal CTO execution plan

Date: 2026-08-30

## North star

Build Vitalarga as a supervised intelligence machine, not as a manually edited directory.

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

- Before content, product, automation or publication work, check `docs/VITALARGA_LIMITES_OPERATIVOS.md`.
- If a task touches one of those hard limits, stop and ask Daniel with the escalation format in that guide.

## Current operating state

Already built:

- Public Netlify site at `https://www.vitalarga.com`.
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
- Admin system status shows source coverage per visible clinic and the next source-support target.
- Admin system status shows specialist coverage for visible clinic profiles.
- Admin review inbox has a specialist filter and shortcut for the next specialist target.
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
- Visible profile completeness can be measured read-only across summary, contact, Google Maps links, Google review links, services, units, specialists and technology, including a next-profile suggestion.
- Stored field claims can be evaluated read-only against publication rules before any policy change.
- Blocking field claims can be routed into internal quality-review cards without editing clinic data.
- Blocking field claims have a read-only Daniel brief so the first manual review target is clearer.
- Visible clinics with an existing official website can now get a matching internal source record before hydration, without editing profile fields or publishing.
- Visible clinics can now discover same-domain team/about pages as internal
  sources before specialist extraction, without editing profile fields or
  publishing.
- Shadow discovery path for clinic candidates.
- Duplicate hints for candidates.
- Quality audit workflow for incomplete clinic profiles, including contact, services, units, specialists and technology.
- Internal profile-enrichment review cards for existing clinics.
- Public clinic pages display richer fields with clearer navigation, no decorative count badges, contact-aware search and more scannable lists.
- Public clinic pages and the admin editor now allow multi-location clinic
  profiles, Google Maps profile links, Google review links and basic
  transparency fields without forcing a schema migration for every existing
  clinic. Public Google Maps buttons are shown only when we have a direct clinic
  profile link; generic searches, directions and street-address links stay
  pending.
- Official clinic websites can now be scanned for direct Google Maps profile
  links and Google review links, creating internal review cards only.
- Google Maps discovery can also scan a small number of same-site contact,
  location or clinic-site pages, which improves direct-profile detection
  without broad crawling or automatic publication.
- Saved-source extraction now prefers team/about pages when specialists are
  missing, so pages with public professionals are reviewed before generic home
  or service pages for the same clinic.
- Production health can be checked read-only for the public site shell, admin shell, sitemap and favicon.
- Safe CTO shadow cycle now includes a Daniel-facing brief in its JSON output and can optionally print only that brief for unattended logs.
- Safe CTO shadow cycle has a backlog guard so safe-apply runs stop adding review cards once the inbox enters the near-full zone.
- Safe CTO shadow cycle can optionally include the read-only production health check.
- Safe CTO shadow cycle can optionally run the strict editorial-limit scan.
- Admin system status shows public website health from lightweight public checks.
- Admin system status and review inbox show duplicated profile-enrichment review pressure.
- Admin system status and review inbox show the first clinic workgroup so Daniel can review clustered cards together.
- Duplicated review pressure has a read-only brief with concrete clinics to start from, and the safe CTO cycle includes that measurement.
- Blocking-claim briefs now show a plain recommended next step per affected clinic without resolving the claim.
- Global plan status can be generated as a read-only executive snapshot from real Supabase state.

Not yet mature:

- Real recurring internet discovery.
- Source snapshots are durable and the watcher now respects monitoring cadence;
  cleanup is still disabled and retention is measured read-only.
- Extraction and verification exist in shadow mode, but they are not yet independent production workers.
- Batch source extraction exists as an operator tool, but should remain manual/supervised until review-card volume is comfortable.
- Deterministic field rules exist locally, but low-risk auto-approval stays disabled until accuracy is measured.
- Doctor, pricing, treatment and SEO workflows.
- Specialist coverage can now be measured, but publication of new professional details still needs manual review.
- Team/about source discovery exists for visible clinics; it is optional and
  should be used in small batches before source-shadow extraction.
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

Goal: once a clinic exists, Vitalarga notices meaningful changes.

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
7. Clinic transparency signals: years in practice, public specialist count,
   visible professional credentialing and whether prices are public.

Definition of done:

- Vitalarga can answer structured questions beyond "which clinics exist".

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

- Vitalarga creates useful pages and outreach from verified data, not from generic text generation.

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
7. Add a deterministic rules module for field risk. Done locally in `scripts/vitalarga_rules.py`; stored claims can now be evaluated read-only with `scripts/evaluate_claim_rules.py`.
8. Build a shadow `EXTRACT_CLINIC_PROFILE` script for one clinic URL. Done locally in `scripts/extract_clinic_profile_shadow.py`; next step is adding an independent verifier.
9. Build a shadow `VERIFY_CLINIC_PROFILE` script for extracted claims. Done locally in `scripts/verify_clinic_profile_shadow.py`; review-card wiring exists in `scripts/submit_shadow_extraction_review.py`.
10. Add a daily digest card/report for open reviews, failed jobs and costs. Done locally in `scripts/admin_digest.py`; a simpler Daniel-facing brief exists in `scripts/daniel_review_brief.py`, and the safe CTO cycle now embeds a Daniel-facing summary. Next step is turning it into a scheduled notification when Daniel chooses the channel.
11. Add a read-only review maturity measurement before any auto-publish expansion. Done locally in `scripts/measure_review_maturity.py`; the signal now appears in the admin status and digest.
12. Process source-change review cards into profile-enrichment proposals. Done locally in `scripts/process_source_change_reviews.py`; it never edits or publishes clinic data.
13. Add source-monitoring cadence so the watcher checks due sources instead of repeatedly scanning the same fresh sources. Done locally in `scripts/monitor_source_changes.py`; use `--force` for manual spot checks.
14. Show source-monitoring freshness in the admin control center. Done locally in `/admin/`, using source records and latest snapshots.
15. Turn conflict/source-less claims into internal quality-review cards. Done locally in `scripts/submit_blocking_claim_reviews.py` and included in the safe CTO shadow cycle; `scripts/blocking_claim_brief.py` summarizes those blockers for Daniel without writing data. Rejected claims remain quality signals, but do not create Daniel-facing blocker cards by default.
16. Add a read-only source snapshot retention report. Done locally in `scripts/measure_source_snapshot_retention.py` and surfaced in `/admin/`; no cleanup/deletion path is enabled.
17. Add a read-only visible-profile completeness report. Done locally in `scripts/measure_profile_completeness.py`, included in the digest/brief and surfaced in `/admin/` with a next-profile suggestion. Google Maps profile links and Google review links are measured as separate gaps.
18. Improve public clinic profile UX so collected fields are easier to scan. Done locally with card-level field signals, a clear "En esta ficha" jump area, lighter profile lists and no decorative count badges.
19. Include profile completeness in the safe CTO shadow cycle. Done locally as a read-only cycle step.
20. Add a production smoke check. Done locally in `scripts/check_production_health.py`; it reads public URLs only and is separate from local checks.
21. Surface visible source coverage in the admin control center. Done locally in `/admin/`, showing source coverage, profiles without sources and the next source-support target.
22. Add a reusable global plan status snapshot. Done locally in `scripts/global_plan_status.py`; it explains the current roadmap phase from real admin/digest state.
23. Add clinic-workgroup shortcuts and status. Done locally in `/admin/`, `scripts/review_backlog_brief.py`, the Daniel brief and global status so clustered review cards can be handled together.
24. Clarify blocking-claim next steps. Done locally in `scripts/blocking_claim_brief.py`; it stays read-only and tells Daniel whether to compare evidence or find an official source.
25. Seed official website sources for visible clinics. Done locally in `scripts/seed_visible_clinic_sources.py` and wired into the safe CTO cycle before source hydration.
26. Add safe Google-link discovery for clinic websites. Done locally in `scripts/discover_clinic_google_links.py`; it can create review cards for direct Google Maps/profile links without editing or publishing clinic data.
27. Make specialist review cards easier to triage. Done locally in `/admin/`: the **Especialistas** quick filter now brings cards with more proposed professionals to the top.
28. Pause new job creation when the review inbox is near the safe-write limit. Done locally in `/admin/`: at five or fewer remaining review slots, the panel asks Daniel to clean existing reviews before adding more work.
29. Improve team-page specialist extraction. Done locally in `scripts/extract_clinic_profile_shadow.py`: explicit name-role team sections can yield more public professionals without publishing them automatically.
30. Add a one-click loader for pending specialists in the clinic editor. Done locally in `/admin/`: detected specialists can be loaded into the form, reviewed in the diff and saved only through manual validation.
31. Flag generic Google Maps links during final validation. Done locally in `/admin/`: search, route or address-like Google links remain pending until a real clinic profile link is reviewed.
32. Remove numbered labels from the internal location editor. Done locally in `/admin/`: locations are shown as principal/adicional instead of "Sede 1" or "Sede 2".
33. Tighten Google Maps discovery against address-like proposals. Done locally in `scripts/discover_clinic_google_links.py`: generic-label street-address links are not proposed as clinic profiles unless they carry a strong place identifier.
34. Add next-click guidance to Daniel's review brief. Done locally in `scripts/daniel_review_brief.py`: the brief now tells Daniel which panel buttons to use first, including the no-new-jobs guard near the review limit.
35. Align Google Maps completeness with the direct-clinic-link rule. Done locally in `/admin/`, `scripts/admin_digest.py` and `scripts/measure_profile_completeness.py`: generic searches, directions links and street-address place URLs stay pending instead of counting as complete.
36. Add explicit multi-location coverage. Done locally in `scripts/measure_location_coverage.py`: clinics with several stored locations can be audited for per-sede address, clinic Maps profile and Google reviews coverage without writing data.
37. Teach the shadow extractor to propose explicit locations. Done locally in `scripts/extract_clinic_profile_shadow.py`: clear street/postcode/city address patterns can become `locations` proposals, verified before review and never published automatically.
38. Keep public Google Maps links direct-only. Done locally in the static site build: public clinic pages no longer generate generic Google Maps searches, no longer link addresses unless a direct clinic profile URL exists, and keep location blocks free of decorative numeric badges.
39. Reduce team-page extraction noise. Done locally in `scripts/extract_clinic_profile_shadow.py`: WordPress menus, appointment CTAs and treatment-list tails are filtered before proposing professionals; the Arvila team page now yields 26 clean published professionals in a read-only live check.
40. Align Google-link discovery with direct-only Maps. Done locally in `scripts/discover_clinic_google_links.py`: clinics with generic stored Maps links remain eligible for discovery until a real clinic-profile URL exists.
41. Make the global plan panel easier to orient. Done locally in `/admin/`: the panel now opens with three plain checkpoints, `Ahora`, `Bloqueo` and `Después`, before the detailed roadmap.
42. Add compact Google-link discovery output. Done locally in `scripts/discover_clinic_google_links.py`: large dry-runs can now show only ready, empty-with-candidates and failed summaries without flooding the session.
43. Clean public multisede summaries. Done locally in the static site build: multi-location profiles no longer put every address in the hero or in one `Dirección principal`; the per-sede block carries each address.
44. Add transparency fields to profile completeness. Done locally in `/admin/`, `scripts/admin_digest.py` and `scripts/measure_profile_completeness.py`: years in practice, public specialist count, visible credentialing and public pricing are now measured as explicit pending/listo signals.
45. Prioritize transparency gaps in source shadow reviews. Done locally in `scripts/submit_source_shadow_reviews.py`: existing sources are now scored against the same transparency gaps before any review card is created.
46. Add compact output for source shadow reviews. Done locally in `scripts/submit_source_shadow_reviews.py`: read-only extraction checks can now show useful ready/skipped/failed summaries without exposing large verification payloads.
47. Reduce noisy source-shadow proposals. Done locally in `scripts/submit_shadow_extraction_review.py` and `scripts/submit_source_shadow_reviews.py`: transparency claims now map into editable fields, and source-based review cards only propose fields tied to current clinic gaps.
48. Verify transparency signals before review. Done locally in `scripts/verify_clinic_profile_shadow.py`: years/counts must be supported in source text, while credentialing and pricing need explicit registration-number or price signals before they are proposed.
49. Skip source-shadow work for already complete profiles. Done locally in `scripts/submit_source_shadow_reviews.py`: source batches now ignore clinics with no measured gaps before creating any review proposal.
50. Surface the recommended review group in quick filters. Done locally in `/admin/`: the review inbox now shows a `Grupo recomendado` chip so Daniel can jump into the highest-friction clinic group from the filter row.
51. Treat explicit locations as their own source-shadow gap. Done locally in `scripts/submit_source_shadow_reviews.py`: location proposals can still surface for multi-sede clinics even when a legacy top-level address already exists.
52. Suppress uppercase navigation text in professional extraction. Done locally in `scripts/extract_clinic_profile_shadow.py`: a live Neolife read-only check no longer proposes treatment-menu text as a professional.
53. Clean navigation boilerplate before source extraction. Done locally in `scripts/capture_source_snapshot.py`: repeated menu/header text is suppressed while useful contact links are preserved, so source excerpts reach clinic content earlier.
54. Extract decade-based practice years. Done locally in `scripts/extract_clinic_profile_shadow.py`: phrases such as "más de una década" now become `más de 10 años` for human review.
55. Require clinic context for ambiguous short Maps links. Done locally in `scripts/discover_clinic_google_links.py`: generic `maps.app.goo.gl` links stay pending unless the clinic name is visible around the link.
56. Split adjacent phone numbers. Done locally in `scripts/extract_clinic_profile_shadow.py`: two Spanish phone numbers written together are separated before review.
57. Add official location-page source discovery. Done locally in `scripts/discover_clinic_location_sources.py`: contact/location/sedes pages can be stored as internal sources without editing profiles or publishing.
58. Preserve file-like source URLs. Done locally in the source discoverers: `.html` pages keep their real URL instead of receiving a trailing slash that can create false 404s.
59. De-duplicate near-identical extracted locations. Done locally in `scripts/extract_clinic_profile_shadow.py`: repeated city suffixes and punctuation variants no longer create duplicate sede proposals.
60. Add compact source hydration output. Done locally in `scripts/hydrate_source_records.py`: large internal source-update runs can be summarized without dumping full snapshot payloads.
61. Stop rehydrating known-empty source excerpts. Done locally in `scripts/hydrate_source_records.py`: pages already marked as having no readable text no longer appear as pending forever.
62. Lock the public Google Maps rule into the project reference. Done locally:
    public pages, admin validation and documentation now treat Google Maps as a
    direct clinic-profile link only; if the profile link is unknown, the button
    remains absent/pending instead of using a street address.
63. Capture verified claims from hydrated official sources. Done locally in
    `scripts/capture_source_shadow_claims.py`: source excerpts can become
    internal `field_claims` without creating review cards, editing profile data
    or publishing public pages.
64. Reduce grouped review friction. Done locally in `/admin/`: when one clinic
    has several open profile-improvement cards, Daniel can load those proposed
    fields into one editor pass and resolve the grouped cards after one
    reviewed save.
65. Simplify the global-plan landing state. Done locally in `/admin/`: the
    first view now focuses on where we are and the next click, while the
    detailed roadmap stays available under a collapsed "Ver desglose del plan"
    section.
66. Add a built-site guard for public clinic UX. Done locally in
    `scripts/check_built_public_profile_ux.py`: after build, every clinic page
    is checked for no decorative location number badges and for clinic-profile
    Google Maps links only.
67. Clarify specialist coverage reporting. Done locally in
    `scripts/measure_specialist_coverage.py`: internal specialist signals are
    shown as detected names, cleaned of role/navigation noise and deduplicated
    before Daniel sees the next review target.
68. Align admin specialist wording with Daniel's review flow. Done locally in
    `/admin/`, `scripts/admin_digest.py` and the admin guide: specialist
    evidence is presented as detected names, counted from actual proposed
    names and excluding rejected/stale internal evidence.
69. Add a pending-locations loader to the clinic editor. Done locally in
    `/admin/`: open location proposals for the active clinic now appear as
    "Sedes detectadas" and can be loaded into the location editor for manual
    review before any save or publication.
70. Prevent weak Maps links from being saved as clinic profile links. Done
    locally in `/admin/`: proposed and manually saved Maps URLs are kept only
    when they look like a direct clinic profile; search, route or street-address
    links remain pending and are not written into public clinic data.
71. Make the global-plan next step more scannable. Done locally in `/admin/`:
    grouped review work now appears as a short route such as filter group, open
    one improvement, load grouped improvements, review and save.
72. Distinguish stored, proposed and internally detected locations. Done locally
    in `scripts/measure_location_coverage.py`: the read-only location report now
    shows explicit saved sedes, review-card proposals and internal location
    evidence separately, so the next safe action is clearer while the inbox is
    near full.
73. Make publication blockers visible in the control center. Done locally in
    `/admin/`: the clinic table now shows what is missing before publication,
    and the clinic editor has a "Para publicar" block with direct jumps to the
    missing fields.
74. Add a manageable control-center sidebar. Done locally in `/admin/`: the
    admin now has persistent navigation for Plan, Sistema, Revisión, Clínicas,
    Trabajos and Actividad, with compact status counters and a mobile
    horizontal layout.
75. Make pending public rebuilds explicit. Done locally in `/admin/` and
    `supabase/migrations/0023_public_site_rebuild_pending_control.sql`: the
    system now tracks the last saved public change separately from the last
    Netlify rebuild request, shows when saved edits are not online yet, and
    gives Daniel a single "Actualizar web ahora" action for batched publishing.
76. Add a public-site freshness diagnostic. Done locally in
    `scripts/check_public_site_freshness.py`: it compares the public Supabase
    clinic feed with the currently deployed clinic pages so stale production
    pages like a not-yet-rebuilt Monarka profile can be identified without
    editing data or triggering Netlify.
77. Wire public freshness into the CTO cycle. Done locally in
    `scripts/run_cto_shadow_cycle.py`: unattended or manual CTO runs can now
    include a read-only "saved data vs public page" check and report a clear
    desfase before Daniel reviews more clinics.
78. Add per-clinic public sync guidance. Done locally in `/admin/`: the clinic
    editor now tells Daniel whether that specific saved ficha is unpublished,
    still unsaved, pending the next public rebuild or already in sync with the
    last known web update.
79. Clarify candidate vs existing-ficha review context. Done locally in
    `/admin/`: review cards now explain whether detected data belongs to a
    candidate that is not yet public or to an existing clinic profile proposal,
    including why proposed specialists do not appear online until Daniel saves
    the ficha.
80. Clean specialist coverage examples. Done locally in
    `scripts/measure_specialist_coverage.py`: internal reports now suppress
    specialty/menu fragments and label weak signals as not having a clear
    professional name, so Daniel is not shown specialties as if they were
    people.
81. Surface internal location evidence in the clinic editor. Done locally in
    `/admin/`: location claims stored in `field_claims` now appear beside open
    location proposals as "Sedes detectadas", can be loaded into the form for
    manual review, and still require Daniel to save before anything public
    changes.
82. Add publication-readiness filtering to the clinic table. Done locally in
    `/admin/`: Daniel can filter clinic records by no required blockers,
    missing required fields, visible profiles with pending work, or profiles
    that are still not public.
83. Add a per-clinic publication readiness diagnostic. Done locally in
    `scripts/clinic_publication_readiness.py`: CTO runs can ask why a specific
    clinic cannot be made visible yet and get the missing required fields
    without editing Supabase or triggering Netlify.
84. Tighten the review quick-action strip. Done locally in `/admin/`: the
    priority action and secondary shortcuts are laid out in a stable grid and
    collapse cleanly on mobile, reducing the scattered-button effect in the
    control center.
85. Make stale public fichas easier to understand. Done locally in `/admin/`:
    when a clinic was edited after the last public-site rebuild, the editor now
    says plainly that the data is saved and the missing public change is a web
    regeneration issue, not a failed save.
86. Translate public freshness mismatches into a practical reason. Done locally
    in `scripts/check_public_site_freshness.py`: stale profile reports now say
    that Supabase has data not yet incorporated by the published site, so the
    next action is clearer without comparing multiple diagnostics.
87. Make the control sidebar act like a work-mode switch. Done locally in
    `/admin/`: the side menu now opens one major section at a time, with a
    `Todo` option for the old long view, so the control center is less
    overwhelming on desktop and mobile.
88. Show the first publication blocker directly in the clinic table. Done
    locally in `/admin/`: the "Falta para publicar" column now names the first
    missing field, such as Google Maps or Dirección, instead of only showing a
    generic count.
89. Include public-site publication state in Daniel's brief. Done locally in
    `scripts/daniel_review_brief.py`: the plain-Spanish review brief now says
    whether the web has saved changes pending to appear online, keeping cases
    like Monarka visible without a separate diagnostic.
90. Let public freshness diagnostics accept normal clinic names. Done locally in
    `scripts/check_public_site_freshness.py`: CTO checks can use
    `--clinic "Monarka"` or `--clinic "Rose Bar"` instead of requiring Daniel
    or the operator to know the exact slug.
91. Pass normal clinic names through the CTO cycle freshness check. Done locally
    in `scripts/run_cto_shadow_cycle.py`: unattended diagnostics can now use
    `--public-freshness-clinic "Monarka"` while the exact slug option remains
    available for automation.
92. Add a plain next step to per-clinic publication diagnostics. Done locally in
    `scripts/clinic_publication_readiness.py`: reports now say the first field
    Daniel should complete before making a draft visible, or point to public
    freshness if a published clinic has no required blockers.
93. Make clinic-name diagnostics tolerant of human spelling. Done locally in
    `scripts/clinic_publication_readiness.py` and
    `scripts/check_public_site_freshness.py`: names now match through spaces,
    hyphens and accents, so "Rose Bar" can find "RoseBar".
94. Add per-clinic specialist next steps. Done locally in
    `scripts/measure_specialist_coverage.py`: missing-specialist rows now say
    whether to consolidate open review cards, prepare a proposal from internal
    names or first find a public team page.
95. Refine Codex's global next-work signal for specialists. Done locally in
    `scripts/global_plan_status.py`: when specialist review cards already exist,
    the global plan now points Codex toward improving their review/consolidation
    flow instead of looking for more team pages.
96. Add per-sede next steps to location coverage. Done locally in
    `scripts/measure_location_coverage.py`: location reports now say the next
    safe action for each pending sede, including the direct Google Business
    profile requirement and keeping generic Maps searches or address links
    pending.
97. Add a combined clinic visibility diagnostic. Done locally in
    `scripts/clinic_public_visibility_report.py`: CTO checks can now explain
    whether a clinic is missing from the public site because it is not public,
    has publication blockers, or is saved in Supabase but waiting for a public
    rebuild. The report stays read-only and groups stale fields by category.
98. Reduce review quick-action noise in the control center. Done locally in
    `/admin/`: the review area now has one "Qué hacer ahora" lead with the
    clinic/context name, while secondary buttons stay short and grouped so the
    panel is easier to scan on desktop and mobile.
99. Wire clinic visibility diagnostics into the CTO cycle. Done locally in
    `scripts/run_cto_shadow_cycle.py`: optional cycle runs can now include
    `--clinic-visibility --clinic-visibility-clinic "Monarka"` to explain one
    clinic's public visibility state without publishing, editing data or
    exposing long professional/team payloads.
100. Explain rejected Google Maps candidates. Done locally in
     `scripts/discover_clinic_google_links.py`: dry runs now keep a compact
     rejection reason when a Maps candidate is found but not safe enough to
     propose, for example because it looks like a street address, a short link
     without clinic context or competing ambiguous candidates.
101. Show next steps for partially covered specialist profiles. Done locally in
     `scripts/measure_specialist_coverage.py`: clinics like Arvila that already
     have some specialists published but more names detected now show the
     consolidation step instead of looking finished.
102. Explain skipped source-shadow work as a next action. Done locally in
     `scripts/submit_source_shadow_reviews.py`: compact source reports now say
     whether Daniel should open an existing review, consolidate a clinic group,
     use the already selected source in the batch or look for a more specific
     official source.
103. Repair specialist pending evidence in the clinic editor. Done locally in
     `/admin/`: specialist suggestions now come from specialist review cards and
     internal professional claims, while location evidence remains separate; the
     panel refreshes after claims load and still requires manual save before
     anything appears publicly.
104. Add read-only specialist reconciliation. Done locally in
     `scripts/specialist_review_reconciliation.py`: one clinic can now show
     published specialists, specialists proposed in open cards, internal
     detected names, duplicates already represented and the next manual review
     step without editing Supabase.
105. Align the admin global plan with specialist review reality. Done locally in
     `/admin/`: when specialist cards already exist, Codex work is described as
     consolidating proposals rather than finding more team pages, keeping the
     center of control closer to Daniel's real next action.
106. Wire specialist reconciliation into CTO cycle. Done locally in
     `scripts/run_cto_shadow_cycle.py`: optional cycle runs can now include a
     compact specialist reconciliation for one clinic or a small visible-clinic
     batch without exposing long professional lists in the automatic log.

## Daniel decision checkpoints

Ask Daniel only when needed for:

- Search/crawler provider choice or account.
- OpenAI/API production key.
- Email notification sender.
- Whether/when to enable any auto-publish category.
- Brand/editorial policy for how much team/pricing/treatment detail Vitalarga should display.
- Business decisions around clinic claim portal and outreach tone.
- Any hard limit listed in `docs/VITALARGA_LIMITES_OPERATIVOS.md`.

Everything else should be advanced directly and reported afterwards.
