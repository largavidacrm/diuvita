# Shadow clinic profile extractor

`EXTRACT_CLINIC_PROFILE` starts as a conservative local tool before becoming a full AI worker.

Current implementation:

- `scripts/extract_clinic_profile_shadow.py`
- `scripts/enrich_candidate_review_from_url.py`
- `scripts/enrich_candidate_reviews_from_team_pages.py`
- `scripts/test_extract_clinic_profile_shadow.py`

It reads one public source page and returns:

- Compact source snapshot.
- Candidate profile hints.
- Field claims.
- Rules-engine decisions.
- Publicly listed specialists and clinical units when they are explicit enough.
- Clear published locations when the address pattern includes a street type and
  city or postcode.
- Visible contact fields from WordPress/Elementor-style pages even when the
  technical `mailto:` or `tel:` target contains template data.
- More than one clear public phone number, with fixed/mobile claims separated
  when the Spanish numbering pattern is unambiguous.
- Basic transparency hints when stated clearly: years in practice, public
  specialist count, visible professional credentialing and public pricing
  signals.
- Clinic name only when the page title looks like an actual clinic name, not a
  marketing sentence.

It does not publish anything.

For candidate clinics, a second official URL can enrich the same open review
card. This is useful when the initial discovery page describes the service but
the public team is listed on a separate page such as "Quiénes somos". The
enrichment keeps every source URL in the review and still requires human
validation before a draft is created.

`scripts/enrich_candidate_reviews_from_team_pages.py` applies the same idea in
batch. It looks for same-site links that clearly point to team/about pages and
updates only existing candidate review cards. Its default mode is a dry run.

`scripts/submit_source_shadow_reviews.py` prioritizes existing source records
against the same completeness gaps used by the admin dashboard, including
locations, specialists, years in practice, public specialist count, visible
credentialing and public pricing.

When it prepares a review card, it filters proposed form fields against the
clinic's current gaps, so repeated services or specialties do not become noisy
review work if those fields are already complete.
Explicit locations are treated as their own gap, so multi-location evidence is
not hidden just because the older top-level address field is filled.

Source-shadow batches skip profiles with no measured gaps, which keeps the
review inbox focused on incomplete records.

Use `--compact` for real read-only checks when the full verification payload
would be too noisy.

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

Starting with a simple deterministic extractor lets Vitalarga build the pipeline before depending on a stronger AI extraction model.

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
  professional titles (`Dr.`, `Dra.`, `Lic.`, `D.O.`) or name-role pairs inside
  explicit team sections, including pages where the name appears before a clear
  role such as medicina general, oncología integrativa, dermatología,
  fisioterapia, optometría, odontología or reception/admin team roles.
- It handles simple member-archive cards where the short name is repeated before
  the full public name, and removes nearby labels such as `Ver Curriculum` or
  secondary role fragments before proposing names.
- It skips common WordPress/navigation text and appointment CTAs before
  extracting team names, so menu items such as treatment names are not proposed
  as professionals.
- It rejects uppercase navigation words such as treatment, benefits, blog or
  program labels before treating a name-role pair as a professional.
- It only detects locations from clear address patterns, including compact
  Spanish addresses split across lines before the postcode/city. It does not
  invent sede names and it does not label locations as `Sede 1` or `Sede 2`.
- It does not infer years in practice from founding dates yet.
- It does not fetch or verify Google Maps profiles yet; those links are edited
  manually or proposed later from explicit sources.
- It should not decide final clinic names from generic page titles.
- It suppresses generic or marketing-like page titles instead of turning them
  into identity claims.
- All extracted claims start without independent verifier acceptance.
- The rules engine therefore sends them to review by default.
- Transparency verification is conservative: years/counts must be present in
  the source text, while public pricing and credentialing rely on explicit price
  and registration-number signals.

This is intentional. The extractor proposes; it does not decide.
