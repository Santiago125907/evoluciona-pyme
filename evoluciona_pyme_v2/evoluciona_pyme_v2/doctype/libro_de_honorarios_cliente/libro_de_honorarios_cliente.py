import frappe
from frappe.model.document import Document


class Libro_de_Honorarios_Cliente(Document):
	def before_save(self):
		self._calcular_campos()
		self._validar_duplicado()

	def _calcular_campos(self):
		# Retención = 10.75% del monto bruto
		if self.monto_bruto:
			self.retencion_honorarios = frappe.utils.flt(self.monto_bruto * 0.1075, 0)
			self.monto_liquido = frappe.utils.flt(self.monto_bruto - self.retencion_honorarios, 0)
			self.total_documento = frappe.utils.flt(self.monto_bruto, 0)
			if not self.costo_empresa:
				self.costo_empresa = self.monto_bruto

	def _validar_duplicado(self):
		if not self.folio or not self.rut_prestador:
			return
		filtros = {
			"doctype": "Libro_de_Honorarios_Cliente",
			"cliente": self.cliente,
			"rut_prestador": self.rut_prestador,
			"folio": self.folio,
			"name": ("!=", self.name or ""),
		}
		if frappe.db.exists(filtros):
			frappe.throw(
				f"Ya existe la boleta N° {self.folio} del prestador {self.rut_prestador} en este cliente.",
				title="Boleta duplicada"
			)
