# Diuvita source provenance

Diuvita should be able to answer a simple question for every important field:

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

By default Diuvita does not store full external pages in the repo. Compact snapshots are enough for audit trails and safer for copyright, storage and review.
Readable excerpts include visible text plus contact-style link targets such as
`mailto:`, `tel:` and Instagram URLs when the page hides them behind icons.
Supabase also keeps compact historical rows in `source_snapshots`, linked to
`source_records`.

## Current implementation

Code:

- `scripts/capture_source_snapshot.py`
- `scripts/source_snapshot_records.py`
- `scripts/test_capture_source_snapshot.py`

Examples:

```bash
python3 scripts/test_capture_source_snapshot.py
python3 scripts/capture_source_snapshot.py https://www.diuvita.com/sobre/ --dry-run
python3 scripts/capture_source_snapshot.py https://www.diuvita.com/sobre/
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
3. Show source history beside proposed changes in the admin.
4. Use snapshot history to measure source volatility before calling expensive AI.
