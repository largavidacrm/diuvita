# Guía rápida del panel Diuvita

URL del panel:

```text
https://www.diuvita.com/admin/
```

## Revisar clínicas nuevas

1. Entra con tu usuario autorizado.
2. Mira el bloque **Necesitan revisión**.
3. Si aparece **Abrir prioridad**, úsalo para abrir la revisión más importante.
4. También puedes pulsar **Revisar** en una propuesta concreta.
5. Comprueba nombre, web, ciudad, fuente, servicios y especialistas detectados.
6. Si parece una clínica válida, pulsa **Crear borrador y validar**.
7. Si no encaja con Diuvita, pulsa **Descartar**.

Crear borrador no publica la clínica. Solo crea una ficha interna para editarla con calma. El botón de publicar aparece después, al editar esa ficha, dentro de **Validación final**.

## Ver el plan global

Arriba del panel verás **Plan global**. Ese bloque resume dónde estamos: fase
actual, estado de la web pública, presión de la bandeja, automatización,
fuentes, especialistas y el siguiente trabajo recomendado.

Puedes pulsar **Abrir siguiente** para ir directamente al grupo o tarjeta que el
panel considera más importante.

## Entender el estado del sistema

En **Estado del sistema**, mira especialmente:

- **Auto-publicación**: debe seguir **Apagada** hasta que tú decidas lo contrario.
- **Modo sombra**: significa que los agentes proponen y crean tareas internas, pero no publican solos.
- **Siguiente acción**: te dice qué bloque conviene revisar primero.
- **Caso prioritario**: te dice la clínica o revisión concreta que conviene abrir primero.
- **Madurez auto-publicación**: si aparece **No lista**, todavía no conviene automatizar publicaciones.
- **Motivo principal**: explica en lenguaje corto qué falta, por ejemplo más revisiones humanas o claims con conflicto.
- **Vigilancia fuentes**: te dice si las webs fuente están recientes o si toca revisarlas.
- **Próxima revisión fuentes**: fecha aproximada del siguiente control de fuentes cuando todo está al día.
- **Retención capturas**: te dice si hay capturas antiguas que podrían revisarse para limpieza futura.
- **Inventario capturas**: resume cuántas capturas antiguas y totales tiene guardadas el sistema.
- **Fuentes por ficha**: muestra cuántas fichas visibles ya tienen fuentes guardadas y trazables.
- **Fichas sin fuente**: indica cuántas fichas visibles todavía necesitan una fuente principal guardada.
- **Siguiente fuente**: señala la ficha que conviene revisar primero para cerrar problemas de fuentes o claims bloqueantes.
- **Especialistas**: muestra cuántas fichas visibles ya tienen especialistas publicados por la clínica.
- **Pendientes especialistas**: indica cuántas fichas visibles siguen sin ese apartado.
- **Siguiente especialistas**: señala la ficha más fácil de revisar para completar especialistas porque ya tiene tarjetas o claims internos.
- **Fichas completas**: muestra cuántas fichas visibles no tienen campos importantes pendientes.
- **Fichas con pendientes**: indica cuántas fichas visibles todavía necesitan completar algún campo público.
- **Campo más pendiente**: resume qué tipo de dato falta en más fichas visibles.
- **Siguiente ficha**: señala la ficha incompleta que conviene revisar primero.
- **Freno bandeja**: avisa si el sistema está cerca de pausar pasos que crean más tarjetas internas.
- **Grupo por clínica**: señala qué clínica conviene revisar en bloque porque concentra varias tarjetas abiertas.
- **Duplicados mejoras**: avisa si hay varias tarjetas abiertas para mejorar la misma clínica.
- **Tarjetas duplicadas**: muestra cuántas tarjetas forman parte de esas repeticiones.
- **Primer atasco**: señala qué clínica con tarjetas repetidas conviene ordenar primero.
- **Web pública**: confirma si la web visible responde correctamente desde el panel.
- **Checks web**: muestra cuántas comprobaciones públicas han pasado.
- **Publicación agrupada**: confirma si las ediciones visibles se agrupan antes
  de pedir a Netlify una nueva publicación.
- **Último rebuild**: muestra cuándo se pidió la última publicación web desde
  Supabase.

En **Necesitan revisión**, el botón **Abrir atasco** abre la primera tarjeta del
grupo repetido más importante cuando hay varias mejoras abiertas para la misma
clínica.

El botón **Filtrar grupo** muestra juntas las tarjetas abiertas de la clínica
que más conviene revisar en bloque. Es útil cuando una misma clínica tiene claim,
auditoría, cambio de fuente y mejoras abiertas a la vez.

Dentro de una tarjeta con varias revisiones relacionadas verás **Orden
recomendado**. Empieza por lo que marque ahí: normalmente claims bloqueantes o
fuentes cambiadas antes de guardar la ficha final.

