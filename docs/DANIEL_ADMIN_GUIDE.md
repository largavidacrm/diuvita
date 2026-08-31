# Guía rápida del panel Vitalarga

URL del panel:

```text
https://www.vitalarga.com/admin/
```

## Revisar clínicas nuevas

1. Entra con tu usuario autorizado.
2. Mira el bloque **Necesitan revisión**.
3. Si aparece **Abrir prioridad**, úsalo para abrir la revisión más importante.
4. También puedes pulsar **Revisar** en una propuesta concreta.
5. Comprueba nombre, web, ciudad, fuente, servicios y especialistas detectados.
6. Si parece una clínica válida, pulsa **Crear borrador y validar**.
7. Si no encaja con Vitalarga, pulsa **Descartar**.

Crear borrador no publica la clínica. Solo crea una ficha interna para editarla con calma. El botón de publicar aparece después, al editar esa ficha, dentro de **Validación final**.

## Ver el plan global

Arriba del panel verás **Plan global**. Léelo de arriba abajo:

1. **Estamos aquí**: te dice en qué fase real estamos, sin obligarte a
   interpretar números.
2. **Tu próximo clic**: es el botón que conviene usar primero.
3. **Tú ahora / Freno de bandeja / Yo puedo seguir con / Datos pendientes /
   No activar todavía**: separa tu revisión humana, el límite operativo, mi
   trabajo técnico seguro y lo que todavía no conviene automatizar.
4. **Mapa simple del plan**: muestra el camino completo sin numeritos
   decorativos.

Puedes pulsar **Filtrar grupo** o **Abrir siguiente** para ir directamente al
grupo o tarjeta que el panel considera más importante. Si ves “control interno”,
no significa que la web esté rota: significa que toca limpiar revisiones antes
de subir la autonomía.

Si **Tú ahora** dice **No crees trabajos nuevos**, usa primero **Filtrar grupo**,
**Especialistas** o **Google Maps** para cerrar tarjetas abiertas.

El menú lateral abre una zona de trabajo cada vez: **Plan**, **Sistema**,
**Revisión**, **Clínicas**, **Trabajos** o **Actividad**. Pulsa **Todo** solo si
quieres volver a la vista larga completa.

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
- **Siguiente especialistas**: señala la ficha más fácil de revisar para completar especialistas porque ya tiene tarjetas o nombres detectados.
- **Fichas completas**: muestra cuántas fichas visibles no tienen campos importantes pendientes.
- **Fichas con pendientes**: indica cuántas fichas visibles todavía necesitan completar algún campo público.
- **Campo más pendiente**: resume qué tipo de dato falta en más fichas visibles.
- **Siguiente ficha**: señala la ficha incompleta que conviene revisar primero.
- **Sedes explícitas**: cuenta cuántas sedes están guardadas como sedes separadas y cuántas clínicas son multisede.
- **Sedes sin Maps**: avisa si alguna sede guardada no tiene enlace a ficha de clínica en Google Maps.
- **Sedes sin valoraciones**: avisa si alguna sede guardada no tiene enlace directo a valoraciones de Google.
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
- En el editor de cada clínica, **Web pública** indica si esa ficha concreta
  tiene cambios guardados que todavía no se ven online.
- Si acabas de validar una ficha y no ves el cambio en vitalarga.com, mira
  **Web pública** en el editor: si dice que está pendiente, el dato está
  guardado y lo que falta es regenerar la web pública.

En **Necesitan revisión**, el botón **Abrir atasco** abre la primera tarjeta del
grupo repetido más importante cuando hay varias mejoras abiertas para la misma
clínica.

El bloque **Caso recomendado** resume la clínica que conviene trabajar como un
caso completo. Muestra cuántas tarjetas tiene abiertas, el orden sugerido y el
botón **Trabajar caso**. Cuando ya estás dentro de ese grupo, el botón cambia a
**Abrir primera tarjeta** y aparece **Ver toda la bandeja** para salir del
filtro.

El botón **Filtrar grupo** muestra juntas las tarjetas abiertas de la clínica
que más conviene revisar en bloque. Es útil cuando una misma clínica tiene claim,
auditoría, cambio de fuente y mejoras abiertas a la vez.

En los filtros rápidos de **Necesitan revisión**, usa **Especialistas** para ver
solo tarjetas que traen profesionales publicados o propuestas relacionadas con
equipo médico. Es la forma más rápida de completar ese apartado sin revisar toda
la bandeja. Al activar ese filtro, arriba salen primero las tarjetas con más
especialistas propuestos.

En la tabla de revisiones, las tarjetas con especialistas muestran una línea
explicando que esos nombres son **propuestas internas**. No aparecen en la web
hasta que abras la tarjeta, revises la fuente pública, cargues la propuesta en
el editor y guardes la ficha.

