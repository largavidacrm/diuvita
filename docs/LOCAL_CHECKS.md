# Local checks

`scripts/run_local_checks.py` runs the local safety checks used before a commit.
It is the quickest way to confirm that a change is ready to save and push.

The full pass currently covers:

1. Python syntax across local scripts.
2. Source snapshot, durable evidence, retention-report and production-health helpers.
3. Netlify deploy guard rules, to avoid paid production builds for internal-only changes.
4. Operational-limit red flags in source content and generated public pages.
5. Publication rules and stored-claim rule evaluation.
6. Shadow extraction, verification, saved-source batches and review-card creation.
7. Admin review UX checks: filters, actions, publication flow, clinic diffs,
   blocking-claim labels, next-action guidance, claim-rule context, maturity
   status, source monitoring status, source-coverage status,
   snapshot-retention status and specialist
   coverage/profile-completeness/public-health/review-backlog status.
8. Public clinic profile UX, built clinic-page UX and basic site asset checks.
9. Admin digest, publication readiness, Daniel review brief,
   blocking-claim brief, review-backlog brief, review-maturity,
   specialist-coverage, profile-completeness and source-coverage checks.
10. Enrichment, candidate promotion, source hydration and source monitoring.
11. Changed-source processing, blocking-claim review routing and the safe CTO
    shadow cycle.
12. Clinic data validation.
13. Static site build.
14. Built-site public profile UX guard.
15. Admin JavaScript syntax.
16. Whitespace and conflict-marker check.

Run:

```bash
python3 scripts/run_local_checks.py
```

For a faster pass while editing:

```bash
python3 scripts/run_local_checks.py --skip-build
```

This script does not read or write Supabase. It only validates local files.
