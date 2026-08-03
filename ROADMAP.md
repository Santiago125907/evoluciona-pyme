# Roadmap — Evoluciona Pyme como plataforma multi-contador

Contexto: la idea es evolucionar el sistema (hoy uso interno de Evoluciona Pyme) hacia una
plataforma que se vende a otros contadores independientes / estudios contables, cada uno con
sus propios clientes y datos aislados. Este documento ordena las etapas, definidas en la
conversación del 2026-08-03.

## Etapa 0 — Base actual (rama `feature/revision-cron-declaraciones`)

Ya hecho y probado en producción: fix del cron de declaraciones/RCV, remanente F29 oficial,
recargo por atraso, estado de pago F29/Previred/Postergación, Panel Mensual con fila expandible
y filtros, hook de alta/baja automática en `tabla_rcv_empresas`. Pendiente: abrir el PR a
`develop` y mergear.

## Etapa 1 — PDF generado localmente (sin depender de un servicio externo)

- Agregar **WeasyPrint** como motor alternativo a Gotenberg (Python puro, sin necesitar entorno
  gráfico/X11 — evita el problema que dio wkhtmltopdf).
- Configurable en `Configuracion App` (elegir motor: Gotenberg / WeasyPrint / wkhtmltopdf).
- Reutiliza el HTML/CSS que ya arma `pdf.py`, sin rehacer el diseño del informe.

## Etapa 2 — Sitio controlador (panel maestro)

Pieza central de la que dependen las etapas siguientes. Un sitio Frappe aparte, tuyo, con:

- **Clave maestra** de acceso, separada de cualquier sitio-cliente.
- Vista consolidada: cuántos clientes tiene cada contador, estado de cada uno, sin salir del
  sitio maestro (cada sitio-cliente expone datos resumidos vía API whitelisted al maestro).
- **Control de cobranza/suscripciones** por contador (plan contratado, estado de pago, etc.).
- **Directorio de resolución** cliente → contador: dado un RUT/email de un cliente final, saber
  a qué sitio pertenece — necesario para el login ruteado de la app/PWA (ver Etapa 5).

## Etapa 3 — Provisioning automatizado de sitios

- Alta de sitio nuevo: `bench new-site` + instalar la app + vhost nginx + certificado SSL
  (certbot) + registro DNS del subdominio, todo en un solo flujo/script.
- Baja de sitio: `bench drop-site` + limpieza de vhost/certificado.
- Conectado al panel de cobranza del sitio maestro (ej.: si un contador no paga, se puede
  suspender su sitio desde ahí).

## Etapa 4 — Personalización por contador

- Logo y colores del PDF/portal **ya existen** como campos en `Configuracion App` — con
  multi-sitio, cada contador tiene su propia instancia de esos campos automáticamente, sin
  cambios de código adicionales.
- Falta: una UI simple para que el contador suba su logo/colores sin tocar el Desk directamente.

## Etapa 5 — App para los clientes de cada contador

- **Plan B / mientras tanto**: PWA instalable ("Agregar a pantalla de inicio"), funciona en
  Android y iOS, no depende de las tiendas. Confirmado como camino inmediato.
- **App genérica white-label**: un solo binario (Play Store / App Store) sin marca de Evoluciona
  Pyme, para todos los contadores. Al iniciar, el cliente final ingresa su RUT/email, la app
  consulta al **sitio maestro** (Etapa 2) a qué contador pertenece, y desde ahí carga el
  logo/colores y hace login contra el sitio de ese contador específico. Un solo APK/IPA,
  apariencia distinta por contador.
- **App propia de Evoluciona Pyme**: con tu marca, aparte de la genérica.
- **App personalizada para un contador que la pida**: servicio adicional pagado (cuenta de
  desarrollador, publicación y revisión en la tienda corren por separado).

## Etapa 6 — Modelo de precios (a definir con datos reales)

- Recomendación: partir solo con **multi-sitio** (plan "dedicado") para todos al principio — es
  más simple y más seguro que mantener dos arquitecturas en paralelo.
- Evaluar un plan más económico en un sitio compartido multi-tenant **más adelante**, solo si
  aparece demanda real de contadores que no puedan pagar el plan dedicado. No construirlo de
  forma especulativa antes de validar la demanda.

## Notas

- El multi-sitio no da "verlos a todos" gratis — cada sitio es una base de datos aislada. El
  panel maestro (Etapa 2) es una pieza de desarrollo real, no una configuración.
- Todo esto es trabajo posterior a mergear la rama actual — no se mezcla con
  `feature/revision-cron-declaraciones`.