Si una tarjeta de especialistas muestra **fuente pendiente**, úsala con más
cuidado: primero abre la web oficial y confirma que esos profesionales aparecen
publicados por la clínica. **Fuente visible** solo significa que el panel tiene
un enlace para revisar, no que el dato esté aprobado.

El filtro rápido **Google Maps** muestra las tarjetas que traen un enlace directo
propuesto a Google Maps o a valoraciones de Google. Ábrelo, comprueba que el
enlace corresponde al perfil real de la clínica y solo entonces carga la
propuesta en la ficha. Si el enlace abre una búsqueda genérica, una dirección
suelta o un perfil dudoso, no lo guardes.

En las fichas, **Google Maps** es el enlace al perfil de la clínica en Google.
**Valoraciones Google** es el enlace directo a sus reseñas. Si no tenemos el
perfil real de la clínica, el campo queda pendiente; no usamos enlaces genéricos
a una dirección.

Si una tarjeta muestra un aviso bajo el enlace de Google Maps, trátalo como
pendiente: abre el enlace y guárdalo solo si ves la ficha real de la clínica.

Dentro de una tarjeta con varias revisiones relacionadas verás **Orden
recomendado**. Empieza por lo que marque ahí: normalmente claims bloqueantes o
fuentes cambiadas antes de guardar la ficha final.

El botón **Abrir fuente** abre la primera tarjeta relacionada con la ficha
marcada en **Siguiente fuente**. Si no hay una tarjeta exacta visible, filtra la
bandeja por esa clínica.

El botón **Abrir especialistas** abre la primera tarjeta relacionada con la
ficha marcada en **Siguiente especialistas**. Si no hay tarjeta exacta, filtra
la bandeja por esa clínica y por revisiones de especialistas.

Al editar una clínica, si aparecen **Detectados en revisión interna**, puedes
pulsar **Cargar al formulario** para pasar esos nombres al campo de
especialistas. Eso no guarda ni publica: solo prepara el formulario para que lo
revises antes de guardar.

En el editor de clínica, **Modalidad de atención** describe si la clínica es
presencial, online o mixta. No decide la publicación. La publicación se decide
con **Estado interno** o con el botón **Publicar**. Las sedes pueden ser
**físicas** u **online**, y cada sede puede quedar visible en la ficha pública o
solo interna.

Si una ficha está en borrador, puedes usar **Descartar ficha**. No borra la
clínica: la archiva, la deja fuera de la web y guarda el motivo en el historial.

Para contacto, puedes guardar teléfono principal, fijo, móvil y WhatsApp. La
búsqueda interna y la búsqueda pública también usan esos teléfonos.

Cuando la madurez diga **Lista para Daniel**, no significa que se active sola. Significa que ya se podría hablar de activar alguna categoría de bajo riesgo, siempre con tu aprobación.

Aunque aparezcan capturas candidatas a limpieza, el sistema no borra nada desde el panel. Borrar evidencias requiere una decisión explícita tuya.

En **Crear trabajo**, el panel avisa cuando la bandeja está casi llena. Si el
freno está cerca del límite, pausa crear más trabajos hasta limpiar revisiones.
Así evitamos llenar la bandeja con más tarjetas antes de cerrar las que ya
existen.

## Revisar mejoras de una ficha existente

Algunas tareas internas no son clínicas nuevas, sino mejoras para una ficha que ya existe.

1. Entra en **Necesitan revisión**.
2. Abre una tarjeta de tipo `clinic_profile_enrichment`.
3. Revisa los campos propuestos y sus fuentes.
4. Pulsa **Editar clínica**.
5. El panel carga la propuesta dentro del formulario.
6. Revisa el contenido, elige el estado de la ficha y guarda solo si te encaja.

Hasta que no guardes, la web pública no cambia. Después de guardar una ficha
publicada o preliminar, puede quedar **pendiente de verse online** hasta que se
ejecute la publicación agrupada.

En las tarjetas de mejora puede aparecer **Enlaces propuestos**. Ahí se muestran
clicables los enlaces que el sistema cree relevantes: Google Maps, valoraciones
de Google, página de precios o web propuesta. Es una ayuda de revisión, no una
aprobación automática.

Al abrir una revisión verás un bloque de contexto arriba. Si dice
**Candidata**, esa clínica todavía no está en la guía pública aunque tenga
profesionales detectados; primero se crea un borrador y después se decide si se
publica. Si dice **Mejora de ficha existente**, la información ya está asociada
a una clínica conocida, pero sigue pendiente de cargarla en el editor y
guardarla.

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

