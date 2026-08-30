# Diuvita — la guía de las clínicas de longevidad

Sitio estático: `data/clinics.json` o Supabase + `data/posts/*.md` → `python3 build.py` → `dist/`.
Deploy: Netlify (build automatico en cada push, ver `netlify.toml`).
Las fichas nuevas esperan validación humana en `pendientes/` antes de entrar en `data/clinics.json`.

## Comandos locales

```bash
python3 scripts/validate_data.py
python3 build.py
```

El build de Netlify ejecuta la validacion antes de generar el sitio.
El dominio canonico es `https://www.diuvita.com`.

El panel operativo se genera en `/admin/`. Los datos quedan protegidos por Supabase Auth y por la lista `admin_users`. Desde ese panel se pueden revisar métricas, crear trabajos en cola y editar clínicas manualmente, incluidos servicios, unidades clínicas, especialistas publicados y contacto. Tras guardar una ficha, Supabase inicia una nueva publicacion de Netlify para que la web estatica recoja los datos vivos.

Las ampliaciones de fichas existentes deben entrar primero como propuestas internas de revisión (`clinic_profile_enrichment`). Los archivos con propuestas detalladas son locales/privados y no se suben a GitHub; se pueden convertir en tarjetas internas con `scripts/submit_profile_enrichment_reviews.py`.

## Siguiente arquitectura

La web publica sigue siendo estatica por ahora. La base tecnica para la siguiente fase esta en:

- `docs/CTO_ROADMAP.md`: plan tecnico por fases.
- `docs/CTO_INTERNAL_EXECUTION_PLAN.md`: plan operativo interno para avanzar hacia la arquitectura objetivo.
- `docs/AGENT_WORKFLOWS.md`: primer diseno de workflows agenticos.
- `docs/RULES_ENGINE.md`: reglas deterministas para decidir si un dato se rechaza, se revisa o puede autoaceptarse en el futuro.
- `supabase/migrations/0001_agent_foundation.sql`: tablas base para verdad versionada, fuentes, jobs, revision humana y eventos.
- `supabase/migrations/0003_admin_clinic_editing.sql`: funcion segura para editar clinicas desde `/admin/` con historial.
- `supabase/migrations/0004_public_site_feed.sql`: feed publico controlado para que la web pueda construir desde Supabase.
- `supabase/migrations/0005_private_rebuild_hook.sql`: gancho privado de Supabase para reconstruir Netlify tras cambios publicables.
- `scripts/export_supabase_seed.py`: exporta las clinicas actuales a SQL para Supabase.
- `scripts/export_supabase_bootstrap.py`: genera un SQL unico con migracion e importacion inicial.
- `scripts/apply_supabase_bootstrap.sh`: aplica el bootstrap contra Supabase usando `DATABASE_URL` local.
- `scripts/check_supabase_foundation.sh`: comprueba recuentos basicos de la base Supabase.
- `scripts/diuvita_rules.py`: motor local de reglas por riesgo de campo.
- `scripts/apply_supabase_sql.sh`: aplica un SQL concreto contra Supabase.
- `scripts/add_supabase_admin.sh`: autoriza un email como administrador del panel.
- `scripts/create_supabase_auth_user.py`: crea un usuario de acceso en Supabase Auth.
- `scripts/check_supabase_auth_login.py`: comprueba que un login de Supabase Auth funciona.
- `.env.example`: plantilla de variables locales y de despliegue.
