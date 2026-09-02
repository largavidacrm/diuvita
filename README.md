# Vitalarga — la guía de las clínicas de longevidad

Sitio estático: `data/clinics.json` o Supabase + `data/posts/*.md` → `python3 build.py` → `dist/`.
Deploy: Netlify (build automatico solo cuando el cambio afecta la web/admin, ver `netlify.toml` y `docs/NETLIFY_DEPLOY_CONTROL.md`).
Las fichas nuevas esperan validación humana en `pendientes/` antes de entrar en `data/clinics.json`.

## Comandos locales

```bash
python3 scripts/validate_data.py
python3 build.py
```

El build de Netlify ejecuta la validacion antes de generar el sitio.
El dominio canonico es `https://www.vitalarga.com`.

El panel operativo se genera en `/admin/`. Los datos quedan protegidos por Supabase Auth y por la lista `admin_users`. Desde ese panel se pueden revisar métricas, crear trabajos en cola, ver historial/evidencias internas y editar clínicas manualmente, incluidos servicios, unidades clínicas, especialistas publicados y contacto. Tras guardar una ficha, Supabase inicia una nueva publicacion de Netlify para que la web estatica recoja los datos vivos.

La home publica incluye **Recomendar Clínica**. Ese formulario anonimo llama a una funcion limitada de Supabase que solo crea un trabajo interno `DISCOVER_CLINIC`; no crea fichas, no escribe en `review_queue` y no publica cambios.

Las ampliaciones de fichas existentes deben entrar primero como propuestas internas de revisión (`clinic_profile_enrichment`). Los archivos con propuestas detalladas son locales/privados y no se suben a GitHub; se pueden convertir en tarjetas internas con `scripts/submit_profile_enrichment_reviews.py`.

## Siguiente arquitectura

La web publica sigue siendo estatica por ahora. La base tecnica para la siguiente fase esta en:

- `docs/CTO_ROADMAP.md`: plan tecnico por fases.
- `docs/CTO_INTERNAL_EXECUTION_PLAN.md`: plan operativo interno para avanzar hacia la arquitectura objetivo.
- `docs/VITALARGA_STYLEBOOK.md`: resumen operativo del nuevo stylebook y sus límites de uso.
- `docs/VITALARGA_LIMITES_OPERATIVOS.md`: limites legales, medicos, editoriales y de publicacion que requieren escalado a Daniel.
- `docs/CLINIC_PORTAL.md`: flujo de reclamación de fichas, recomendaciones de clínicas y propuestas de cambios, siempre con revisión manual.
- `docs/CLINIC_PORTAL_ACTIVATION.md`: semáforo interno para preparar la activación del portal sin tocar producción.
- `docs/AGENT_WORKFLOWS.md`: primer diseno de workflows agenticos.
- `docs/RULES_ENGINE.md`: reglas deterministas para decidir si un dato se rechaza, se revisa o puede autoaceptarse en el futuro.
- `docs/CLAIM_RULE_EVALUATION.md`: ensayo de reglas sobre claims ya guardados, sin escribir ni publicar.
- `docs/SOURCE_PROVENANCE.md`: estrategia de evidencias compactas para saber de dónde sale cada dato.
- `docs/SHADOW_EXTRACTOR.md`: primer extractor local en modo sombra para convertir una fuente en claims estructurados.
- `docs/SHADOW_VERIFIER.md`: primer verificador local que desafía claims extraídos antes de reglas/publicación.
- `docs/SHADOW_REVIEW_SUBMISSION.md`: conexión entre extractor/verificador shadow y tarjetas internas del admin.
- `docs/SOURCE_SHADOW_REVIEW_BATCH.md`: lote seguro para convertir fuentes ya guardadas en propuestas internas de mejora.
- `docs/ADMIN_DIGEST.md`: resumen interno de CTO para revisiones, jobs y costes registrados.
- `docs/DANIEL_REVIEW_BRIEF.md`: resumen accionable en lenguaje simple para que Daniel sepa qué revisar primero.
- `docs/GLOBAL_PLAN_STATUS.md`: resumen ejecutivo de dónde está Vitalarga dentro del plan global.
- `docs/NETLIFY_DEPLOY_CONTROL.md`: reglas para agrupar publicaciones y evitar builds de Netlify innecesarios.
- `docs/REVIEW_MATURITY.md`: medición de madurez antes de plantear auto-publicación de bajo riesgo.
- `docs/HUMAN_FIELD_LOCKS.md`: protecciones para campos corregidos manualmente por Daniel.
- `docs/SPECIALIST_COVERAGE.md`: medición solo lectura de cobertura de especialistas publicados.
- `docs/PROFILE_COMPLETENESS.md`: checklist solo lectura de campos públicos pendientes en fichas visibles.
- `docs/SOURCE_COVERAGE.md`: medición solo lectura de cobertura de fuentes y claims por ficha visible.
- `scripts/seed_visible_clinic_sources.py`: guarda como fuente interna la web oficial ya conocida de fichas visibles que aún no tienen esa fuente.
- `docs/ENRICHMENT_CLAIMS_CAPTURE.md`: captura interna de fuentes y claims desde propuestas de mejora.
- `docs/CANDIDATE_DRAFT_PROMOTION.md`: herramienta conservadora para convertir candidatas en borradores internos.
- `docs/BLOCKING_CLAIM_REVIEWS.md`: tarjetas y brief de claims bloqueantes antes de publicar o relajar reglas.
- `docs/SOURCE_RECORD_HYDRATION.md`: hidratación de evidencias compactas para fuentes guardadas.
- `docs/SOURCE_CHANGE_MONITORING.md`: primer watcher para detectar cambios en fuentes ya guardadas.
- `docs/SOURCE_CHANGE_REVIEW_PROCESSING.md`: puente seguro desde fuente cambiada a propuesta interna revisable.
- `docs/SOURCE_SNAPSHOT_RETENTION.md`: informe solo lectura sobre retencion de capturas de fuentes.
- `docs/CTO_SHADOW_CYCLE.md`: ciclo seguro para encadenar tareas internas repetibles.
- `docs/PRODUCTION_HEALTH.md`: comprobación solo lectura de salud del sitio publicado.
- `docs/LOCAL_CHECKS.md`: comprobaciones locales antes de guardar y subir cambios.
- `supabase/migrations/0014_source_snapshots.sql`: historial interno de capturas compactas de fuentes.
- `supabase/migrations/0015_candidate_draft_validation_flow.sql`: flujo claro candidata -> borrador -> validación final.
- `supabase/migrations/0016_normalize_existing_candidate_drafts.sql`: normaliza candidatas internas antiguas a borrador.
- `supabase/migrations/0017_admin_restore_clinic_version.sql`: restauración auditada de fichas desde el historial.
- `supabase/migrations/0018_batch_public_site_rebuilds.sql`: prepara ventanas de publicacion agrupada para reducir rebuilds de Netlify desde Supabase.
- `supabase/migrations/0019_admin_publication_control_summary.sql`: expone al admin el estado de publicacion agrupada sin revelar el hook privado.
- `supabase/migrations/0021_vitalarga_brand_rename.sql`: migra ajustes internos vivos de la marca anterior a Vitalarga.
- `supabase/migrations/0022_neutralize_progevita_summary.sql`: neutraliza texto sensible de Progevita en Supabase.
- `supabase/migrations/0023_clinic_portal.sql`: tablas y funciones para portal de clínicas, reclamaciones, membresías y propuestas de cambios.
- `supabase/migrations/0001_agent_foundation.sql`: tablas base para verdad versionada, fuentes, jobs, revision humana y eventos.
- `supabase/migrations/0003_admin_clinic_editing.sql`: funcion segura para editar clinicas desde `/admin/` con historial.
- `supabase/migrations/0004_public_site_feed.sql`: feed publico controlado para que la web pueda construir desde Supabase.
- `supabase/migrations/0005_private_rebuild_hook.sql`: gancho privado de Supabase para reconstruir Netlify tras cambios publicables.
- `supabase/migrations/0012_human_field_locks.sql`: función de admin para proteger campos corregidos manualmente.
- `scripts/export_supabase_seed.py`: exporta las clinicas actuales a SQL para Supabase.
- `scripts/export_supabase_bootstrap.py`: genera un SQL unico con migracion e importacion inicial.
- `scripts/apply_supabase_bootstrap.sh`: aplica el bootstrap contra Supabase usando `DATABASE_URL` local.
- `scripts/check_supabase_foundation.sh`: comprueba recuentos basicos de la base Supabase.
- `scripts/check_supabase_rebuild_batching.sh`: comprueba si Supabase agrupa peticiones de rebuild a Netlify.
- `scripts/capture_source_snapshot.py`: captura metadatos, hash y extracto corto de una fuente publica.
- `scripts/source_snapshot_records.py`: helpers SQL para guardar capturas compactas en Supabase.
- `scripts/vitalarga_rules.py`: motor local de reglas por riesgo de campo.
- `scripts/evaluate_claim_rules.py`: evalua claims guardados contra las reglas en modo solo lectura.
- `scripts/extract_clinic_profile_shadow.py`: extractor inicial de claims de clínica en modo sombra.
- `scripts/verify_clinic_profile_shadow.py`: verificador inicial de claims extraídos en modo sombra.
- `scripts/submit_shadow_extraction_review.py`: convierte una extracción verificada en una tarjeta interna revisable.
- `scripts/submit_source_shadow_reviews.py`: ejecuta extracción/verificación shadow sobre fuentes de clínicas existentes, priorizando fichas incompletas.
- `scripts/admin_digest.py`: imprime un resumen operativo interno de Supabase, solo lectura.
- `scripts/daniel_review_brief.py`: imprime un brief de revisión para Daniel, solo lectura y sin payloads técnicos.
- `scripts/global_plan_status.py`: imprime el estado del plan global en lenguaje ejecutivo, sin escribir datos.
- `scripts/check_clinic_portal_activation.py`: imprime un semáforo de activación del portal, separando código listo de decisiones manuales.
- `scripts/blocking_claim_brief.py`: resume claims bloqueantes por clínica para revisión manual, solo lectura.
- `scripts/measure_review_maturity.py`: mide si hay suficiente revisión humana antes de relajar reglas.
- `scripts/measure_specialist_coverage.py`: mide cobertura de especialistas publicados por clínica, sin editar fichas.
- `scripts/measure_profile_completeness.py`: mide campos públicos pendientes en fichas visibles, sin editar fichas.
- `scripts/measure_source_coverage.py`: mide fuentes, claims y bloqueos por ficha visible, sin editar fichas.
- `scripts/seed_visible_clinic_sources.py`: guarda webs oficiales ya conocidas como fuentes internas, sin editar fichas ni publicar.
- `scripts/capture_enrichment_review_claims.py`: convierte propuestas internas en `source_records` y `field_claims`.
- `scripts/promote_candidate_reviews.py`: simula o crea borradores internos desde candidatas revisables.
- `scripts/hydrate_source_records.py`: completa `source_records` con título, hash y extracto corto.
- `scripts/monitor_source_changes.py`: compara hashes de fuentes y crea revisiones internas si cambian.
- `scripts/process_source_change_reviews.py`: convierte revisiones de fuente cambiada en propuestas internas de mejora.
- `scripts/measure_source_snapshot_retention.py`: mide si hay capturas antiguas candidatas a limpieza, sin borrar nada.
- `scripts/run_cto_shadow_cycle.py`: ejecuta el ciclo sombra seguro de CTO; incluye resumen simple para Daniel y puede incluir chequeo de producción opcional.
- `scripts/check_production_health.py`: comprueba URLs públicas de producción, sin login ni escrituras.
- `scripts/run_local_checks.py`: ejecuta pruebas, validación, build y revisión básica del admin.
- `scripts/apply_supabase_sql.sh`: aplica un SQL concreto contra Supabase.
- `scripts/add_supabase_admin.sh`: autoriza un email como administrador del panel.
- `scripts/create_supabase_auth_user.py`: crea un usuario de acceso en Supabase Auth.
- `scripts/check_supabase_auth_login.py`: comprueba que un login de Supabase Auth funciona.
- `.env.example`: plantilla de variables locales y de despliegue.
