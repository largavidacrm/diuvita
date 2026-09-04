# Guía rápida del panel Vitalarga

URL del panel:

```text
https://www.vitalarga.com/admin/
```

URL local de trabajo, cuando Codex deja un servidor abierto:

```text
http://127.0.0.1:PUERTO/admin/
```

Usa siempre el enlace local concreto que te dé Codex en ese momento. Si hay
varias pestañas con puertos distintos, normalmente vale el más reciente. El
acceso local sirve solo la web generada en `dist/`. No publica producción, no
toca Netlify y no expone el archivo `.env`. En local, la cabecera puede mostrar
un distintivo **Local · rama · commit** para confirmar que estás mirando la
versión que Codex acaba de preparar.

El botón de menú de la cabecera permite reducir o mostrar la barra lateral
izquierda. Sirve para ganar anchura cuando estés revisando fichas largas.

## Revisar clínicas nuevas

1. Entra con tu usuario autorizado.
2. Mira el bloque **Necesitan revisión**.
3. Usa los filtros si quieres acotar por tipo, prioridad, Google Maps o
   especialistas.
4. Pulsa **Revisar** en una propuesta concreta.
5. Comprueba nombre, web, ciudad, fuente, servicios y especialistas detectados.
6. Si parece una clínica válida, pulsa **Aprobar**. En una clínica nueva, eso
   crea un borrador interno para editarlo con calma.
7. Si no encaja con Vitalarga, pulsa **Rechazar**.
8. Si el dato es útil pero necesita corrección, pulsa **Modificar**, cambia
   solo los campos que aparecen en esa propuesta y confirma con **Guardar
   modificación**.

Aprobar una clínica nueva no publica la clínica. Solo crea una ficha interna.
El botón de publicar aparece después, al editar esa ficha, dentro de
**Validación final**.

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

Puedes pulsar **Abrir prioridad** para ir directamente a la tarjeta concreta
que conviene decidir primero. **Filtrar grupo** sigue disponible como ayuda
secundaria cuando una clínica concentra varias tarjetas, pero no sustituye la
decisión una por una. Si ves “control interno”, no significa que la web esté
rota: significa que toca limpiar revisiones antes de subir la autonomía.

Si **Tú ahora** dice **No crees trabajos nuevos**, usa primero **Abrir
prioridad** para cerrar la propuesta pendiente. Después puedes usar
**Especialistas**, **Google Maps** o **Filtrar grupo** si ayudan a bajar la cola.

Si **Tu próximo clic** dice **Revisar reclamación**, abre esa tarjeta antes de
crear nuevas fichas. Una reclamación de ficha no confirma identidad, no concede
acceso y no cambia datos públicos: solo avisa de que Daniel debe decidir el
siguiente paso.

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
- **Fichas pendientes**: resume las fichas incompletas sin convertir una clínica secundaria en prioridad si ya hay una tarjeta concreta que revisar.
- **Listas para publicar**: cuenta cuántas fichas no archivadas no tienen faltantes obligatorios.
- **Faltantes publicación**: indica cuántas fichas siguen bloqueadas antes de poder pasar a preliminar o publicada.
- **Principal faltante**: resume el primer tipo de bloqueo repetido, por ejemplo Google Maps de clínica.
- **Siguiente publicación**: señala la ficha con más puntos obligatorios pendientes para trabajarla primero.
- **Sedes explícitas**: cuenta cuántas sedes están guardadas como sedes separadas y cuántas clínicas son multisede.
- **Sedes sin Maps**: avisa si alguna sede guardada no tiene enlace a ficha de clínica en Google Maps.
- **Sedes sin valoraciones**: avisa si alguna sede guardada no tiene enlace directo a valoraciones de Google.
- **Freno bandeja**: avisa si el sistema está cerca de pausar pasos que crean
  más tarjetas internas y cuántas propuestas quedan antes de la pausa
  preventiva. La pausa empieza antes del límite máximo para no llenar la cola.
- **Reclamaciones de ficha**: solicitudes de una clínica para revisar una ficha; siempre requieren decisión humana.
- **Contexto de grupo**: señala qué clínica concentra varias tarjetas abiertas para que puedas filtrarlas y abrirlas una por una, pero no sustituye la prioridad principal.
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

Cuando tengas duda de si una mejora técnica del panel ya está online o sigue
solo en este worktree, Codex puede usar el informe interno de preparación para
publicación. Ese informe no publica nada: solo separa cambios locales, commits
pendientes y comprobaciones de la web pública. La sección **Lectura para
Daniel** es la respuesta corta: si dice que hay commits locales pendientes o que
producción no está comprobada, trátalo como **no demostrado online**.

