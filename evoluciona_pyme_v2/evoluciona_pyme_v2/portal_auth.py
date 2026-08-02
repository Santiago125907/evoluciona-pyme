"""
Autenticación del Portal de Clientes — Evoluciona Pyme
Sin sesión Frappe: tokens propios en Portal_Session.
"""
import frappe
import hashlib
import secrets
import hmac
from datetime import datetime, timedelta

TOKEN_DIAS = 730
RESET_HORAS = 1
PASSWORD_DEFAULT = "evoluciona123"


# ── Utilidades internas ────────────────────────────────────────────────────────

def _hash_password(password):
    """SHA-256 con salt fijo del site."""
    salt = frappe.conf.get("db_password", "ev_salt_2026")
    return hashlib.sha256("{}{}".format(salt, password).encode()).hexdigest()


def _generar_token():
    return secrets.token_urlsafe(48)


def _get_contacto(email):
    name = frappe.db.get_value("Contacto_Cliente", {"email": email, "activo": 1}, "name")
    if not name:
        return None
    return frappe.get_doc("Contacto_Cliente", name)


def _crear_sesion(contacto_name, email):
    expira = datetime.now() + timedelta(days=TOKEN_DIAS)
    token = _generar_token()
    frappe.get_doc({
        "doctype": "Portal_Session",
        "token": token,
        "contacto": contacto_name,
        "email": email,
        "activo": 1,
        "expira_en": expira,
        "ip_origen": frappe.local.request_ip if hasattr(frappe.local, "request_ip") else "",
    }).insert(ignore_permissions=True)
    frappe.db.commit()
    return token


def _renovar_sesion(session_doc):
    """Sliding window: cada request renueva los 730 días."""
    nueva_expira = datetime.now() + timedelta(days=TOKEN_DIAS)
    frappe.db.set_value("Portal_Session", session_doc.name, "expira_en", nueva_expira)
    frappe.db.commit()


def _get_empresas(email):
    """Empresas donde el contacto tiene acceso al portal activo."""
    rows = frappe.db.sql("""
        SELECT fc.name, fc.razon_social, fc.rut_cliente, fc.estado_cliente, fc.estado_portal,
               fc.clave_sii, fc.erut_archivo
        FROM `tabFicha_Cliente` fc
        INNER JOIN `tabFicha_Contacto` fco ON fco.parent = fc.name
        WHERE fco.email = %(email)s
          AND fco.puede_ver_portal = 1
          AND fc.habilitar_portal = 1
        ORDER BY fc.razon_social ASC
    """, {"email": email}, as_dict=True)
    return rows


# ── APIs públicas (allow_guest — no requieren sesión Frappe) ──────────────────

@frappe.whitelist(allow_guest=True)
def login_portal(email, password):
    """Login con email + contraseña. Retorna token + empresas."""
    email = (email or "").strip().lower()
    if not email or not password:
        frappe.throw("Email y contraseña son requeridos.", frappe.ValidationError)

    contacto = _get_contacto(email)
    if not contacto:
        frappe.throw("Credenciales incorrectas.", frappe.AuthenticationError)

    hash_ingresado = _hash_password(password)
    if not hmac.compare_digest(contacto.password_hash or "", hash_ingresado):
        frappe.throw("Credenciales incorrectas.", frappe.AuthenticationError)

    frappe.db.set_value("Contacto_Cliente", contacto.name, "ultimo_login", datetime.now())
    token = _crear_sesion(contacto.name, email)
    empresas = _get_empresas(email)

    return {
        "token": token,
        "nombre": contacto.nombre,
        "email": contacto.email,
        "debe_cambiar_password": bool(contacto.debe_cambiar_password),
        "empresas": empresas,
    }


@frappe.whitelist(allow_guest=True)
def verificar_token(token):
    """Valida el token y lo renueva (sliding window). Retorna datos del contacto."""
    if not token:
        frappe.throw("Token requerido.", frappe.AuthenticationError)

    session = frappe.db.get_value(
        "Portal_Session",
        {"token": token, "activo": 1},
        ["name", "contacto", "email", "expira_en"],
        as_dict=True
    )
    if not session:
        frappe.throw("Sesión inválida.", frappe.AuthenticationError)

    if datetime.now() > frappe.utils.get_datetime(session.expira_en):
        frappe.db.set_value("Portal_Session", session.name, "activo", 0)
        frappe.db.commit()
        frappe.throw("Sesión expirada.", frappe.AuthenticationError)

    _renovar_sesion(frappe.get_doc("Portal_Session", session.name))

    contacto = frappe.get_doc("Contacto_Cliente", session.contacto)
    empresas = _get_empresas(session.email)

    return {
        "nombre": contacto.nombre,
        "email": contacto.email,
        "debe_cambiar_password": bool(contacto.debe_cambiar_password),
        "empresas": empresas,
    }


