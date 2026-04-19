import frappe
from frappe.core.doctype.doctype.doctype import export_customizations
frappe.init(site='mi-empresa.local')
frappe.connect()
from frappe.modules.export_file import export_to_files
export_to_files(record_list=[['DocType', 'Declaracion_Mensual']], record_module='Evoluciona Pyme V2')
