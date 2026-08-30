# Human field locks

Human field locks protect clinic fields Daniel has corrected manually.

Current scope:

- clinic name and summary;
- website and contact fields;
- country, city, region and address;
- services, specialties, units, published specialists and technology.

The admin panel stores active locks in `public.human_overrides` through
`public.admin_set_clinic_field_locks`.

Rules for future agents:

- If a field has an active human lock, agents may create evidence or review
  cards, but they must not overwrite the public value automatically.
- A human lock can be removed from the admin panel by unchecking the field and
  saving the clinic.
- Auto-publish remains disabled until Daniel explicitly changes that policy.

This feature is intentionally separate from the normal clinic save path. If
locking fails, the clinic edit can still be preserved and reviewed.
