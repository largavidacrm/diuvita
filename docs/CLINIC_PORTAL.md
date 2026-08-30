# Portal de clínicas Vitalarga

Fecha: 2026-08-30

Estado: construido en rama local separada, pendiente de revisión de Daniel,
migración Supabase y activación en producción.

## Objetivo

Dar a las clínicas y a usuarios externos una vía ordenada para:

- recomendar una clínica que no aparece en Vitalarga;
- pedir acceso a una ficha ya publicada;
- permitir que una clínica aprobada proponga cambios sobre su ficha.

El principio operativo no cambia: nada se publica automáticamente. Toda alta,
reclamación o modificación queda en revisión manual interna.

## Flujo 1: recomendar clínica

1. Una persona entra en `/portal-clinicas/` y elige "Recomendar clínica".
2. Envía nombre, web oficial, ciudad, país, email, relación con la clínica,
   fuentes públicas opcionales y contexto.
3. Supabase guarda la solicitud en `clinic_claim_requests` con
   `request_kind = recommend_clinic`.
4. Se crea una tarjeta interna en `review_queue` como `candidate_clinic`.
5. En `/admin/`, Daniel puede convertirla en borrador interno o descartarla.
6. Si se convierte en borrador, sigue el flujo existente de validación final.

La clínica no aparece en la web pública solo por ser recomendada.

## Flujo 2: reclamar ficha existente

1. Una clínica entra desde `/portal-clinicas/` o desde el enlace
   "Reclamar o corregir esta ficha" en una ficha pública.
2. Envía la ficha, nombre, cargo, email corporativo y mensaje de verificación.
3. Supabase guarda la solicitud en `clinic_claim_requests` con
   `request_kind = claim_existing`.
4. Se crea una tarjeta interna `clinic_claim_request` en `review_queue`.
5. En `/admin/`, Daniel puede aprobar acceso, pedir más información o rechazar.
6. Al aprobar, se crea una membresía en `clinic_portal_memberships` y la ficha
   queda marcada con `identity_confirmed_at`.
7. La web puede mostrar el distintivo "Datos confirmados por el centro".

Ese distintivo solo significa que el centro ha confirmado su identidad o acceso
a la ficha. No significa recomendación médica, ranking, calidad asistencial ni
validación de resultados.

## Flujo 3: proponer cambios de ficha

1. Una clínica aprobada entra con enlace mágico de Supabase Auth.
2. Ve sus clínicas con acceso activo y las solicitudes recientes.
3. Propone cambios en campos soportados: nombre, web, ciudad, país, dirección,
   resumen, servicios, especialidades, unidades, profesionales publicados,
   tecnología y contacto.
4. Supabase guarda la propuesta en `clinic_profile_change_requests`.
5. Se crea una tarjeta `clinic_profile_enrichment` en `review_queue`.
6. En `/admin/`, Daniel carga la propuesta en el editor, revisa fuentes y guarda
   solo si procede.

Una clínica puede proponer contenido, pero no puede editar ni publicar
directamente.

## Deliberadamente fuera de esta fase

- Subida de CIF, documentos societarios o archivos.
- Almacenamiento de documentos privados.
- Emails salientes enviados por Vitalarga.
- Publicación automática de altas o modificaciones.
- Reseñas de usuarios, testimonios o experiencias de pacientes.
- Datos de pacientes o consultas sanitarias individuales.
- Distintivo fuerte que pueda interpretarse como aval de calidad médica.

La subida de CIF tiene sentido como fase posterior, pero exige decidir
privacidad, retención documental, acceso interno, borrado y base legal antes de
implementarla.

## Antes de activar en producción

1. Revisar el texto legal y de privacidad asociado al portal.
2. Aplicar `supabase/migrations/0023_clinic_portal.sql`.
3. Revisar Supabase Auth: emails mágicos, URLs permitidas y remitente.
4. Decidir cómo se contactará manualmente cuando una solicitud quede en
   `needs_more_info`.
5. Probar una solicitud real de recomendación y una reclamación de ficha.
6. Revisar si el build público debe usar Supabase como fuente para mostrar datos
   de identidad confirmada en producción.
