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

## Run

```bash
python3 scripts/measure_source_coverage.py
```

Machine-readable output:

```bash
python3 scripts/measure_source_coverage.py --json
```

This supports the provenance goal in `docs/SOURCE_PROVENANCE.md`: every
important public fact should eventually answer “why do we believe this?” from a
stored source trail.
