# Local checks

`scripts/run_local_checks.py` runs the local safety checks used before a commit:

1. Python syntax checks;
2. shadow workflow tests;
3. data validation;
4. static build;
5. admin JavaScript syntax check;
6. whitespace/conflict-marker check.

Run:

```bash
python3 scripts/run_local_checks.py
```

For a faster pass while editing:

```bash
python3 scripts/run_local_checks.py --skip-build
```

This script does not read or write Supabase. It only validates local files.
