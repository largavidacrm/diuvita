# Production health

`scripts/check_production_health.py` is a read-only smoke check for the deployed
Vitalarga site.

It verifies that a small set of public URLs respond and contain expected shell
markers:

- home page;
- admin shell;
- one public clinic profile with richer UX;
- sitemap;
- favicon.

The deployed HTML markers also cover the main supervision cues: public profile
stats, card-level field signals, the admin priority case, source-coverage cues,
specialist next-review cue, duplicate-review filtering, the review backlog guard,
related review cards, claim traceability and the candidate-to-publication flow.

It does not log in, publish clinics, edit Supabase, resolve review cards or
inspect private data. It is intentionally separate from `scripts/run_local_checks.py`
because it reads the live website over the network.

## Run

```bash
python3 scripts/check_production_health.py
```

JSON output:

```bash
python3 scripts/check_production_health.py --json
```

After a deploy, Netlify may need a short propagation window. Use bounded
retries when the goal is to distinguish a slow deploy from a real issue:

```bash
python3 scripts/check_production_health.py --retries 2 --retry-delay 20
```

## CTO cycle

The safe CTO shadow cycle can include this check as an optional final step:

```bash
python3 scripts/run_cto_shadow_cycle.py --production-health
```

It remains read-only in both dry-run and safe-apply mode.
