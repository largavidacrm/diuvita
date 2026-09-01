# Vitalarga SEO readiness

Fecha de trabajo: 2026-09-01

Este documento fija el estado pre-SEO de Vitalarga desde el repositorio local.
Sirve para decidir que se puede mejorar ya y que debe esperar hasta que la
calidad de datos este mas madura.

## Principio operativo

Vitalarga puede avanzar SEO tecnico sin convertir la guia en ranking,
recomendacion medica ni contenido medico promocional.

La regla base es:

- SEO tecnico: permitido si mejora rastreo, estructura, rendimiento,
  accesibilidad, canonical, sitemap, robots, titles, metadescriptions, schema
  prudente o enlaces internos.
- SEO programatico: esperar hasta cerrar mejor bandeja, trazabilidad y campos
  base.
- Datos de clinicas: cualquier dato medico, contacto, equipo, precio o prueba
  encontrado por agentes queda como propuesta revisable con fuente. No se
  publica automaticamente.
- Google Maps: solo vale el perfil real de la clinica. Busquedas, direcciones
  genericas y enlaces de rutas siguen pendientes.

## Estado tecnico observado

El generador local ya incluye piezas tecnicas necesarias:

- dominio canonico: `https://www.vitalarga.com`;
- `sitemap.xml` generado desde paginas principales, legales, fichas, ciudades
  y blog;
- `robots.txt` con sitemap publico;
- etiqueta canonical por pagina;
- titles y metadescriptions por pagina;
- schema prudente `WebSite`, `MedicalClinic` y `Article`;
- `/admin/` marcado con `noindex,nofollow`;
- escaner de limites operativos para fuente y sitio construido;
- checks de salud publica separados de los checks locales.

Esto no significa que el SEO completo este listo para crecer en volumen. Solo
significa que la base tecnica existe y se puede seguir endureciendo en local.

## Gates antes de SEO programatico

Antes de crear muchas landings por ciudad, tratamiento, prueba o comparativa,
deben cumplirse estos gates:

1. Bandeja de revision en zona manejable, idealmente 25 o menos tarjetas
   abiertas.
2. Cada ficha publicable debe explicar con claridad que falta para publicarse.
3. Campos base visibles o pendientes de forma trazable:
   - resumen;
   - Google Maps directo de la clinica;
   - contacto publico;
   - modalidad presencial, online o mixta;
   - fuente visible;
   - ultima verificacion.
4. Estructura preparada para comparabilidad sin publicar automaticamente:
   - REGCESS o registro sanitario;
   - idiomas;
   - pruebas concretas;
   - precio publico si existe;
   - que incluye el chequeo inicial;
   - duracion del chequeo inicial.
5. Propuestas de agentes acotadas a una clinica, un grupo de campos y una
   fuente concreta cuando Daniel aporte una URL.
6. Ningun claim medico, precio, profesional o dato de contacto debe saltarse la
   revision humana.

## Orden publico

El orden publico deseado es neutro y rotatorio, con una indicacion visible de
que no es ranking ni recomendacion.

Estado local: implementado como rotacion visible diaria en listas publicas y
carrusel de logos. Debe verificarse que:

- no favorece de forma estable a una clinica concreta;
- no crea lenguaje de recomendacion, calidad, superioridad o ranking;
- no toca datos sensibles;
- no anade declaraciones publicas nuevas de ownership, independencia,
  vinculacion comercial o monetizacion sin aprobacion explicita.

## Trabajo SEO permitido ahora

Se puede avanzar localmente en:

- revisar y reforzar sitemap, robots y canonical;
- revisar titles y metadescriptions para evitar claims o lenguaje de ranking;
- revisar schema prudente y minimo;
- mejorar enlaces internos entre home, ciudad, ficha y contenidos existentes;
- comprobar que `/admin/` queda fuera de indexacion;
- medir salud publica sin publicar ni desplegar;
- documentar gaps y crear tests que eviten regresiones.

## Trabajo que espera

Debe esperar hasta cerrar datos y bandeja:

- landings programaticas masivas;
- paginas por tratamiento, prueba, precio o comparativa;
- textos que sugieran mejor clinica, top, ranking, recomendacion o eleccion
  medica;
- automatizacion de publicacion de datos medicos, equipo, precios o contacto;
- cualquier declaracion publica nueva sobre independencia, ownership,
  vinculacion comercial, publicidad o monetizacion.

## Verificacion local

Checks relevantes:

```bash
python3 scripts/run_local_checks.py
python3 scripts/check_operational_limits.py
python3 scripts/check_operational_limits.py --built-site
python3 scripts/release_readiness_report.py
python3 scripts/check_production_health.py
python3 scripts/check_public_site_freshness.py
```

Los dos ultimos miran la web publica de forma read-only cuando se ejecutan con
red disponible. No hacen push, no despliegan, no escriben en Supabase y no
resuelven revisiones.

## Lectura para Daniel

La base tecnica SEO puede seguir mejorando ya en local. Lo que no conviene aun
es crecer con muchas paginas nuevas hasta que las fichas tengan datos base mas
limpios, la bandeja sea facil de revisar y cada propuesta tenga fuente clara.
