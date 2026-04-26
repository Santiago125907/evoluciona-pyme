import frappe
from frappe.model.document import Document


class Libro_de_Gastos_Cliente(Document):
	def before_save(self):
		self._calcular_total()

	def _calcular_total(self):
		neto = frappe.utils.flt(self.neto)
		iva = frappe.utils.flt(self.iva)
		self.total_documento = neto + iva
		if not self.costo_empresa:
			self.costo_empresa = self.total_documento
