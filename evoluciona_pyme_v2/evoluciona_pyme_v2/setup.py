import frappe


def after_install():
    try:
        from frappe.utils.fixtures import sync_fixtures
        sync_fixtures(app="evoluciona_pyme_v2")
        frappe.db.commit()
        from frappe.desk.doctype.desktop_icon.desktop_icon import create_desktop_icons_from_installed_apps
        create_desktop_icons_from_installed_apps()
        frappe.db.commit()
    except Exception:
        frappe.log_error("Setup - after_install", frappe.get_traceback())


