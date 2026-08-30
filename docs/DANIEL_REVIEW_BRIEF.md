# Daniel review brief

`scripts/daniel_review_brief.py` prints a plain-Spanish, read-only brief for
Daniel.

It is designed for future morning or weekly automations. It answers:

- what Daniel should review first;
- which visible review card is the best starting point;
- a fallback example by review type when the first priority list is limited;
- whether the clinic portal has access requests, user suggestions or clinic-requested changes pending;
- how many open cards exist by type;
- whether auto-publication is still off;
- how many visible profiles still have measured public fields pending;
- which measured public field is missing from the most visible profiles;
- which incomplete visible profile should be reviewed next;
- how many visible profiles include published specialists;
- which missing-specialist profile is the best first review target;
- how many visible profiles have stored and hydrated source support;
- which visible profile is the best first source-support target;
- whether the review inbox has repeated improvement cards for the same clinic;
- which clinic should be handled as a grouped review session;
- which repeated-improvement bottleneck should be sorted first;
- whether the review inbox is close to the safe-write backlog guard;
- whether source monitoring is fresh or pending;
- whether there are open technical failures;
- optionally, whether the live public website responds correctly.

It does not publish clinics, edit data, resolve reviews, approve clinic portal
access, send emails or expose review payloads.

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

When the first action is claims bloqueantes, use the focused read-only brief:

```bash
python3 scripts/blocking_claim_brief.py
```

The brief reuses the protected admin digest query and reads Supabase connection
settings from `.env`.
