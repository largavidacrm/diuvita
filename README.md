# Diuvita — la guía de las clínicas de longevidad

Sitio estático: `data/clinics.json` + `data/posts/*.md` → `python3 build.py` → `dist/`.
Deploy: Netlify (build automatico en cada push, ver `netlify.toml`).
Las fichas nuevas esperan validación humana en `pendientes/` antes de entrar en `data/clinics.json`.

## Comandos locales

```bash
python3 scripts/validate_data.py
python3 build.py
```

El build de Netlify ejecuta la validacion antes de generar el sitio.
El dominio canonico es `https://www.diuvita.com`.

## Siguiente arquitectura

La web publica sigue siendo estatica por ahora. La base tecnica para la siguiente fase esta en:

- `docs/CTO_ROADMAP.md`: plan tecnico por fases.
- `docs/AGENT_WORKFLOWS.md`: primer diseno de workflows agenticos.
- `supabase/migrations/0001_agent_foundation.sql`: tablas base para verdad versionada, fuentes, jobs, revision humana y eventos.
- `scripts/export_supabase_seed.py`: exporta las clinicas actuales a SQL para Supabase.
- `scripts/export_supabase_bootstrap.py`: genera un SQL unico con migracion e importacion inicial.
- `.env.example`: plantilla de variables locales y de despliegue.
