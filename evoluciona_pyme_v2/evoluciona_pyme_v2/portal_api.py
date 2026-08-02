"""
APIs del Portal de Clientes — datos del dashboard y notificaciones FCM.
Toda llamada requiere token válido de Portal_Session.
"""
import json
import os
import frappe
import requests
from datetime import datetime
from evoluciona_pyme_v2.evoluciona_pyme_v2.portal_auth import _get_empresas


def _get_fcm_access_token():
    """
    Obtiene un access token OAuth2 para FCM v1 usando la cuenta de servicio.
    El JSON de la cuenta de servicio debe estar en private/files del sitio.
    """
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request as GoogleRequest

    # Ruta al JSON dentro del sitio Frappe
    sa_filename = frappe.conf.get(
        "firebase_service_account",
        "evolucionapyme-portal-firebase-adminsdk-fbsvc-84d0a2c7d3.json",
    )
    sa_path = os.path.join(frappe.get_site_path(), "private", "files", sa_filename)

    if not os.path.exists(sa_path):
        frappe.log_error("Archivo de cuenta de servicio Firebase no encontrado: {}".format(sa_path), "FCM Push")
        return None, None

    with open(sa_path) as f:
        sa_info = json.load(f)

    project_id = sa_info.get("project_id")

    creds = service_account.Credentials.from_service_account_info(
        sa_info,
        scopes=["https://www.googleapis.com/auth/firebase.messaging"],
    )
    creds.refresh(GoogleRequest())
    return creds.token, project_id

ESTADO_VISIBLE = ("Publicado", "Enviado")   # estados visibles en el portal


def _validar_token(token):
    """Valida el token y retorna el email del contacto. Lanza error si inválido."""
    if not token:
        frappe.throw("Token requerido.", frappe.AuthenticationError)

    session = frappe.db.get_value(
        "Portal_Session",
        {"token": token, "activo": 1},
        ["contacto", "email", "expira_en"],
        as_dict=True,
    )
    if not session:
        frappe.throw("Sesión inválida.", frappe.AuthenticationError)

    if datetime.now() > frappe.utils.get_datetime(session.expira_en):
        frappe.db.set_value("Portal_Session", {"token": token}, "activo", 0)
        frappe.db.commit()
        frappe.throw("Sesión expirada.", frappe.AuthenticationError)

    return session.email


def _verificar_acceso(email, cliente):
    """Verifica que el contacto tenga acceso a esa empresa."""
    tiene = frappe.db.exists(
        "Ficha_Contacto",
        {"parent": cliente, "email": email, "puede_ver_portal": 1},
    )
    if not tiene:
        frappe.throw("Sin acceso a esta empresa.", frappe.PermissionError)


