# Blocking claim reviews

`scripts/submit_blocking_claim_reviews.py` turns blocking field claims into
internal `clinic_quality_audit` review cards.

It watches for claims that are:

- `conflict`;
- `rejected`;
- missing a linked source record.

It does not edit clinic profiles, publish clinics or resolve existing reviews.
It only creates or refreshes internal review cards so Daniel can inspect the
clinic and its evidence from `/admin/`.

## Run

Preview only:

```bash
python3 scripts/submit_blocking_claim_reviews.py
```

Create or refresh internal review cards:

```bash
python3 scripts/submit_blocking_claim_reviews.py --apply
```

The safe CTO shadow cycle runs this step after source-change processing.
