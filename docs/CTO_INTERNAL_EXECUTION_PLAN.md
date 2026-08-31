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
- Admin system status and review inbox show the concrete priority review first, while clinic workgroups remain available as secondary context for clustered cards and future LLM assistance.
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
50. Keep clinic workgroup signals available without crowding the review inbox. Done locally in `/admin/`: grouped review pressure still informs internal prioritization and future LLM assistance, but the visible inbox stays focused on filters, rows and one `Revisar` button per proposal.
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
107. Add read-only Google-link review reconciliation. Done locally in
     `scripts/google_link_review_reconciliation.py`: open Google Maps/review
     cards can now be inspected for direct clinic-profile links, unsafe
     search/route/address links and the next manual validation step without
     editing clinics or creating more review cards.
108. Wire Google-link reconciliation into CTO cycle. Done locally in
     `scripts/run_cto_shadow_cycle.py`: optional cycle runs can now include a
     compact Google-link review summary, showing direct-profile readiness or
     unsafe Maps cards without printing long URLs or review payloads.
109. Compact the review workbench UX. Done locally in `/admin/`: the review
     panel now shows the recommended action before filters, keeps action titles
     short, moves long clinic/review names into detail copy and uses a stable
     button grid that stays readable on mobile.
110. Summarize specialist reconciliation batches. Done locally in
     `scripts/specialist_review_reconciliation.py`: specialist reports now show
     aggregate pending-name/card counts and compact source URLs per review card,
     so Daniel can see why names are proposed without publishing them.
111. Make weak Google Maps entries visible before saving. Done locally in
     `/admin/`: the clinic editor now warns when a Maps field contains a search,
     route, street-address page or non-Maps URL, focuses the problematic field
     and blocks saving until it is removed or replaced with the clinic's direct
     Google Business/Profile URL.
112. Make review workgroups visible as clinic cases. Done locally in `/admin/`:
     the review inbox now shows a case-oriented panel above filters with the
     recommended clinic group, card counts, suggested order and direct actions
     to work the case or return to the full inbox.
113. Surface saved-but-not-public clinic edits in the clinic table. Done locally
     in `/admin/`: visible fichas whose latest edit is newer than the last public
     web update now show a "Pendiente de web" state and can be filtered as
     "Pendientes de web pública", making cases like Monarka understandable before
     opening the editor.
114. Explain proposal-only specialist cards in the review table. Done locally in
     `/admin/`: review rows with specialist proposals now show a short second
     line clarifying that names are internal proposals and are not published
     automatically, while Google Maps rows remind Daniel to accept only the real
     clinic profile.
115. Make public freshness reports easier to scan. Done locally in
     `scripts/check_public_site_freshness.py`: stale public-page checks now
     summarize affected field groups, such as contact, specialists or
     technology, before showing individual examples.
116. Make per-clinic publication blockers actionable. Done locally in
     `scripts/clinic_publication_readiness.py`: readiness reports now list every
     missing publication blocker with a plain-language place to fix it in the
     admin, including the direct-clinic Google Maps rule and blocking-claim
     review step.
117. Add review-backlog pressure to location coverage. Done locally in
     `scripts/measure_location_coverage.py`: sede reports now show open review
     pressure and defer turning internal location detections into new review
     cards when the bandeja is close to the safe-write limit.
118. Add clinic-focused review backlog reports. Done locally in
     `scripts/review_backlog_brief.py`: the read-only backlog brief now accepts
     `--clinic` and, when focused, shows the concrete cards in that clinic case
     so Daniel can work related clinic-case groups together.
119. Update Daniel's admin guide for the new review workflow. Done locally in
     `docs/DANIEL_ADMIN_GUIDE.md`: the guide now explains the case-recommended
     review panel, proposal-only specialist rows, the "Pendientes de web
     pública" clinic filter and the meaning of "Pendiente de web".
120. Add source and duplicate-awareness to specialist reconciliation. Done
     locally in `scripts/specialist_review_reconciliation.py`: specialist
     reports now show how many review cards have a clear source, how many cards
     contain names not yet in the ficha and how many proposed names are already
     represented, without publishing any professional data.
121. Simplify location editing in the admin. Done locally in `/admin/`: the
     primary location now lives in the main address, Google Maps and Google
     reviews fields, while the location editor shows only additional sedes. The
     saved structured location data is still preserved for public pages and
     multi-location clinics.
