import frappe

ROLES = {
    "admin":      "Evoluciona Admin",
    "supervisor": "Evoluciona Supervisor",
    "senior":     "Evoluciona Senior",
    "asesor":     "Evoluciona Asesor",
    "basic":      "Evoluciona Basic",
}


def is_usuario_basico(user=None):
    """Retorna True si el usuario tiene rol Basic (sin datos bancarios ni footer en PDF).
    Administrator y System Manager nunca son básicos (tienen todos los roles por defecto)."""
    user = user or frappe.session.user
    roles = frappe.get_roles(user)
    # Administrator tiene TODOS los roles en Frappe — excluirlo explícitamente
    if 'Administrator' in roles or 'System Manager' in roles:
        return False
    return ROLES["basic"] in roles


def _get_rol_usuario(user=None):
    """Retorna el rol más alto del usuario en el sistema Evoluciona."""
    user = user or frappe.session.user
    roles = frappe.get_roles(user)
    if ROLES["admin"] in roles or "System Manager" in roles:
        return "admin"
    if ROLES["supervisor"] in roles:
        return "supervisor"
    if ROLES["senior"] in roles:
        return "senior"
    if ROLES["asesor"] in roles:
        return "asesor"
    return "asesor"


@frappe.whitelist()
def get_rol_usuario():
    return _get_rol_usuario()


@frappe.whitelist()
def get_clientes_para_asignacion(filtro="todos", usuario_filtro=None):
    """
    filtro: 'todos' | 'sin_asignar' | 'por_usuario'
    usuario_filtro: email del usuario (solo cuando filtro='por_usuario')
    """
    rol = _get_rol_usuario()
    if rol not in ("admin", "supervisor"):
        frappe.throw("Sin permiso para ver la gestión de asesores.")

    conditions = "estado_cliente = 'Activo'"
    values = {}

    if filtro == "sin_asignar":
        conditions += " AND (asesor_asignado IS NULL OR asesor_asignado = '')"
    elif filtro == "por_usuario" and usuario_filtro:
        conditions += " AND asesor_asignado = %(usuario_filtro)s"
        values["usuario_filtro"] = usuario_filtro

    rows = frappe.db.sql(f"""
        SELECT name, razon_social, rut_cliente, asesor_asignado
        FROM `tabFicha_Cliente`
        WHERE {conditions}
        ORDER BY razon_social ASC
    """, values, as_dict=True)

    for r in rows:
        if r.get("asesor_asignado"):
            r["nombre_asesor"] = frappe.db.get_value(
                "User", r["asesor_asignado"], "full_name") or r["asesor_asignado"]
        else:
            r["nombre_asesor"] = ""

    return rows


@frappe.whitelist()
def get_asesores():
    """Usuarios con rol Evoluciona para el selector."""
    roles_ev = list(ROLES.values())
    usuarios = frappe.db.sql("""
        SELECT DISTINCT u.name, u.full_name, u.user_image
        FROM `tabUser` u
        JOIN `tabHas Role` hr ON hr.parent = u.name
        WHERE hr.role IN %(roles)s
          AND u.enabled = 1
          AND u.name != 'Administrator'
        ORDER BY u.full_name ASC
    """, {"roles": roles_ev}, as_dict=True)

    for u in usuarios:
        u["rol"] = _get_rol_usuario(u["name"])
        u["total_asignados"] = frappe.db.count("Ficha_Cliente", {"asesor_asignado": u["name"]})

    return usuarios


@frappe.whitelist()
def asignar_clientes(clientes, usuario):
    rol = _get_rol_usuario()
    if rol not in ("admin", "supervisor"):
        frappe.throw("Sin permiso para asignar clientes.")

    import json
    if isinstance(clientes, str):
        clientes = json.loads(clientes)
    if not clientes:
        return {"asignados": 0}

    if not frappe.db.exists("User", usuario):
        frappe.throw(f"Usuario '{usuario}' no existe.")

    for nombre in clientes:
        frappe.db.set_value("Ficha_Cliente", nombre, "asesor_asignado", usuario)
    frappe.db.commit()
    return {"asignados": len(clientes)}


@frappe.whitelist()
def quitar_clientes(clientes):
    rol = _get_rol_usuario()
    if rol not in ("admin", "supervisor"):
        frappe.throw("Sin permiso para quitar asignaciones.")

    import json
    if isinstance(clientes, str):
        clientes = json.loads(clientes)
    if not clientes:
        return {"quitados": 0}

    for nombre in clientes:
        frappe.db.set_value("Ficha_Cliente", nombre, "asesor_asignado", None)
    frappe.db.commit()
    return {"quitados": len(clientes)}