# ── APIs públicas ─────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=True)
def get_resumen_portal(token, cliente, ano=None, mes=None):
    """
    Resumen del mes actual para el dashboard.
    Retorna los datos de la Declaracion_Mensual publicada (estado=Enviado).
    """
    email = _validar_token(token)
    _verificar_acceso(email, cliente)

    hoy = datetime.now()
    ano = int(ano or hoy.year)
    mes = int(mes or hoy.month)

    fields = [
        "name", "estado", "mes", "ano",
        "total_f29_a_pagar", "total_previred_a_pagar",
        "fecha_vencimiento_f29", "fecha_vencimiento_previred",
        "pdf_link_cliente", "pdf_drive_file_id",
        "monto_iva_postergar", "postegar_pago_iva",
    ]

    # Buscar el mes solicitado primero
    decl = frappe.db.get_value(
        "Declaracion_Mensual",
        {"cliente": cliente, "ano": str(ano), "mes": str(mes), "publicado_portal": 1, "estado": ("in", ESTADO_VISIBLE)},
        fields, as_dict=True,
    )

    # Si no hay declaración del mes actual, mostrar la más reciente publicada
    if not decl:
        resultados = frappe.db.get_all(
            "Declaracion_Mensual",
            filters={"cliente": cliente, "publicado_portal": 1, "estado": ("in", ESTADO_VISIBLE)},
            fields=fields,
            order_by="ano desc, mes desc",
            limit=1,
        )
        decl = resultados[0] if resultados else None

    if not decl:
        return None

    decl_mes = int(decl.mes)
    decl_ano = int(decl.ano)
    decl_periodo = decl_ano * 100 + decl_mes

    # ── Honorarios del mes actual y mora (Cobranza_Cliente) ───────────────────
    honorarios_mes = 0.0
    honorarios_mora = 0.0
    try:
        cobranzas = frappe.db.sql("""
            SELECT monto_a_cobrar, periodo_mes, periodo_ano
            FROM `tabCobranza_Cliente`
            WHERE cliente = %(c)s
              AND estado_cobranza IN ('Vencido', 'Por Cobrar', 'Facturado')
        """, {"c": cliente}, as_dict=True)
        for cob in cobranzas:
            cob_periodo = int(cob.periodo_ano) * 100 + int(cob.periodo_mes)
            if cob_periodo == decl_periodo:
                honorarios_mes += float(cob.monto_a_cobrar or 0)
            elif cob_periodo < decl_periodo:
                honorarios_mora += float(cob.monto_a_cobrar or 0)
    except Exception as e:
        frappe.log_error("portal get_resumen honorarios: {}".format(str(e)), "Portal API")

    # ── Postergación IVA que vence en este período ─────────────────────────────
    postergacion_vencida = 0.0
    postergaciones_detalle = []
    try:
        posts = frappe.db.sql("""
            SELECT monto_postergado, mes_origen, ano_origen
            FROM `tabPostergacion_IVA`
            WHERE cliente = %(c)s
              AND mes_f29_pagado = %(mes)s
              AND ano_f29_pagado = %(ano)s
        """, {"c": cliente, "mes": decl_mes, "ano": decl_ano}, as_dict=True)
        for p in posts:
            postergacion_vencida += float(p.monto_postergado or 0)
            if p.mes_origen and p.ano_origen:
                postergaciones_detalle.append({
                    "monto":   float(p.monto_postergado or 0),
                    "periodo": "{}/{}".format(p.mes_origen, p.ano_origen),
                })
    except Exception as e:
        frappe.log_error("portal get_resumen postergacion: {}".format(str(e)), "Portal API")

    f29        = float(decl.total_f29_a_pagar    or 0)
    previred   = float(decl.total_previred_a_pagar or 0)
    # posible_postergar siempre es monto_iva_postergar, sin depender del checkbox.
    # La decisión de postergar la toma el usuario en el portal.
    postergable = float(decl.monto_iva_postergar or 0)

    # Totales: honorarios_mes + honorarios_mora + postergacion_vencida + previred + f29
    base      = honorarios_mes + honorarios_mora + postergacion_vencida + previred
    op1_total = base + f29
    op2_total = base + (f29 - postergable)   # siempre calcula el ahorro real

    # ── Comparación de gastos vs mes anterior ─────────────────────────────────
    mes_ant = decl_mes - 1 if decl_mes > 1 else 12
    ano_ant = decl_ano if decl_mes > 1 else decl_ano - 1

    def _total_gastos(c, m, a):
        def gv(dt, campo):
            try:
                return float(frappe.db.get_value(dt, {"cliente": c, "mes": m, "ano": a}, campo) or 0)
            except Exception:
                return 0.0
        return (gv("Libro_de_Compras_Cliente",    "total_neto") +
                gv("Libro_de_Honorarios_Cliente", "total")      +
                gv("Registro_Remuneraciones",     "total_liquido") +
                gv("Libro_de_Gastos_Cliente",     "total"))

    gastos_actual   = _total_gastos(cliente, decl_mes, decl_ano)
    gastos_anterior = _total_gastos(cliente, mes_ant,  ano_ant)
    pct_cambio = (
        round((gastos_actual - gastos_anterior) / gastos_anterior * 100)
        if gastos_anterior > 0 else None
    )

    return {
        "name":                  decl.name,
        "mes":                   decl_mes,
        "ano":                   decl_ano,
        "estado":                decl.estado,
        "f29_full":              f29,
        "previred":              previred,
        "honorarios":            honorarios_mes,
        "honorarios_mora":       honorarios_mora,
        "postergacion_vencida":  postergacion_vencida,
        "postergaciones_detalle":postergaciones_detalle,
        "posible_postergar":     postergable,
        "op1_total":             op1_total,
        "op2_total":             op2_total,
        "postergado":            postergable,
        "vence_f29":             str(decl.fecha_vencimiento_f29      or ""),
        "vence_previred":        str(decl.fecha_vencimiento_previred  or ""),
        "pdf_url":               decl.pdf_link_cliente or "",
        "gastos_mes_actual":     gastos_actual,
        "gastos_mes_anterior":   gastos_anterior,
        "pct_cambio_gastos":     pct_cambio,
    }


@frappe.whitelist(allow_guest=True)
def get_historial_portal(token, cliente):
    """
    Historial de declaraciones publicadas para el cliente con desglose completo
    (igual al resumen del Home): honorarios, mora, previred, postergacion, f29.
    """
    email = _validar_token(token)
    _verificar_acceso(email, cliente)

    rows = frappe.db.sql("""
        SELECT
            name, mes, ano, estado,
            total_f29_a_pagar, total_previred_a_pagar,
            monto_iva_postergar,
            pdf_link_cliente,
            fecha_vencimiento_f29
        FROM `tabDeclaracion_Mensual`
        WHERE cliente = %(cliente)s
          AND publicado_portal = 1
          AND estado IN ('Publicado', 'Enviado')
        ORDER BY ano DESC, mes DESC
        LIMIT 24
    """, {"cliente": cliente}, as_dict=True)

    if not rows:
        return []

    # ── Cobranzas del cliente (todas, para calcular honorarios y mora por período) ─
    cobranzas = []
    try:
        cobranzas = frappe.db.sql("""
            SELECT monto_a_cobrar, periodo_mes, periodo_ano
            FROM `tabCobranza_Cliente`
            WHERE cliente = %(c)s
        """, {"c": cliente}, as_dict=True)
    except Exception as e:
        frappe.log_error(str(e), "get_historial_portal - cobranzas")

    # ── Postergaciones del cliente (todas) ────────────────────────────────────
    postergaciones = []
    try:
        postergaciones = frappe.db.sql("""
            SELECT mes_f29_pagado, ano_f29_pagado, SUM(monto_postergado) as total
            FROM `tabPostergacion_IVA`
            WHERE cliente = %(c)s
            GROUP BY mes_f29_pagado, ano_f29_pagado
        """, {"c": cliente}, as_dict=True)
    except Exception as e:
        frappe.log_error(str(e), "get_historial_portal - postergaciones")

    post_map = {(int(p.mes_f29_pagado), int(p.ano_f29_pagado)): float(p.total or 0) for p in postergaciones}

    resultado = []
    for r in rows:
        decl_mes    = int(r.mes)
        decl_ano    = int(r.ano)
        decl_periodo = decl_ano * 100 + decl_mes

        # Honorarios del período exacto y mora (períodos anteriores)
        hon_mes  = 0.0
        hon_mora = 0.0
        for cob in cobranzas:
            try:
                cob_periodo = int(cob.periodo_ano) * 100 + int(cob.periodo_mes)
                if cob_periodo == decl_periodo:
                    hon_mes  += float(cob.monto_a_cobrar or 0)
                elif cob_periodo < decl_periodo:
                    hon_mora += float(cob.monto_a_cobrar or 0)
            except Exception:
                pass

        f29          = float(r.total_f29_a_pagar    or 0)
        previred     = float(r.total_previred_a_pagar or 0)
        postergable  = float(r.monto_iva_postergar   or 0)
        postergacion = post_map.get((decl_mes, decl_ano), 0.0)
        total        = hon_mes + hon_mora + postergacion + previred + f29

        resultado.append({
            "name":             r.name,
            "mes":              decl_mes,
            "ano":              decl_ano,
            "estado":           r.estado,
            "f29":              f29,
            "previred":         previred,
            "honorarios":       hon_mes,
            "honorarios_mora":  hon_mora,
            "postergacion":     postergacion,
            "posible_postergar": postergable,
            "total":            total,
            "total_sin_post":   total - postergable,
            "pdf_url":          r.pdf_link_cliente or "",
            "vence":            str(r.fecha_vencimiento_f29 or ""),
        })

    return resultado


