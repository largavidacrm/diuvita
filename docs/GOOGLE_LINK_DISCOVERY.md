# Google link discovery

`scripts/discover_clinic_google_links.py` looks for direct Google Maps profile
links and Google review links on a clinic's official website.

Default mode is dry-run:

```bash
python3 scripts/discover_clinic_google_links.py --limit 5
```

To focus one clinic:

```bash
python3 scripts/discover_clinic_google_links.py --clinic-slug monarka-clinic --limit 1
```

Apply mode creates internal `clinic_profile_enrichment` review cards only:

```bash
python3 scripts/discover_clinic_google_links.py --limit 5 --apply
```

It does not edit clinic profiles, resolve existing review cards, publish public
pages or trigger a deploy. Daniel still checks that each link opens the correct
Google clinic profile before saving it.

Operational rule: the public website should prefer a stored direct Google Maps
profile link. If none exists yet, the fallback Google Maps link searches by
clinic name, city and country, not by street address alone.
