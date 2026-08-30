# Source change monitoring

`scripts/monitor_source_changes.py` is the first Watcher tool.

It reads hydrated clinic `source_records`, fetches the current page, compares the
new readable-text hash with the stored hash when available and reports whether
the source changed. Falling back to full content hash is allowed only when text
hashes are missing.

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
