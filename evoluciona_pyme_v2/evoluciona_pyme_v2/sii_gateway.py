import frappe
import requests

DEFAULT_URL = "https://sii.sjscuti.cl"

# Pedimos solo REGISTRO, que es lo que el SII cuenta en su resumen oficial y por
# tanto lo que debe cuadrar con el F29. Las compras pendientes entran solas al
# registro pasados los 8 días de acuse, así que en un mes cerrado no queda ninguna.
# Además, en ventas el estado no existe: el gateway consulta una vez por estado
# pedido y re-etiqueta el mismo documento, de modo que pedir dos los duplica.
ESTADOS_REGISTRO = ["REGISTRO"]


def _config():
    from frappe.utils.password import get_decrypted_password

    url = frappe.db.get_single_value("Configuracion App", "sii_api_url") or DEFAULT_URL
    token = get_decrypted_password(
        "Configuracion App", "Configuracion App", "sii_api_token", raise_exception=False
    )
    if not token:
        frappe.throw("Falta el token del SII Gateway en Configuracion App.")
    return url.rstrip("/"), token


def tipo_login(rut):
    """Los RUT bajo 50.000.000 son personas naturales; el resto, empresas."""
    cuerpo = str(rut or "").split("-")[0].replace(".", "").strip()
    try:
        return "persona" if int(cuerpo) < 50_000_000 else "empresa"
    except ValueError:
        return "empresa"


def login_de(ficha):
    return {
        "rut": ficha.rut_cliente,
        "clave": ficha.clave_sii,
        "tipo": tipo_login(ficha.rut_cliente),
    }


def cuerpo_rcv(ficha, periodo):
    return {
        "login": login_de(ficha),
        "contribuyente": ficha.rut_cliente,
        "periodo": periodo,
        "estados": ESTADOS_REGISTRO,
    }


def post(path, body, timeout=120):
    url, token = _config()
    resp = None
    try:
        resp = requests.post(
            f"{url}{path}",
            headers={"X-API-Key": token, "Content-Type": "application/json"},
            json=body or {},
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.Timeout:
        frappe.throw(f"SII Gateway: timeout en {path}.")
    except requests.exceptions.HTTPError:
        frappe.throw(f"SII Gateway error {resp.status_code} en {path}: {resp.text[:300]}")
    except Exception as e:
        frappe.throw(f"SII Gateway: {e}")


def get(path, params=None, timeout=60):
    url, token = _config()
    resp = None
    try:
        resp = requests.get(
            f"{url}{path}",
            headers={"X-API-Key": token},
            params=params or {},
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.Timeout:
        frappe.throw(f"SII Gateway: timeout en {path}.")
    except requests.exceptions.HTTPError:
        frappe.throw(f"SII Gateway error {resp.status_code} en {path}: {resp.text[:300]}")
    except Exception as e:
        frappe.throw(f"SII Gateway: {e}")


CODIGO_REMANENTE_MES_ANTERIOR = "504"


def actualizar_remanente_cliente(cliente, ano, mes):
    """
    Consulta el F29 oficial del SII para el período y actualiza la línea del
    código 504 (Remanente Crédito Fiscal Mes Anterior) del Borrador_F29
    correspondiente. No toca total_a_pagar ni ningún otro código — eso lo
    valida un humano.
    Retorna True si actualizó la línea, False si no encontró Borrador_F29
    para ese período o el código no vino en la respuesta.
    """
    ficha = frappe.get_doc("Ficha_Cliente", cliente)
    periodo = f"{ano}-{str(mes).zfill(2)}"
    body = {
        "login": login_de(ficha),
        "contribuyente": ficha.rut_cliente,
        "periodo": periodo,
    }
    respuesta = post("/v1/f29/formulario", body, timeout=180)
    monto = (respuesta.get("todos_los_codigos") or {}).get(CODIGO_REMANENTE_MES_ANTERIOR)
    if monto is None:
        return False

    f29_name = frappe.db.get_value(
        "Borrador_F29", {"cliente": cliente, "ano": str(ano), "mes": str(mes)}, "name"
    )
    if not f29_name:
        return False

    doc = frappe.get_doc("Borrador_F29", f29_name)
    for linea in doc.tabla_creditos:
        if str(linea.codigo_f29) == CODIGO_REMANENTE_MES_ANTERIOR:
            linea.monto = monto
            linea.tipo_origen = "SII Oficial"
            break
    else:
        doc.append("tabla_creditos", {
            "codigo_f29": CODIGO_REMANENTE_MES_ANTERIOR,
            "descripcion": "Remanente Crédito Fiscal Mes Anterior",
            "monto": monto,
            "tipo_operacion_subtotal": "Suma",
            "tipo_origen": "SII Oficial",
        })
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return True
