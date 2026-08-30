# Source change monitoring

`scripts/monitor_source_changes.py` is the first Watcher tool.

It reads hydrated clinic `source_records`, fetches the current page, compares the
new readable-text hash with the stored hash when available and reports whether
the source changed. Falling back to full content hash is allowed only when text
hashes are missing.

When a change is detected, the watcher adds conservative material hints to the
internal payload. These hints do not update the clinic; they only tell the
reviewer whether the changed source may affect contact data, team, services,
prices or medical claims.

Dry run:

```bash
python3 scripts/monitor_source_changes.py --limit 10
```

Apply:

```bash
python3 scripts/monitor_source_changes.py --limit 10 --apply
```

Apply mode creates internal `source_change_detected` review cards. It does not
edit clinic data, update source hashes, resolve review cards or publish pages.
Daniel can then decide whether a changed source needs a profile update.

Open source-change cards can be processed into separate profile-enrichment
proposals with `scripts/process_source_change_reviews.py`. That second step is
also safe by default and keeps Daniel in the final review loop.