122. Surface source clarity on specialist review rows. Done locally in
     `/admin/`: review rows with proposed specialists now show whether a source
     is visible or still pending, so Daniel can prioritize review quality
     without treating names as automatically publishable.
123. Reconcile specialist claim sources. Done locally in
     `scripts/specialist_review_reconciliation.py`: when a specialist review
     card lacks its own source URL, the read-only report now also shows source
     URLs linked to internal specialist claims, making cases like Neolife
     reviewable without publishing names automatically.
124. Repair IMDA-style source extraction. Done locally in
     `scripts/capture_source_snapshot.py`, `scripts/extract_clinic_profile_shadow.py`
     and team-source discovery: Elementor/WordPress pages no longer hide visible
     body/footer text behind void menu controls, visible contact labels win over
     placeholder `mailto:`/`tel:` targets, split Spanish addresses such as IMDA's
     Goya address become internal location proposals, multiple clear phone
     numbers can map to principal/fixed/mobile review fields, and checked common
     team paths such as `/equipo/` are prioritized when they provide cleaner
     public professional proposals.
125. Add read-only consolidation for duplicate enrichment cards. Done locally in
     `scripts/consolidate_profile_enrichment_reviews.py` and the CTO cycle:
     duplicate `clinic_profile_enrichment` cards for the same clinic can now be
     merged into one proposed field set, with source counts, already-present
     fields and scalar conflicts shown before Daniel reviews the affected
     proposals one by one. It does not resolve cards, edit clinics or publish
     anything.
126. Block weak phone proposals in the admin editor. Done locally in `/admin/`:
     phone fields now warn when a value does not look like a plausible Spanish
     contact number, grouped enrichment proposals normalize aliases such as
     `phone`/`telephone` to `telefono`, and saving is stopped until suspicious
     contact values are corrected or removed. This prevents IDs such as medical
     registration numbers from being closed as public phone data.
127. Surface clinic claim requests as human-only review work. Done locally in
     `/admin/`, `scripts/admin_digest.py`, `scripts/daniel_review_brief.py` and
     `scripts/review_backlog_brief.py`: `clinic_claim_request` cards now have a
     dedicated filter, priority path and plain safety copy explaining that they
     do not verify identity, grant access, edit clinic data or publish anything.
     They open the existing clinic context for Daniel's decision instead of
     being treated like draft-creation cards.
128. Warn about weak contact data before grouped proposal loading. Done locally
     in `/admin/`: related review groups now show a **Contacto dudoso** warning
     when enrichment cards contain phone-like values that do not look like
     plausible Spanish contact numbers, so Daniel sees the issue before
     approving the affected proposal.
129. Split clear multi-phone enrichment proposals. Done locally in `/admin/`
     and `scripts/consolidate_profile_enrichment_reviews.py`: when a grouped
     proposal contains multiple clear Spanish phone numbers in one contact
     field, the system separates them into reviewable phone fields such as
     principal/fixed/mobile instead of leaving a mixed value. The result still
     requires Daniel's manual review and save.
130. Add a safe local dashboard server helper. Done locally in
     `scripts/serve_local_dashboard.py`: the local review URL can be served from
     `dist/` only, defaults to `127.0.0.1:8765`, blocks network-exposed hosts
     and avoids serving the worktree root or `.env`.
131. Reduce clinic-name bias in Daniel's review brief. Done locally in
     `scripts/daniel_review_brief.py`: when a higher-priority item such as a
     clinic claim request is open, secondary profile and duplicate-backlog
     signals stay aggregate instead of repeatedly naming a lower-priority
     clinic.
132. Make grouped enrichment payload size visible before loading it. Done
     locally in `/admin/`: the clinic-case panel can highlight how many
     proposed locations, phone numbers and specialists a high-volume case like
     IMDA contains, while keeping the human decision sequential and without
     auto-saving or publishing data.
133. Make focused backlog case cards distinguishable without exposing payloads.
     Done locally in `scripts/review_backlog_brief.py`: clinic-focused reports
     now show safe proposed-field labels and counts of sedes, phones and
     specialists per card, while stripping the raw review payload from text and
     JSON output.
134. Add a private export bridge for specialist evidence. Done locally in
     `scripts/export_specialist_claim_proposals.py`: internal specialist claims
     can be turned into a reviewable proposal batch without writing Supabase,
     editing clinics or publishing names. The normal output shows counts only,
     JSON/output files are explicit, and repo-local output is blocked by
     default to avoid committing unpublished proposal payloads.