@frappe.whitelist(allow_guest=True)
def cambiar_password(token, password_actual, password_nueva):
    """Cambia la contraseña del contacto autenticado."""
    if not token:
        frappe.throw("Token requerido.", frappe.AuthenticationError)

    session = frappe.db.get_value(
        "Portal_Session",
        {"token": token, "activo": 1},
        ["contacto", "expira_en"],
        as_dict=True
    )
    if not session or datetime.now() > frappe.utils.get_datetime(session.expira_en):
        frappe.throw("Sesión inválida o expirada.", frappe.AuthenticationError)

    contacto = frappe.get_doc("Contacto_Cliente", session.contacto)
    if not hmac.compare_digest(contacto.password_hash or "", _hash_password(password_actual)):
        frappe.throw("La contraseña actual es incorrecta.", frappe.ValidationError)

    if len(password_nueva) < 6:
        frappe.throw("La contraseña debe tener al menos 6 caracteres.", frappe.ValidationError)

    frappe.db.set_value("Contacto_Cliente", contacto.name, {
        "password_hash": _hash_password(password_nueva),
        "debe_cambiar_password": 0,
    })
    frappe.db.commit()
    return {"ok": True}


@frappe.whitelist(allow_guest=True)
def cambiar_password_inicial(token, password_nueva):
    """Cambia contraseña sin requerir la actual. Solo válido cuando debe_cambiar_password = 1."""
    if not token:
        frappe.throw("Token requerido.", frappe.AuthenticationError)

    session = frappe.db.get_value(
        "Portal_Session",
        {"token": token, "activo": 1},
        ["contacto", "expira_en"],
        as_dict=True
    )
    if not session or datetime.now() > frappe.utils.get_datetime(session.expira_en):
        frappe.throw("Sesión inválida o expirada.", frappe.AuthenticationError)

    contacto = frappe.get_doc("Contacto_Cliente", session.contacto)
    if not contacto.debe_cambiar_password:
        frappe.throw("No autorizado.", frappe.AuthenticationError)

    if len(password_nueva) < 6:
        frappe.throw("La contraseña debe tener al menos 6 caracteres.", frappe.ValidationError)

    frappe.db.set_value("Contacto_Cliente", contacto.name, {
        "password_hash": _hash_password(password_nueva),
        "debe_cambiar_password": 0,
    })
    frappe.db.commit()
    return {"ok": True}


@frappe.whitelist(allow_guest=True)
def solicitar_reset_password(email):
    """Envía email con link para resetear contraseña (expira 1 hora)."""
    email = (email or "").strip().lower()
    contacto = _get_contacto(email)
    if not contacto:
        return {"ok": True}  # No revelar si el email existe

    token = _generar_token()
    expira = datetime.now() + timedelta(hours=RESET_HORAS)

    frappe.get_doc({
        "doctype": "Portal_Session",
        "token": "RESET_{}".format(token),
        "contacto": contacto.name,
        "email": email,
        "activo": 1,
        "expira_en": expira,
    }).insert(ignore_permissions=True)
    frappe.db.commit()

    config = frappe.get_single("Configuracion App")
    nombre_empresa = getattr(config, "nombre_empresa", "Evoluciona Pyme") or "Evoluciona Pyme"
    telefono = getattr(config, "telefono", "") or ""
    sitio_web = getattr(config, "sitio_web", "") or ""
    reset_url = "https://portal.evolucionapyme.cl/reset-password?token={}".format(token)

    frappe.sendmail(
        recipients=[email],
        subject="Recuperar contraseña — {}".format(nombre_empresa),
        message="""
        <div style="font-family:sans-serif;max-width:520px;margin:auto">
          <h2 style="color:#00C4CC">{empresa}</h2>
          <p>Hola <strong>{nombre}</strong>,</p>
          <p>Recibimos una solicitud para restablecer tu contraseña.</p>
          <p>
            <a href="{url}" style="background:#00C4CC;color:#fff;padding:12px 28px;border-radius:6px;text-decoration:none;font-weight:600;display:inline-block">
              Restablecer contraseña
            </a>
          </p>
          <p style="font-size:12px;color:#888">Este link expira en 1 hora. Si no lo solicitaste, ignora este correo.</p>
          <hr style="border:none;border-top:1px solid #eee;margin:20px 0">
          <p style="font-size:12px;color:#aaa">{empresa} &nbsp;|&nbsp; {telefono} &nbsp;|&nbsp; {web}</p>
        </div>
        """.format(nombre=contacto.nombre, url=reset_url, empresa=nombre_empresa,
                   telefono=telefono, web=sitio_web),
    )
    return {"ok": True}


