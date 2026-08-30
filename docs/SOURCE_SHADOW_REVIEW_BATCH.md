# Source shadow review batch

`scripts/submit_source_shadow_reviews.py` runs the existing shadow extraction
and verification chain against saved clinic sources.

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

Safety boundaries:

- no clinic records are edited;
- no public pages are published;
- existing open review cards are skipped by default;
- generated payloads stay inside internal review cards;
- Daniel still reviews and saves manually in `/admin/`.
