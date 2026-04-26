import frappe


def sync_fixtures_post_migrate():
    """Reimporta los fixtures de evoluciona_pyme_v2 después del migrate
    para restaurar el Workspace y otros registros que el migrate elimina como huérfanos."""
    try:
        from frappe.utils.fixtures import sync_fixtures
        sync_fixtures(app="evoluciona_pyme_v2")
        frappe.db.commit()
    except Exception:
        frappe.log_error("Setup - sync_fixtures_post_migrate", frappe.get_traceback())
