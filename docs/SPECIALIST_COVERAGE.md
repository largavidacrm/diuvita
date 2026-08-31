# Specialist coverage

`scripts/measure_specialist_coverage.py` is a read-only coverage report for
published specialists on visible Vitalarga clinic profiles.

It answers:

- how many visible clinics have specialists listed;
- how many visible clinics do not;
- whether there are detected specialist names waiting in the evidence layer;
- whether open review cards already mention specialists.
- which missing-specialist clinic is the best first review target.
- what to do next for each clinic: consolidate open cards, prepare a review
  proposal or look for a public team page.

It does not validate credentials, publish names, edit clinics or rank clinics.

## Run

```bash
python3 scripts/measure_specialist_coverage.py
```

Machine-readable output:

```bash
python3 scripts/measure_specialist_coverage.py --json
```

For one clinic, use the reconciliation report when Daniel needs to compare what
is already public with open review cards and internal detected names:

```bash
python3 scripts/specialist_review_reconciliation.py --clinic "Kairos"
```

That report is also read-only. It does not publish professional names; it points
to the next human review step.

The same top-line coverage signal is included in `/admin/`,
`scripts/admin_digest.py` and `scripts/daniel_review_brief.py`.
The admin review inbox also has an **Especialistas** filter and an
**Abrir especialistas** shortcut for the next measured specialist target.

Missing-specialist rows are ordered by easiest review path first: open review
cards, then detected specialist names, then the remaining visible profiles.

This report supports the safe rule in `docs/VITALARGA_LIMITES_OPERATIVOS.md`: only
public professional information can be used, and any publication still goes
through Daniel's manual review in `/admin/`.