## Editar sedes de una clínica

En el editor de clínica, la sede principal se edita en los campos normales de
**Dirección**, **Google Maps** y **Valoraciones Google**. El apartado **Sedes
adicionales** solo se usa cuando la clínica tiene más de una ubicación.

El editor evita duplicar la sede principal debajo del formulario. También evita
etiquetas tipo “Sede 1” o “Sede 2”: usa sede principal y sedes adicionales para
que no parezca un ranking ni un contador.

Cada sede puede tener:

- Nombre de la sede.
- Ciudad.
- Dirección.
- Enlace directo al perfil de Google Maps.
- Enlace directo a valoraciones de Google.

Usa **Añadir sede** para crear otra ubicación y **Quitar** para eliminar una
sede que no quieras guardar. Si existe un enlace de Google Maps, debe ser el
perfil real de la clínica, no solo una búsqueda por dirección.

## Duplicados

Si el sistema detecta que una propuesta se parece mucho a una clínica existente, verás **Coincidencias en Vitalarga**.

Cuando sea un duplicado probable, el botón de crear borrador queda bloqueado. En ese caso, lo normal es descartarlo o revisarlo manualmente más adelante.

Si varias tarjetas abiertas intentan mejorar la misma ficha, la tabla muestra **Varias propuestas**. Puedes usar el filtro rápido **Atascos** para ver solo esas repeticiones.

Cuando abras una tarjeta y existan otras revisiones abiertas para la misma
clínica, verás **Otras revisiones de esta clínica**. Úsalo para revisar esas
tarjetas juntas y evitar resolver una propuesta sin mirar las relacionadas.

El sistema también puede generar un informe interno de consolidación para esas
mejoras duplicadas. Ese informe no cambia nada: solo dice qué campos se pueden
unir, qué fuentes hay detrás y si hay conflictos como dos teléfonos principales
distintos. Si no hay conflictos, lo normal es abrir el caso y usar **Cargar
mejoras juntas**.

## Editar una clínica

1. Baja al bloque **Clínicas**.
2. Busca la clínica por nombre o ciudad.
3. Usa el filtro de preparación si quieres ver solo fichas sin faltantes,
   fichas con faltantes, visibles con pendientes, pendientes de web pública o
   no visibles.
4. Mira la columna **Falta para publicar**: el primer campo en negrita es lo
   primero que conviene completar.
5. Pulsa **Editar**.
6. Cambia los datos que quieras: resumen, servicios, especialidades, unidades clínicas, especialistas, contacto, sedes, Google Maps, valoraciones Google y transparencia pública.
7. Mira el bloque **Validación final**.
8. El botón de guardar cambia según el estado elegido: **Guardar borrador**,
   **Guardar en revisión**, **Guardar como preliminar** o **Guardar como publicada**.
9. Guarda cuando esté correcto.

Si eliges **Preliminar** o **Publicada** y todavía hay claims bloqueantes,
**Validación final** lo marcará como pendiente y el aviso de guardado te lo
recordará antes de mandar la ficha a la web.

Si una clínica tiene varias ubicaciones, usa **Sedes**. La **Dirección** sigue
sirviendo como sede principal para fichas simples. En la web pública,
**Google Maps** debe abrir la ficha de la clínica en Google Maps cuando tengamos
ese enlace directo guardado. Si todavía falta, no mostramos botón de Google
Maps: queda pendiente hasta encontrar la ficha real de la clínica. El enlace
directo a valoraciones de Google se guarda aparte cuando exista.

Si el sistema ha encontrado sedes en una propuesta o en una evidencia interna,
el editor puede mostrar **Sedes detectadas en revisión interna**. Ese bloque no
publica nada por sí solo: pulsa **Cargar sedes al formulario**, revisa ciudad,
dirección y Google Maps, y después guarda la ficha solo si está correcto.

En **Validación final**, Google Maps queda como pendiente si el enlace parece
una búsqueda genérica, una ruta o una dirección suelta en vez de un perfil de
clínica.

Los campos de transparencia —años en ejercicio, número de especialistas,
colegiación visible y precio público— solo deben rellenarse cuando salgan de una
fuente pública revisable. No son rankings ni recomendaciones.

Si la clínica está como **Publicada** o **Preliminar**, el cambio se manda a la web automáticamente. Puede tardar unos minutos.
Si está como **Borrador**, **Revisión**, **Descubierta**, **Extraída**, **Verificada** o **Archivada**, se guarda dentro del panel pero no aparece como ficha pública.

Si una ficha aparece como **Pendiente de web**, no es que se haya perdido el
cambio: está guardado en el admin y falta que la web pública se actualice en el
lote correspondiente.

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