@frappe.whitelist(allow_guest=True)
def get_mis_empresas(token):
    """Retorna las empresas del contacto autenticado (para refrescar sin re-login)."""
    if not token:
        frappe.throw("Token requerido.", frappe.AuthenticationError)

    session = frappe.db.get_value(
        "Portal_Session",
        {"token": token, "activo": 1},
        ["email", "expira_en"],
        as_dict=True,
    )
    if not session or datetime.now() > frappe.utils.get_datetime(session.expira_en):
        frappe.throw("Sesión inválida.", frappe.AuthenticationError)

    return _get_empresas(session.email)


# ── FCM — registro y envío de notificaciones push ─────────────────────────────

@frappe.whitelist(allow_guest=True)
def get_kpis_portal(token, cliente, ano=None):
    """KPIs financieros anuales con breakdown de gastos por categoría."""
    email = _validar_token(token)
    _verificar_acceso(email, cliente)

    ano = int(ano or datetime.now().year)
    ano_str = str(ano)

    # Ingresos (Libro_de_Ingresos_Cliente)
    ing_rows = frappe.db.sql("""
        SELECT mes_tributario as mes, SUM(neto) as total
        FROM `tabLibro_de_Ingresos_Cliente`
        WHERE cliente = %(c)s AND ano_tributario = %(a)s
        GROUP BY mes_tributario ORDER BY mes_tributario
    """, {"c": cliente, "a": ano_str}, as_dict=True)

    # Compras (Libro_de_Compras_Cliente)
    comp_rows = frappe.db.sql("""
        SELECT mes_tributario as mes, SUM(costo_empresa) as total
        FROM `tabLibro_de_Compras_Cliente`
        WHERE cliente = %(c)s AND ano_tributario = %(a)s
        GROUP BY mes_tributario ORDER BY mes_tributario
    """, {"c": cliente, "a": ano_str}, as_dict=True)

    # Honorarios (Libro_de_Honorarios_Cliente)
    hon_rows = frappe.db.sql("""
        SELECT mes_tributario as mes, SUM(costo_empresa) as total
        FROM `tabLibro_de_Honorarios_Cliente`
        WHERE cliente = %(c)s AND ano_tributario = %(a)s
        GROUP BY mes_tributario ORDER BY mes_tributario
    """, {"c": cliente, "a": ano_str}, as_dict=True)

    # Gastos operacionales (Libro_de_Gastos_Cliente)
    gas_rows = frappe.db.sql("""
        SELECT mes_tributario as mes, SUM(costo_empresa) as total
        FROM `tabLibro_de_Gastos_Cliente`
        WHERE cliente = %(c)s AND ano_tributario = %(a)s
        GROUP BY mes_tributario ORDER BY mes_tributario
    """, {"c": cliente, "a": ano_str}, as_dict=True)

    # Remuneraciones (Registro_Remuneraciones — usa ano/mes, NO ano_tributario/mes_tributario)
    rem_rows = frappe.db.sql("""
        SELECT mes, SUM(costo_total_empleador) as total
        FROM `tabRegistro_Remuneraciones`
        WHERE cliente = %(c)s AND ano = %(a)s
        GROUP BY mes ORDER BY mes
    """, {"c": cliente, "a": ano}, as_dict=True)

    def to_map(rows):
        return {int(r.mes): float(r.total or 0) for r in rows}

    ing_map  = to_map(ing_rows)
    comp_map = to_map(comp_rows)
    hon_map  = to_map(hon_rows)
    gas_map  = to_map(gas_rows)
    rem_map  = to_map(rem_rows)

    meses_data = []
    acumulado = 0.0
    for m in range(1, 13):
        ing  = ing_map.get(m, 0.0)
        comp = comp_map.get(m, 0.0)
        hon  = hon_map.get(m, 0.0)
        gas  = gas_map.get(m, 0.0)
        rem  = rem_map.get(m, 0.0)
        gastos = comp + hon + gas + rem
        res    = ing - gastos
        acumulado += res
        meses_data.append({
            "mes":            m,
            "ingresos":       ing,
            "compras":        comp,
            "honorarios":     hon,
            "gastos_op":      gas,
            "remuneraciones": rem,
            "gastos":         gastos,
            "resultado":      res,
            "acumulado":      acumulado,
        })

    return {"ano": ano, "meses": meses_data}


