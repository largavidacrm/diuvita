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
8. measure visible source coverage without writing evidence;
9. measure visible-profile completeness without editing clinics;
10. measure review-inbox bottlenecks without resolving cards;
11. print the admin digest;
12. evaluate stored claims against publication rules.
13. optionally run strict editorial limit checks;
14. optionally check public production URLs without logging in or writing data.

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

To avoid review noise, safe apply mode first checks the open review backlog.
If there are 50 or more open review cards, the cycle skips the steps that could
create more review cards and continues with safe read-only measurements. The
limit can be adjusted:

```bash
python3 scripts/run_cto_shadow_cycle.py --apply-safe --max-open-reviews-for-safe-writes 75
```

Use `0` only for an intentionally unfenced internal run.

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
Review-backlog measurement is read-only and helps identify duplicate
profile-enrichment pressure before adding more cards.
Source-coverage measurement is read-only and highlights visible clinics whose
source trail is weak before expanding automation.
The JSON output also includes a `daniel_brief` block with the simple status,
next action, review backlog, top missing clinic field, next incomplete profile
to review, source-support coverage, next source-support target and publication
guard.

For a Daniel-readable run log:

```bash
python3 scripts/run_cto_shadow_cycle.py --plain-brief
```

That brief is still generated from the same safe cycle. It does not publish,
edit clinic data, resolve review cards or hide a failed technical step.

The production health check is off by default because it reads the live website
over the network. To include it at the end of a cycle:

```bash
python3 scripts/run_cto_shadow_cycle.py --production-health
```

This step only verifies public pages and expected interface markers. It does not
log in, change Supabase, publish clinics or resolve review cards.

Strict editorial mode is also off by default. To include the more sensitive scan
for rankings, awards or comparison language:

```bash
python3 scripts/run_cto_shadow_cycle.py --strict-editorial
```

If this step finds a hard-limit issue, the cycle reports it and stops for
Daniel's decision instead of changing the content.

This script is intended for future scheduled CTO runs once Daniel chooses the
cadence and notification channel.
