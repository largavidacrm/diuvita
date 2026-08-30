# Profile completeness

`scripts/measure_profile_completeness.py` is a read-only checklist for visible
Vitalarga clinic profiles.

It measures whether each visible clinic profile has the main public fields that
the current quality audit expects:

- sufficient summary;
- official website;
- address or at least one complete public location;
- Google Maps clinic profile link, not a generic search, directions link or
  street-address-only place URL;
- email or phone;
- services;
- specialties;
- clinical units;
- published specialists;
- highlighted technology;
- years in practice when publicly stated;
- public specialist/team count when publicly stated;
- whether medical-team credentialing is visibly identified;
- whether pricing is public.

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

This report supports the safe rule in `docs/VITALARGA_LIMITES_OPERATIVOS.md`:
missing or weak public information can be detected automatically, but publication
or correction still goes through Daniel's manual review in `/admin/`.

The top-line signal is also shown in `/admin/` as:

- `Fichas completas`;
- `Fichas con pendientes`.
- `Campo más pendiente`;
- `Siguiente ficha`.

The transparency fields are measured separately from the underlying content.
For example, a clinic can have named professionals listed but still be missing
the public team-size signal, and a clinic can show an address while still
missing the direct Google Business/Profile URL.

Multi-location clinics are treated as one clinic profile with one or more
locations. A complete location can satisfy the address check even when the
legacy top-level address field is empty.

The Google Maps check intentionally stays stricter than "any map link". It only
counts a direct-looking clinic profile link, for example a Google place URL,
`place_id`, `cid`, `query_place_id` or official Google short place link. Generic
searches, directions links and street-address-only place URLs remain pending for
manual review.
