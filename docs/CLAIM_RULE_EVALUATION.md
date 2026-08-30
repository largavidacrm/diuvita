# Claim rule evaluation

`scripts/evaluate_claim_rules.py` is a read-only safety report for stored
`field_claims`.

It applies the deterministic rules from `scripts/vitalarga_rules.py` to claims
already in Supabase and answers:

- how many claims would be kept in review;
- how many would be rejected by the rules;
- how many low-risk claims would become eligible in a future preview mode;
- which reasons block automatic acceptance.

It does not update clinics, resolve reviews, write claims or publish pages.

The admin evidence cards mirror the same conservative rule context so Daniel can
see the risk tier and current rule decision while reviewing a clinic.

## Usage

Current Supabase policy:

```bash
python3 scripts/evaluate_claim_rules.py
```

Preview low-risk auto-publish without writing anything:

```bash
python3 scripts/evaluate_claim_rules.py --preview-low-risk-autopublish
```

Useful filters:

```bash
python3 scripts/evaluate_claim_rules.py --status review
python3 scripts/evaluate_claim_rules.py --clinic-slug monarka-clinic
python3 scripts/evaluate_claim_rules.py --json
```

## Operating rule

This tool is for measurement only. Any real auto-publication expansion still
requires Daniel's explicit decision and must respect
`docs/VITALARGA_LIMITES_OPERATIVOS.md`.
