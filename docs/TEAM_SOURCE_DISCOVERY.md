# Team source discovery

`scripts/discover_clinic_team_sources.py` finds official clinic pages that look
like team, doctors, professionals or about pages.

Why this exists:

- many clinics publish specialists outside the homepage;
- the source-shadow extractor only works well when those pages are stored as
  internal sources;
- storing the source first keeps the process auditable before any profile data
  changes.

Default mode is read-only:

```bash
python3 scripts/discover_clinic_team_sources.py
```

Focus one clinic:

```bash
python3 scripts/discover_clinic_team_sources.py --clinic-slug arvila-magna
```

Store discovered team/about pages as internal source records:

```bash
python3 scripts/discover_clinic_team_sources.py --clinic-slug arvila-magna --apply
```

The tool only stores `source_records` with `source_type = official_team_page`.
It does not edit clinic profiles, create or resolve review cards, publish the
website or change public content.

Besides explicit links found on the homepage, the discoverer can make a very
small checked probe for common official team paths such as `/equipo/` and
`/equipo-medico/`. A probed URL is kept only when the page responds on the same
clinic domain and its visible text contains team/professional signals.

The safe CTO cycle can include this discovery step explicitly:

```bash
python3 scripts/run_cto_shadow_cycle.py --team-source-limit 5
```

In safe apply mode, the same flag can store newly discovered source records:

```bash
python3 scripts/run_cto_shadow_cycle.py --apply-safe --team-source-limit 5
```

Recommended sequence for specialist gaps:

1. discover team/about pages;
2. hydrate those source records;
3. run source-shadow extraction for a small batch;
4. review the resulting profile-enrichment card in `/admin/`;
5. publish only through the clinic editor's final validation.