135. Wire private specialist proposal readiness into the CTO cycle. Done
     locally in `scripts/run_cto_shadow_cycle.py`: optional read-only runs can
     include `--specialist-claim-proposals`, compact raw proposal JSON out of
     the cycle output and show Daniel only how many private specialist proposal
     batches are ready or skipped because cards already exist.
136. Let publication readiness run as a global read-only summary. Done locally
     in `scripts/clinic_publication_readiness.py`: the diagnostic can now run
     without a clinic query, sort non-archived fichas by required blockers and
     report measured counts, visible counts, ready fichas, blocking claims and
     top missing fields before any per-clinic detail.
137. Add publication-readiness visibility to CTO cycle runs. Done locally in
     `scripts/run_cto_shadow_cycle.py`: optional `--publication-readiness` and
     `--publication-readiness-clinic` runs now add compact readiness status to
     the Daniel brief without editing clinics, publishing pages or dumping full
     match rows.
138. Surface publication-readiness status in the admin control center. Done
     locally in `/admin/`: the system panel now shows ready-to-publish fichas,
     fichas with required blockers, the most common blocker and the next ficha
     to work, reusing the same direct Google Maps and blocking-claim rules as
     the editor.
139. Add publication-readiness guidance to Daniel's brief. Done locally in
     `scripts/admin_digest.py` and `scripts/daniel_review_brief.py`: the
     read-only digest now separates required publication blockers from broader
     profile-completeness gaps, showing ready fichas, the main blocker and the
     next ficha to work without creating review cards or exposing proposal
     payloads.
140. Add publication-readiness guidance to the global plan snapshot. Done
     locally in `scripts/global_plan_status.py`: the roadmap snapshot now shows
     ready-to-publish counts, the main required blocker and the next
     publication target, and routes Codex toward Google Maps review work when
     that is the leading publication blocker.
141. Add compact Google-link reconciliation output. Done locally in
     `scripts/google_link_review_reconciliation.py`: manual Google Maps review
     checks can now print counts and next steps without dumping long Google URLs,
     while the full mode remains available for deliberate link-by-link review.
142. Add safe compact Google-link discovery output. Done locally in
     `scripts/discover_clinic_google_links.py`: dry-run discovery can now report
     ready, rejected and failed clinic counts without printing proposed Google
     URLs, keeping review logs small and safe while full output remains
     available for deliberate operator inspection.
143. Make clinic proposal validation sequential. Done locally in `/admin/`:
     opening a review card now shows only the affected clinic, proposal type,
     current relevant data, proposed change, evidence and essential warnings,
     then offers exactly Approve, Reject or Modify. Finishing any decision
     resolves that one card and advances to the next open proposal, while
     group-analysis helpers remain available for future LLM-assisted
     prioritisation without grouping human decisions.
144. Add LLM-ready decision packets for review proposals. Done locally in
     `scripts/review_proposal_decision_packets.py`: open `review_queue` cards
     can be converted into read-only one-card/one-decision packets with clinic
     identity, current/proposed field shapes, evidence hosts and warnings. The
     default output omits raw values and full URLs; explicit value mode is
     reserved for local assisted preparation. Each packet carries a schema
     version, allowed actions and editable fields, and never resolves cards,
     edits clinics or publishes pages.
145. Make Daniel's review brief safer for automation. Done locally in
     `scripts/daniel_review_brief.py`: JSON output now omits operator/account
     fields by default for LLM or automation plumbing, with an explicit local
     debugging flag when those fields are genuinely needed.
146. Add a guard for future LLM review suggestions. Done locally in
     `scripts/validate_review_decision_suggestion.py`: advisory LLM output can
     be validated against a one-card decision packet before being shown or used,
     blocking publication/control keys, mismatched review ids and field changes
     outside `editable_fields`, plus weak Google Maps and doubtful phone
     modifications. The guard has no Supabase access and writes no data.
147. Standardize future LLM review prompts. Done locally in
     `scripts/prepare_review_decision_llm_prompt.py`: a one-card decision
     packet can become a safe prompt bundle with system/user messages, expected
     JSON schema and validator reference. The default prompt strips raw values
     even if the packet input contains them; full values require an explicit
     local flag and still produce no writes.
148. Make open reviews clinic-centered. Done locally in `/admin/`: after Daniel
     opens a review, the middle column switches from the queue to the selected
     clinic ficha, while the right column stays focused on the single proposed
     change, evidence, warnings and Approve/Reject/Modify actions. The
     underlying one-card decision packet structure remains intact for future
     LLM-assisted preparation.