En **Necesitan revisión**, la bandeja se mantiene deliberadamente simple:
filtros, tabla y botón **Revisar**. El sistema puede usar señales internas para
ordenar trabajo o para futura ayuda con LLM, pero no mezcla esas prioridades
con la decisión que tienes delante.

La bandeja agrupa visualmente por ficha cuando una clínica acumula varias
mejoras. Por debajo siguen existiendo decisiones separadas para que la IA, las
fuentes y el historial no mezclen cambios. En la práctica, ves una ficha de
clínica en la lista y, al abrirla, decides una propuesta concreta cada vez.

Si varias tarjetas tienen la misma prioridad y fecha, el panel desempata de
forma estable por título e identificador interno. Así el listado, el plan global
y los informes de Codex señalan la misma siguiente tarjeta.

El filtro **Reclamaciones** muestra solicitudes de clínicas sobre una ficha.
Úsalo para revisar quién reclama la ficha y decidir si hace falta pedir prueba,
conceder acceso o rechazar la solicitud. El sistema no concede acceso ni edita
la ficha automáticamente.

Si apruebas una reclamación de ficha, el panel registra el interlocutor en
**Contacto interno** dentro de la ficha. Ese apartado no es visible en la web
pública y no concede acceso por sí solo.

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

Si una propuesta de especialistas trae nombres mezclados con textos como
**Aviso Legal**, **COLABORADORES**, sociedades profesionales, menús o categorías
médicas, el panel la marcará como algo que hay que corregir antes de aprobar.
Usa **Modificar** y deja solo nombres claros publicados por la clínica, o
rechaza la propuesta.

Si sabes dónde está la fuente oficial, por ejemplo una página de equipo o
especialistas de la propia clínica, puedes pegarla en **Dile al agente dónde
mirar** dentro de esa revisión. El agente usará esa URL solo para preparar una
nueva propuesta revisable de especialistas; no guarda nombres ni publica nada
automáticamente.

El filtro rápido **Google Maps** muestra las tarjetas que traen cualquier enlace
propuesto a Google Maps o a valoraciones de Google, tanto si parece bueno como
si parece dudoso. Ábrelo, comprueba que el enlace corresponde al perfil real de
la clínica y solo entonces carga la propuesta en la ficha. Si el enlace abre una
búsqueda genérica, una dirección suelta o un perfil dudoso, no lo guardes.

Dentro de una propuesta, la etiqueta junto al dato te dice qué tipo de decisión
espera ese campo. **Perfil revisable** no significa aprobado: significa que el
enlace tiene forma de ficha de Google Maps y aun así debes abrirlo y comprobar
que es la clínica correcta.

En las propuestas de Google Maps también verás un estado compacto del enlace.
**Parece perfil directo** significa que el formato encaja con una ficha de
Google Maps, pero sigue siendo obligatorio abrirlo y confirmar que corresponde
a esa clínica. La tarjeta muestra una **Comprobación manual** con el nombre de
la ficha que debe coincidir en Google. **No guardar tal cual** significa que
parece búsqueda, ruta, dirección suelta o enlace insuficiente.

En las revisiones manuales de calidad, al pulsar **Revisar** primero se abre la
vista en columnas: ficha de la clínica y revisión concreta. Desde ahí,
**Modificar** o **Revisión manual** abre la ficha en el campo pendiente. Al
guardar, esa revisión queda cerrada solo para ese campo y vuelves a la lista.
Si la misma tarjeta tenía más faltantes, seguirán apareciendo como revisiones
pendientes; no los da por resueltos en bloque. En la propia lista verás una línea **Abrirá:**
para saber antes de entrar qué campo se va a editar.

En la vista en columnas puedes pulsar **Editar ficha** en el panel izquierdo
para corregir directamente datos generales de la clínica, como nombre,
descripción, web, ubicación, sedes, servicios, especialistas o contacto. Esos
cambios no se guardan al escribirlos: solo se aplican si apruebas la propuesta
o guardas una modificación. Si rechazas la propuesta, esas correcciones no se
aplican. Mientras editas, verás un resumen corto de los cambios manuales
preparados para comprobarlos antes de decidir.
También puedes corregir ahí el **Contacto interno** de la clínica. Ese apartado
es privado de operación y no se muestra en la web pública.

