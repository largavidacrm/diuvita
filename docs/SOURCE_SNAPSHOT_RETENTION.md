# Source snapshot retention

`scripts/measure_source_snapshot_retention.py` is a read-only report for compact
source snapshots.

It previews a conservative retention policy:

- keep at least the latest 3 snapshots for each source;
- only consider cleanup for snapshots older than 180 days;
- never delete anything.

## Run

```bash
python3 scripts/measure_source_snapshot_retention.py
```

Machine-readable output:

```bash
python3 scripts/measure_source_snapshot_retention.py --json
```

Changing or deleting stored evidence still requires a separate Daniel decision.