149. Ignore invalid downloaded logo assets. Done locally in `build.py` and
     `scripts/fetch_logos.py`: logo files that are actually HTML or challenge
     pages are no longer treated as valid images. Tiara Health remains in the
     guide, but its blocked logo download is marked invalid until a real
     official logo asset is available.
150. Add local release-readiness reporting. Done locally in
     `scripts/release_readiness_report.py`: Codex can now answer whether a
     change is only local or also visible in production using read-only local
     markers, git state and optional public health checks. The report never
     pushes, deploys, edits Supabase or triggers Netlify.
151. Simplify review decisions and preserve LLM handoff signals. Done locally
     in `/admin/`: the review queue no longer shows oversized recommendation
     panels by default, the left control menu can be collapsed, clinic claim
     requests can register a private internal contact in the clinic record,
     quality audits can open the clinic editor at the missing field, and Daniel
     can attach an official URL as a queued `EXTRACT_CLINIC_PROFILE` job for
     later agent extraction. None of this publishes data or grants clinic
     access automatically.
152. Add a worker for review-supplied source URLs. Done locally in
     `scripts/process_extract_clinic_profile_jobs.py`: queued
     `EXTRACT_CLINIC_PROFILE` jobs created from a review can now fetch the
     supplied source, run the shadow extractor/verifier, filter findings to the
     fields requested by that review, create a new enrichment card when useful
     and mark the job completed. It never edits clinic data or publishes.
153. Preserve manual-review targets for future LLM assistance. Done locally in
     `scripts/review_proposal_decision_packets.py`,
     `scripts/prepare_review_decision_llm_prompt.py` and
     `scripts/validate_review_decision_suggestion.py`: quality-audit cards that
     only name missing fields now carry safe admin targets and bounded
     source-job fields, so a future LLM can suggest "open this field manually"
     without inventing values, writing Supabase data or changing publication.
154. Prioritize concrete review decisions over clinic groups. Done locally in
     `/admin/`, `scripts/admin_digest.py`, `scripts/daniel_review_brief.py`,
     `scripts/global_plan_status.py` and `scripts/run_cto_shadow_cycle.py`:
     Daniel's first action now opens the highest-priority actionable review
     card, while clinic groups such as repeated Sensabell work stay visible as
     secondary backlog context and LLM-ready signals.
155. Make review-supplied source jobs legible for Daniel and LLM-ready. Done
     locally in `/admin/`: quality-audit cards now say **Dile al agente dónde
     mirar**, suggest the right kind of official page for the missing field
     (for example team/specialists pages), and queue source jobs with explicit
     human-supplied-source metadata, requested field labels and a
     proposal-only output contract.
156. Make quality-audit field actions explicitly manual. Done locally in
     `/admin/`: pending-field cards now present **Revisión manual** as the
     visible action instead of the vague "Completar en ficha" wording, while
     still opening the clinic editor focused on the exact missing field. The
     review-source job panel also shows the remaining safe margin before the
     preventive backlog pause and respects that pause for agent/LLM source
     jobs.
157. Add manual-review context inside the clinic editor. Done locally in
     `/admin/`: when Daniel opens a quality-audit field through **Revisión
     manual**, the clinic editor shows a compact banner with the exact field,
     the pending issue and a button to refocus that field. Saving still resolves
     only that review card and advances to the next pending proposal.
158. Carry manual-review context into LLM decision packets. Done locally in
     `scripts/review_proposal_decision_packets.py` and
     `scripts/prepare_review_decision_llm_prompt.py`: quality-audit packets now
     include safe `manual_review_context` metadata with the display title,
     admin target, issue label, operator route and no-invention boundary. This
     preserves future LLM assistance without allowing writes or invented field
     changes.
159. Align review briefs with manual-review wording. Done locally in `/admin/`,
     `scripts/admin_digest.py`, `scripts/daniel_review_brief.py` and
     `scripts/global_plan_status.py`: quality-audit priorities now read as
     **Revisión manual de fichas** and legacy stored titles are displayed as
     **Revisión manual:** in Daniel-facing outputs, without rewriting Supabase
     review records.
160. Align read-only backlog guard copy with the preventive pause. Done locally
     in `scripts/admin_digest.py`, `scripts/daniel_review_brief.py` and
     `scripts/global_plan_status.py`: briefs now distinguish normal margin,
     short margin, preventive pause and hard stop, including how many proposals
     remain before pause. This matches the admin source/job controls and writes
     no Supabase data.
