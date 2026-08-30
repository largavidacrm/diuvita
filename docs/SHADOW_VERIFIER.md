# Shadow clinic profile verifier

`VERIFY_CLINIC_PROFILE` is the first prosecutor-style verifier.

Current implementation:

- `scripts/verify_clinic_profile_shadow.py`
- `scripts/test_verify_clinic_profile_shadow.py`

It reads extraction JSON from `scripts/extract_clinic_profile_shadow.py`, checks each claim against the source text and returns:

- Verified claims.
- Verifier verdicts.
- Verifier reasons.
- Rules-engine decisions.
- Summary counts.

It does not improve or rewrite the extractor result. It challenges it.

## Current behavior

- Website claims are accepted only when the host matches the source host.
- Email, phone and Instagram claims must appear explicitly.
- List claims are accepted only when every value is found explicitly.
- Weak or unsupported claims go to review or rejection.
- Rules still keep publication in review because auto-publish is off.

## Example

```bash
python3 scripts/test_verify_clinic_profile_shadow.py
python3 scripts/verify_clinic_profile_shadow.py data/extractions/example.json
```

This gives Vitalarga the first complete local chain:

```text
source -> snapshot -> extraction -> verification -> rules decisions
```