@frappe.whitelist(allow_guest=True)
def get_servicios_portal(token, cliente=None):
    """Catálogo de servicios activos del portal."""
    _validar_token(token)
    servicios = frappe.get_all(
        "Servicio_Portal",
        filters={"activo": 1},
        fields=[
            "name", "nombre", "descripcion_corta", "descripcion_larga",
            "categoria", "tipo", "imagen", "icono", "color",
            "nombre_socio", "logo_socio",
            "precio", "precio_oferta", "precio_unidad",
            "accion", "link_externo", "whatsapp_numero",
            "destacado", "orden",
        ],
        order_by="destacado desc, orden asc, nombre asc",
        limit=100,
    )
    for s in servicios:
        s["planes"] = frappe.get_all(
            "Plan_Servicio_Portal",
            filters={"parent": s.name},
            fields=["nombre_plan", "precio", "precio_oferta", "precio_unidad", "descripcion", "destacado"],
            order_by="idx asc",
        )
        # Convertir floats para JSON
        for campo in ["precio", "precio_oferta"]:
            if s.get(campo):
                s[campo] = float(s[campo])
        for plan in s["planes"]:
            for campo in ["precio", "precio_oferta"]:
                if plan.get(campo):
                    plan[campo] = float(plan[campo])
    return servicios


@frappe.whitelist(allow_guest=True)
def enviar_solicitud_servicio(token, cliente=None, servicio_name="",
                               plan_seleccionado="", nombre_contacto="",
                               telefono="", email="", comentario=""):
    """Guarda una solicitud de contratación de servicio."""
    _validar_token(token)
    nombre_serv = frappe.db.get_value("Servicio_Portal", servicio_name, "nombre") or servicio_name
    sol = frappe.get_doc({
        "doctype":           "Solicitud_Servicio_Portal",
        "cliente":           cliente or "",
        "servicio":          servicio_name,
        "nombre_servicio":   nombre_serv,
        "plan_seleccionado": plan_seleccionado,
        "nombre_contacto":   nombre_contacto,
        "telefono":          telefono,
        "email":             email,
        "comentario":        comentario,
        "fecha_solicitud":   frappe.utils.now(),
        "estado":            "Nuevo",
    })
    sol.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"ok": True, "name": sol.name}


@frappe.whitelist(allow_guest=True)
def get_remuneraciones_portal(token, cliente, ano=None):
    """Listado de registros de remuneraciones del cliente, con detalle completo."""
    email = _validar_token(token)
    _verificar_acceso(email, cliente)

    filtros = {"cliente": cliente}
    if ano:
        filtros["ano"] = str(ano)

    rems = frappe.get_all(
        "Registro_Remuneraciones",
        filters=filtros,
        fields=[
            "name", "ano", "mes",
            "total_empleados_activos",
            "total_haberes_imponibles",
            "total_haberes_no_imponibles",
            "costo_total_empleador",
            "total_afp",
            "total_salud",
            "total_seguro_cesantia",
            "total_sis_mutual",
            "total_previred_a_pagar",
            "retencion_prestamo_solidario",
            "impuesto_unico",
        ],
        order_by="ano desc, mes desc",
        limit=48,
    )
    return rems


@frappe.whitelist(allow_guest=True)
def registrar_fcm_token(token, fcm_token):
    """Guarda o actualiza el FCM token del dispositivo del contacto."""
    if not token or not fcm_token:
        return {"ok": False}

    session = frappe.db.get_value(
        "Portal_Session",
        {"token": token, "activo": 1},
        ["contacto", "email", "expira_en"],
        as_dict=True,
    )
    if not session or datetime.now() > frappe.utils.get_datetime(session.expira_en):
        return {"ok": False}

    # Actualizar si ya existe, crear si no
    existing = frappe.db.get_value("Portal_FCM_Token", {"fcm_token": fcm_token}, "name")
    if existing:
        frappe.db.set_value("Portal_FCM_Token", existing, {
            "ultima_vez": datetime.now(),
            "activo": 1,
        })
    else:
        frappe.get_doc({
            "doctype": "Portal_FCM_Token",
            "contacto": session.contacto,
            "email": session.email,
            "fcm_token": fcm_token,
            "activo": 1,
            "ultima_vez": datetime.now(),
        }).insert(ignore_permissions=True)

    frappe.db.commit()
    return {"ok": True}


@frappe.whitelist(allow_guest=True)
def get_erut_portal(token, cliente):
    """
    Retorna el archivo e-RUT del cliente en base64 para visualización en el portal.
    Soporta archivos públicos (/files/) y privados (/private/files/).
    """
    email = _validar_token(token)
    _verificar_acceso(email, cliente)

    erut_path = frappe.db.get_value("Ficha_Cliente", cliente, "erut_archivo")
    if not erut_path:
        return None

    import os, base64, mimetypes

    filename = os.path.basename(erut_path.split("?")[0])

    if erut_path.startswith("/private/files/"):
        abs_path = os.path.join(frappe.get_site_path(), "private", "files", filename)
    elif erut_path.startswith("/files/"):
        abs_path = os.path.join(frappe.get_site_path(), "public", "files", filename)
    else:
        # URL externa — devolver tal cual para que el frontend la abra directamente
        return {"url": erut_path}

    if not os.path.exists(abs_path):
        frappe.throw("Archivo e-RUT no encontrado en el servidor.", frappe.DoesNotExistError)

    mime_type = mimetypes.guess_type(abs_path)[0] or "application/pdf"
    with open(abs_path, "rb") as f:
        content_b64 = base64.b64encode(f.read()).decode("utf-8")

    return {
        "filename": filename,
        "mime_type": mime_type,
        "content_b64": content_b64,
    }


