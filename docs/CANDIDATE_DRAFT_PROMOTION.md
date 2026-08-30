# Candidate draft promotion

`scripts/promote_candidate_reviews.py` prepares the next internal workflow step:
turning `candidate_clinic` review cards into unpublished draft clinics.

Default behavior is dry-run only:

```bash
python3 scripts/promote_candidate_reviews.py
```

Apply mode:

```bash
python3 scripts/promote_candidate_reviews.py --apply
```

Safety rules:

- candidates below the confidence threshold stay on hold;
- probable duplicates are blocked;
- created clinics are `draft`, never public;
- the existing Supabase function writes source records, field claims, an entity
  version and audit events.

This is ready as an operator tool, but bulk apply should wait until Daniel is
comfortable with draft creation policy.
