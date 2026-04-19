import frappe

def execute():
    doctypes_to_delete = [
        "Test_API",
        "Test_Calculadora",
        "Test_Numero",
        "Simpleapi"
    ]
    
    for dt in doctypes_to_delete:
        try:
            if frappe.db.exists("DocType", dt):
                frappe.delete_doc("DocType", dt, force=1)
                print(f"Deleted Doctype: {dt}")
            else:
                print(f"Doctype {dt} not found.")
        except Exception as e:
            print(f"Error deleting {dt}: {e}")
            
    frappe.db.commit()
    print("Cleanup complete.")
