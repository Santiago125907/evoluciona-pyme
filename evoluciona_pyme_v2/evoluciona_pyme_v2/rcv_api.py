import frappe
from evoluciona_pyme_v2.evoluciona_pyme_v2 import sii_gateway

_TIPO_COMPRA = {
    "33": "FACTURA ELECTRÓNICA",
    "34": "FACTURA EXENTA ELECTRÓNICA",
    "46": "FACTURA DE COMPRA ELECTRÓNICA",
    "56": "NOTA DE DÉBITO ELECTRÓNICA",
    "61": "NOTA DE CRÉDITO ELECTRÓNICA",
    "43": "LIQUIDACIÓN FACTURA",
}

_TIPO_VENTA = {
    "33": "FACTURA ELECTRÓNICA",
    "34": "FACTURA NO ELECTRÓNICA",
    "56": "NOTA DE DÉBITO ELECTRÓNICA",
    "61": "NOTA DE CRÉDITO ELECTRÓNICA",
    "39": "Total Oper. del mes Boleta Electr.(39)",
    "41": "Total Oper. del mes Boleta Exenta Electr.(41)",
    "48": "Total mes Comprobantes Pago Electrónico(48)",
}

# Boletas y comprobantes no vienen como documentos individuales: solo llegan
# totalizados en /v1/rcv/resumen y se guardan como una fila RESUMEN por tipo.
_CODIGOS_RESUMEN = {"39", "41", "48"}


def _dedup(docs, campo_rut):
    """
    El SII repite folios dentro de un período: junto al documento real llegan
    copias en cero (monto_total 0 y fecha_recepcion nula). Nos quedamos con la
    de mayor monto por (tipo, folio, contraparte) para no depender del orden.
    """
    mejores = {}
    for doc in docs:
        clave = (str(doc.get("tipo_dte", "")), str(doc.get("folio", "")), doc.get(campo_rut, ""))
        actual = mejores.get(clave)
        if actual is None or frappe.utils.flt(doc.get("monto_total", 0)) > frappe.utils.flt(actual.get("monto_total", 0)):
            mejores[clave] = doc
    return list(mejores.values())


def _insertar_compras(cliente, ano, mes, docs, usa_iva):
    unicos = _dedup(docs, "rut_emisor")
    for doc in unicos:
        neto   = frappe.utils.flt(doc.get("monto_neto", 0))
        iva    = frappe.utils.flt(doc.get("monto_iva", 0))
        exento = frappe.utils.flt(doc.get("monto_exento", 0))
        # ILA, tabacos, combustibles: ya vienen sumados dentro de monto_total
        otros  = sum(frappe.utils.flt(i.get("valor", 0)) for i in (doc.get("otros_impuestos") or []))
        total  = frappe.utils.flt(doc.get("monto_total", 0)) or (neto + iva + exento + otros)

        # monto_iva es el IVA recuperable; el no recuperable no da derecho a crédito
        iva_credito = iva if usa_iva else 0
        costo       = total - iva_credito

        try:
            frappe.get_doc({
                "doctype": "Libro_de_Compras_Cliente",
                "cliente": cliente,
                "fecha_documento": doc.get("fecha"),
                "ano_tributario": str(ano),
                "mes_tributario": str(mes),
                "tipo_documento": _TIPO_COMPRA.get(str(doc.get("tipo_dte", "")), "OTRO"),
                "folio": str(doc.get("folio", "")),
                "rut_proveedor": doc.get("rut_emisor", ""),
                "razon_social_proveedor": doc.get("razon_social", ""),
                "monto_exento": exento,
                "neto": neto,
                "iva_credito": iva_credito,
                "otros_impuestos": otros,
                "total_documento": total,
                "costo_empresa": costo,
            }).insert(ignore_permissions=True)
        except frappe.exceptions.ValidationError:
            pass  # el SII a veces repite folios dentro del mismo período
    frappe.db.commit()
    return len(unicos)