@frappe.whitelist(allow_guest=True)
def get_config_portal(token, cliente):
    """
    Retorna configuración de pago para el portal:
    - Datos bancarios de Configuracion App (globales)
    - pdf_modo_basico del cliente (para ocultar opción "Lo paga Evoluciona")
    """
    email = _validar_token(token)
    _verificar_acceso(email, cliente)

    cfg = frappe.get_single("Configuracion App")
    ficha = frappe.get_value("Ficha_Cliente", cliente,
        ["pdf_modo_basico", "whatsapp_asesor", "nombre_asesor"], as_dict=True) or {}

    return {
        "banco":           cfg.banco          or "",
        "tipo_cuenta":     cfg.tipo_cuenta    or "",
        "numero_cuenta":   cfg.numero_cuenta  or "",
        "nombre_titular":  cfg.nombre_titular or "",
        "rut_empresa":     cfg.rut_empresa    or "",
        "email_pago":      cfg.email_pago     or "",
        "pdf_basico":      bool(ficha.get("pdf_modo_basico")),
        "whatsapp_asesor": ficha.get("whatsapp_asesor") or "",
        "nombre_asesor":   ficha.get("nombre_asesor")   or "",
    }


@frappe.whitelist(allow_guest=True)
def get_anuncios_portal(token, cliente):
    """Retorna anuncios/banners activos para el cliente."""
    email = _validar_token(token)
    _verificar_acceso(email, cliente)

    today = frappe.utils.today()
    # Anuncios activos y vigentes (para todos O específicos para este cliente)
    anuncios = frappe.db.sql("""
        SELECT a.name, a.titulo, a.cuerpo, a.emoji, a.color
        FROM `tabAnuncio_Portal` a
        WHERE a.activo = 1
          AND (a.fecha_hasta IS NULL OR a.fecha_hasta >= %(today)s)
          AND (
            a.para_todos = 1
            OR EXISTS (
                SELECT 1 FROM `tabDestinatario_Anuncio` da
                WHERE da.parent = a.name AND da.cliente = %(cliente)s
            )
          )
        ORDER BY a.creation DESC
        LIMIT 3
    """, {"today": today, "cliente": cliente}, as_dict=True)

    return anuncios


# ─── Historial de notificaciones ─────────────────────────────────────────────

def _log_notif(cliente, titulo, cuerpo, tipo="manual", enviados=0):
    """Registra una notificación en el historial del portal."""
    try:
        frappe.get_doc({
            "doctype":  "Historial_Notif_Portal",
            "cliente":  cliente,
            "titulo":   titulo,
            "cuerpo":   cuerpo,
            "tipo":     tipo,
            "leido":    0,
            "enviados": enviados,
        }).insert(ignore_permissions=True)
        # No hacemos commit aquí — el llamador ya lo hace
    except Exception as e:
        frappe.log_error(str(e), "log_notif error")


@frappe.whitelist(allow_guest=True)
def get_historial_notif_portal(token, cliente):
    """Retorna las últimas 40 notificaciones del cliente y cuántas no han sido leídas."""
    email = _validar_token(token)
    _verificar_acceso(email, cliente)

    notifs = frappe.db.sql("""
        SELECT name, titulo, cuerpo, tipo, leido, creation
        FROM `tabHistorial_Notif_Portal`
        WHERE cliente = %(cliente)s
        ORDER BY creation DESC
        LIMIT 40
    """, {"cliente": cliente}, as_dict=True)

    no_leidas = sum(1 for n in notifs if not n.get("leido"))
    return {"notificaciones": notifs, "no_leidas": no_leidas}


@frappe.whitelist(allow_guest=True)
def marcar_notifs_leidas(token, cliente):
    """Marca todas las notificaciones del cliente como leídas."""
    email = _validar_token(token)
    _verificar_acceso(email, cliente)

    frappe.db.sql("""
        UPDATE `tabHistorial_Notif_Portal`
        SET leido = 1
        WHERE cliente = %(cliente)s AND leido = 0
    """, {"cliente": cliente})
    frappe.db.commit()
    return {"ok": True}


def enviar_push_a_cliente(cliente, titulo, cuerpo, data=None):
    """
    Envía notificación push a todos los dispositivos activos del cliente.
    Usa Web Push nativo (pywebpush/VAPID) como canal principal.
    También intenta FCM v1 si hay tokens FCM registrados.
    cliente = name de Ficha_Cliente
    """
    tipo_notif = (data or {}).get("tipo", "manual")
    url_click  = (data or {}).get("url", "/")

    # ── Web Push VAPID (pywebpush) — canal principal ──────────────────────────
    enviados = 0
    try:
        enviados = _enviar_push_webpush_cliente(
            cliente, titulo, cuerpo, url_click, tipo_notif
        )
    except Exception as e:
        import traceback
        frappe.log_error(
            "pywebpush exception cliente={}\n{}".format(cliente, traceback.format_exc()),
            "Web Push"
        )

    # ── FCM v1 — canal secundario (si hay tokens FCM) ─────────────────────────
    try:
        _enviar_push_fcm_cliente(cliente, titulo, cuerpo, data)
    except Exception as e:
        frappe.log_error("FCM exception: {}".format(str(e)), "FCM Push")

    return enviados