161. Extend release-readiness checks for manual-review changes. Done locally in
     `scripts/release_readiness_report.py`: local-vs-production reporting now
     checks the admin manual-review banner, manual-review wording and LLM
     `manual_review_context`, plus the built admin marker after `build.py`.
162. Normalize quality-audit labels to manual-review language. Done locally in
     `/admin/`, `scripts/admin_digest.py`, `scripts/daniel_review_brief.py`,
     `scripts/review_backlog_brief.py` and review decision packets: Daniel-facing
     filters, summaries, workgroups, dismissal notes and LLM packet labels now
     say **Revisión manual** instead of **Auditoría**, while the underlying
     technical `clinic_quality_audit` type remains unchanged.
163. Make manual review open the exact clinic field. Done locally in `/admin/`:
     quality-review cards with a known missing field now open the clinic editor
     directly at that field, keep the manual-review banner visible, and leave
     source-change/proposal cards on the single-decision approve/reject/modify
     path.
164. Normalize dashboard visual scale. Done locally in `/admin/`: shared
     typography tokens now control labels, controls, panel copy, card titles and
     metric numbers across the control center, the page title is less oversized,
     and the review priority filter uses a shorter label to avoid clipped text.
165. Keep review columns stable. Done locally in `/admin/`: the review queue no
     longer expands into a one-column, full-width mode when no proposal is
     selected, so Daniel always sees the pending list as part of the review
     workspace instead of feeling the ficha columns disappeared.
166. Add LLM source handoff inside manual reviews. Done locally in `/admin/`:
     when a manual review opens the clinic editor at a missing field, Daniel can
     also paste an official clinic URL in the same review banner so the agent
     creates a new internal proposal for those fields without publishing or
     saving data automatically.
167. Scope manual-review source jobs to the active field. Done locally in
     `/admin/`: source URLs submitted from the manual-review banner now target
     the field Daniel is editing first, falling back to the full card only when
     no unique field target is available.
168. Preserve scoped source handoff in LLM packets. Done locally in
     `scripts/review_proposal_decision_packets.py` and
     `scripts/prepare_review_decision_llm_prompt.py`: manual-review packets now
     describe the **Pasar URL al agente** route, the official-source requirement
     and the `primary_target_first` scope so future LLM assistance matches the
     admin workflow.
169. Persist source-job scope metadata from the admin. Done locally in
     `/admin/`: review-supplied `EXTRACT_CLINIC_PROFILE` jobs now carry
     `target_scope`, `ui_route`, `primary_requested_fields` and
     `primary_requested_field_labels`, so future workers can respect Daniel's
     exact manual-review field instead of broadening the source task.
170. Keep review columns visible on desktop/tablet. Done locally in `/admin/`:
     the review queue now keeps its two-column workspace until narrow mobile
     widths and shows a compact right-side placeholder before a proposal is
     selected, so the dashboard does not look like it has fallen back to a
     full-width list.
171. Preserve source-job scope in generated proposals. Done locally in
     `scripts/process_extract_clinic_profile_jobs.py`: when Daniel passes an
     official URL to the agent from a manual review, the resulting internal
     proposal keeps `primary_requested_fields`, `primary_requested_field_labels`,
     `target_scope` and `ui_route`, so the future LLM workflow stays focused on
     the exact field Daniel wanted to inspect.
172. Guard public logos against broken images. Done locally in `build.py`: logo
     chips and clinic-card logos now include a text fallback that appears if an
     approved image asset fails to load, preventing broken-image icons such as
     the Tiara Health case Daniel spotted.
173. Harden LLM suggestion validation. Done locally in
     `scripts/validate_review_decision_suggestion.py`: future LLM suggestions
     now reject unexpected keys such as stray `source_url` fields and return
     the validated manual admin target when `modify` means opening a field
     manually, keeping source jobs separate from decision suggestions.
174. Show Daniel-supplied source scope in review evidence. Done locally in
     `/admin/`: review cards created from an operator-supplied URL now show a
     compact internal origin line with the requested field and
     `primary_target_first` scope, so Daniel can see why that evidence is being
     considered without opening other queue context.
175. Expose source-job context in LLM decision packets. Done locally in
     `scripts/review_proposal_decision_packets.py` and
     `scripts/prepare_review_decision_llm_prompt.py`: proposals generated from
     a Daniel-supplied URL now carry safe `source_job_context` metadata, so a
     future LLM can understand the original field request and source handoff
     without receiving write permission or broadening the review.
