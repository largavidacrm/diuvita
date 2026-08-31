# Location coverage

`scripts/measure_location_coverage.py` is a read-only checklist for explicit
clinic locations stored in visible Vitalarga profiles.

It measures:

- clinics with explicit location rows;
- clinics with more than one location;
- location rows with an address;
- location rows with a direct-looking Google Maps clinic profile link;
- location rows with a Google reviews link;
- open review cards that already propose explicit locations;
- internal location evidence that has not yet become a review card.

It does not publish clinics, edit clinic data, resolve review cards or rank
clinics by quality. The output is an internal operational checklist only.

## Run

```bash
python3 scripts/measure_location_coverage.py
```

Machine-readable output:

```bash
python3 scripts/measure_location_coverage.py --json
```

Multi-location clinics should remain one clinic profile with several location
rows. Public and admin labels should avoid numbered labels such as `Sede 1` or
`Sede 2`; use `Sede principal`, `Sede adicional`, city names or the clinic's own
published location names.

The Google Maps check follows the project rule: count and publish only a
direct-looking clinic profile link. Generic searches, directions links and
street-address-only place URLs stay pending for manual review and are not shown
as public Google Maps buttons.

When the review inbox is near the safe-write limit, internal location evidence
should remain measured only. Convert it into review cards after Daniel has
reduced the open review backlog.
