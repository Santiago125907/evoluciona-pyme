"""
Notificaciones push del portal — disparadas por scheduler diario.

Envía push en dos momentos:
  D-2: 2 días antes del vencimiento (aviso preventivo)
  D-0: el día del vencimiento (recordatorio urgente)

Cubre:
  1. F29 (Declaracion_Mensual.fecha_vencimiento_f29)
  2. Previred (Declaracion_Mensual.fecha_vencimiento_previred)
  3. Postergación IVA (cuando aplica)
  4. Vencimientos generales (Vencimiento_Cliente)
"""
import frappe
from datetime import date, timedelta

MESES = ['Enero','Febrero','Marzo','Abril','Mayo','Junio',
         'Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']


def _fmt(n):
    try:
        return '$' + '{:,.0f}'.format(float(n or 0)).replace(',', '.')
    except Exception:
        return '$0'


def _ya_notificado(clave):
    return bool(frappe.cache().get_value('portal_push_' + clave))


def _marcar_notificado(clave):
    frappe.cache().set_value('portal_push_' + clave, 1, expires_in_sec=108000)


# ── Scheduler entry point ─────────────────────────────────────────────────────

def recordatorio_vencimiento():
    """Corre diariamente. Envía push de vencimientos D-2 y D-0."""
    hoy     = date.today()
    en2dias = hoy + timedelta(days=2)

    from evoluciona_pyme_v2.evoluciona_pyme_v2.portal_api import enviar_push_a_cliente

    _notif_declaraciones(hoy, en2dias, enviar_push_a_cliente)
    _notif_vencimientos_cliente(hoy, en2dias, enviar_push_a_cliente)


# ── Declaraciones Mensuales ───────────────────────────────────────────────────

def _notif_declaraciones(hoy, en2dias, enviar):
    declaraciones = frappe.db.sql("""
        SELECT name, cliente, mes, ano,
               total_f29_a_pagar, total_previred_a_pagar,
               fecha_vencimiento_f29, fecha_vencimiento_previred,
               postegar_pago_iva, fecha_vencimiento_postergacion
        FROM `tabDeclaracion_Mensual`
        WHERE publicado_portal = 1
          AND cliente IS NOT NULL AND cliente != ''
          AND (
              fecha_vencimiento_f29              IN %(fechas)s
           OR fecha_vencimiento_previred         IN %(fechas)s
           OR (postegar_pago_iva = 1 AND fecha_vencimiento_postergacion IN %(fechas)s)
          )
    """, {"fechas": (str(hoy), str(en2dias))}, as_dict=True)

    for d in declaraciones:
        mes_nombre = MESES[int(d.mes or 1) - 1] if d.mes else ''
        f29      = float(d.total_f29_a_pagar or 0)
        previred = float(d.total_previred_a_pagar or 0)

        _enviar_si_procede(
            cliente=d.cliente, fecha_venc=d.fecha_vencimiento_f29,
            hoy=hoy, en2dias=en2dias,
            clave='f29_{}_{}'.format(d.name, d.fecha_vencimiento_f29),
            titulo_2d='⏰ F29 vence en 2 días — {} {}'.format(mes_nombre, d.ano),
            cuerpo_2d='Recuerda transferirnos {} antes del {} para que realicemos el pago del F29 a tiempo.'.format(
                _fmt(f29), _fmt_fecha(d.fecha_vencimiento_f29)),
            titulo_0d='🚨 Vence hoy el F29 — {} {}'.format(mes_nombre, d.ano),
            cuerpo_0d='Hoy vence el F29 ({}). Recuerda pagar a tiempo para evitar multas.'.format(_fmt(f29)),
            tipo='vencimiento', enviar=enviar,
        )

        _enviar_si_procede(
            cliente=d.cliente, fecha_venc=d.fecha_vencimiento_previred,
            hoy=hoy, en2dias=en2dias,
            clave='prev_{}_{}'.format(d.name, d.fecha_vencimiento_previred),
            titulo_2d='⏰ Previred vence en 2 días — {} {}'.format(mes_nombre, d.ano),
            cuerpo_2d='Recuerda transferirnos {} antes del {} para que paguemos Previred a tiempo.'.format(
                _fmt(previred), _fmt_fecha(d.fecha_vencimiento_previred)),
            titulo_0d='🚨 Vence hoy Previred (día 12) — {} {}'.format(mes_nombre, d.ano),
            cuerpo_0d='Hoy vence Previred ({}). Recuerda pagar antes de que cierre el sistema.'.format(_fmt(previred)),
            tipo='vencimiento', enviar=enviar,
        )

        if d.postegar_pago_iva and d.fecha_vencimiento_postergacion:
            _enviar_si_procede(
                cliente=d.cliente, fecha_venc=d.fecha_vencimiento_postergacion,
                hoy=hoy, en2dias=en2dias,
                clave='post_{}_{}'.format(d.name, d.fecha_vencimiento_postergacion),
                titulo_2d='⏰ Postergación IVA vence en 2 días — {} {}'.format(mes_nombre, d.ano),
                cuerpo_2d='El plazo de postergación del IVA vence el {}.'.format(
                    _fmt_fecha(d.fecha_vencimiento_postergacion)),
                titulo_0d='🚨 Vence hoy la postergación de IVA — {} {}'.format(mes_nombre, d.ano),
                cuerpo_0d='Hoy vence la postergación de IVA. Revisa tu situación tributaria.',
                tipo='vencimiento', enviar=enviar,
            )


