import frappe
from frappe.utils import add_months, getdate, formatdate

def crear_tareas_mensuales():
    # Migrated from server_Crear_Tareas_Mensuales.py
    mes_actual = getdate().replace(day=1)

    fichas = frappe.get_all(
        "Ficha_Cliente",
        filters={"estado": "Activo"},
        fields=["name", "cliente", "responsable_asignado"]
    )

    frappe.log_error(f"Iniciando creación de tareas mensuales. Fichas encontradas: {len(fichas)}", "Crear Tareas Mensuales")

    # The rest of the script...
    # (Since I need to inject the full content, I'll write the shell first and then use the previous extracted file via script)