176. Make Google Maps review status explicit. Done locally in `/admin/` and LLM
     decision packets: Maps proposals now show a compact link verdict such as
     **Parece perfil directo** or **No guardar tal cual**, and packets carry a
     non-auto-publishable `google_maps_review` context so future assistance
     preserves the human Google Business/Profile check.
177. Resolve manual review cards field by field. Done locally in `/admin/`:
     when a quality/manual review contains several missing fields, saving the
     active field removes only that issue from the open card and then reopens
     the next pending field. If the active field is still incomplete, the card
     stays open instead of being silently resolved.
178. Audit old review cards for source-job context. Done locally in
     `scripts/audit_review_source_job_context.py`: open enrichment proposals can
     now be checked for LLM-source provenance, including whether missing context
     is recoverable from `agent_jobs` or must stay as purely manual review.
179. Include weak Maps proposals in the Google quick filter. Done locally in
     `/admin/`: the **Google Maps** filter now catches any proposed Maps or
     review-link URL, including links that later need rejection or correction,
     so dudosos do not hide outside Daniel's Maps review path.
180. Align the read-only digest with Maps review filtering. Done locally in
     `scripts/admin_digest.py`: Google Maps review counts now include weak or
     malformed proposed Maps URLs, while the save/publication guards still
     accept only real clinic Google Business/Profile links after human review.
181. Keep manual reviews sequential without losing columns. Done locally in
     `/admin/`: clicking **Revisar** on a manual review now opens the normal
     clinic-plus-decision workspace instead of jumping straight to the full
     clinic editor, shows only the next pending field, and keeps source handoff
     scoped to that visible field for future LLM assistance. The review table
     also clamps long titles to keep row heights consistent.
182. Add a field-level order to duplicate-enrichment diagnosis. Done locally in
     `scripts/consolidate_profile_enrichment_reviews.py`: duplicate improvement
     groups now include a read-only `review_sequence` that prioritizes conflicts,
     weak phones, Google links and then other fields, so future LLM or operator
     flows can prepare the case without merging multiple admin decisions.
183. Structure Google Maps review decisions for future assistance. Done locally
     in `scripts/google_link_review_reconciliation.py`: open Google-link cards
     now expose `manual_decision_items` with the field, status, safe admin
     action and `safe_to_auto_publish: false`, preserving the rule that even
     direct-looking Google Business/Profile links require human confirmation
     before they enter a clinic ficha.
184. Structure specialist review decisions without exposing them by default.
     Done locally in `scripts/specialist_review_reconciliation.py`: specialist
     reports now expose manual per-card decision items with source presence and
     `safe_to_auto_publish: false`, plus a compact mode that hides professional
     names and URLs while still showing counts, source coverage and next action.
185. Keep the review workspace visibly sequential. Done locally in `/admin/`:
     the review area now has explicit queue, decision and clinic-edit layout
     modes, so the inbox remains a two-column work area on desktop and opening
     **Revisar** switches to clinic ficha plus one proposal decision instead of
     a full-width table.
186. Add specialist source handoff from review cards. Done locally in `/admin/`:
     specialist proposals without a clear source can accept a Daniel-supplied
     official team page URL, creating only a bounded specialist review job with
     `ui_route: "review_card_specialist_source_handoff"` and no permission to
     publish or update unrelated fields.
187. Add Google Reviews decision context for LLM assistance. Done locally in
     `scripts/review_proposal_decision_packets.py`: proposed Google review links
     now carry a read-only `google_reviews_review` block, separate from Google
     Maps profile validation, so future LLM help knows reviews must match the
     main clinic Google Business/Profile before Daniel saves them.
188. Add decision ordering to Google-link review diagnostics. Done locally in
     `scripts/google_link_review_reconciliation.py`: Google link reports now
     carry `manual_decision_sequence`, reviewing the clinic Google Maps profile
     before Google reviews while keeping every item `safe_to_auto_publish:
     false`.
189. Guard dashboard visual consistency. Done locally in `/admin/` and
     `scripts/test_admin_visual_consistency.py`: the review table now gives more
     width to the subject, keeps type/priority/date compact, aligns rows
     predictably and adds a local check so dashboard typography and card radii
     stay within the current design scale.
190. Make Google reviews dependency visible in the review card. Done locally in
     `/admin/`: if a proposal includes Google review links, the warning block now
     tells Daniel to confirm the real Google Maps clinic profile first and then
     confirm the reviews belong to that same profile.

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
