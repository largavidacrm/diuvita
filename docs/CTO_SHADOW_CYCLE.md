# CTO shadow cycle

`scripts/run_cto_shadow_cycle.py` runs the safe recurring Diuvita CTO loop:

1. capture enrichment review claims;
2. hydrate pending source records;
3. monitor source changes;
4. print the admin digest.

Default mode is dry-run:

```bash
python3 scripts/run_cto_shadow_cycle.py
```

Safe apply mode:

```bash
python3 scripts/run_cto_shadow_cycle.py --apply-safe
```

Safe apply still does not publish, edit public clinic data or promote candidate
reviews into draft clinics. It only writes internal evidence/review state.

This script is intended for future scheduled CTO runs once Daniel chooses the
cadence and notification channel.
