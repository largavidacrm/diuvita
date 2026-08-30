# Global plan status

`scripts/global_plan_status.py` prints a plain-Spanish, read-only snapshot of
where Diuvita is in the global CTO plan.

It combines the protected admin digest with the roadmap lanes:

- control center;
- source traceability;
- shadow automation loop;
- source monitoring;
- specialist/knowledge-graph coverage;
- growth workflows still waiting for stronger accuracy and lower review load.

The "Siguiente trabajo recomendado" section also includes the first clinic
workgroup, so Daniel can clear several related review cards in one session.

It does not publish clinics, edit Supabase, resolve review cards or create new
work. It is meant for quick answers to "where are we in the plan?"

## Run

```bash
python3 scripts/global_plan_status.py
```

JSON output is available for future automation plumbing:

```bash
python3 scripts/global_plan_status.py --json
```