@frappe.whitelist(allow_guest=True)
def confirmar_reset_password(token, password_nueva):
    """Aplica la nueva contraseña tras el link de reset."""
    if not token:
        frappe.throw("Token inválido.", frappe.AuthenticationError)

    session = frappe.db.get_value(
        "Portal_Session",
        {"token": "RESET_{}".format(token), "activo": 1},
        ["name", "contacto", "expira_en"],
        as_dict=True
    )
    if not session or datetime.now() > frappe.utils.get_datetime(session.expira_en):
        frappe.throw("El link expiró o ya fue usado.", frappe.AuthenticationError)

    if len(password_nueva) < 6:
        frappe.throw("La contraseña debe tener al menos 6 caracteres.", frappe.ValidationError)

    frappe.db.set_value("Contacto_Cliente", session.contacto, {
        "password_hash": _hash_password(password_nueva),
        "debe_cambiar_password": 0,
    })
    frappe.db.set_value("Portal_Session", session.name, "activo", 0)
    frappe.db.commit()
    return {"ok": True}


@frappe.whitelist(allow_guest=True)
def logout_portal(token):
    """Invalida el token de sesión."""
    if token:
        frappe.db.set_value("Portal_Session", {"token": token}, "activo", 0)
        frappe.db.commit()
    return {"ok": True}


@frappe.whitelist(allow_guest=True)
def get_config_portal():
    """Config pública del portal para el mensaje de error en login."""
    config = frappe.get_single("Configuracion App")
    return {
        "nombre_empresa": getattr(config, "nombre_empresa", "Evoluciona Pyme") or "Evoluciona Pyme",
        "telefono": getattr(config, "telefono", "") or "",
        "email_contacto": getattr(config, "email_contacto", "") or "",
        "sitio_web": getattr(config, "sitio_web", "") or "",
        "logo": getattr(config, "logo_empresa", "") or "",
    }


# ── Hook: enviar bienvenida cuando se activa portal por primera vez ────────────

def enviar_bienvenida_portal(doc, method=None):
    """
    Doc event on_update de Ficha_Cliente.
    Envía email de bienvenida solo la primera vez que un contacto
    obtiene acceso (total empresas con portal == 1).
    """
    if not doc.habilitar_portal:
        return

    config = frappe.get_single("Configuracion App")
    nombre_empresa = getattr(config, "nombre_empresa", "Evoluciona Pyme") or "Evoluciona Pyme"
    telefono = getattr(config, "telefono", "") or ""
    sitio_web = getattr(config, "sitio_web", "") or ""

    actualizar_estado = False

    for fila in (doc.contactos or []):
        if not fila.puede_ver_portal or not fila.email:
            continue

        contacto = _get_contacto(fila.email)
        if not contacto:
            continue

        # Solo enviar si es la primera empresa con portal para este contacto
        total = frappe.db.count(
            "Ficha_Contacto",
            {"email": fila.email, "puede_ver_portal": 1}
        )
        if total != 1:
            continue

        # Asignar password por defecto si no tiene
        if not contacto.password_hash:
            frappe.db.set_value("Contacto_Cliente", contacto.name, {
                "password_hash": _hash_password(PASSWORD_DEFAULT),
                "debe_cambiar_password": 1,
            })
            frappe.db.commit()

        frappe.sendmail(
            recipients=[fila.email],
            subject="Tu acceso a {} está listo 🎉".format(nombre_empresa),
            message="""
            <div style="font-family:sans-serif;max-width:520px;margin:auto">
              <h2 style="color:#00C4CC">{empresa}</h2>
              <p>Hola <strong>{nombre}</strong>,</p>
              <p>Te damos acceso al portal de gestión de <strong>{razon_social}</strong>.</p>
              <div style="background:#f5f5f5;border-radius:8px;padding:16px 20px;margin:20px 0;font-size:14px">
                <div style="margin-bottom:6px"><strong>Email:</strong> {email}</div>
                <div><strong>Contraseña:</strong> {password}</div>
              </div>
              <p>
                <a href="https://portal.evolucionapyme.cl"
                   style="background:#00C4CC;color:#fff;padding:12px 28px;border-radius:6px;text-decoration:none;font-weight:600;display:inline-block">
                  Entrar al portal
                </a>
              </p>
              <p style="font-size:12px;color:#888;margin-top:12px">
                📱 <strong>Instala la app:</strong> abre el link en tu celular → menú del navegador → "Agregar a pantalla de inicio".
              </p>
              <p style="font-size:12px;color:#888">
                Te recomendamos cambiar tu contraseña al entrar por primera vez.
              </p>
              <hr style="border:none;border-top:1px solid #eee;margin:24px 0">
              <p style="font-size:12px;color:#aaa">{empresa} &nbsp;|&nbsp; {telefono} &nbsp;|&nbsp; {web}</p>
            </div>
            """.format(
                empresa=nombre_empresa,
                nombre=fila.nombre or fila.email,
                razon_social=doc.razon_social,
                email=fila.email,
                password=PASSWORD_DEFAULT,
                telefono=telefono,
                web=sitio_web,
            ),
        )
        actualizar_estado = True

    if actualizar_estado:
        frappe.db.set_value("Ficha_Cliente", doc.name, {
            "estado_portal": "Activo",
            "fecha_creacion_portal": datetime.now(),
        })
        frappe.db.commit()
