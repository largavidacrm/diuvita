# Daniel review brief

`scripts/daniel_review_brief.py` prints a plain-Spanish, read-only brief for
Daniel.

It is designed for future morning or weekly automations. It answers:

- what Daniel should review first;
- which next clicks Daniel should use in the panel;
- which visible review card is the best starting point;
- a fallback example by review type when the first priority list is limited;
- whether the clinic portal has access requests, user suggestions or clinic-requested changes pending;
- how many open cards exist by type;
- whether auto-publication is still off;
- whether public-site publication has saved changes pending to appear online;
- how many non-archived fichas have no required publication blockers;
- which required publication blocker is most common;
- which ficha should be worked first before Daniel decides whether to make it
  visible;
- how many visible profiles still have measured public fields pending;
- which measured public field is missing from the most visible profiles;
- whether there are open Google Maps/review-link proposals and which one to
  start with;
- whether there are open cards with specialist names already proposed;
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

This JSON omits operator/account fields by default. For local debugging only,
they can be kept explicitly:

```bash
python3 scripts/daniel_review_brief.py --json --include-account-fields
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
