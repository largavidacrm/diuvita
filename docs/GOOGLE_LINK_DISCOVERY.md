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

Compact read-only output for large batches:

```bash
python3 scripts/discover_clinic_google_links.py --limit 19 --compact
```

To inspect open Google-link review cards without creating new work:

```bash
python3 scripts/google_link_review_reconciliation.py
```

Compact output hides URLs and keeps only counts plus next steps:

```bash
python3 scripts/google_link_review_reconciliation.py --compact
```

To focus one clinic or review-title fragment:

```bash
python3 scripts/google_link_review_reconciliation.py --clinic "Arvila"
```

That reconciliation report is read-only. It separates direct-looking clinic
profile links from searches, routes or street-address links, and gives Daniel
the next manual review step.

Apply mode creates internal `clinic_profile_enrichment` review cards only:

```bash
python3 scripts/discover_clinic_google_links.py --limit 5 --apply
```

It does not edit clinic profiles, resolve existing review cards, publish public
pages or trigger a deploy. Daniel still checks that each link opens the correct
Google clinic profile before saving it.

Operational rule: the public website should show Google Maps only when a stored
link looks like the clinic's own Google Business/Profile page. If none exists
yet, keep Google Maps pending in admin instead of publishing a generic search,
directions link or street-address link.

Discovery rule: a Google Maps link whose visible text looks only like a street
address is not enough unless the URL or label also contains the clinic name.
Those cases should be checked manually before becoming public profile links.

If the link label is generic, such as "Google Maps", and the URL looks like a
street-address `/maps/place/` URL instead of a named clinic profile, it is also
left for manual review. Generic labels are accepted only when the URL has a
strong direct-place signal such as `place_id`, `cid` or a Google short place
link.

Extra caution for short links: `maps.app.goo.gl` and `goo.gl/maps` links are not
proposed from a generic label such as "Google Maps" unless the visible label or
URL context also includes the clinic name. Those links can hide a simple address
pin, so they remain pending for Daniel instead of becoming a proposed clinic
profile link automatically.
