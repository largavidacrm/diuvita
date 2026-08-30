# Source record hydration

`scripts/hydrate_source_records.py` fills pending `source_records` with compact
evidence:

- source title;
- retrieval timestamp;
- content hash;
- readable-text hash;
- short readable excerpt;
- HTTP metadata.

It does not store complete web pages, edit clinic profiles, resolve reviews or
publish anything.

Dry run:

```bash
python3 scripts/hydrate_source_records.py --limit 10
```

Apply:

```bash
python3 scripts/hydrate_source_records.py --limit 10 --apply
```

Failures are reported per URL so one blocked website does not stop the rest of
the evidence capture.

If a public site rejects the default Vitalarga provenance header with HTTP 403 or
406, the capturer retries once with normal browser-compatible headers and stores
that request profile in metadata. It does not use cookies, logins, captcha
workarounds or high-frequency retries.

To retry sources that recently failed:

```bash
python3 scripts/hydrate_source_records.py --limit 10 --retry-errors
```
