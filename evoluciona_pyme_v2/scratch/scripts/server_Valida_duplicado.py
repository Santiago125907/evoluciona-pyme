# Script para validar duplicados en Libro_de_Egresos_Cliente (Versión Mejorada)

# 1. Definimos la "huella digital" del documento, ahora con 4 parámetros.
filters = {
    "doctype": "Libro_de_Egresos_Cliente",
    "cliente": doc.cliente,
    "rut_proveedor": doc.rut_proveedor,
    "folio": doc.folio,
    "tipo_egreso": doc.tipo_egreso  # <-- NUEVO PARÁMETRO AÑADIDO
}

# 2. Si estamos editando un documento, nos aseguramos de no compararlo consigo mismo.
if not doc.is_new():
    filters["name"] = ("!=", doc.name)

# 3. Buscamos en la base de datos si ya existe un documento con esa huella exacta.
is_duplicated = frappe.db.exists(filters)

# 4. Si se encuentra un duplicado, detenemos el guardado y lanzamos un error más específico.
if is_duplicated:
    frappe.throw("Error de Duplicidad: Ya existe un documento con el mismo RUT de proveedor, Folio y Tipo de Egreso para este cliente.")