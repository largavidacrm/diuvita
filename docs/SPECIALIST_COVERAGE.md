# Specialist coverage

`scripts/measure_specialist_coverage.py` is a read-only coverage report for
published specialists on visible Diuvita clinic profiles.

It answers:

- how many visible clinics have specialists listed;
- how many visible clinics do not;
- whether there are internal specialist claims waiting in the evidence layer;
- whether open review cards already mention specialists.

It does not validate credentials, publish names, edit clinics or rank clinics.

## Run

```bash
python3 scripts/measure_specialist_coverage.py
```

Machine-readable output:

```bash
python3 scripts/measure_specialist_coverage.py --json
```

The same top-line coverage signal is included in `scripts/admin_digest.py` and
`scripts/daniel_review_brief.py`.

This report supports the safe rule in `docs/DIUVITA_LIMITES_OPERATIVOS.md`: only
public professional information can be used, and any publication still goes
through Daniel's manual review in `/admin/`.
