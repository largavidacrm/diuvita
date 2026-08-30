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
- `scripts/test_submit_shadow_extraction_review.py`

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