def _insertar_ventas(cliente, ano, mes, docs, por_tipo):
    unicos = _dedup(docs, "rut_receptor")
    for doc in unicos:
        neto   = frappe.utils.flt(doc.get("monto_neto", 0))
        iva    = frappe.utils.flt(doc.get("monto_iva", 0))
        exento = frappe.utils.flt(doc.get("monto_exento", 0))
        frappe.get_doc({
            "doctype": "Libro_de_Ingresos_Cliente",
            "cliente": cliente,
            "fecha_documento": doc.get("fecha"),
            "ano_tributario": str(ano),
            "mes_tributario": str(mes),
            "tipo_documento": _TIPO_VENTA.get(str(doc.get("tipo_dte", "")), "FACTURA ELECTRÓNICA"),
            "folio": str(doc.get("folio", "")),
            "rut_receptor": doc.get("rut_receptor", ""),
            "razon_social_receptor": doc.get("razon_social_receptor", ""),
            "monto_exento": exento,
            "neto": neto,
            "iva": iva,
            "total": frappe.utils.flt(doc.get("monto_total", 0)) or (neto + iva + exento),
        }).insert(ignore_permissions=True)

    import calendar
    ultimo_dia    = calendar.monthrange(int(ano), int(mes))[1]
    fecha_resumen = f"{ano}-{str(mes).zfill(2)}-{ultimo_dia}"

    for item in por_tipo or []:
        codigo = str(item.get("tipo_dte", ""))
        if codigo not in _CODIGOS_RESUMEN:
            continue
        frappe.get_doc({
            "doctype": "Libro_de_Ingresos_Cliente",
            "cliente": cliente,
            "fecha_documento": fecha_resumen,
            "ano_tributario": str(ano),
            "mes_tributario": str(mes),
            "tipo_documento": _TIPO_VENTA[codigo],
            "folio": "RESUMEN",
            "monto_exento": frappe.utils.flt(item.get("monto_exento", 0)),
            "neto": frappe.utils.flt(item.get("monto_neto", 0)),
            "iva": frappe.utils.flt(item.get("monto_iva", 0)),
            "total": frappe.utils.flt(item.get("monto_total", 0)),
        }).insert(ignore_permissions=True)
    frappe.db.commit()
    return len(unicos)


def _resumen_ventas(ficha, periodo):
    """Totales por tipo de documento en estado REGISTRO (de ahí salen boletas 39/41/48)."""
    cuerpo = dict(sii_gateway.cuerpo_rcv(ficha, periodo), operacion="VENTA")
    resp = sii_gateway.post("/v1/rcv/resumen", cuerpo)
    registro = (resp.get("resumen") or {}).get("REGISTRO") or {}
    return registro.get("por_tipo") or []


def descargar_rcv_cliente(cliente_name, periodo, compras=True, ventas=True):
    """
    Descarga compras y/o ventas del SII para un cliente y período ('YYYY-MM').
    Idempotente: borra el período y lo repuebla, pero solo después de tener los
    datos en mano, para no dejar el período vacío si la API falla.
    """
    ficha = frappe.get_doc("Ficha_Cliente", cliente_name)
    if not ficha.rut_cliente or not ficha.clave_sii:
        frappe.log_error("Sin credenciales SII", f"RCV {cliente_name}")
        return {"ok": False, "compras": 0, "ventas": 0}

    usa_iva = bool(frappe.utils.cint(ficha.usa_iva_credito) if ficha.usa_iva_credito is not None else True)
    ano, mes_str = periodo.split("-")
    mes = int(mes_str)
    cuerpo = sii_gateway.cuerpo_rcv(ficha, periodo)

    resultado = {"ok": True, "compras": 0, "ventas": 0}

    if compras:
        try:
            docs = sii_gateway.post("/v1/rcv/compras", cuerpo).get("documentos") or []
        except Exception as e:
            resultado["ok"] = False
            frappe.log_error(str(e), f"RCV compras {cliente_name} {periodo}")
        else:
            frappe.db.delete("Libro_de_Compras_Cliente", {
                "cliente": cliente_name, "ano_tributario": ano, "mes_tributario": str(mes)
            })
            frappe.db.commit()
            resultado["compras"] = _insertar_compras(cliente_name, ano, mes, docs, usa_iva)

    if ventas:
        try:
            docs     = sii_gateway.post("/v1/rcv/ventas", cuerpo).get("documentos") or []
            por_tipo = _resumen_ventas(ficha, periodo)
        except Exception as e:
            resultado["ok"] = False
            frappe.log_error(str(e), f"RCV ventas {cliente_name} {periodo}")
        else:
            frappe.db.delete("Libro_de_Ingresos_Cliente", {
                "cliente": cliente_name, "ano_tributario": ano, "mes_tributario": str(mes)
            })
            frappe.db.commit()
            resultado["ventas"] = _insertar_ventas(cliente_name, ano, mes, docs, por_tipo)

    return resultado


