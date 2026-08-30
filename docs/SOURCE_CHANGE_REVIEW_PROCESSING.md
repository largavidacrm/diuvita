# Source change review processing

`scripts/process_source_change_reviews.py` is the bridge from a changed source
to a new internal profile-enrichment proposal.

It reads open `source_change_detected` cards, fetches the changed source again,
runs the existing shadow extractor and verifier, and prepares a
`clinic_profile_enrichment` review payload for Daniel.

Default mode is dry-run:

```bash
python3 scripts/process_source_change_reviews.py --limit 3
```

Apply mode creates only internal review cards:

```bash
python3 scripts/process_source_change_reviews.py --limit 3 --apply
```

Safety boundaries:

- It does not edit `clinics.current_data`.
- It does not publish pages.
- It does not resolve the original source-change card.
- It carries the source-change material hints into the new proposal.
- If an open proposal already exists for the same clinic and source, apply mode
  refreshes that proposal instead of creating a duplicate.
- If another open enrichment proposal already exists for the same clinic, apply
  mode reuses that open clinic review instead of creating a parallel card.
- Daniel still decides whether any extracted change is saved.
