# Global plan status

`scripts/global_plan_status.py` prints a plain-Spanish, read-only snapshot of
where Vitalarga is in the global CTO plan.

It combines the protected admin digest with the roadmap lanes:

- Daniel's immediate next review action;
- the next panel clicks Daniel should use;
- safe work Codex can continue without creating more review pressure;
- what should not be activated yet;
- control center;
- source traceability;
- shadow automation loop;
- source monitoring;
- specialist/knowledge-graph coverage;
- growth workflows still waiting for stronger accuracy and lower review load.

The "Siguiente trabajo recomendado" section also includes the first clinic
workgroup, the first Google Maps/review-link proposal and open specialist
proposal coverage, so Daniel can clear several related review cards in one
session.

The same executive view is surfaced in `/admin/` as **Plan global**, above the
detailed system status.

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