def descargar_rcv_todos(periodo):
    """Descarga RCV según la tabla de empresas configurada en Configuracion App."""
    cfg = frappe.get_doc("Configuracion App")
    empresas = cfg.get("tabla_rcv_empresas") or []

    if not empresas:
        frappe.log_error("tabla_rcv_empresas vacía — no hay empresas configuradas", "RCV masivo")
        return

    for fila in empresas:
        if not fila.descargar_compras and not fila.descargar_ventas:
            continue
        if frappe.db.get_value("Ficha_Cliente", fila.empresa, "estado_cliente") != "Activo":
            continue
        try:
            descargar_rcv_cliente(
                fila.empresa,
                periodo,
                compras=bool(fila.descargar_compras),
                ventas=bool(fila.descargar_ventas),
            )
        except Exception as e:
            frappe.log_error(str(e), f"RCV masivo {fila.empresa}")
        frappe.db.commit()


@frappe.whitelist()
def descargar_rcv_manual(cliente, periodo):
    """Trigger manual desde la UI. periodo = 'YYYY-MM'"""
    return descargar_rcv_cliente(cliente, periodo)


@frappe.whitelist()
def cargar_documentos_api(doc_name, compras=1, ventas=1, honorarios=0):
    """Carga compras/ventas/honorarios desde la API SII para el cliente y período del Borrador_F29."""
    from evoluciona_pyme_v2.evoluciona_pyme_v2 import bhe_api

    doc = frappe.get_doc("Borrador_F29", doc_name)
    cliente = doc.cliente
    ano     = int(doc.ano)
    mes     = int(doc.mes)
    periodo = f"{ano}-{str(mes).zfill(2)}"

    compras    = frappe.utils.cint(compras)
    ventas     = frappe.utils.cint(ventas)
    honorarios = frappe.utils.cint(honorarios)

    partes = []

    if compras or ventas:
        r = descargar_rcv_cliente(cliente, periodo, compras=bool(compras), ventas=bool(ventas))
        if compras:
            partes.append(f"Compras ({r['compras']})")
        if ventas:
            partes.append(f"Ventas ({r['ventas']})")
        if not r["ok"]:
            partes.append("⚠ con errores, revisa el Error Log")

    if honorarios:
        bhe_api.descargar_bhe_cliente(cliente, ano, mes)
        partes.append("Honorarios")

    detalle = f"Cargados: {', '.join(partes)} — período {mes}/{ano}"
    return {"ok": True, "detalle": detalle}


@frappe.whitelist()
def cargar_anio_cliente(cliente, ano, compras=1, ventas=1, honorarios=0, meses_bhe="[]"):
    """
    Descarga registros históricos del SII para un cliente, mes a mes.
    - Compras/Ventas: hasta el mes anterior si es el año en curso.
    - Honorarios: meses_bhe=[] → hasta mes anterior; meses_bhe=[1,3] → solo esos meses.
    """
    import json as _json
    from evoluciona_pyme_v2.evoluciona_pyme_v2 import bhe_api
    from frappe.utils import now_datetime

    ano        = int(ano)
    compras    = frappe.utils.cint(compras)
    ventas     = frappe.utils.cint(ventas)
    honorarios = frappe.utils.cint(honorarios)

    if isinstance(meses_bhe, str):
        try:
            meses_bhe = _json.loads(meses_bhe)
        except Exception:
            meses_bhe = []
    meses_bhe = [int(m) for m in (meses_bhe or [])]

    ficha = frappe.get_doc("Ficha_Cliente", cliente)
    if not ficha.rut_cliente or not ficha.clave_sii:
        frappe.throw(f"Sin credenciales SII para {cliente}")

    hoy       = now_datetime()
    mes_hasta = (hoy.month - 1) if ano == hoy.year else 12

    lineas    = []
    n_errores = 0

    if compras or ventas:
        con_datos = vacios = err = 0
        for mes_num in range(1, mes_hasta + 1):
            periodo = f"{ano}-{str(mes_num).zfill(2)}"
            try:
                r = descargar_rcv_cliente(cliente, periodo, compras=bool(compras), ventas=bool(ventas))
            except Exception as e:
                err += 1
                frappe.log_error(str(e), f"RCV anual {cliente} {periodo}")
                continue
            if not r["ok"]:
                err += 1
            elif r["compras"] or r["ventas"]:
                con_datos += 1
            else:
                vacios += 1
            frappe.db.commit()
        n_errores += err
        etiqueta = "Compras y ventas" if (compras and ventas) else ("Compras" if compras else "Ventas")
        lineas.append(f"{etiqueta}: {con_datos} meses con datos, {vacios} vacíos, {err} errores")

    if honorarios:
        meses_a_cargar = meses_bhe or list(range(1, mes_hasta + 1))
        total = len(meses_a_cargar)

        if not meses_a_cargar:
            lineas.append("Honorarios: año actual sin meses previos aún")
        else:
            ok = err = 0
            for mes_num in meses_a_cargar:
                try:
                    result = bhe_api.descargar_bhe_cliente(cliente, ano, mes_num)
                    ok += 1 if result else 0
                    err += 0 if result else 1
                    n_errores += 0 if result else 1
                except Exception as e:
                    err += 1; n_errores += 1
                    frappe.log_error(str(e), f"BHE {cliente} {ano}/{mes_num}")
            lineas.append(f"Honorarios: {ok}/{total} meses{f', {err} errores' if err else ''}")

    detalle = f"Año {ano} — " + " | ".join(lineas)
    return {"ok": n_errores == 0, "detalle": detalle, "errores": n_errores}


