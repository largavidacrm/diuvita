# Local checks

`scripts/run_local_checks.py` runs the local safety checks used before a commit.
It is the quickest way to confirm that a change is ready to save and push.

The full pass currently covers:

1. Python syntax across local scripts.
2. Source snapshot and durable evidence helpers.
3. Publication rules and stored-claim rule evaluation.
4. Shadow extraction, verification and review-card creation.
5. Admin review UX checks: filters, clinic diffs and claim-rule context.
6. Admin digest and review-maturity checks.
7. Enrichment, candidate promotion, source hydration and source monitoring.
8. Changed-source processing and the safe CTO shadow cycle.
9. Clinic data validation.
10. Static site build.
11. Admin JavaScript syntax.
12. Whitespace and conflict-marker check.

Run:

```bash
python3 scripts/run_local_checks.py
```

For a faster pass while editing:

```bash
python3 scripts/run_local_checks.py --skip-build
```

This script does not read or write Supabase. It only validates local files.
