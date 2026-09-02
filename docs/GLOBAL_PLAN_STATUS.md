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
- publication readiness and the main required blocker before making fichas
  visible;
- shadow automation loop;
- source monitoring;
- clinic portal intake and manual validation;
- specialist/knowledge-graph coverage;
- growth workflows still waiting for stronger accuracy and lower review load.


The "Siguiente trabajo recomendado" section also includes the next publication
target, clinic workgroup context, the first Google Maps/review-link proposal,
open specialist proposal coverage and the next clinic-portal action, so Daniel
can clear related review cards without confusing required publication blockers
with broader completeness gaps or approving anything automatically.


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
