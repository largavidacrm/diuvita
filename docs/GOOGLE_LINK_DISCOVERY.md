# Google link discovery

`scripts/discover_clinic_google_links.py` looks for direct Google Maps profile
links and Google review links on a clinic's official website. It checks the
home page and up to three same-site pages that look like contact, location,
where-we-are or clinic-site pages.

Default mode is dry-run:

```bash
python3 scripts/discover_clinic_google_links.py --limit 5
```

To keep it to the home page only:

```bash
python3 scripts/discover_clinic_google_links.py --limit 5 --max-secondary-pages 0
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

Discovery rule: a Google Maps link whose visible text looks only like a street
address is not enough unless the URL or label also contains the clinic name.
Those cases should be checked manually before becoming public profile links.

If the link label is generic, such as "Google Maps", and the URL looks like a
street-address `/maps/place/` URL instead of a named clinic profile, it is also
left for manual review. Generic labels are accepted only when the URL has a
strong direct-place signal such as `place_id`, `cid` or a Google short place
link.
