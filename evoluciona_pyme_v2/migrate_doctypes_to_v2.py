import json
import frappe
from frappe.core.doctype.doctype.doctype import DocType

def execute():
    file_path = '/home/erpnext/erpnext-bench/apps/evoluciona_pyme/evoluciona_pyme/fixtures/doctype.json'
    with open(file_path, 'r') as f:
        data = json.load(f)

    for dt in data:
        if 'name' not in dt:
            continue
        
        name = dt['name']
        
        if frappe.db.exists("DocType", name):
            doc = frappe.get_doc("DocType", name)
            doc.custom = 0
            doc.module = "Evoluciona Pyme V2"
            try:
                doc.save(ignore_permissions=True)
                print(f"Updated {name} to custom=0 and module=Evoluciona Pyme V2")
            except Exception as e:
                print(f"Error updating {name}: {e}")
        else:
            dt['custom'] = 0
            dt['module'] = "Evoluciona Pyme V2"
            doc = frappe.get_doc(dt)
            try:
                doc.insert(ignore_permissions=True)
                print(f"Created {name} as custom=0")
            except Exception as e:
                print(f"Error creating {name}: {e}")

    frappe.db.commit()
    print("Migration completed.")
