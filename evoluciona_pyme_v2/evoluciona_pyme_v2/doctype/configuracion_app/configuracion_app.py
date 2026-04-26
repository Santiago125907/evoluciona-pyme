import frappe
from frappe.model.document import Document


class ConfiguracionApp(Document):

    def validate(self):
        self._calcular_cron_expresion()
        self._validar_dia()

    def _validar_dia(self):
        dia = self.dia_ejecucion_tareas or 1
        if not (1 <= int(dia) <= 28):
            frappe.throw("El día de ejecución debe estar entre 1 y 28.")

    def _calcular_cron_expresion(self):
        if not self.habilitar_tareas_mensuales:
            self.cron_expresion_calculada = "(deshabilitado)"
            return
        hora = (self.hora_ejecucion_tareas or "08:00").split(":")[0].lstrip("0") or "0"
        dia = self.dia_ejecucion_tareas or 1
        self.cron_expresion_calculada = f"0 {hora} {dia} * *"