El botón **Abrir fuente** abre la primera tarjeta relacionada con la ficha
marcada en **Siguiente fuente**. Si no hay una tarjeta exacta visible, filtra la
bandeja por esa clínica.

El botón **Abrir especialistas** abre la primera tarjeta relacionada con la
ficha marcada en **Siguiente especialistas**. Si no hay tarjeta exacta, filtra
la bandeja por esa clínica y por revisiones de especialistas.

Cuando la madurez diga **Lista para Daniel**, no significa que se active sola. Significa que ya se podría hablar de activar alguna categoría de bajo riesgo, siempre con tu aprobación.

Aunque aparezcan capturas candidatas a limpieza, el sistema no borra nada desde el panel. Borrar evidencias requiere una decisión explícita tuya.

En **Crear trabajo**, el panel avisa cuando la bandeja está casi llena. Si el
freno llega al límite, bloquea crear más trabajos hasta limpiar revisiones.

## Revisar mejoras de una ficha existente

Algunas tareas internas no son clínicas nuevas, sino mejoras para una ficha que ya existe.

1. Entra en **Necesitan revisión**.
2. Abre una tarjeta de tipo `clinic_profile_enrichment`.
3. Revisa los campos propuestos y sus fuentes.
4. Pulsa **Editar clínica**.
5. El panel carga la propuesta dentro del formulario.
6. Revisa el contenido, elige el estado de la ficha y guarda solo si te encaja.

Hasta que no guardes, la web pública no cambia.

Si ves una tarjeta llamada **Claim bloqueante**, significa que el sistema encontró una evidencia en conflicto o sin fuente suficiente. Ábrela, pulsa **Editar clínica** y revisa el bloque **Evidencias propuestas** antes de guardar o cerrar la revisión. Un claim rechazado normal no te bloquea: simplemente queda fuera de publicación y sirve para medir la precisión del sistema.

En esas tarjetas verás **Paso recomendado**. No es una decisión automática: te
orienta sobre si conviene comparar evidencias, buscar una fuente oficial o dejar
ese dato fuera de publicación.

En **Evidencias propuestas**, cada claim muestra el motivo de la regla, cuándo
se guardó y un enlace a la fuente cuando existe. Eso te permite ver de dónde
sale un dato sin leer información técnica cruda.

Puedes usar el filtro **Claims bloqueantes** para ver solo ese tipo de revisión.
Puedes usar el filtro **Especialistas** para ver solo tarjetas que mencionan
especialistas publicados o profesionales detectados.

En la tarjeta de revisión verás **Camino de publicación**. Ese bloque recuerda el flujo:
crear borrador interno, completar datos y publicar solo desde el editor de clínica.

## Duplicados

Si el sistema detecta que una propuesta se parece mucho a una clínica existente, verás **Coincidencias en Diuvita**.

Cuando sea un duplicado probable, el botón de crear borrador queda bloqueado. En ese caso, lo normal es descartarlo o revisarlo manualmente más adelante.

Si varias tarjetas abiertas intentan mejorar la misma ficha, la tabla muestra **Varias propuestas**. Puedes usar el filtro rápido **Atascos** para ver solo esas repeticiones.

Cuando abras una tarjeta y existan otras revisiones abiertas para la misma
clínica, verás **Otras revisiones de esta clínica**. Úsalo para revisar esas
tarjetas juntas y evitar resolver una propuesta sin mirar las relacionadas.

## Editar una clínica

1. Baja al bloque **Clínicas**.
2. Busca la clínica por nombre o ciudad.
3. Pulsa **Editar**.
4. Cambia los datos que quieras: resumen, servicios, especialidades, unidades clínicas, especialistas, contacto, etc.
5. Mira el bloque **Validación final**.
6. El botón de guardar cambia según el estado elegido: **Guardar borrador**,
   **Guardar en revisión**, **Guardar como preliminar** o **Guardar como publicada**.
7. Guarda cuando esté correcto.

Si eliges **Preliminar** o **Publicada** y todavía hay claims bloqueantes,
**Validación final** lo marcará como pendiente y el aviso de guardado te lo
recordará antes de mandar la ficha a la web.

Si la clínica está como **Publicada** o **Preliminar**, el cambio se manda a la web automáticamente. Puede tardar unos minutos.
Si está como **Borrador**, **Revisión**, **Descubierta**, **Extraída**, **Verificada** o **Archivada**, se guarda dentro del panel pero no aparece como ficha pública.

En **Historial de cambios**, cada versión antigua indica qué campos cambiarían si la restauras. Restaurar pide confirmación, sobrescribe la ficha actual y queda registrado como una nueva versión.

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
