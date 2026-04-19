# Copyright (c) 2026, Santiago Romero and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Libro_de_Egresos_Cliente(Document):
	def before_save(self):
		"""Valida que no exista un egreso duplicado para el mismo cliente, proveedor, folio y tipo."""
		filters = {
			"doctype": "Libro_de_Egresos_Cliente",
			"cliente": self.cliente,
			"rut_proveedor": self.rut_proveedor,
			"folio": self.folio,
			"tipo_egreso": self.tipo_egreso,
		}

		# Al editar, excluir el propio documento de la búsqueda
		if not self.is_new():
			filters["name"] = ("!=", self.name)

		if frappe.db.exists(filters):
			frappe.throw(
				"Error de Duplicidad: Ya existe un documento con el mismo "
				"RUT de proveedor, Folio y Tipo de Egreso para este cliente."
			)
