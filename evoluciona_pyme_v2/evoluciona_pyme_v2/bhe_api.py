import frappe
from evoluciona_pyme_v2.evoluciona_pyme_v2 import sii_gateway


def _primero(doc, *claves):
    for k in claves:
        v = doc.get(k)
        if v not in (None, ""):
            return v
    return None


def _limpiar_periodo(cliente, ano, mes):
    frappe.db.delete("Libro_de_Honorarios_Cliente", {
        "cliente": cliente,
        "ano_tributario": str(ano),
        "mes_tributario": str(mes),
    })
    frappe.db.commit()


def _insertar_boletas(cliente, ano, mes, boletas, tipo_boleta):
    """tipo_boleta: 'Recibida' (BHE, honorarios pagados) o 'Emitida' (BTE, honorarios cobrados)."""
    n = 0
    for doc in boletas:
        if doc.get("anulada"):
            continue
        bruto    = frappe.utils.flt(_primero(doc, "total_honorarios", "honorario_bruto", "bruto") or 0)
        retenido = frappe.utils.flt(_primero(doc, "retencion", "retenido") or 0)
        liquido  = frappe.utils.flt(_primero(doc, "honorarios_liquidos", "total_liquido", "liquido", "pagado") or 0)

        frappe.get_doc({
            "doctype": "Libro_de_Honorarios_Cliente",
            "cliente": cliente,
            "tipo_boleta": tipo_boleta,
            "folio": str(_primero(doc, "nro_boleta", "folio", "numero") or ""),
            "rut_prestador": _primero(doc, "rut_emisor", "rut_receptor", "rut_tercero") or "",
            "nombre_prestador": _primero(doc, "nombre_emisor", "nombre_receptor", "nombre_tercero") or "",
            "fecha_documento": doc.get("fecha"),
            "ano_tributario": str(ano),
            "mes_tributario": str(mes),
            "monto_bruto": bruto,
            "retencion_honorarios": retenido,
            "monto_liquido": liquido,
            "total_documento": bruto,
            "costo_empresa": bruto,
        }).insert(ignore_permissions=True)
        n += 1
    frappe.db.commit()
    return n


def descargar_bhe_cliente(cliente_name, ano, mes):
    """
    Descarga BHE recibidas + BTE emitidas del SII para un cliente y período.
    Idempotente: limpia el período solo después de tener ambas respuestas.
    """
    ficha = frappe.get_doc("Ficha_Cliente", cliente_name)
    if not ficha.rut_cliente or not ficha.clave_sii:
        frappe.log_error("Sin credenciales SII", f"BHE {cliente_name}")
        return False

    periodo = f"{ano}-{str(mes).zfill(2)}"
    cuerpo = {
        "login": sii_gateway.login_de(ficha),
        "contribuyente": ficha.rut_cliente,
        "periodo": periodo,
    }

    try:
        recibidas = sii_gateway.post("/v1/bhe/recibidas", cuerpo).get("boletas") or []
        emitidas  = sii_gateway.post("/v1/bte/emitidas", cuerpo).get("boletas") or []
    except Exception as e:
        frappe.log_error(str(e), f"BHE {cliente_name} {ano}/{mes}")
        return False

    _limpiar_periodo(cliente_name, ano, mes)
    _insertar_boletas(cliente_name, ano, mes, recibidas, "Recibida")
    _insertar_boletas(cliente_name, ano, mes, emitidas, "Emitida")
    return True


def descargar_bhe_anual(cliente_name, ano):
    """
    Recorre los meses del año consultando el período mensual: el gateway no expone
    un endpoint anual. A diferencia de la versión anterior, guarda cada boleta en
    detalle en vez de una fila RESUMEN por mes.
    """
    from frappe.utils import now_datetime

    ficha = frappe.get_doc("Ficha_Cliente", cliente_name)
    if not ficha.rut_cliente or not ficha.clave_sii:
        frappe.log_error("Sin credenciales SII", f"BHE anual {cliente_name}")
        return {"ok": False}

    hoy       = now_datetime()
    mes_hasta = (hoy.month - 1) if int(ano) == hoy.year else 12

    meses_ok = meses_err = 0
    for mes_num in range(1, mes_hasta + 1):
        try:
            if descargar_bhe_cliente(cliente_name, int(ano), mes_num):
                meses_ok += 1
            else:
                meses_err += 1
        except Exception as e:
            meses_err += 1
            frappe.log_error(str(e), f"BHE anual {cliente_name} {ano}/{mes_num}")

    return {"ok": meses_err == 0, "meses_ok": meses_ok, "meses_error": meses_err}


@frappe.whitelist()
def descargar_bhe_manual(cliente, ano, mes):
    """Trigger manual desde la UI. ano y mes como enteros."""
    ok = descargar_bhe_cliente(cliente, int(ano), int(mes))
    return {"ok": ok}
