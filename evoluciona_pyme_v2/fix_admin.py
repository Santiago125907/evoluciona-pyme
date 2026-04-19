import frappe

def fix():
    # Remove custom properties from Website Settings
    web_settings = frappe.get_doc("Website Settings", "Website Settings")
    if web_settings.home_page == "portal-del-cliente":
        pass 
    
    # Reset role home pages for Administrator and System Manager
    if frappe.db.exists("DocType", "Role Home Page"):
        for rhp in frappe.get_all("Role Home Page"):
            doc = frappe.get_doc("Role Home Page", rhp.name)
            if doc.role in ["Administrator", "System Manager"]:
                frappe.delete_doc("Role Home Page", rhp.name)
                print(f"Deleted Role Home Page config for {doc.role}")

    # Ensure Administrator has Desk Access
    user = frappe.get_doc("User", "Administrator")
    if not user.has_desk_access:
        user.db_set("has_desk_access", 1)
        frappe.db.commit()
        print("Restored Desk Access for Administrator")
    
    # Also fix massive_perm_fix logic if there's any Workspace overrides causing issues by deleting custom Workspace overrides if any, but let's start with this.
    frappe.db.commit()
    print("Fixed Admin routing!")
