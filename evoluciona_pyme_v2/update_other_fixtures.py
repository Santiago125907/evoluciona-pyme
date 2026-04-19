import json
import frappe

def execute():
    try:
        # Move Workspace
        ws_list = frappe.get_all('Workspace', filters={'module': 'Evoluciona Pyme'})
        for ws in ws_list:
            doc = frappe.get_doc('Workspace', ws.name)
            doc.module = 'Evoluciona Pyme V2'
            doc.custom = 0
            doc.save(ignore_permissions=True)
            print(f"Updated Workspace {ws.name}")
        
        # Move Web Pages
        wp_list = frappe.get_all('Web Page', filters={'module': 'Evoluciona Pyme'})
        for wp in wp_list:
            doc = frappe.get_doc('Web Page', wp.name)
            doc.module = 'Evoluciona Pyme V2'
            doc.save(ignore_permissions=True)
            print(f"Updated Web Page {wp.name}")
            
        frappe.db.commit()
    except Exception as e:
        print("Error:", e)
