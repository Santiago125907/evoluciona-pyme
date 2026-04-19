# Copyright (c) 2026, Santiago Romero and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Cobranza_Cliente(Document):
	def before_save(self):
		self.calcular_dias_vencimiento()

	def calcular_dias_vencimiento(self):
		"""Calcula días para vencer y actualiza estado si está vencido"""
		if not self.fecha_vencimiento:
			return

		hoy = frappe.utils.getdate(frappe.utils.nowdate())
		fecha_venc = frappe.utils.getdate(self.fecha_vencimiento)

		diferencia = frappe.utils.date_diff(fecha_venc, hoy)
		self.dias_para_vencer = int(diferencia)

		if diferencia < 0 and self.estado_cobranza not in ["Pagado", "Anulado"]:
			self.estado_cobranza = "Vencido"
