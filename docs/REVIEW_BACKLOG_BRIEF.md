# Review backlog brief

`scripts/review_backlog_brief.py` is a read-only operational brief for the
Vitalarga review inbox.

It answers:

- how many review cards are open;
- whether the inbox is close to the safe-write backlog guard and how many
  proposals remain before the preventive pause;
- how many profile-enrichment cards are open;
- which clinics concentrate several open review cards across review types;
- the recommended order inside each clinic group, including human-only clinic
  claim requests before ordinary source or profile work;
- safe per-card proposal summaries, such as field names and counts of proposed
  locations, phones or specialists, without printing the full enrichment
  payload;
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

This is most useful when `Freno bandeja` or the preventive pause is close to
active, or when `/admin/` shows duplicated profile-enrichment pressure.

Clinic claim requests remain review-only signals. The brief can tell Daniel
where they are, but it does not verify identity, grant access, edit clinic data
or resolve the review card.