def acusar_recibo_inteligente(cliente, ano, mes, simular=True):
    """
    Decide qué facturas de compra pendientes de acuse conviene acusar este mes
    y cuáles dejar para que se registren solas el mes siguiente (Ley 19.983:
    a los 8 días el SII las registra igual, con o sin acuse manual).

    Lógica:
    1. Calcula el IVA determinado preliminar como débito (IVA de ventas en
       REGISTRO, vía /v1/rcv/resumen) menos crédito (IVA de compras en
       REGISTRO, mismo endpoint), menos el remanente que dejó el mes
       anterior — ese último dato NO se pide al SII: ya está guardado en el
       Borrador_F29 local del mes anterior (remanente_mes_siguiente), que a
       esta fecha ya existe y ya fue calculado por el flujo normal.
       Se usa /v1/rcv/resumen y no /v1/f29/borrador porque el borrador puede
       omitir el IVA de ventas por boleta (tipos 39/41), quedando el débito
       en 0 y el preliminar completamente errado.
    2. Si ese preliminar ya es <= 0 (hay remanente/crédito suficiente), no
       acusa nada — no tiene sentido sumar más crédito este mes.
    3. Si es > 0, ordena los documentos pendientes con IVA > 0 de menor a
       mayor y va sumando mientras el IVA a pagar resultante se mantenga
       >= monto_iva_esperado del cliente (0 = sin límite, acusa todo).
       Los documentos exentos (monto_iva=0) se acusan siempre, ya que no
       afectan el cálculo y solo importa no perder su plazo.
    """
    ficha = frappe.get_doc("Ficha_Cliente", cliente)
    if not ficha.acuse_recibo_automatico:
        return {"ok": True, "omitido": True, "motivo": "Automatización desactivada para este cliente"}
    if not ficha.rut_cliente or not ficha.clave_sii:
        return {"ok": False, "omitido": True, "motivo": "Sin credenciales SII"}

    periodo = f"{ano}-{str(mes).zfill(2)}"
    monto_esperado = frappe.utils.flt(ficha.monto_iva_esperado)

    usa_iva = bool(frappe.utils.cint(ficha.usa_iva_credito) if ficha.usa_iva_credito is not None else True)

    debito  = frappe.utils.flt(sii_gateway.resumen_rcv(ficha, periodo, "VENTA").get("monto_iva"))
    credito = frappe.utils.flt(sii_gateway.resumen_rcv(ficha, periodo, "COMPRA").get("monto_iva")) if usa_iva else 0
    iva_determinado = debito - credito

    fecha_periodo = frappe.utils.getdate(f"{ano}-{str(mes).zfill(2)}-01")
    fecha_anterior = frappe.utils.add_months(fecha_periodo, -1)
    remanente_anterior = frappe.utils.flt(frappe.db.get_value(
        "Borrador_F29",
        {"cliente": cliente, "ano": str(fecha_anterior.year), "mes": str(fecha_anterior.month)},
        "remanente_mes_siguiente",
    ))

    preliminar = iva_determinado - remanente_anterior

    if preliminar <= 0:
        return {
            "ok": True, "acusados": [], "cantidad": 0, "preliminar": preliminar,
            "motivo": "Ya hay remanente/crédito suficiente sin necesidad de acusar más este mes",
        }

    pendientes = sii_gateway.pendientes_acuse(ficha, periodo).get("documentos") or []
    sin_iva = [d for d in pendientes if frappe.utils.flt(d.get("monto_iva")) == 0]
    con_iva = sorted(
        [d for d in pendientes if frappe.utils.flt(d.get("monto_iva")) > 0],
        key=lambda d: frappe.utils.flt(d.get("monto_iva")),
    )

    seleccionados = list(sin_iva)
    restante = preliminar

    if monto_esperado <= 0:
        seleccionados += con_iva
    else:
        for doc in con_iva:
            iva_doc = frappe.utils.flt(doc.get("monto_iva"))
            if restante - iva_doc >= monto_esperado:
                seleccionados.append(doc)
                restante -= iva_doc
            else:
                break  # ordenados de menor a mayor: los que siguen tampoco calzan

    if not seleccionados:
        return {
            "ok": True, "acusados": [], "cantidad": 0, "preliminar": preliminar,
            "motivo": "Ningún documento pendiente calza dentro del monto esperado",
        }

    documentos_payload = [
        {"tipo_dte": int(d["tipo_dte"]), "folio": str(d["folio"]), "rut_emisor": d["rut_emisor"]}
        for d in seleccionados
    ]
    respuesta = sii_gateway.enviar_acuse(ficha, periodo, documentos_payload, cod_evento="ERM", simular=simular)

    return {
        "ok": True,
        "acusados": documentos_payload,
        "cantidad": len(documentos_payload),
        "preliminar": preliminar,
        "simulado": bool(simular),
        "respuesta_gateway": respuesta,
    }