def _enviar_push_webpush_cliente(cliente, titulo, cuerpo, url="/", tipo="manual"):
    """Envía push via pywebpush/VAPID a todas las suscripciones Web Push del cliente."""
    import json as _json
    try:
        from pywebpush import webpush, WebPushException
    except ImportError:
        frappe.log_error("pywebpush no está instalado en el entorno de Frappe", "Web Push")
        return 0

    vapid_private = frappe.conf.get("vapid_private_key")
    vapid_public  = frappe.conf.get("vapid_public_key")
    if not vapid_private or not vapid_public:
        frappe.log_error("VAPID keys no configuradas en site_config", "Web Push")
        return 0

    # Emails de contactos con acceso al portal en este cliente
    emails = frappe.db.sql("""
        SELECT DISTINCT fco.email
        FROM `tabFicha_Contacto` fco
        WHERE fco.parent = %(c)s AND fco.puede_ver_portal = 1
    """, {"c": cliente}, as_dict=True)
    emails_list = [r.email for r in emails if r.email]
    if not emails_list:
        return 0

    # Obtener contactos activos
    contactos = frappe.db.sql("""
        SELECT name FROM `tabContacto_Cliente`
        WHERE email IN %(emails)s AND activo = 1
    """, {"emails": emails_list}, as_dict=True)
    contacto_names = [r.name for r in contactos]
    if not contacto_names:
        return 0

    # Obtener suscripciones activas
    subs = frappe.db.sql("""
        SELECT name, endpoint, p256dh, auth_key
        FROM `tabPortal_Push_Sub`
        WHERE contacto IN %(contactos)s AND activo = 1
    """, {"contactos": contacto_names}, as_dict=True)
    if not subs:
        return 0

    payload = _json.dumps({"title": titulo, "body": cuerpo, "url": url})
    enviados = 0
    for s in subs:
        if not s.endpoint or not s.p256dh or not s.auth_key:
            continue
        try:
            webpush(
                subscription_info={
                    "endpoint": s.endpoint,
                    "keys": {"p256dh": s.p256dh, "auth": s.auth_key},
                },
                data=payload,
                vapid_private_key=vapid_private,
                vapid_claims={
                    "sub": "mailto:admin@evolucionapyme.cl",
                    "aud": s.endpoint.split("/")[0] + "//" + s.endpoint.split("/")[2],
                },
                content_encoding="aes128gcm",
                ttl=86400,
            )
            enviados += 1
        except Exception as e:
            import traceback
            err = str(e)
            frappe.log_error(
                "pywebpush endpoint={} error={}\n{}".format(
                    s.endpoint[:60], err, traceback.format_exc()[:1500]
                ),
                "Web Push Error"
            )
            # Suscripción inválida o expirada → desactivar
            if "410" in err or "404" in err or "invalid" in err.lower() or "Gone" in err:
                frappe.db.set_value("Portal_Push_Sub", s.name, "activo", 0)

    # Loguear en historial de notificaciones del portal
    _log_notif(cliente, titulo, cuerpo, tipo=tipo, enviados=enviados)
    frappe.db.commit()
    return enviados


def _enviar_push_fcm_cliente(cliente, titulo, cuerpo, data=None):
    """Envía push via FCM v1 a tokens FCM registrados. No hace nada si no hay tokens."""
    emails = frappe.db.sql("""
        SELECT DISTINCT fco.email
        FROM `tabFicha_Contacto` fco
        WHERE fco.parent = %(cliente)s AND fco.puede_ver_portal = 1
    """, {"cliente": cliente}, as_dict=True)
    emails_list = [r.email for r in emails if r.email]
    if not emails_list:
        return

    tokens = frappe.db.sql("""
        SELECT fcm_token FROM `tabPortal_FCM_Token`
        WHERE email IN %(emails)s AND activo = 1
    """, {"emails": emails_list}, as_dict=True)
    if not tokens:
        return  # sin tokens FCM → nada que hacer

    access_token, project_id = _get_fcm_access_token()
    if not access_token or not project_id:
        return

    url = "https://fcm.googleapis.com/v1/projects/{}/messages:send".format(project_id)
    headers = {
        "Authorization": "Bearer {}".format(access_token),
        "Content-Type": "application/json",
    }
    for t in tokens:
        payload = {
            "message": {
                "token": t.fcm_token,
                "notification": {"title": titulo, "body": cuerpo},
                "webpush": {
                    "notification": {
                        "icon": "https://portal.evolucionapyme.cl/pwa-192.png",
                        "click_action": "https://portal.evolucionapyme.cl",
                    },
                    "fcm_options": {"link": "https://portal.evolucionapyme.cl"},
                },
                "data": {k: str(v) for k, v in (data or {}).items()},
            }
        }
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=15)
            if not resp.ok:
                if resp.status_code in (400, 404):
                    frappe.db.set_value("Portal_FCM_Token", {"fcm_token": t.fcm_token}, "activo", 0)
                else:
                    frappe.log_error("FCM error: {}".format(resp.text), "FCM Push")
        except Exception as e:
            frappe.log_error("FCM request error: {}".format(str(e)), "FCM Push")
    frappe.db.commit()


