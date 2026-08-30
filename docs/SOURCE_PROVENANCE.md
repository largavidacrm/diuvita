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

## Current implementation

Code:

- `scripts/capture_source_snapshot.py`
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

That folder is local/ignored by Git. Future work can upload snapshot metadata to Supabase `source_records` and keep any larger evidence outside GitHub.

## Next integration points

1. `EXTRACT_CLINIC_PROFILE` should capture a snapshot before extracting claims.
2. `field_claims.source_record_id` should link every important claim to a source.
3. The admin UI should show source evidence beside proposed changes.
4. Monitoring should compare hashes before calling expensive AI.