Al entrar en la ficha desde **Revisión manual**, arriba verás una banda con el
campo afectado y el motivo exacto de la tarjeta. Si sabes que el dato está en
una página oficial de la clínica, puedes pegar esa URL en **Enviar al
agente**; el agente/LLM la usará para el campo que estás revisando. Siempre crea
propuestas revisables, sin publicar ni guardar datos automáticamente.
El editor abre el bloque correspondiente y marca visualmente el campo activo
para que no tengas que buscarlo por toda la ficha.

En las fichas, **Google Maps** es el enlace al perfil de la clínica en Google.
Las valoraciones no se guardan como campo independiente: si Daniel quiere
verlas, están dentro del propio perfil de Google Maps. Si no tenemos el perfil
real de la clínica, Google Maps queda pendiente; no usamos enlaces genéricos a
una dirección.

Si una tarjeta muestra un aviso bajo el enlace de Google Maps, trátalo como
pendiente: abre el enlace y apruébalo solo si ves la ficha real de la clínica.

Cuando una misma clínica tenga varias tarjetas abiertas, el panel puede usarlo
como señal interna para ordenar prioridades o filtrar la lista. Al abrir una tarjeta, aun así,
decides solo esa propuesta: aprobar, rechazar o modificar. No se mezclan varias
decisiones dentro de la misma ficha.

Si una propuesta muestra **Contacto dudoso**, no la apruebes tal cual: significa
que trae un teléfono con forma rara o mezclada. Puedes modificar solo ese campo,
separarlo en fijo/móvil/WhatsApp si procede o rechazarlo si no es claramente un
contacto. Si el panel ya separa dos números claros en principal/fijo/móvil,
revísalos igualmente antes de aprobar: la separación ayuda, pero no aprueba el
dato.

Al editar una clínica, si aparecen **Detectados en revisión interna**, puedes
pulsar **Cargar al formulario** para pasar esos nombres al campo de
especialistas. Eso no guarda ni publica: solo prepara el formulario para que lo
revises antes de guardar.

Si una revisión manual dice que faltan datos pero la fuente está clara, abre la
tarjeta: primero verás la ficha y la revisión en columnas. Desde ahí, pulsa
**Modificar** o **Revisión manual** para abrir directamente el campo que toca en
la ficha. Si conoces una URL oficial donde el agente debe mirar, pégala en
**URL oficial para el agente** y pulsa **Enviar al agente**. Por ejemplo, si
faltan especialistas, pega la página oficial de equipo o especialistas. Eso
crea trabajo interno para propuestas revisables, limitado a los campos
pendientes de esa tarjeta; no guarda ni publica datos.

Codex también puede generar una lectura interna de rutas de revisión manual.
Sirve para saber qué tarjetas deben abrir un campo concreto, cuáles permiten
pegar una URL oficial para el agente y cuáles siguen siendo solo revisión
humana. Esa lectura no llama a ningún LLM, no cambia datos y no resuelve
tarjetas.
El ciclo CTO interno también puede incluir esa lectura para preparar futura
ayuda LLM, pero la decisión sigue estando en el panel: una tarjeta, una
decisión humana.

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

En el menú lateral tienes **Recomendar clínica**. Ahí puedes crear trabajo
para el agente sin tocar la web: escribe una petición en texto libre, pega un
link oficial si lo tienes, elige si es una clínica nueva o una ficha existente,
y, si quieres, indica qué dato quieres que revise. No hay que usar ejemplos
prefijados: una frase como "Neleva, completar especialistas" y un link oficial
son suficientes. El trabajo entra en la cola interna. El panel avisa cuando la
bandeja está casi llena. Si el freno está cerca del límite, pausa crear más
trabajos hasta limpiar revisiones. Así evitamos llenar la bandeja con más
propuestas antes de cerrar las que ya existen.

Para completar una clínica existente, elige **Completar clínica existente**,
selecciona la ficha, pega una URL oficial y, si quieres, indica qué información
buscas: especialistas, servicios, sedes, contacto, Google Maps u otro campo. El
campo **Nota para el agente** sirve para escribir frases normales, por ejemplo
"en esta página está todo el equipo; completar especialistas publicados". El
trabajo queda en **Trabajos pendientes** hasta que lo procese el ciclo CTO
supervisado. Cuando haya datos revisables, volverá como propuesta; no se guarda
ni publica automáticamente.

En **Trabajos** verás primero **Trabajos pendientes** y después **Trabajos
recientes**. Pendiente significa que el agente todavía tiene que procesarlo o
lo está procesando; completado significa que ya terminó y, si encontró datos
útiles, dejó una propuesta para revisar. En cada trabajo pendiente verás una
línea breve de **Siguiente**: si hay link oficial, puede procesarse en el ciclo
CTO; si solo hay texto libre, espera un proveedor real de búsqueda o que se
añada una fuente oficial.

