# Location source discovery

`scripts/discover_clinic_location_sources.py` looks for official same-domain
pages that are likely to contain clinic addresses, location details or access
information.

It looks for links such as:

- contact/location pages;
- "where we are" pages;
- clinic/site pages;
- pages about how to get there.

Default mode is dry-run:

```bash
python3 scripts/discover_clinic_location_sources.py --limit 10
```

Apply mode stores `source_records` only:

```bash
python3 scripts/discover_clinic_location_sources.py --limit 10 --apply
```

It does not edit clinic profiles, create public pages, resolve reviews or
publish the website. The purpose is to improve the source base for later
human-reviewed extraction of explicit locations, Google clinic profile links and
Google reviews links.