@frappe.whitelist()
def get_stats_panel(ano, mes):
    """Stats del panel según rol del usuario logueado."""
    ano, mes = int(ano), int(mes)
    rol = _get_rol_usuario()
    user = frappe.session.user

    # Obtener IDs de clientes según rol
    if rol == "admin":
        clientes_names = frappe.db.sql(
            "SELECT name FROM `tabFicha_Cliente` WHERE estado_cliente='Activo'",
            as_list=True)
        clientes_names = [r[0] for r in clientes_names]
    elif rol in ("supervisor", "senior"):
        rows = frappe.db.sql("""
            SELECT name FROM `tabFicha_Cliente`
            WHERE estado_cliente='Activo'
              AND (asesor_asignado=%(u)s OR asesor_asignado IS NULL OR asesor_asignado='')
        """, {"u": user}, as_list=True)
        clientes_names = [r[0] for r in rows]
    else:
        rows = frappe.db.sql(
            "SELECT name FROM `tabFicha_Cliente` WHERE estado_cliente='Activo' AND asesor_asignado=%(u)s",
            {"u": user}, as_list=True)
        clientes_names = [r[0] for r in rows]

    total = len(clientes_names)
    if not total:
        return _stats_vacias(rol)

    safe_list = clientes_names or ["__none__"]

    decs = frappe.db.sql("""
        SELECT estado FROM `tabDeclaracion_Mensual`
        WHERE ano=%(ano)s AND mes=%(mes)s AND cliente IN %(c)s
    """, {"ano": ano, "mes": mes, "c": safe_list}, as_dict=True)

    borrador   = sum(1 for d in decs if not d.estado or d.estado == "Borrador")
    validacion = sum(1 for d in decs if d.estado == "En Validación")
    listos     = sum(1 for d in decs if d.estado == "Listo")
    enviados   = sum(1 for d in decs if d.estado == "Enviado")
    sin_dec    = total - len(decs)
    avance     = listos + enviados
    pct        = round(avance / total * 100) if total else 0

    cobros = frappe.db.sql("""
        SELECT monto_a_cobrar, estado_cobranza FROM `tabCobranza_Cliente`
        WHERE periodo_ano=%(ano)s AND periodo_mes=%(mes)s AND cliente IN %(c)s
    """, {"ano": ano, "mes": mes, "c": safe_list}, as_dict=True)

    def _sum(lst):
        return sum(float(c.monto_a_cobrar or 0) for c in lst)

    return {
        "rol": rol,
        "total": total,
        "avance": avance,
        "pct": pct,
        "borrador": borrador,
        "validacion": validacion,
        "listos": listos,
        "enviados": enviados,
        "sin_dec": sin_dec,
        "cobros": {
            "por_cobrar": {"n": sum(1 for c in cobros if c.estado_cobranza == "Por Cobrar"),
                           "monto": _sum([c for c in cobros if c.estado_cobranza == "Por Cobrar"])},
            "facturado":  {"n": sum(1 for c in cobros if c.estado_cobranza == "Facturado"),
                           "monto": _sum([c for c in cobros if c.estado_cobranza == "Facturado"])},
            "pagado":     {"n": sum(1 for c in cobros if c.estado_cobranza == "Pagado"),
                           "monto": _sum([c for c in cobros if c.estado_cobranza == "Pagado"])},
        }
    }


def _stats_vacias(rol):
    return {
        "rol": rol, "total": 0, "avance": 0, "pct": 0,
        "borrador": 0, "validacion": 0, "listos": 0, "enviados": 0, "sin_dec": 0,
        "cobros": {
            "por_cobrar": {"n": 0, "monto": 0},
            "facturado":  {"n": 0, "monto": 0},
            "pagado":     {"n": 0, "monto": 0},
        }
    }


def auto_asignar_asesor(doc, method=None):
    """Doc event: si quien crea la Ficha_Cliente es un Asesor/Senior, se auto-asigna."""
    if not getattr(doc, 'name', None):
        return  # insert programático sin name aún
    if getattr(doc, 'asesor_asignado', None):
        return  # ya tiene asignado, no tocar
    rol = _get_rol_usuario(frappe.session.user)
    if rol in ("asesor", "senior"):
        frappe.db.set_value("Ficha_Cliente", doc.name, "asesor_asignado", frappe.session.user)
        frappe.db.commit()
