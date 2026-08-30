# Source coverage

`scripts/measure_source_coverage.py` is a read-only report for visible Diuvita
clinic profiles.

It measures, per visible clinic:

- stored source records;
- hydrated source records with a content hash;
- stored compact source snapshots;
- internal field claims;
- claims with and without linked source records;
- blocking claims that still need review.

It also suggests one next source-support action. The suggestion is operational:
clinics with no source records or no hydrated sources come first, then clinics
with blocking or source-less claims. It is not a quality ranking.

It does not fetch websites, create sources, write claims, edit clinic profiles,
resolve reviews or publish pages.

`scripts/seed_visible_clinic_sources.py` complements this report. It can store a
visible clinic's already-known official website as an internal `source_records`
row when that same website host is missing from its provenance trail. This is a
controlled internal write: it does not edit profile fields, create claims,
resolve reviews or publish pages.

## Run

```bash
python3 scripts/measure_source_coverage.py
```

Machine-readable output:

```bash
python3 scripts/measure_source_coverage.py --json
```

Dry-run the official website source seeder:

```bash
python3 scripts/seed_visible_clinic_sources.py
```

Machine-readable dry-run:

```bash
python3 scripts/seed_visible_clinic_sources.py --json
```

Apply it after reviewing the dry-run output:

```bash
python3 scripts/seed_visible_clinic_sources.py --apply
```

This supports the provenance goal in `docs/SOURCE_PROVENANCE.md`: every
important public fact should eventually answer “why do we believe this?” from a
stored source trail.
