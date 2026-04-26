import frappe
from frappe.model.document import Document


class Libro_de_Compras_Cliente(Document):
	def before_save(self):
		self._validar_duplicado()

	def _validar_duplicado(self):
		if not self.folio or not self.rut_proveedor:
			return
		filtros = {
			"doctype": "Libro_de_Compras_Cliente",
			"cliente": self.cliente,
			"rut_proveedor": self.rut_proveedor,
			"folio": self.folio,
			"tipo_documento": self.tipo_documento,
			"name": ("!=", self.name or ""),
		}
		if frappe.db.exists(filtros):
			frappe.throw(
				f"Ya existe un registro para el folio {self.folio} del proveedor {self.rut_proveedor} "
				f"con tipo {self.tipo_documento} en este cliente.",
				title="Documento duplicado"
			)
