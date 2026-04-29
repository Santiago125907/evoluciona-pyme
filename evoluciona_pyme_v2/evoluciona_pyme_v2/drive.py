import json
import frappe
import requests as _requests
from urllib.parse import urlencode


# ──────────────────────────────────────────────────────────
# SERVICE ACCOUNT (para carpetas)
# ──────────────────────────────────────────────────────────

def get_drive_service():
    config = frappe.get_single("Configuracion_Drive")
    if not config.activo:
        frappe.throw("Integración con Google Drive no está activa.")
    if not config.service_account_json:
        frappe.throw("Falta el JSON de la Service Account en Configuracion Drive.")
    if not config.carpeta_madre_id:
        frappe.throw("Falta el ID de la carpeta madre en Configuracion Drive.")

    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    creds_dict = json.loads(config.service_account_json)
    credentials = service_account.Credentials.from_service_account_info(
        creds_dict,
        scopes=["https://www.googleapis.com/auth/drive"]
    )
    return build("drive", "v3", credentials=credentials)


# ──────────────────────────────────────────────────────────
# OAUTH2 (para subir archivos como usuario Gmail)
# ──────────────────────────────────────────────────────────

def get_drive_service_oauth():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request as GoogleRequest
    from googleapiclient.discovery import build

    config = frappe.get_single("Configuracion_Drive")
    refresh_token = config.get_password("oauth_refresh_token")
    client_secret = config.get_password("oauth_client_secret")

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=config.oauth_client_id,
        client_secret=client_secret,
        scopes=["https://www.googleapis.com/auth/drive"]
    )
    creds.refresh(GoogleRequest())
    return build("drive", "v3", credentials=creds)


def _tiene_oauth():
    config = frappe.get_single("Configuracion_Drive")
    return bool(config.get("oauth_autorizado") and config.get("oauth_client_id")
                and config.get_password("oauth_refresh_token"))


@frappe.whitelist()
def iniciar_oauth_drive(usar_playground=False):
    config = frappe.get_single("Configuracion_Drive")
    if not config.oauth_client_id:
        frappe.throw("Configura el OAuth Client ID primero.")

    if usar_playground:
        redirect_uri = "https://developers.google.com/oauthplayground"
    else:
        redirect_uri = _get_redirect_uri()

    params = {
        "client_id": config.oauth_client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/drive",
        "access_type": "offline",
        "prompt": "consent",
    }
    return "https://accounts.google.com/o/oauth2/auth?" + urlencode(params)


@frappe.whitelist()
def guardar_refresh_token_manual(refresh_token):
    if not refresh_token:
        frappe.throw("El refresh token no puede estar vacío.")
    frappe.db.set_value("Configuracion_Drive", "Configuracion_Drive", {
        "oauth_refresh_token": refresh_token,
        "oauth_autorizado": 1,
    })
    frappe.db.commit()
    return {"status": "ok"}


@frappe.whitelist(allow_guest=True)
def oauth_callback_drive():
    code = frappe.form_dict.get("code")
    error = frappe.form_dict.get("error")

    if error or not code:
        frappe.respond_as_web_page(
            "Error OAuth Drive",
            "No se pudo autorizar: {}".format(error or "sin código"),
            http_status_code=400
        )
        return

    config = frappe.get_single("Configuracion_Drive")
    redirect_uri = _get_redirect_uri()

    resp = _requests.post("https://oauth2.googleapis.com/token", data={
        "code": code,
        "client_id": config.oauth_client_id,
        "client_secret": config.get_password("oauth_client_secret"),
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    })
    tokens = resp.json()

    if "refresh_token" not in tokens:
        frappe.respond_as_web_page(
            "Error OAuth Drive",
            "No se obtuvo refresh_token. Respuesta: {}".format(json.dumps(tokens)),
            http_status_code=400
        )
        return

    frappe.db.set_value("Configuracion_Drive", "Configuracion_Drive", {
        "oauth_refresh_token": tokens["refresh_token"],
        "oauth_autorizado": 1,
    })
    frappe.db.commit()

    frappe.local.response["type"] = "redirect"
    frappe.local.response["location"] = "/app/configuracion_drive?oauth=ok"


def _get_redirect_uri():
    site_url = frappe.utils.get_url()
    return "{}/api/method/evoluciona_pyme_v2.evoluciona_pyme_v2.drive.oauth_callback_drive".format(
        site_url.rstrip("/")
    )


