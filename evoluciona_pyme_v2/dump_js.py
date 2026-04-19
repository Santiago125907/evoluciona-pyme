import frappe

def dump():
    page = frappe.get_doc("Web Page", "portal-del-cliente")
    print("--- START HTML ---")
    print(page.main_section)
    print("--- END HTML ---")
