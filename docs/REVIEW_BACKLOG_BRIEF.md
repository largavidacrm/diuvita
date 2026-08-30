# Review backlog brief

`scripts/review_backlog_brief.py` is a read-only operational brief for the
Vitalarga review inbox.

It answers:

- how many review cards are open;
- whether the inbox is close to the safe-write backlog guard;
- how many profile-enrichment cards are open;
- which clinics concentrate several open review cards across review types;
- the recommended order inside each clinic group;
- which clinics have several profile-enrichment cards open at the same time;
- which duplicate group is the best first manual review target.

It does not discard cards, resolve reviews, edit clinic profiles, create drafts
or publish pages. It only helps Daniel decide where to start in `/admin/`.

## Run

```bash
python3 scripts/review_backlog_brief.py
```

Machine-readable output:

```bash
python3 scripts/review_backlog_brief.py --json
```

This is most useful when `Freno bandeja` is close to active or when `/admin/`
shows duplicated profile-enrichment pressure.
