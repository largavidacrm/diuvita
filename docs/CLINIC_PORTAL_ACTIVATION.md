# Activación del portal de clínicas

`scripts/check_clinic_portal_activation.py` imprime un semáforo interno, solo
lectura, para distinguir entre código listo y decisiones pendientes antes de
activar el portal de clínicas de Vitalarga.

## Qué comprueba

- Que `/portal-clinicas/` se genera en el sitio estático.
- Que la migración local crea solicitudes, membresías, propuestas de cambio y
  reglas de acceso.
- Que existen los flujos de reclamar ficha, sugerir clínica, iniciar sesión con
  enlace mágico y proponer cambios.
- Que el admin puede aprobar, rechazar o pedir más información.
- Que las solicitudes se ven en el admin, el digest, el brief de Daniel y el
  estado global del plan.
- Que la fase actual no incluye subida de documentos, emails salientes de
  Vitalarga, distintivo fuerte ni publicación automática.

## Uso normal

```bash
python3 scripts/check_clinic_portal_activation.py
```

El resultado normal, antes de tocar producción, debe ser:

```text
listo técnicamente; pendiente de decisión/manual
```

Eso significa que el código local está preparado, pero que todavía faltan pasos
que no deben hacerse sin Daniel:

- revisar privacidad, base legal, retención y textos visibles;
- aplicar la migración en Supabase real;
- configurar Supabase Auth para los enlaces mágicos;
- hacer una prueba real controlada;
- aprobar expresamente la publicación.

## Uso cuando Daniel haya validado pasos

El script permite marcar decisiones ya hechas solo para el informe de ese
momento:

```bash
python3 scripts/check_clinic_portal_activation.py \
  --legal-privacy-reviewed \
  --supabase-migration-applied \
  --supabase-auth-configured \
  --manual-flow-tested \
  --production-approved
```

También puede emitir JSON para futuras automatizaciones:

```bash
python3 scripts/check_clinic_portal_activation.py --json
```

## Límite operativo

Este informe no activa Supabase, no toca Netlify, no publica el portal y no
aprueba cuentas de clínicas. Si el semáforo se usa para preparar producción,
Daniel debe aprobar explícitamente los pasos externos.
