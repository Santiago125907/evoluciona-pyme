import frappe
from frappe.modules.export_file import export_to_files

def execute():
    try:
        if frappe.db.exists("DocType", "Declaracion_Mensual"):
            frappe.db.set_value("DocType", "Declaracion_Mensual", "custom", 0)
            frappe.db.set_value("DocType", "Declaracion_Mensual", "module", "Evoluciona Pyme V2")
            frappe.db.commit()
            
            # Export to generate files
            export_to_files(record_list=[['DocType', 'Declaracion_Mensual']], record_module='Evoluciona Pyme V2')
            print("Successfully exported Declaracion_Mensual")
        else:
            print("DocType Declaracion_Mensual does not exist in DB.")
    except Exception as e:
        print("Error:", e)
