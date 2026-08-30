# Guía rápida del panel Diuvita

URL del panel:

```text
https://www.diuvita.com/admin/
```

## Revisar clínicas nuevas

1. Entra con tu usuario autorizado.
2. Mira el bloque **Necesitan revisión**.
3. Pulsa **Revisar** en una propuesta.
4. Comprueba nombre, web, ciudad, fuente, servicios y especialistas detectados.
5. Si parece una clínica válida, pulsa **Crear borrador y validar**.
6. Si no encaja con Diuvita, pulsa **Descartar**.

Crear borrador no publica la clínica. Solo crea una ficha interna para editarla con calma.

## Entender el estado del sistema

En **Estado del sistema**, mira especialmente:

- **Auto-publicación**: debe seguir **Apagada** hasta que tú decidas lo contrario.
- **Modo sombra**: significa que los agentes proponen y crean tareas internas, pero no publican solos.
- **Madurez auto-publicación**: si aparece **No lista**, todavía no conviene automatizar publicaciones.
- **Motivo principal**: explica en lenguaje corto qué falta, por ejemplo más revisiones humanas o claims con conflicto.

Cuando la madurez diga **Lista para Daniel**, no significa que se active sola. Significa que ya se podría hablar de activar alguna categoría de bajo riesgo, siempre con tu aprobación.

## Revisar mejoras de una ficha existente

Algunas tareas internas no son clínicas nuevas, sino mejoras para una ficha que ya existe.

1. Entra en **Necesitan revisión**.
2. Abre una tarjeta de tipo `clinic_profile_enrichment`.
3. Revisa los campos propuestos y sus fuentes.
4. Pulsa **Editar clínica**.
5. El panel carga la propuesta dentro del formulario.
6. Revisa el contenido, elige el estado de la ficha y guarda solo si te encaja.

Hasta que no guardes, la web pública no cambia.

## Duplicados

Si el sistema detecta que una propuesta se parece mucho a una clínica existente, verás **Coincidencias en Diuvita**.

Cuando sea un duplicado probable, el botón de crear borrador queda bloqueado. En ese caso, lo normal es descartarlo o revisarlo manualmente más adelante.

## Editar una clínica

1. Baja al bloque **Clínicas**.
2. Busca la clínica por nombre o ciudad.
3. Pulsa **Editar**.
4. Cambia los datos que quieras: resumen, servicios, especialidades, unidades clínicas, especialistas, contacto, etc.
5. Mira el bloque **Validación final**.
6. El botón de guardar cambia según el estado elegido: **Guardar borrador**,
   **Guardar en revisión**, **Guardar como preliminar** o **Guardar como publicada**.
7. Guarda cuando esté correcto.

Si la clínica está como **Publicada** o **Preliminar**, el cambio se manda a la web automáticamente. Puede tardar unos minutos.
Si está como **Borrador**, **Revisión**, **Descubierta**, **Extraída**, **Verificada** o **Archivada**, se guarda dentro del panel pero no aparece como ficha pública.

## Auditar fichas

En **Crear trabajo**, puedes elegir **Auditar fichas**.

Eso revisa las fichas visibles y crea tareas si falta algo importante, por ejemplo especialistas, servicios, especialidades, dirección, resumen o contacto.

La auditoría no cambia la web. Solo crea tareas internas para revisar.

## Estados importantes

- **Publicada**: aparece en la web.
- **Preliminar**: aparece en la web con aviso de ficha preliminar.
- **Descubierta**, **Borrador**, **Revisión** o **Archivada**: no aparecen en la web pública.

## Qué revisar mañana

Revisa primero las propuestas internas de ampliación de fichas publicadas que aparecen en **Necesitan revisión**. Esas propuestas están en Supabase como revisión interna; todavía no han cambiado la web pública.
