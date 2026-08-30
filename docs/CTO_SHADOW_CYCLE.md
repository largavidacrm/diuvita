# CTO shadow cycle

`scripts/run_cto_shadow_cycle.py` runs the safe recurring Diuvita CTO loop:

1. capture enrichment review claims;
2. hydrate pending source records;
3. monitor source changes;
4. process changed-source cards into profile-enrichment proposals;
5. turn blocking claims into internal quality-review cards;
6. print the admin digest;
7. evaluate stored claims against publication rules.

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
The claim-rule evaluation step is read-only in both modes. Blocking-claim cards
are internal review items only.
The cycle output is compact by default: it keeps counters and small examples,
but avoids printing full evidence payloads or large claim lists.
Source monitoring respects cadence by default, so a healthy run may report zero
checked sources when all sources were recently observed.

This script is intended for future scheduled CTO runs once Daniel chooses the
cadence and notification channel.
