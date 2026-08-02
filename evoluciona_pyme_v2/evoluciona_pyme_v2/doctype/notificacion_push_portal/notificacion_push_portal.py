import frappe
from frappe.model.document import Document


class Notificacion_Push_Portal(Document):
    pass


@frappe.whitelist()
def enviar_notificacion(name):
    """
    Envía la notificación push. Puede llamarse aunque ya esté enviada (reenvío).
    - enviar_a_todos = 1  →  todos los clientes con suscripciones activas
    - enviar_a_todos = 0  →  solo los clientes en la tabla 'destinatarios'
    """
    doc = frappe.get_doc("Notificacion_Push_Portal", name)

    from evoluciona_pyme_v2.evoluciona_pyme_v2.portal_api import enviar_push_a_cliente

    total = 0

    if doc.enviar_a_todos:
        # Todos los clientes que tienen al menos una suscripción Web Push activa
        # La relación es: Portal_Push_Sub.contacto → Contacto_Cliente.name
        #                 Contacto_Cliente.email → Ficha_Contacto.email → Ficha_Contacto.parent (= cliente)
        clientes_rows = frappe.db.sql("""
            SELECT DISTINCT fco.parent AS cliente
            FROM `tabPortal_Push_Sub` ps
            INNER JOIN `tabContacto_Cliente` cc
                ON cc.name = ps.contacto AND cc.activo = 1
            INNER JOIN `tabFicha_Contacto` fco
                ON fco.email = cc.email AND fco.puede_ver_portal = 1
            WHERE ps.activo = 1
        """, as_dict=True)

        for row in clientes_rows:
            if not row.cliente:
                continue
            try:
                r = enviar_push_a_cliente(row.cliente, doc.titulo, doc.cuerpo, data={"url": "/"})
                total += r if isinstance(r, int) else 1
            except Exception as e:
                frappe.log_error(
                    "Push masivo error cliente {}: {}".format(row.cliente, str(e)),
                    "Portal Push"
                )
    else:
        if not doc.destinatarios:
            frappe.throw("Agrega al menos un cliente en la tabla de destinatarios, o marca 'Enviar a todos'.")

        for dest in doc.destinatarios:
            if not dest.cliente:
                continue
            try:
                r = enviar_push_a_cliente(dest.cliente, doc.titulo, doc.cuerpo, data={"url": "/"})
                total += r if isinstance(r, int) else 1
            except Exception as e:
                frappe.log_error(
                    "Push error cliente {}: {}".format(dest.cliente, str(e)),
                    "Portal Push"
                )

    frappe.db.set_value("Notificacion_Push_Portal", name, {
        "enviado":        1,
        "fecha_envio":    frappe.utils.now(),
        "total_enviados": total,
    })
    frappe.db.commit()
    return {"ok": True, "total_enviados": total}


@frappe.whitelist()
def contar_dispositivos(name):
    """Previsualización: cuántos dispositivos recibirían esta notificación."""
    doc = frappe.get_doc("Notificacion_Push_Portal", name)

    if doc.enviar_a_todos:
        count = frappe.db.sql("""
            SELECT COUNT(DISTINCT ps.name)
            FROM `tabPortal_Push_Sub` ps
            INNER JOIN `tabContacto_Cliente` cc
                ON cc.name = ps.contacto AND cc.activo = 1
            INNER JOIN `tabFicha_Contacto` fco
                ON fco.email = cc.email AND fco.puede_ver_portal = 1
            WHERE ps.activo = 1
        """)[0][0]

        clientes = frappe.db.sql("""
            SELECT COUNT(DISTINCT fco.parent)
            FROM `tabPortal_Push_Sub` ps
            INNER JOIN `tabContacto_Cliente` cc
                ON cc.name = ps.contacto AND cc.activo = 1
            INNER JOIN `tabFicha_Contacto` fco
                ON fco.email = cc.email AND fco.puede_ver_portal = 1
            WHERE ps.activo = 1
        """)[0][0]
    else:
        clientes_list = [d.cliente for d in doc.destinatarios if d.cliente]
        if not clientes_list:
            return {"dispositivos": 0, "clientes": 0}

        count = frappe.db.sql("""
            SELECT COUNT(DISTINCT ps.name)
            FROM `tabPortal_Push_Sub` ps
            INNER JOIN `tabContacto_Cliente` cc
                ON cc.name = ps.contacto AND cc.activo = 1
            INNER JOIN `tabFicha_Contacto` fco
                ON fco.email = cc.email AND fco.puede_ver_portal = 1
            WHERE ps.activo = 1 AND fco.parent IN %(lista)s
        """, {"lista": clientes_list})[0][0]

        clientes = len(clientes_list)

    return {"dispositivos": int(count or 0), "clientes": int(clientes or 0)}
