# Shadow clinic profile extractor

`EXTRACT_CLINIC_PROFILE` starts as a conservative local tool before becoming a full AI worker.

Current implementation:

- `scripts/extract_clinic_profile_shadow.py`
- `scripts/enrich_candidate_review_from_url.py`
- `scripts/test_extract_clinic_profile_shadow.py`

It reads one public source page and returns:

- Compact source snapshot.
- Candidate profile hints.
- Field claims.
- Rules-engine decisions.
- Publicly listed specialists and clinical units when they are explicit enough.
- Clinic name only when the page title looks like an actual clinic name, not a
  marketing sentence.

It does not publish anything.

For candidate clinics, a second official URL can enrich the same open review
card. This is useful when the initial discovery page describes the service but
the public team is listed on a separate page such as "Quiénes somos". The
enrichment keeps every source URL in the review and still requires human
validation before a draft is created.

For extraction, it reads a larger compact excerpt than the provenance snapshot
and also captures useful hidden contact links such as `mailto:`, `tel:` and
Instagram profile URLs. This improves internal proposals without storing or
publishing the full source page.

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
  doctor titles or name-role pairs inside explicit team sections, clinical
  units and known longevity keywords.
- It should not decide final clinic names from generic page titles.
- It suppresses generic or marketing-like page titles instead of turning them
  into identity claims.
- All extracted claims start without independent verifier acceptance.
- The rules engine therefore sends them to review by default.

This is intentional. The extractor proposes; it does not decide.