def acusar_recibo_todos(ano, mes, simular=True):
    """Corre acusar_recibo_inteligente para todos los clientes activos con la automatización activada."""
    clientes = frappe.get_all(
        "Ficha_Cliente",
        filters={"estado_cliente": "Activo", "acuse_recibo_automatico": 1},
        pluck="name",
    )
    resumen = []
    for cliente in clientes:
        try:
            r = acusar_recibo_inteligente(cliente, ano, mes, simular=simular)
        except Exception as e:
            r = {"ok": False, "error": str(e)}
            frappe.log_error(str(e), f"Acuse inteligente {cliente} {ano}-{mes}")
        resumen.append({"cliente": cliente, **r})
        frappe.db.commit()
    return resumen


@frappe.whitelist()
def probar_acuse_inteligente(cliente, ano, mes, simular=1):
    """Trigger manual desde el Desk para revisar qué haría la automatización antes de dejarla en modo real."""
    return acusar_recibo_inteligente(cliente, int(ano), int(mes), simular=bool(frappe.utils.cint(simular)))


def agregar_cliente_a_tabla_rcv(doc, method=None):
    """
    Hook after_insert Y on_update de Ficha_Cliente. Suma el cliente a
    tabla_rcv_empresas en Configuracion App con compras/ventas/honorarios
    activados, para que el cron mensual de RCV (dispatcher_libros) lo
    cubra automaticamente sin tener que agregarlo a mano.
    Solo actua si el cliente esta Activo (no Inactivo/Potencial) y si
    todavia no esta en la tabla -- cubre tanto el alta directa como el
    caso de un cliente que nace Inactivo/Potencial y luego pasa a Activo
    (ese nunca entra por after_insert, lo agarra este mismo chequeo en
    on_update).
    """
    try:
        if doc.get("estado_cliente") != "Activo":
            return

        cfg = frappe.get_doc("Configuracion App")
        ya_configurado = {fila.empresa for fila in cfg.get("tabla_rcv_empresas")}
        if doc.name in ya_configurado:
            return

        cfg.append("tabla_rcv_empresas", {
            "empresa": doc.name,
            "descargar_compras": 1,
            "descargar_ventas": 1,
            "descargar_honorarios": 1,
        })
        cfg.save(ignore_permissions=True)
        frappe.db.commit()
    except Exception as e:
        frappe.log_error(str(e), f"agregar_cliente_a_tabla_rcv {doc.name}")
