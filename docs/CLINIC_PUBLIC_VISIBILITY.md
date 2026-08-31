# Clinic public visibility

`scripts/clinic_public_visibility_report.py` is a read-only diagnostic for the
common question: "I changed a clinic; why is it not visible online?"

It combines two checks:

- publication readiness in Supabase;
- saved public data compared with the currently published clinic page.

Use it when a visible profile looks stale, when Daniel has just edited a clinic,
or when a draft/preliminary/published state is unclear.

## Run

```bash
python3 scripts/clinic_public_visibility_report.py --clinic "Monarka"
```

The report does not publish, edit clinics or trigger Netlify. If it detects that
Supabase has newer data than the public page, the next step remains a Daniel
decision because a public rebuild may create Netlify usage.

The output groups missing public fields by category only. It deliberately avoids
dumping full unpublished professional/team details into the terminal summary.
