# Enrichment claims capture

`scripts/capture_enrichment_review_claims.py` turns open
`clinic_profile_enrichment` review cards into internal evidence:

- `source_records` for the proposal source URLs;
- `field_claims` for every proposed field;
- an audit event named `enrichment_review_claims_captured`;
- a marker on the review payload so it is not captured again by default.

It does not edit `clinics.current_data`, resolve reviews or publish pages.

## Dry run

```bash
python3 scripts/capture_enrichment_review_claims.py
```

## Apply

```bash
python3 scripts/capture_enrichment_review_claims.py --apply
```

Claims that match an active human field lock are stored with
`human_locked = true`, so later publication rules can keep Daniel's manual value
safe.
