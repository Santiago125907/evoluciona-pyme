# Copyright (c) 2026, Santiago Romero and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Ficha_Cliente(Document):
	def validate(self):
		self.validar_descuentos()

	def validar_descuentos(self):
		for fila in (self.get("descuentos_cliente") or []):
			if not fila.get("mes_inicio"):
				frappe.throw(f"Descuento '{fila.get('descripcion') or fila.idx}': falta \"Mes inicio\".")

			if fila.get("aplica_una_vez"):
				continue

			if not fila.get("mes_fin"):
				frappe.throw(
					f"Descuento '{fila.get('descripcion') or fila.idx}': falta \"Mes fin\" "
					"(o marca \"Aplica una sola vez\" si es puntual)."
				)

			if frappe.utils.getdate(fila.mes_inicio) > frappe.utils.getdate(fila.mes_fin):
				frappe.throw(
					f"Descuento '{fila.get('descripcion') or fila.idx}': \"Mes inicio\" "
					"no puede ser posterior a \"Mes fin\"."
				)
