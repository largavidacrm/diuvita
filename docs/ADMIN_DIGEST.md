# Admin digest

The admin digest is a read-only CTO snapshot for Diuvita operations.

It answers:

- how many clinics are public or preliminary;
- how many internal review cards are open;
- whether agents are in shadow mode;
- whether any jobs failed;
- how much agent cost is recorded in the database.

It does not publish clinics, edit data, or resolve review items.

## Run

```bash
python3 scripts/admin_digest.py
```

JSON output for future automations:

```bash
python3 scripts/admin_digest.py --json
```

The script reads Supabase connection settings from `.env` and uses the active admin email. It calls the protected `admin_dashboard_summary()` function before reading supporting operational rows.
