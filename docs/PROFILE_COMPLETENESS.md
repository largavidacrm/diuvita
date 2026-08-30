# Profile completeness

`scripts/measure_profile_completeness.py` is a read-only checklist for visible
Diuvita clinic profiles.

It measures whether each visible clinic profile has the main public fields that
the current quality audit expects:

- sufficient summary;
- official website;
- address or at least one complete public location;
- email or phone;
- services;
- specialties;
- clinical units;
- published specialists;
- highlighted technology.

It does not publish clinics, edit clinic data, resolve review cards or rank
clinics by quality. The output is an internal operational checklist only.

It also selects one suggested next profile to review. That suggestion is based
on operational work already waiting in the admin queue first, then number of
missing measured fields, then published profiles before preliminary profiles.
It is not a quality ranking.

## Run

```bash
python3 scripts/measure_profile_completeness.py
```

Machine-readable output:

```bash
python3 scripts/measure_profile_completeness.py --json
```

This report supports the safe rule in `docs/DIUVITA_LIMITES_OPERATIVOS.md`:
missing or weak public information can be detected automatically, but publication
or correction still goes through Daniel's manual review in `/admin/`.

The top-line signal is also shown in `/admin/` as:

- `Fichas completas`;
- `Fichas con pendientes`.
- `Campo más pendiente`;
- `Siguiente ficha`.

Multi-location clinics are treated as one clinic profile with one or more
locations. A complete location can satisfy the address check even when the
legacy top-level address field is empty.
