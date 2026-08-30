# CTO shadow cycle

`scripts/run_cto_shadow_cycle.py` runs the safe recurring Diuvita CTO loop:

Reference boundary: the cycle must respect
`docs/DIUVITA_LIMITES_OPERATIVOS.md` before any content, publication,
communication or product action. If a step touches one of those limits, it stops
for Daniel instead of implementing, softening or silently discarding the change.

1. capture enrichment review claims;
2. hydrate pending source records;
3. monitor source changes;
4. process changed-source cards into profile-enrichment proposals;
5. optionally run saved-source shadow extraction batches;
6. turn blocking claims into internal quality-review cards;
7. measure source snapshot retention without deleting evidence;
8. measure visible-profile completeness without editing clinics;
9. print the admin digest;
10. evaluate stored claims against publication rules.

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
are internal review items only. Source snapshot retention is measured only; no
cleanup/deletion path is enabled. Profile completeness is also measured only;
it does not edit fields or resolve review cards.
Saved-source shadow extraction is off by default. To include a small batch:

```bash
python3 scripts/run_cto_shadow_cycle.py --source-shadow-limit 3
```

In safe apply mode, that optional batch can create or refresh internal review
cards, but still does not edit clinics or publish pages.
The cycle output is compact by default: it keeps counters and small examples,
but avoids printing full evidence payloads, long text digests or large claim lists.
Source monitoring respects cadence by default, so a healthy run may report zero
checked sources when all sources were recently observed.

This script is intended for future scheduled CTO runs once Daniel chooses the
cadence and notification channel.
