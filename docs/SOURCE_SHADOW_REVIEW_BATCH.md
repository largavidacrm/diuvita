# Source shadow review batch

`scripts/submit_source_shadow_reviews.py` runs the existing shadow extraction
and verification chain against saved clinic sources.

The batch prioritizes visible clinics with more measured public fields pending
before older or more complete profiles. When specialists are missing, official
team/about pages and URLs that look like equipo, profesionales, doctors or team
pages move ahead of generic home/service pages. Existing open cards for the
same source are still skipped unless `--replace-existing` is used. By default it
also avoids creating more than one open enrichment card for the same clinic, so
Daniel's inbox stays reviewable.

It is a bridge toward the autonomous clinic loop:

```text
saved clinic source
  -> fetch current page
  -> extract profile claims
  -> verify claims
  -> apply deterministic rules
  -> create an internal clinic_profile_enrichment review card
```

Default mode is dry-run:

```bash
python3 scripts/submit_source_shadow_reviews.py
```

Create internal review cards:

```bash
python3 scripts/submit_source_shadow_reviews.py --apply
```

Focus one clinic:

```bash
python3 scripts/submit_source_shadow_reviews.py --clinic-slug sensabell
```

Refresh an existing open card for the same source:

```bash
python3 scripts/submit_source_shadow_reviews.py --clinic-slug sensabell --replace-existing --apply
```

Allow multiple open cards for the same clinic only when deliberately comparing
several sources:

```bash
python3 scripts/submit_source_shadow_reviews.py --allow-multiple-open-clinic-reviews --apply
```

The safe CTO cycle can include this batch when explicitly requested:

```bash
python3 scripts/run_cto_shadow_cycle.py --source-shadow-limit 3
```

Safety boundaries:

- no clinic records are edited;
- no public pages are published;
- existing open review cards are skipped by default;
- one open enrichment card per clinic is the default;
- generated payloads stay inside internal review cards;
- Daniel still reviews and saves manually in `/admin/`.