# ─── Web Push — endpoints públicos ───────────────────────────────────────────

@frappe.whitelist(allow_guest=True)
def get_vapid_public_key(token):
    """Retorna la clave pública VAPID para que el browser pueda suscribirse."""
    _validar_token(token)
    key = frappe.conf.get("vapid_public_key")
    if not key:
        frappe.throw("VAPID no configurado")
    return {"public_key": key}


@frappe.whitelist(allow_guest=True)
def registrar_push_sub(token, suscripcion, cliente=None):
    """Guarda la suscripción Web Push del dispositivo del usuario."""
    import json as _json
    sesion = frappe.db.get_value(
        "Portal_Session",
        {"token": token, "activo": 1},
        ["contacto", "email"],
        as_dict=True,
    )
    if not sesion:
        frappe.throw("Sesión inválida", frappe.AuthenticationError)

    try:
        sub = _json.loads(suscripcion) if isinstance(suscripcion, str) else suscripcion
    except Exception:
        frappe.throw("Suscripción inválida")

    endpoint = sub.get("endpoint", "")
    p256dh   = (sub.get("keys") or {}).get("p256dh", "")
    auth_key = (sub.get("keys") or {}).get("auth", "")

    if not endpoint or not p256dh or not auth_key:
        frappe.throw("Suscripción incompleta")

    # Desactivar suscripciones previas del mismo endpoint si ya existen
    existing = frappe.db.get_value("Portal_Push_Sub", {"endpoint": endpoint}, "name")
    if existing:
        frappe.db.set_value("Portal_Push_Sub", existing, {
            "contacto":   sesion.contacto,
            "cliente":    cliente or "",
            "p256dh":     p256dh,
            "auth_key":   auth_key,
            "activo":     1,
        })
    else:
        frappe.get_doc({
            "doctype":   "Portal_Push_Sub",
            "contacto":  sesion.contacto,
            "cliente":   cliente or "",
            "endpoint":  endpoint,
            "p256dh":    p256dh,
            "auth_key":  auth_key,
            "activo":    1,
        }).insert(ignore_permissions=True)

    frappe.db.commit()
    return {"ok": True}


# ─── Gastos Portal ────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=True)
def get_gastos_portal(token, cliente, ano=None, mes=None):
    """Retorna los gastos del cliente para el período indicado."""
    email = _validar_token(token)
    _verificar_acceso(email, cliente)
    filtros = {"cliente": cliente}
    if ano:
        filtros["ano_tributario"] = str(ano)
    if mes:
        filtros["mes_tributario"] = str(mes)
    gastos = frappe.get_all(
        "Libro_de_Gastos_Cliente",
        filters=filtros,
        fields=[
            "name", "fecha_documento", "tipo_gasto", "descripcion",
            "razon_social_proveedor", "total_documento", "costo_empresa", "link_documento",
        ],
        order_by="fecha_documento desc",
        limit=200,
    )
    return gastos