# ── Vencimientos_Cliente genéricos ────────────────────────────────────────────

def _notif_vencimientos_cliente(hoy, en2dias, enviar):
    vencimientos = frappe.db.sql("""
        SELECT name, cliente, descripcion, fecha_vencimiento, monto_a_pagar
        FROM `tabVencimiento_Cliente`
        WHERE fecha_vencimiento IN %(fechas)s
          AND (estado IS NULL OR estado NOT IN ('Pagado', 'Anulado'))
          AND cliente IS NOT NULL AND cliente != ''
    """, {"fechas": (str(hoy), str(en2dias))}, as_dict=True)

    for v in vencimientos:
        monto_txt = '  |  Monto: {}'.format(_fmt(v.monto_a_pagar)) if v.monto_a_pagar else ''
        desc = v.descripcion or 'Obligación tributaria'
        _enviar_si_procede(
            cliente=v.cliente, fecha_venc=v.fecha_vencimiento,
            hoy=hoy, en2dias=en2dias,
            clave='vc_{}_{}'.format(v.name, v.fecha_vencimiento),
            titulo_2d='⏰ Vence en 2 días: {}'.format(desc),
            cuerpo_2d='Fecha límite: {}{}'.format(_fmt_fecha(v.fecha_vencimiento), monto_txt),
            titulo_0d='🚨 Vence hoy: {}'.format(desc),
            cuerpo_0d='Hoy es el último día.{}'.format(monto_txt),
            tipo='vencimiento', enviar=enviar,
        )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _enviar_si_procede(cliente, fecha_venc, hoy, en2dias,
                       clave, titulo_2d, cuerpo_2d, titulo_0d, cuerpo_0d,
                       tipo, enviar):
    if not fecha_venc or not cliente:
        return
    try:
        fv = fecha_venc if isinstance(fecha_venc, date) else date.fromisoformat(str(fecha_venc))
    except Exception:
        return

    if fv == en2dias:
        k = clave + '_2d'
        if not _ya_notificado(k):
            try:
                enviar(cliente, titulo_2d, cuerpo_2d, data={"tipo": tipo, "cliente": cliente})
                _marcar_notificado(k)
            except Exception as e:
                frappe.log_error(str(e), 'Portal Push D-2 {}'.format(cliente))

    elif fv == hoy:
        k = clave + '_0d'
        if not _ya_notificado(k):
            try:
                enviar(cliente, titulo_0d, cuerpo_0d, data={"tipo": tipo, "cliente": cliente})
                _marcar_notificado(k)
            except Exception as e:
                frappe.log_error(str(e), 'Portal Push D-0 {}'.format(cliente))


def _fmt_fecha(fecha):
    if not fecha:
        return ''
    try:
        f = fecha if isinstance(fecha, date) else date.fromisoformat(str(fecha))
        return '{} de {}'.format(f.day, MESES[f.month - 1])
    except Exception:
        return str(fecha)


def on_declaracion_update(doc, method=None):
    """
    Hook on_update de Declaracion_Mensual.
    Envía push al portal cuando la declaración pasa a estado Publicado.
    """
    try:
        if getattr(doc, "estado", None) != "Publicado":
            return
        if not getattr(doc, "publicado_portal", 0):
            return

        from evoluciona_pyme_v2.evoluciona_pyme_v2.portal_api import enviar_push_a_cliente
        mes_nombre = MESES[int(doc.mes) - 1] if doc.mes else ''
        enviar_push_a_cliente(
            cliente=doc.cliente,
            titulo=f"Informe {mes_nombre} {doc.ano} disponible",
            cuerpo="Tu informe mensual ya está listo. Revísalo en la app.",
            data={"tipo": "declaracion", "cliente": doc.cliente,
                  "mes": str(doc.mes), "ano": str(doc.ano)},
        )
    except Exception as e:
        frappe.log_error(str(e), f"on_declaracion_update push {doc.name}")