Si una recomendación tiene **link oficial**, el ciclo CTO puede procesarla y
convertirla en una propuesta de clínica candidata. Si solo tiene texto libre,
queda pendiente hasta que activemos un proveedor real de búsqueda; el sistema
no inventa clínicas desde una frase suelta.

En la web pública hay un botón **Recomendar Clínica**. Cualquier visitante puede
enviar una clínica o una fuente oficial. Eso entra aquí como trabajo pendiente:
no crea ficha pública, no cambia una clínica existente y no aprueba nada sin
revisión humana.

La pantalla de revisión tiene dos momentos. Primero ves la bandeja con sus
filtros y una columna lateral de selección. Al pulsar **Revisar** en una
ficha, la bandeja se oculta y se abre la ficha de la clínica en el centro,
con la decisión concreta de esa propuesta a la derecha. Si la tarjeta es una
revisión manual de un campo pendiente, usa **Modificar** o **Revisión manual**
dentro de esa vista para abrir el campo exacto.

La tabla de revisión está pensada para escanear, no para leer fichas completas:
los títulos largos se recortan visualmente, las columnas mantienen anchuras
estables y el botón **Revisar** abre la ficha con una sola decisión activa.

## Revisar mejoras de una ficha existente

Algunas tareas internas no son clínicas nuevas, sino mejoras para una ficha que ya existe.

1. Entra en **Necesitan revisión**.
2. Abre una tarjeta de tipo `clinic_profile_enrichment`.
3. La columna central cambia de bandeja a **Ficha de la clínica** para que veas
   el contexto de esa clínica sin seguir mirando la cola.
4. La columna derecha muestra solo esa propuesta concreta: qué cambio se valora,
   fuente o evidencia, avisos imprescindibles y la observación breve.
5. Si la propuesta trae varias mini-tarjetas, puedes decidir cada campo ahí
   mismo con **Aprobar**, **Rechazar** o **Modificar**. Al resolver un campo,
   desaparece de esa propuesta y queda registrado en la tarjeta.
6. Elige una sola acción global: **Aprobar**, **Rechazar** o **Modificar** solo
   cuando quieras resolver toda la propuesta de una vez.
7. Si modificas, corrige únicamente los campos que vienen en esa propuesta y
   confirma con **Guardar modificación**.
   En revisiones manuales, **Modificar** o **Revisión manual** te lleva al campo
   que falta.
8. Al terminar, el panel cierra esa ficha y vuelve a la lista. Tú eliges la
   siguiente revisión; el panel no salta automáticamente a otra tarjeta.

La aprobación aplica la propuesta mediante el flujo existente, pero no cambia la
publicación por accidente. Datos sensibles, Google Maps dudoso, precios, equipo
o claims conflictivos siguen requiriendo revisión humana y pueden quedar
bloqueados como aviso.

Hasta que no guardes, la web pública no cambia. Después de guardar una ficha
publicada o preliminar, queda **pendiente de verse online**. Termina primero el
lote de ediciones y pulsa una sola vez **Actualizar web ahora**.

Si ves una tarjeta llamada **Claim bloqueante**, significa que el sistema encontró una evidencia en conflicto o sin fuente suficiente. Ábrela, revisa **Fuente o evidencia** y decide si apruebas, rechazas o modificas esa propuesta. Un claim rechazado normal no te bloquea: simplemente queda fuera de publicación y sirve para medir la precisión del sistema.

Si ves una tarjeta llamada **Reclamación de ficha**, trátala como una solicitud
de verificación humana. La tarjeta sirve para mirar contexto, pero no crea
borrador, no publica, no cambia datos y no concede acceso por sí sola. Daniel
decide si se pide prueba, si se acepta o si se cierra.

En las tarjetas de claims bloqueantes verás avisos imprescindibles. No son una
decisión automática: te orientan sobre si conviene comparar evidencias, buscar
una fuente oficial o dejar ese dato fuera de publicación.

En **Fuente o evidencia**, cada propuesta muestra los enlaces o datos que
justifican el cambio cuando existen. Eso te permite ver de dónde sale un dato
sin leer información técnica cruda.

Si ves **Fuente sin contexto de tarea**, significa que el enlace sirve como
evidencia para revisar, pero no sabemos qué quería pedir exactamente el trabajo
original. No se usa como orden para el LLM ni para completar otros campos.
Si la tarjeta ya trae campos propuestos, puedes aprobarlos, rechazarlos o
modificarlos manualmente; lo único bloqueado es pedirle al LLM que amplíe la
ficha desde esa fuente sin contexto.

