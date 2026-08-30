# Vitalarga source provenance

Vitalarga should be able to answer a simple question for every important field:

```text
Why do we believe this?
```

The provenance layer stores compact evidence about source pages:

- Source URL.
- Final URL after redirects.
- Page title.
- Retrieval time.
- HTTP status and content type.
- SHA-256 content hash.
- Short readable excerpt.

By default Vitalarga does not store full external pages in the repo. Compact snapshots are enough for audit trails and safer for copyright, storage and review.
Readable excerpts include visible text plus contact-style link targets such as
`mailto:`, `tel:` and Instagram URLs when the page hides them behind icons.
Supabase also keeps compact historical rows in `source_snapshots`, linked to
`source_records`.

## Current implementation

Code:

- `scripts/capture_source_snapshot.py`
- `scripts/source_snapshot_records.py`
- `scripts/measure_source_coverage.py`
- `scripts/discover_clinic_team_sources.py`
- `scripts/discover_clinic_location_sources.py`
- `scripts/hydrate_source_records.py`
- `scripts/test_capture_source_snapshot.py`

The admin evidence panel now shows a compact trace for each internal claim:
rule reason, saved date and linked source title/URL when available. This keeps
Daniel's review view readable without exposing full extraction payloads.
`scripts/measure_source_coverage.py` adds a read-only per-clinic view of source
coverage so weak evidence trails can be prioritized before expanding automation.
`scripts/discover_clinic_team_sources.py` finds same-domain team/about pages and
can store them as internal source records without changing profile fields.
`scripts/discover_clinic_location_sources.py` does the same for contact/location
pages. `scripts/hydrate_source_records.py --compact` keeps hydration runs
readable when many internal sources are updated at once.

Examples:

```bash
python3 scripts/test_capture_source_snapshot.py
python3 scripts/test_measure_source_coverage.py
python3 scripts/discover_clinic_team_sources.py --clinic-slug arvila-magna
python3 scripts/discover_clinic_location_sources.py --clinic-slug clinicas-ume
python3 scripts/hydrate_source_records.py --limit 20 --compact
python3 scripts/capture_source_snapshot.py https://www.vitalarga.com/sobre/ --dry-run
python3 scripts/capture_source_snapshot.py https://www.vitalarga.com/sobre/
```

Saved snapshots go under:

```text
data/source_snapshots/
```

That folder is local/ignored by Git. Supabase stores compact snapshot metadata
and excerpts in `source_snapshots`; larger evidence should stay outside GitHub.

## Next integration points

1. Store external full-page archives outside GitHub only if later needed.
2. Link every important field claim to the strongest source record.
3. Expand source history beside proposed changes in the admin when Daniel needs deeper audits.
4. Use snapshot history to measure source volatility before calling expensive AI.
