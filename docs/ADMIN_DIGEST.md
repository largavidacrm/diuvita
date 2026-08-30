# Admin digest

The admin digest is a read-only CTO snapshot for Diuvita operations.

It answers:

- how many clinics are public or preliminary;
- how many internal review cards are open;
- whether any review cards are blocking-claim reviews;
- one representative open card per review type, when available;
- what the next recommended internal action is;
- whether agents are in shadow mode;
- whether low-risk auto-publish is mature enough to discuss;
- whether any jobs failed;
- whether clinic source monitoring is fresh or due;
- how many visible profiles include published specialists;
- how many visible profiles have all measured public fields present;
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
- `Proxima revision prevista`: the next scheduled source check when everything is fresh.
- `Cadencia`: how many sources are checked weekly, standard monthly, slow quarterly, or with a custom cadence.

This is an operational signal only. It does not fetch sources, change public clinic data, publish clinics, or resolve review cards.

## Profile completeness

The digest also includes a read-only top-line completeness signal for visible
profiles. It uses the same public-field checks as the quality-audit workflow and
does not rank clinics, edit records or publish changes.
