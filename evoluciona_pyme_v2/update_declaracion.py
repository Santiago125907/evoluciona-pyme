import frappe

def execute():
    try:
        doc = frappe.get_doc('DocType', 'Declaracion_Mensual')
        doc.module = 'Evoluciona Pyme V2'
        doc.custom = 0
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        print("Updated Declaracion_Mensual module successfully!")
    except Exception as e:
        print("Error:", e)

