# CTO shadow cycle

`scripts/run_cto_shadow_cycle.py` runs the safe recurring Vitalarga CTO loop:

Reference boundary: the cycle must respect
`docs/VITALARGA_LIMITES_OPERATIVOS.md` before any content, publication,
communication or product action. If a step touches one of those limits, it stops
for Daniel instead of implementing, softening or silently discarding the change.

1. capture enrichment review claims;
2. seed official website source records for visible clinics;
3. optionally discover official team/about pages for visible clinics;
4. optionally discover official Google Maps/review links from clinic websites;
5. hydrate pending source records;
6. monitor source changes;
7. process changed-source cards into profile-enrichment proposals;
8. optionally run saved-source shadow extraction batches;
9. turn blocking claims into internal quality-review cards;
10. measure source snapshot retention without deleting evidence;
11. measure visible source coverage without writing evidence;
12. measure visible-profile completeness without editing clinics;
13. measure review-inbox bottlenecks without resolving cards;
14. print the admin digest;
15. evaluate stored claims against publication rules.
16. optionally run strict editorial limit checks;
17. optionally check public production URLs without logging in or writing data.
18. optionally compare saved public data with deployed clinic pages to detect
    stale pages.

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
Official website seeding only stores already-known clinic websites as internal
source records when the same website host is missing.
Team-source discovery is off by default; when enabled, it only stores
same-domain team/about pages as internal source records.
Google-link discovery is off by default; when enabled, it only creates internal
review cards for Google Maps profile links and Google review links found on the
clinic's own website.
The claim-rule evaluation step is read-only in both modes. Blocking-claim cards
are internal review items only. Source snapshot retention is measured only; no
cleanup/deletion path is enabled. Profile completeness is also measured only;
it does not edit fields or resolve review cards.

To avoid review noise, safe apply mode first checks the open review backlog.
The hard guard remains 50 open cards, but the default unattended cycle stops
review-card writing at 45 open cards so Daniel is not left at the edge of the
limit. When the guard is active, the cycle skips the steps that could create
more review cards and continues with safe read-only measurements. The soft stop
can be adjusted:

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

Team-page discovery is also off by default. To search a small visible-clinic
batch for specialist pages before hydration:

```bash
python3 scripts/run_cto_shadow_cycle.py --team-source-limit 5
```

To focus one clinic:

```bash
python3 scripts/run_cto_shadow_cycle.py --team-source-limit 1 --team-source-clinic-slug arvila-magna
```

Google-link discovery is also off by default. To search a small visible-clinic
batch for direct Google Maps and Google review links:

```bash
python3 scripts/run_cto_shadow_cycle.py --google-link-limit 5
```

To focus one clinic:

```bash
python3 scripts/run_cto_shadow_cycle.py --google-link-limit 1 --google-link-clinic-slug monarka-clinic
```

In safe apply mode, this creates review cards only. Daniel still confirms that
the link opens the correct clinic before saving it into the public profile.

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

The public freshness check is also off by default. It compares what is saved in
the public Supabase feed with what is currently visible on deployed clinic
pages, which is the clearest diagnostic when Daniel has just validated a clinic
and does not yet see the change online:

```bash
python3 scripts/run_cto_shadow_cycle.py --public-freshness --public-freshness-clinic "Monarka" --plain-brief
```

If this step reports a desfase, the data is saved but the static website needs
the next batched rebuild. It still does not trigger Netlify or publish anything
by itself.

Strict editorial mode is also off by default. To include the more sensitive scan
for rankings, awards or comparison language:

```bash
python3 scripts/run_cto_shadow_cycle.py --strict-editorial
```

If this step finds a hard-limit issue, the cycle reports it and stops for
Daniel's decision instead of changing the content.

This script is intended for future scheduled CTO runs once Daniel chooses the
cadence and notification channel.
