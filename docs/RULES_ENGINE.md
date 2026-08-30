# Diuvita rules engine

The rules engine is the deterministic layer between AI output and publication.

The AI can:

- Discover a clinic.
- Extract a field.
- Verify or challenge a field.
- Provide source evidence and confidence.

The rules engine decides:

- `auto_accept`
- `review`
- `reject`

Default policy is conservative:

- Auto-publish is off.
- Low-risk accepted claims can become eligible for future auto-accept.
- Medium-risk claims stay in review by default.
- High-risk claims need stricter verification and usually human approval.
- Human-locked fields can never be overwritten automatically.

## Risk tiers

Low risk:

- Identity basics.
- Location.
- Official website.
- Public email.
- Public phone.
- Public Instagram.

Medium risk:

- Services.
- Clinical units.
- Diagnostics.
- Programs.
- Technologies.
- Publicly listed specialists.

High risk:

- Physician credentials.
- Prices.
- Treatments.
- Medical/evidence claims.
- Outcomes, guarantees or comparative quality claims.

## Current implementation

Code:

- `scripts/diuvita_rules.py`
- `scripts/test_diuvita_rules.py`
- `scripts/evaluate_claim_rules.py`
- `scripts/test_evaluate_claim_rules.py`

Example:

```bash
python3 scripts/test_diuvita_rules.py
python3 scripts/diuvita_rules.py claims.json
python3 scripts/evaluate_claim_rules.py --preview-low-risk-autopublish
```

The first useful integration point is `EXTRACT_CLINIC_PROFILE` and `VERIFY_CLINIC_PROFILE`: extracted claims should pass through `decide_claim()` before they create review items or publication candidates.

Stored `field_claims` can now be evaluated read-only with
`scripts/evaluate_claim_rules.py`. That report does not write to Supabase or
publish anything.