@frappe.whitelist(allow_guest=True)
def registrar_gasto_portal(token, cliente, fecha, tipo_gasto, razon_social_proveedor,
                            descripcion="", neto=0, iva=0,
                            total_documento=0, costo_empresa=0,
                            imagen_b64=None, imagen_ext=None):
    """Registra un gasto y opcionalmente sube la imagen del comprobante a Google Drive."""
    email = _validar_token(token)
    _verificar_acceso(email, cliente)

    fecha_dt = datetime.strptime(fecha, "%Y-%m-%d")
    ano_trib = str(fecha_dt.year)
    mes_trib = str(fecha_dt.month)
    link_doc = ""

    if imagen_b64 and imagen_ext:
        try:
            import base64, io
            from evoluciona_pyme_v2.evoluciona_pyme_v2.drive import (
                get_drive_service, get_drive_service_oauth, _crear_subcarpeta, _tiene_oauth
            )
            from googleapiclient.http import MediaInMemoryUpload

            drive_matriz_id = frappe.db.get_value("Ficha_Cliente", cliente, "drive_matriz_id")
            if drive_matriz_id:
                # Service account: solo para carpetas (no tiene cuota para archivos)
                svc_folders = get_drive_service()

                # Buscar o crear carpeta "gastos" dentro de la carpeta raíz del cliente
                query = (
                    f"name = 'gastos' and '{drive_matriz_id}' in parents "
                    f"and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
                )
                res = svc_folders.files().list(q=query, fields="files(id)").execute()
                files = res.get("files", [])
                if files:
                    gastos_folder_id = files[0]["id"]
                else:
                    gastos_folder_id, _ = _crear_subcarpeta(svc_folders, "gastos", drive_matriz_id)

                # OAuth para subir archivos (la service account no tiene cuota de almacenamiento)
                svc_upload = get_drive_service_oauth() if _tiene_oauth() else svc_folders

                # Decodificar imagen
                img_bytes = base64.b64decode(imagen_b64)
                ext_lower = str(imagen_ext).lower()

                # Optimizar imagen con Pillow: redimensionar y comprimir
                try:
                    from PIL import Image
                    img = Image.open(io.BytesIO(img_bytes))
                    # Convertir a RGB si es necesario (para guardar como JPEG)
                    if img.mode in ("RGBA", "P", "CMYK"):
                        img = img.convert("RGB")
                        ext_lower = "jpg"
                    # Redimensionar si supera 1400px en el lado mayor
                    max_px = 1400
                    w, h = img.size
                    if max(w, h) > max_px:
                        ratio = max_px / max(w, h)
                        img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
                    # Comprimir
                    buf = io.BytesIO()
                    fmt = "JPEG" if ext_lower in ("jpg", "jpeg") else "PNG"
                    save_kwargs = {"optimize": True}
                    if fmt == "JPEG":
                        save_kwargs["quality"] = 72
                    img.save(buf, format=fmt, **save_kwargs)
                    img_bytes = buf.getvalue()
                except Exception as pil_err:
                    frappe.log_error(str(pil_err), "registrar_gasto_portal - Pillow")

                mime_map = {
                    "jpg": "image/jpeg", "jpeg": "image/jpeg",
                    "png": "image/png",  "gif": "image/gif",
                    "webp": "image/webp","heic": "image/heic",
                }
                mimetype = mime_map.get(ext_lower, "image/jpeg")
                nombre_prov = (razon_social_proveedor or "gasto")[:30].replace("/", "-").replace(" ", "_")
                nombre_arch = f"{fecha.replace('-', '')}_{nombre_prov}.{ext_lower}"

                archivo = svc_upload.files().create(
                    body={"name": nombre_arch, "parents": [gastos_folder_id]},
                    media_body=MediaInMemoryUpload(img_bytes, mimetype=mimetype),
                    fields="id,webViewLink",
                    supportsAllDrives=True,
                ).execute()

                file_id = archivo.get("id", "")

                # Hacer el archivo público (cualquiera con el link puede verlo)
                if file_id:
                    try:
                        svc_upload.permissions().create(
                            fileId=file_id,
                            body={"role": "reader", "type": "anyone"},
                            supportsAllDrives=True,
                        ).execute()
                        # URL de vista directa (no requiere login de Google)
                        link_doc = f"https://drive.google.com/uc?id={file_id}"
                    except Exception:
                        link_doc = archivo.get("webViewLink", "")

        except Exception as e:
            frappe.log_error(str(e), "registrar_gasto_portal - Drive")

    gasto = frappe.get_doc({
        "doctype":                "Libro_de_Gastos_Cliente",
        "cliente":                cliente,
        "fecha_documento":        fecha,
        "ano_tributario":         ano_trib,
        "mes_tributario":         mes_trib,
        "tipo_gasto":             tipo_gasto,
        "descripcion":            descripcion,
        "razon_social_proveedor": razon_social_proveedor,
        "neto":                   float(neto or 0),
        "iva":                    float(iva or 0),
        "total_documento":        float(total_documento or 0),
        "costo_empresa":          float(costo_empresa or 0),
        "link_documento":         link_doc,
    })
    gasto.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"name": gasto.name, "link_documento": link_doc}


@frappe.whitelist(allow_guest=True)
def eliminar_gasto_portal(token, cliente, gasto_name):
    """Elimina un gasto verificando que pertenezca al cliente."""
    email = _validar_token(token)
    _verificar_acceso(email, cliente)
    gasto_cliente = frappe.db.get_value("Libro_de_Gastos_Cliente", gasto_name, "cliente")
    if gasto_cliente != cliente:
        frappe.throw("No autorizado")
    frappe.delete_doc("Libro_de_Gastos_Cliente", gasto_name, ignore_permissions=True)
    frappe.db.commit()
    return {"status": "ok"}


@frappe.whitelist(allow_guest=True)
def get_gasto_imagen_portal(token, cliente, gasto_name):
    """
    Retorna la imagen del comprobante de un gasto como base64.
    Descarga el archivo desde Google Drive usando la service account.
    El link_documento tiene el formato https://drive.google.com/uc?id=FILE_ID
    """
    email = _validar_token(token)
    _verificar_acceso(email, cliente)

    gasto = frappe.db.get_value(
        "Libro_de_Gastos_Cliente", gasto_name,
        ["cliente", "link_documento"], as_dict=True
    )
    if not gasto or gasto.cliente != cliente:
        frappe.throw("No autorizado")
    if not gasto.link_documento:
        frappe.throw("Este gasto no tiene documento adjunto")

    link = gasto.link_documento
    # Extraer el file_id del link https://drive.google.com/uc?id=FILE_ID
    file_id = None
    if "id=" in link:
        file_id = link.split("id=")[-1].split("&")[0]
    if not file_id:
        frappe.throw("No se pudo determinar el ID del archivo en Drive")

    try:
        import base64 as b64mod
        from evoluciona_pyme_v2.evoluciona_pyme_v2.drive import (
            get_drive_service, get_drive_service_oauth, _tiene_oauth
        )

        svc = get_drive_service_oauth() if _tiene_oauth() else get_drive_service()

        # Obtener metadata (mimetype)
        meta = svc.files().get(
            fileId=file_id, fields="mimeType,name", supportsAllDrives=True
        ).execute()
        mimetype = meta.get("mimeType", "image/jpeg")

        # Descargar contenido
        req  = svc.files().get_media(fileId=file_id, supportsAllDrives=True)
        from googleapiclient.http import MediaIoBaseDownload
        import io
        buf  = io.BytesIO()
        dl   = MediaIoBaseDownload(buf, req)
        done = False
        while not done:
            _, done = dl.next_chunk()
        img_b64 = b64mod.b64encode(buf.getvalue()).decode("utf-8")
        return {"b64": img_b64, "mimetype": mimetype}

    except Exception as e:
        frappe.log_error(str(e), "get_gasto_imagen_portal")
        frappe.throw("No se pudo obtener la imagen")
