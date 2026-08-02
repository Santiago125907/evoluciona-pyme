# Copyright (c) 2026, Santiago Romero and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Registro_Remuneraciones(Document):
    def on_update(self):
        """Sincroniza el total de previred a la Declaracion_Mensual del mismo cliente/mes/año."""
        self._sync_declaracion_mensual()

    def _sync_declaracion_mensual(self):
        if not (self.cliente and self.mes and self.ano):
            return
        decl_name = frappe.db.get_value(
            "Declaracion_Mensual",
            {
                "cliente": self.cliente,
                "mes":     str(self.mes),
                "ano":     str(self.ano),
                "estado":  ["not in", ["Publicado", "Enviado"]],
            },
            "name",
        )
        if not decl_name:
            return
        frappe.db.set_value("Declaracion_Mensual", decl_name, {
            "total_previred_a_pagar": float(self.total_previred_a_pagar or 0),
        })
        frappe.db.commit()
