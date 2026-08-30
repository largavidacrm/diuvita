# Límites operativos de Diuvita

Fuente: texto aportado por Daniel e integrado en el proyecto el 2026-08-30.

Propósito: servir como guía de referencia para decisiones de producto, contenido,
automatización, datos y publicación en `www.diuvita.com`.

## Contexto

Diuvita es una guía informativa e independiente de clínicas de medicina de
longevidad en España. Su posicionamiento legal es deliberado y es la principal
protección jurídica del proyecto: contenido editorial neutro, sin publicidad
sanitaria, sin rankings, sin pago por aparecer y sin recomendaciones médicas.
Ninguna tarea de contenido, producto o código puede erosionar ese perímetro
sin decisión expresa de Daniel.

## Regla central: protocolo de escalado

Si una tarea toca cualquiera de los límites siguientes, o existe duda razonable
de si los toca, detenerse y preguntar a Daniel antes de actuar. Queda prohibido:

- implementar sin preguntar;
- descartar u omitir en silencio la parte conflictiva;
- resolver por iniciativa propia con una versión "suavizada".

Se presenta el conflicto y se espera decisión.

Formato obligatorio de consulta:

```text
⚠️ LÍMITE DETECTADO
- Qué se pretendía hacer: [descripción]
- Límite afectado: [número y nombre]
- Riesgo en una frase: [explicación]
- Opciones: (1) [alternativa segura] (2) [hacerlo con autorización] (3) no hacerlo
- No he implementado ni descartado nada. Quedo a la espera de tu decisión.
```

## Límites duros

Estos límites nunca se cruzan sin autorización expresa de Daniel.

### L1 · Imágenes

No publicar, descargar, incrustar ni reutilizar fotografías de clínicas,
instalaciones, personal o pacientes, aunque estén en la web de la propia clínica
o en Google.

Solo se permiten:

- logos oficiales usados para identificar al centro;
- material creado por Diuvita o con licencia escrita.

Cualquier otra imagen exige preguntar.

### L2 · Recomendaciones médicas

No recomendar clínicas, tratamientos, pruebas, suplementos ni pautas de salud a
nadie, en ningún formato: fichas, blog, FAQ, metadescripciones, redes o
respuestas a usuarios.

No responder consultas de salud individuales.

Información general con fuentes no equivale a consejo. Expresiones del tipo
"la mejor opción para ti", "te conviene" o "deberías hacerte" están prohibidas.

### L3 · Rankings y comparativas

No ordenar clínicas por calidad ni crear "top", "mejor", estrellas,
puntuaciones o comparativas que impliquen superioridad de un centro sobre otro.

Sí se permite orden neutro: alfabético, geográfico o por especialidad.

### L4 · Claims terapéuticos

No afirmar que un tratamiento cura, revierte, rejuvenece o alarga la vida, ni
atribuir eficacia no acreditada.

Los claims de cada clínica se describen en estilo atributivo neutro, por ejemplo
"la clínica ofrece" o "la clínica afirma", nunca como hechos validados por
Diuvita.

### L5 · Testimonios y pacientes

No publicar testimonios, reseñas de pacientes, fotos antes/después ni casos
clínicos.

### L6 · Datos personales

Datos de pacientes: nunca.

Datos de profesionales: solo información profesional pública, como nombre,
especialidad, cargo o colegiación.

Toda petición de supresión, rectificación u oposición recibida se escala
siempre, sin ejecutar ni ignorar.

### L7 · Neutralidad respecto a Monarka Clinic

Monarka se trata exactamente igual que el resto: misma estructura, extensión,
tono y orden neutro.

Cualquier contenido o decisión editorial que favorezca a Monarka, o que la
afecte de forma distinta al resto de clínicas, exige preguntar.

### L8 · Monetización y publicidad

No introducir ni sugerir en el sitio pago por aparecer, destacados, afiliación,
enlaces patrocinados ni publicidad de clínicas, tratamientos o productos.

Cualquier vía de ingresos exige preguntar porque cambia el régimen legal
completo del proyecto.

### L9 · Textos de terceros

No copiar textos de webs de clínicas ni de medios.

La redacción debe ser original siempre. Solo se permiten citas mínimas y con
fuente. Sin scraping masivo.

### L10 · Textos legales y afirmaciones sobre la guía

No crear ni modificar el aviso legal, la política de privacidad, cookies, los
criterios de inclusión ni afirmaciones del tipo "independiente", "sin pago" o
"revisado manualmente" sin aprobación previa.

### L11 · Comunicaciones salientes

No enviar emails ni mensajes a clínicas, profesionales o usuarios en nombre de
Diuvita sin aprobación previa del texto y del destinatario.

### L12 · Nuevas funcionalidades con dimensión legal

Buscadores o formularios que pidan datos de salud del usuario, chatbots de cara
al público, cuentas de usuario, reseñas de usuarios y newsletters solo se
diseñan o implementan con aprobación previa.

### L13 · Exactitud de las fichas

No publicar afirmaciones fácticas no verificables sobre una clínica, como
precios, resultados, acreditaciones o titulaciones, sin fuente pública
comprobable.

Toda petición de una clínica, ya sea alta, baja o corrección, se escala siempre.

## Zona verde

Estas tareas se pueden avanzar sin necesidad de preguntar:

- Redactar y editar fichas descriptivas neutras a partir de información pública
  verificable, con el estilo actual del sitio.
- Crear contenido educativo general del blog sobre medicina de longevidad, con
  fuentes científicas, sin consejo individual y cerrando con la indicación de
  consultar a un profesional sanitario.
- Mejorar SEO técnico, estructura, rendimiento, accesibilidad y correcciones de
  estilo o erratas que no alteren el sentido.
- Crear filtros y ordenaciones neutras: ciudad, país, especialidad o alfabético.

## Herramientas internas

El escáner `scripts/check_operational_limits.py` detecta señales públicas obvias
de estos límites. El modo normal se usa en las comprobaciones locales.

Para una revisión editorial más estricta de rankings, premios o lenguaje de
calidad/precio:

```bash
python3 scripts/check_operational_limits.py --strict-editorial
```

Ese modo es deliberadamente más sensible y sirve para preparar decisiones de
Daniel; no cambia contenido ni publica nada.

## Criterio residual

Ante cualquier situación no prevista con posible dimensión legal, médica o
reputacional, preguntar.

Preguntar de más no tiene coste; implementar o descartar de más, sí.

## Protección técnica

El repositorio incluye `scripts/check_operational_limits.py`, una comprobación
conservadora para detectar señales obvias de riesgo en contenido público:
recomendaciones directas, rankings, claims terapéuticos, testimonios o señales
de publicidad/afiliación.

La comprobación se ejecuta sobre los archivos fuente y también sobre las
páginas públicas ya generadas en `dist/`. No sustituye la revisión de Daniel,
pero ayuda a evitar que un texto problemático entre por accidente en el build
o en el despliegue de Netlify.
