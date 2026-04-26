import frappe


def after_install():
    try:
        from frappe.utils.fixtures import sync_fixtures
        sync_fixtures(app="evoluciona_pyme_v2")
        frappe.db.commit()
    except Exception:
        frappe.log_error("Setup - after_install", frappe.get_traceback())


def sync_fixtures_post_migrate():
    try:
        from frappe.utils.fixtures import sync_fixtures
        sync_fixtures(app="evoluciona_pyme_v2")
        frappe.db.commit()
    except Exception:
        frappe.log_error("Setup - sync_fixtures_post_migrate", frappe.get_traceback())
