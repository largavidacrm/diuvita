# Shadow extraction review submission

This connects the local chain to the admin inbox:

```text
source URL
  -> snapshot
  -> extract claims
  -> verify claims
  -> rules decisions
  -> internal review card
```

Current implementation:

- `scripts/submit_shadow_extraction_review.py`
- `scripts/submit_source_shadow_reviews.py` for saved-source batches
- `scripts/test_submit_shadow_extraction_review.py`
- `scripts/test_submit_source_shadow_reviews.py`

It creates `clinic_profile_enrichment` review cards for existing clinics.

It does not update clinic records or publish pages.

## Example

Dry run:

```bash
python3 scripts/submit_shadow_extraction_review.py \
  --clinic-slug monarka-clinic \
  --url https://monarkaclinic.com/clinica-longevidad-barcelona/
```

Create the internal review card:

```bash
python3 scripts/submit_shadow_extraction_review.py \
  --clinic-slug monarka-clinic \
  --url https://monarkaclinic.com/clinica-longevidad-barcelona/ \
  --apply
```

Daniel still reviews and saves manually in `/admin/`.

## Batch from saved sources

Dry run:

```bash
python3 scripts/submit_source_shadow_reviews.py
```

Create internal cards:

```bash
python3 scripts/submit_source_shadow_reviews.py --apply
```

Existing open cards for the same source are skipped unless `--replace-existing`
is passed. Existing open enrichment cards for the same clinic also block new
cards by default, even if the source URL is different, so Daniel does not receive
several competing proposals for the same Vitalarga profile.

Allow multiple open cards for one clinic only when deliberately comparing
several sources:

```bash
python3 scripts/submit_shadow_extraction_review.py \
  --clinic-slug monarka-clinic \
  --url https://monarkaclinic.com/clinica-longevidad-barcelona/ \
  --allow-multiple-open-clinic-reviews \
  --apply
```
