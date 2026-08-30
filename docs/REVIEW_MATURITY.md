# Review maturity measurement

`scripts/measure_review_maturity.py` is a read-only safety report for Diuvita.

It answers whether the system has enough human review history before any future
low-risk auto-publish expansion.

It checks:

- candidate clinic review decisions against the target sample size;
- open, resolved and dismissed review cards by type;
- field claims by verification status;
- specific blocking claims, including clinic, field, verification status and
  whether a source is attached;
- claims with or without saved sources;
- failed or stuck jobs in the last 7 days.

Current policy remains conservative: a "ready" report is only a signal that the
low-risk category can be discussed. It does not enable auto-publish.

## Run

```bash
python3 scripts/measure_review_maturity.py
```

Machine-readable output:

```bash
python3 scripts/measure_review_maturity.py --json
```
