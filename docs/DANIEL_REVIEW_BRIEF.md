# Daniel review brief

`scripts/daniel_review_brief.py` prints a plain-Spanish, read-only brief for
Daniel.

It is designed for future morning or weekly automations. It answers:

- what Daniel should review first;
- which visible review card is the best starting point;
- how many open cards exist by type;
- whether auto-publication is still off;
- how many visible profiles still have measured public fields pending;
- how many visible profiles include published specialists;
- whether source monitoring is fresh or pending;
- whether there are open technical failures;
- optionally, whether the live public website responds correctly.

It does not publish clinics, edit data, resolve reviews, send emails or expose
review payloads.

## Run

```bash
python3 scripts/daniel_review_brief.py
```

JSON output is also available for automation plumbing:

```bash
python3 scripts/daniel_review_brief.py --json
```

To include a read-only public website check:

```bash
python3 scripts/daniel_review_brief.py --production-health
```

The brief reuses the protected admin digest query and reads Supabase connection
settings from `.env`.
