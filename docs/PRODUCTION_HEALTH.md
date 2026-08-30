# Production health

`scripts/check_production_health.py` is a read-only smoke check for the deployed
Diuvita site.

It verifies that a small set of public URLs respond and contain expected shell
markers:

- home page;
- admin shell;
- one public clinic profile with richer UX;
- sitemap;
- favicon.

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

## CTO cycle

The safe CTO shadow cycle can include this check as an optional final step:

```bash
python3 scripts/run_cto_shadow_cycle.py --production-health
```

It remains read-only in both dry-run and safe-apply mode.
