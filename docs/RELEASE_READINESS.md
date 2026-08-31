# Informe de preparación para publicación

`scripts/release_readiness_report.py` resume si el worktree local de Vitalarga
está listo para revisión y si la web pública ya contiene los marcadores
esperados.

Es una herramienta de diagnóstico. No hace push, no despliega Netlify, no edita
Supabase y no resuelve tarjetas.

## Uso local

```bash
python3 scripts/release_readiness_report.py
```

El informe muestra:

- rama y commit local;
- si quedan cambios sin commit;
- si hay commits locales pendientes de push cuando el worktree tiene upstream;
- marcadores locales del admin de revisión;
- protección de assets, incluido el caso de logos descargados que no son
  imágenes reales;
- una lectura rápida para Daniel.

## Comprobar si está online

Para mirar la web pública sin publicar nada:

```bash
python3 scripts/release_readiness_report.py --production-health
```

Si producción aparece como **No comprobada**, significa únicamente que el
informe no ha mirado `www.vitalarga.com`. Si aparece **Atención**, la web pública
no contiene todavía todos los marcadores esperados o alguna URL no respondió.

En ambos casos, poner cambios online sigue requiriendo aprobación explícita de
Daniel para push o despliegue.

## Relación con otras comprobaciones

- `scripts/run_local_checks.py` verifica que el repositorio local sigue sano.
- `scripts/check_production_health.py` mira solo la salud pública desplegada.
- `scripts/check_public_site_freshness.py` compara Supabase público con páginas
  publicadas para detectar desfases de contenido.

Este informe junta las señales principales para responder rápido a preguntas
como: "¿esto que estoy viendo ya está online o solo está en local?".