Si pegas una **URL oficial para el agente**, la revisión actual se cierra y
desaparece de la cola visible. El agente solo puede crear una nueva propuesta
revisable con lo que haya encontrado; no publica ni guarda datos directamente en
la ficha. Ese trabajo no se ejecuta al pulsar **Actualizar**: queda en cola para
el ciclo CTO supervisado. Cuando Codex procesa esa cola con extracción de URL de
revisión, si encuentra datos claros crea o refresca una propuesta revisable y la
tarjeta original queda cerrada como sustituida. Si no encuentra nada útil, queda
registrado como trabajo revisado/fallido según el resultado, sin tocar la ficha
pública.

Puedes usar el filtro **Claims bloqueantes** para ver solo ese tipo de revisión.
Puedes usar el filtro **Especialistas** para ver solo tarjetas que mencionan
especialistas publicados o profesionales detectados.

Al abrir una tarjeta, no verás caminos de publicación, otras revisiones,
resúmenes de cola ni acciones para crear trabajo. Verás la ficha de la clínica
en el centro y la decisión de esa propuesta a la derecha. La ficha abierta
representa una propuesta y una decisión.

## Editar sedes de una clínica

En el editor de clínica, la sede principal se edita en los campos normales de
**Dirección** y **Google Maps**. El apartado **Sedes adicionales** solo se usa
cuando la clínica tiene más de una ubicación.

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

El sistema también puede generar un informe interno de consolidación para esas
mejoras duplicadas. Ese informe no cambia nada: solo dice qué campos se repiten,
qué fuentes hay detrás y si hay conflictos como dos teléfonos principales
distintos. Sirve para priorizar y para futura ayuda con LLM, pero la decisión en
el panel sigue siendo una propuesta cada vez.

Si una propuesta de teléfono muestra un aviso, no la apruebes tal cual. Ese
valor no parece un teléfono español real; modifícalo o recházalo. Así evitamos
convertir identificadores, colegiaciones u otros números internos en contacto
público.

## Editar una clínica

1. Baja al bloque **Clínicas**.
2. Busca la clínica por nombre o ciudad.
3. Usa el filtro de preparación si quieres ver solo fichas sin faltantes,
   fichas con faltantes, visibles con pendientes, pendientes de web pública o
   no visibles.
4. Mira la columna **Falta para publicar**: el primer campo en negrita es lo
   primero que conviene completar.
5. Pulsa **Editar**.
6. Cambia los datos que quieras: resumen, servicios, especialidades, unidades
   clínicas, especialistas, contacto público, contacto interno no visible en
   web, sedes, Google Maps, valoraciones Google y transparencia pública.
7. Mira el bloque **Validación final**.
8. El botón de guardar cambia según el estado elegido: **Guardar borrador**,
   **Guardar en revisión**, **Guardar como preliminar** o **Guardar como publicada**.
9. Guarda cuando esté correcto.

Si eliges **Preliminar** o **Publicada** y todavía hay claims bloqueantes,
**Validación final** lo marcará como pendiente y el aviso de guardado te lo
recordará antes de mandar la ficha a la web.
Si el sistema aún está comprobando claims, el botón de publicar puede pedirte
esperar o reintentar la carga; no debería mostrar como faltante la frase
positiva **Sin claims bloqueantes pendientes**.

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

En **Recomendar clínica**, puedes elegir **Auditar fichas existentes**.

Eso revisa las fichas visibles y crea tareas si falta algo importante, por ejemplo especialistas, servicios, especialidades, dirección, resumen o contacto.
Puedes dejarlo en toda la base, o elegir una clínica concreta de Vitalarga.
Si eliges una clínica y un dato, por ejemplo **Tiara Health** y **Especialistas publicados**, la auditoría queda acotada a esa ficha y a ese campo.
En **Alcance opcional** puedes pegar una nota o un link oficial para orientar el trabajo.

La revisión manual no cambia la web. Solo crea tareas internas para revisar.

## Estados importantes

- **Publicada**: aparece en la web.
- **Preliminar**: aparece en la web con aviso de ficha preliminar.
- **Descubierta**, **Borrador**, **Revisión** o **Archivada**: no aparecen en la web pública.

## Qué revisar mañana

Revisa primero las propuestas internas de ampliación de fichas publicadas que aparecen en **Necesitan revisión**. Esas propuestas están en Supabase como revisión interna; todavía no han cambiado la web pública.
