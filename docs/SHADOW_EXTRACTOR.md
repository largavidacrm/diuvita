# Shadow clinic profile extractor

`EXTRACT_CLINIC_PROFILE` starts as a conservative local tool before becoming a full AI worker.

Current implementation:

- `scripts/extract_clinic_profile_shadow.py`
- `scripts/test_extract_clinic_profile_shadow.py`

It reads one public source page and returns:

- Compact source snapshot.
- Candidate profile hints.
- Field claims.
- Rules-engine decisions.
- Publicly listed specialists and clinical units when they are explicit enough.

It does not publish anything.

## Why this exists

The target architecture needs a stable output shape:

```text
source page
  -> structured claims
  -> verification
  -> rules
  -> review or publication candidate
```

Starting with a simple deterministic extractor lets Diuvita build the pipeline before depending on a stronger AI extraction model.

## Example

```bash
python3 scripts/test_extract_clinic_profile_shadow.py
python3 scripts/extract_clinic_profile_shadow.py https://example.com/longevity
```

With `--write`, output goes under:

```text
data/extractions/
```

That folder is local/ignored by Git.

## Current limitations

- It only detects obvious contact details, public specialist names with clear
  doctor titles, clinical units and known longevity keywords.
- It should not decide final clinic names from generic page titles.
- All extracted claims start without independent verifier acceptance.
- The rules engine therefore sends them to review by default.

This is intentional. The extractor proposes; it does not decide.
