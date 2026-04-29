import json
import frappe
from frappe.model.document import Document


class Configuracion_Drive(Document):
    def before_save(self):
        if self.service_account_json:
            try:
                data = json.loads(self.service_account_json)
                self.client_email_info = data.get("client_email", "")
            except Exception:
                frappe.throw("El JSON ingresado no es válido.")