@frappe.whitelist()
def get_redirect_uri_info():
    return _get_redirect_uri()


# ──────────────────────────────────────────────────────────
# CARPETAS (usa Service Account — no requiere cuota)
# ──────────────────────────────────────────────────────────

def _crear_subcarpeta(service, nombre, padre_id):
    carpeta = service.files().create(
        body={
            "name": nombre,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [padre_id]
        },
        fields="id"
    ).execute()
    return carpeta.get("id")


def crear_carpeta_cliente(cliente_name):
    config = frappe.get_single("Configuracion_Drive")
    if not config.activo:
        return

    cliente = frappe.get_doc("Ficha_Cliente", cliente_name)
    service = get_drive_service()
    valores = {}

    if not cliente.get("drive_folder_id"):
        nombre = f"{cliente.abreviatura_cliente or cliente_name} - {cliente.razon_social or ''}".strip(" -")
        carpeta = service.files().create(
            body={
                "name": nombre,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [config.carpeta_madre_id]
            },
            fields="id,webViewLink"
        ).execute()
        carpeta_id = carpeta.get("id")
        valores["drive_folder_id"] = carpeta_id
        valores["drive_folder_url"] = carpeta.get("webViewLink")
        valores["drive_folder_id_display"] = carpeta_id
        valores["drive_folder_url_display"] = carpeta.get("webViewLink")
    else:
        carpeta_id = cliente.get("drive_folder_id")
        carpeta = None

    if not cliente.get("drive_f29_id"):
        valores["drive_f29_id"] = _crear_subcarpeta(service, "F29", carpeta_id)
    if not cliente.get("drive_libros_id"):
        valores["drive_libros_id"] = _crear_subcarpeta(service, "Libros", carpeta_id)
    if not cliente.get("drive_declaraciones_id"):
        valores["drive_declaraciones_id"] = _crear_subcarpeta(service, "Declaraciones", carpeta_id)

    if valores:
        frappe.db.set_value("Ficha_Cliente", cliente_name, valores)
        frappe.db.commit()
        frappe.logger().info(f"Carpeta Drive actualizada para {cliente_name}: {carpeta_id}")

    return carpeta


def obtener_o_crear_carpeta_año(service, carpeta_padre_id, año):
    año_str = str(año)
    query = (
        f"name = '{año_str}' "
        f"and '{carpeta_padre_id}' in parents "
        f"and mimeType = 'application/vnd.google-apps.folder' "
        f"and trashed = false"
    )
    resultado = service.files().list(q=query, fields="files(id)").execute()
    archivos = resultado.get("files", [])
    if archivos:
        return archivos[0]["id"]

    carpeta = service.files().create(
        body={
            "name": año_str,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [carpeta_padre_id]
        },
        fields="id"
    ).execute()
    return carpeta.get("id")


# ──────────────────────────────────────────────────────────
# SUBIR ARCHIVO (usa OAuth si está configurado)
# ──────────────────────────────────────────────────────────

def subir_pdf(file_bytes, nombre_archivo, carpeta_id, año=None):
    from googleapiclient.http import MediaInMemoryUpload

    if _tiene_oauth():
        service = get_drive_service_oauth()
    else:
        service = get_drive_service()

    if año:
        carpeta_id = obtener_o_crear_carpeta_año(service, carpeta_id, año)

    archivo = service.files().create(
        body={
            "name": nombre_archivo,
            "parents": [carpeta_id]
        },
        media_body=MediaInMemoryUpload(file_bytes, mimetype="application/pdf"),
        fields="id,webViewLink",
        supportsAllDrives=True
    ).execute()

    return {
        "id": archivo.get("id"),
        "url": archivo.get("webViewLink")
    }


# ──────────────────────────────────────────────────────────
# WHITELISTED
# ──────────────────────────────────────────────────────────

@frappe.whitelist()
def crear_carpeta_manual(cliente):
    try:
        resultado = crear_carpeta_cliente(cliente)
        if resultado:
            return {"status": "ok", "url": resultado.get("webViewLink")}
        return {"status": "ya_existe", "message": "El cliente ya tiene carpeta asignada."}
    except Exception as e:
        frappe.log_error(str(e), "Drive - crear_carpeta_manual")
        return {"status": "error", "message": str(e)}
