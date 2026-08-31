# Admin digest

The admin digest is a read-only CTO snapshot for Vitalarga operations.

It answers:

- how many clinics are public or preliminary;
- how many internal review cards are open;
- whether any review cards are blocking-claim reviews;
- one representative open card per review type, when available;
- whether several open enrichment cards are stacked on the same clinic;
- which clinic concentrates the highest-priority group of open review cards;
- whether the review inbox is near the safe-write backlog guard;
- whether Google Maps/review-link proposals are open and which safe review card
  should be opened first;
- whether specialist proposals are already present and which card has the
  largest batch;
- what the next recommended internal action is;
- whether agents are in shadow mode;
- whether low-risk auto-publish is mature enough to discuss;
- whether the clinic portal has pending access requests, user suggestions or clinic-requested profile changes;
- whether any jobs failed;
- whether clinic source monitoring is fresh or due;
- how many visible profiles have stored source support and hydrated sources;
- which visible profile is the best first source-support target;
- how many visible profiles include published specialists;
- which missing-specialist visible profile is the best first review target;
- how many visible profiles have all measured public fields present;
- which measured public field is missing from the most visible profiles;
- how much agent cost is recorded in the database.

It does not publish clinics, edit data, or resolve review items.

## Run

```bash
python3 scripts/admin_digest.py
```

JSON output for future automations:

```bash
python3 scripts/admin_digest.py --json
```

For a less technical, Daniel-facing summary, use:

```bash
python3 scripts/daniel_review_brief.py
```

The script reads Supabase connection settings from `.env` and uses the active admin email. It calls the protected `admin_dashboard_summary()` function before reading supporting operational rows.

## Source monitoring

The digest includes a read-only "Vigilancia de fuentes" block:

- `Fuentes vigilables`: hydrated clinic sources with a stored content hash and a public URL.
- `Fuentes vencidas ahora`: sources that are due for a fresh check based on their cadence.
- `Cobertura fuentes`: how many visible clinic profiles have stored and hydrated source support.
- `Siguiente fuente`: the first visible profile to review for source support, source hydration or blocking claims.
- `Proxima revision prevista`: the next scheduled source check when everything is fresh.
- `Cadencia`: how many sources are checked weekly, standard monthly, slow quarterly, or with a custom cadence.

This is an operational signal only. It does not fetch sources, change public clinic data, publish clinics, or resolve review cards.

## Clinic portal

The digest includes a read-only "Portal clinicas" block for clinic access
requests, clinic-originated change requests and user-suggested clinics. It only
points Daniel to the right manual review queue; it does not approve accounts,
publish clinic data, send emails or mark medical quality.

## Profile completeness

The digest also includes a read-only top-line completeness signal for visible
profiles. It uses the same public-field checks as the quality-audit workflow and
does not rank clinics, edit records or publish changes. It also suggests one
next visible profile to review, prioritizing profiles that already have related
review cards open and then profiles with more measured public fields missing.

When several profile-enrichment cards are open for the same clinic, the digest
also shows the first duplicate bottleneck to tidy in `/admin/`.
