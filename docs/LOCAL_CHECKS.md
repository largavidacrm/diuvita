# Local checks

`scripts/run_local_checks.py` runs the local safety checks used before a commit.
It is the quickest way to confirm that a change is ready to save and push.

The full pass currently covers:

1. Python syntax across local scripts.
2. Source snapshot, durable evidence, retention-report and production-health helpers.
3. Operational-limit red flags in source content and generated public pages.
4. Publication rules and stored-claim rule evaluation.
5. Shadow extraction, verification, saved-source batches and review-card creation.
6. Admin review UX checks: filters, actions, publication flow, clinic diffs,
   blocking-claim labels, next-action guidance, claim-rule context, maturity
   status, source monitoring status, snapshot-retention status and specialist
   coverage/profile-completeness/public-health status.
7. Public clinic profile UX and basic site asset checks.
8. Admin digest, Daniel review brief, review-maturity, specialist-coverage and
   profile-completeness checks.
9. Enrichment, candidate promotion, source hydration and source monitoring.
10. Changed-source processing, blocking-claim review routing and the safe CTO
    shadow cycle.
11. Clinic data validation.
12. Static site build.
13. Admin JavaScript syntax.
14. Whitespace and conflict-marker check.

Run:

```bash
python3 scripts/run_local_checks.py
```

For a faster pass while editing:

```bash
python3 scripts/run_local_checks.py --skip-build
```

This script does not read or write Supabase. It only validates local files.
