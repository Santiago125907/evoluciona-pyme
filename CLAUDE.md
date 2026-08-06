# evoluciona_pyme_v2

App Frappe de contabilidad y gestión de clientes para Evoluciona Pyme.

## Infraestructura

- **Backend (Frappe)**: `comando.evolucionapyme.cl` — bench en `/home/frappe/frappe-bench`, sitio `comando.evolucionapyme.cl`. Corre bajo el usuario del sistema `frappe` (usar `sudo -u frappe bash -lc '...'` para bench/git en ese directorio).
- **Portal**: `portal.evolucionapyme.cl` — frontend estático (Vite/React) en `/var/www/portal-src`, su `/api/` hace proxy al backend Frappe.
- **Repo**: https://github.com/Santiago125907/evoluciona-pyme (remote `upstream`)

## Flujo de ramas

- `develop` es la rama estable, espejo de lo que corre en producción. **No commitear directo acá.**
- Cada funcionalidad nueva va en su propia rama `feature/<nombre>` creada desde `develop`.
- Al terminar una feature: push de la rama + Pull Request a `develop` para revisión antes de mergear.
- Rama de trabajo actual: ver `git branch` — la que esté activa es la que se está usando para el desarrollo en curso.

## ⚠️ Seguridad en `bench migrate` — no reintroducir

Hasta agosto 2026 la app tenía hooks custom (`before_migrate` / `after_migrate` en `hooks.py`) que forzaban
`frappe.reload_doc(..., force=True)` sobre todos los DocTypes antes y después del migrate estándar. Esto
ignoraba la comparación de timestamps que Frappe usa como salvaguarda, y en la práctica **pisaba y dropeaba
columnas** cuando el JSON en el repo estaba desactualizado respecto a la DB real. Fue la causa de pérdida de
datos/tablas en producción.

Se removieron esos hooks (commit `c0f7ad2`). Reglas para el futuro:

- **No usar `force=True`** en `reload_doc` dentro de hooks de migrate.
- Si un campo se agrega/edita directo en producción vía "Customize Form" en el Desk, hay que exportarlo al
  `.json` del DocType en el repo (modo developer) antes de que otro ambiente corra `migrate`, o se pierde.
- Antes de correr `bench migrate` en producción: sacar backup primero (`bench --site comando.evolucionapyme.cl
  backup --with-files`).
- Confiar en el flujo estándar de Frappe (sync por timestamp + `fixtures` declarado en `hooks.py`) en vez de
  forzar sincronizaciones manuales.
- **Ojo con el campo `modified` del JSON de cada DocType.** Frappe decide si sincroniza un DocType comparando
  ese timestamp contra la DB — si se edita el `.json` a mano (fuera del Desk en developer mode, que es lo que
  normalmente lo actualiza solo) sin tocar `modified`, el campo nuevo queda en el archivo pero `bench migrate`
  lo salta para siempre pensando que no cambió nada. Pasó con `publicado_portal` en Declaracion_Mensual y otros
  3 campos en otros DocTypes (agosto 2026) — la columna ya existía en la tabla pero no estaba registrada como
  campo del DocType, y el código que la usaba tiraba `AttributeError`. Se arregló puntualmente con
  `bench --site comando.evolucionapyme.cl reload-doctype "<DocType>"` para cada uno (seguro: solo agrega
  metadata, no toca columnas que ya existen). Si un campo nuevo no aparece después de un migrate, sospechar de
  esto antes que nada.
- **El mismo problema aplica a las Pages del Desk** (ej. `panel_mensual.json`, `panel_app.json`): el campo
  `modified` de esos JSON controla el cache-busting del script de la página. Si editas el `.js` de una Page
  y el cambio "no aparece" pese a `bench build` + reiniciar procesos, sospecha de esto primero: bumpear
  `modified` en el `.json` de la Page y correr `frappe.reload_doc("evoluciona_pyme_v2", "page", "<nombre>", force=True)`
  puntual para esa página (en consola), más `bench clear-cache`.
- **Después de editar cualquier `.py` del backend** (hooks, tasks, api, etc.): hace falta reiniciar los
  procesos de supervisor (`frappe-bench-web`, los `frappe-bench-workers`) además de comitear — el código
  Python vive en memoria en los workers y no se recarga solo. `bench build` es solo para JS/CSS.

## Testing

Hay un sitio de pruebas dedicado (`test_site`) para correr tests -- **no correr
`bench run-tests` contra `comando.evolucionapyme.cl`**: varias de nuestras funciones hacen
`frappe.db.commit()` explicito, lo que rompe el rollback automatico que da la proteccion de
tests de Frappe, y se podria filtrar data de prueba a produccion.

```bash
sudo -u frappe bash -c 'cd /home/frappe/frappe-bench && bench --site test_site run-tests --module "evoluciona_pyme_v2.evoluciona_pyme_v2.doctype.declaracion_mensual.test_declaracion_mensual"'
```

- Contraseña root de MariaDB (necesaria para recrear `test_site` si hace falta):
  `/home/frappe/.config/evoluciona_pyme_v2/mariadb_root.env` (permisos 600). Se fijo manualmente
  porque el root de MariaDB no tenia contraseña conocida (solo auth por socket).
- `test_site` tiene `developer_mode` y `allow_tests` activados, y la app instalada. Comparte el
  mismo codigo fuente que `comando.evolucionapyme.cl` (mismo bench), pero base de datos propia.
- Si un test falla con `AttributeError` o `Unknown column` en un campo que sabes que existe en el
  `.json`: es el mismo problema de metadata documentado mas abajo (campo `modified`), aplicado a
  `test_site`. Arreglar con `frappe.reload_doc(..., force=True)` puntual para ese DocType en
  `bench --site test_site console`, sin correr `bench --site test_site migrate` despues (se vio
  que un migrate posterior puede revertir el reload puntual -- no se investigo la causa raiz).
- `Cobranza_Cliente.factura_vinculada` apunta a `Sales Invoice` (ERPNext, no instalado en este
  bench) -- cualquier test que dependa de `Cobranza_Cliente` necesita
  `IGNORE_TEST_RECORD_DEPENDENCIES = ["Sales Invoice"]` en su propio archivo `test_*.py` (tiene
  que ir en el modulo de test del DocType que tiene el link, no en el que lo usa indirectamente).
- Los hooks reales de `Ficha_Cliente` (`crear_carpeta_cliente` a Google Drive, etc.) se disparan
  igual en tests -- mockear con `unittest.mock.patch` los que llaman a servicios externos.

## Roadmap

Ver [ROADMAP.md](ROADMAP.md) para el plan de evolución hacia una plataforma multi-contador
(multi-sitio, sitio controlador, personalización por contador, app móvil). No confundir con
trabajo del día a día -- son etapas grandes, posteriores a lo que se está mergeando ahora.

## Convenciones

- Commits en español, descriptivos, explicando el *por qué* cuando no es obvio.
- No commitear `site_config.json`, tokens, ni credenciales — nunca deben vivir en el repo de la app.
- Al terminar de trabajar una rama `feature/xxx` y antes de abrir el PR: escribir un resumen breve
  (causa del problema, qué se cambió, cómo se probó, pendientes) y entregárselo al usuario para que lo
  pegue como descripción del PR. No commitear ese resumen dentro del repo de la app — es contenido del
  PR, no código del proyecto.
