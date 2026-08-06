# Copyright (c) 2026, Santiago Romero and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []
# Sales Invoice es de ERPNext (Cobranza_Cliente.factura_vinculada) -- no esta
# instalado en este bench y no lo usan estos tests.
IGNORE_TEST_RECORD_DEPENDENCIES = ["Sales Invoice"]


def _crear_cliente_test(rut, abrev, monto_base_fijo=100000):
	"""Cliente minimo con precio fijo -- evita tener que armar Plan_Contable/tramos
	solo para probar la creacion de cobranza. Mockea crear_carpeta_cliente porque
	el hook after_insert real llama a la API de Google Drive."""
	if frappe.db.exists("Ficha_Cliente", rut):
		frappe.delete_doc("Ficha_Cliente", rut, force=True)
	cliente = frappe.get_doc({
		"doctype": "Ficha_Cliente",
		"razon_social": f"_Test Cliente {abrev}",
		"rut_cliente": rut,
		"abreviatura_cliente": abrev,
		"estado_cliente": "Activo",
		"precio_fijo": 1,
		"monto_base_fijo": monto_base_fijo,
		"dia_vencimiento": "15 días después",
	})
	with patch("evoluciona_pyme_v2.evoluciona_pyme_v2.drive.crear_carpeta_cliente"):
		cliente.insert(ignore_permissions=True)
	return cliente


def _crear_declaracion_lista(cliente_name, ano, mes):
	"""Inserta la Declaracion_Mensual y la guarda una segunda vez marcada 'Listo'
	-- crear_cobranza_si_corresponde solo corre en saves posteriores al insert
	(is_new() protege la primera vez), igual que en producción."""
	id_doc = f"_Test-DM-{cliente_name}-{ano}-{mes}"
	if frappe.db.exists("Declaracion_Mensual", id_doc):
		frappe.delete_doc("Declaracion_Mensual", id_doc, force=True)

	dm = frappe.get_doc({
		"doctype": "Declaracion_Mensual",
		"id_documento": id_doc,
		"cliente": cliente_name,
		"ano": str(ano),
		"mes": str(mes),
	})
	dm.insert(ignore_permissions=True)

	dm.check_gasto_rem_cargado = 1
	dm.check_f29_cuadrado = 1
	dm.save(ignore_permissions=True)
	return dm


class IntegrationTestDeclaracion_Mensual(IntegrationTestCase):
	"""
	Integration tests for Declaracion_Mensual.
	"""

	def test_crear_cobranza_al_pasar_a_listo(self):
		"""La cobranza no se crea al insertar (documento nuevo); se crea recien
		en el siguiente guardado, cuando el estado calculado queda en 'Listo',
		y el monto debe calzar con el precio fijo del cliente."""
		cliente = _crear_cliente_test("_Test-RUT-COB-1", "TCOB1", monto_base_fijo=123000)

		dm = frappe.get_doc({
			"doctype": "Declaracion_Mensual",
			"id_documento": "_Test-DM-nueva-cob1",
			"cliente": cliente.name,
			"ano": "2026",
			"mes": "5",
		})
		dm.insert(ignore_permissions=True)
		self.assertEqual(dm.estado, "Borrador")
		self.assertFalse(frappe.db.exists("Cobranza_Cliente", {"cliente": dm.cliente, "periodo_ano": int(dm.ano), "periodo_mes": int(dm.mes)}))

		dm.check_gasto_rem_cargado = 1
		dm.check_f29_cuadrado = 1
		dm.save(ignore_permissions=True)
		self.assertEqual(dm.estado, "Listo")

		cobranza_name = frappe.db.get_value("Cobranza_Cliente", {"cliente": dm.cliente, "periodo_ano": int(dm.ano), "periodo_mes": int(dm.mes)}, "name")
		self.assertTrue(cobranza_name, "Debio crearse una Cobranza_Cliente al pasar a Listo")

		cobranza = frappe.get_doc("Cobranza_Cliente", cobranza_name)
		self.assertEqual(float(cobranza.monto_a_cobrar), 123000.0)
		self.assertEqual(cobranza.estado_cobranza, "Por Cobrar")

	def test_no_duplica_cobranza_si_ya_existe(self):
		"""Si ya existe una Cobranza_Cliente para el cliente/periodo, no crea otra
		aunque el estado siga calculando 'Listo' en guardados sucesivos."""
		cliente = _crear_cliente_test("_Test-RUT-COB-2", "TCOB2", monto_base_fijo=50000)
		dm = _crear_declaracion_lista(cliente.name, 2026, 5)

		total_antes = frappe.db.count("Cobranza_Cliente", {"cliente": cliente.name})
		self.assertEqual(total_antes, 1)

		# Un segundo guardado en estado Listo no debe generar una segunda cobranza.
		dm.check_previred_cuadrado = 1
		dm.save(ignore_permissions=True)

		total_despues = frappe.db.count("Cobranza_Cliente", {"cliente": cliente.name})
		self.assertEqual(total_despues, 1)

	def test_recargo_por_pago_atrasado_se_aplica_una_vez(self):
		"""Si la cobranza del mes anterior quedo marcada pago_atrasado=1 (sin
		recargo_aplicado todavia), la cobranza del mes siguiente debe sumar el
		monto_recargo_pago_atrasado configurado -- y no debe volver a sumarlo si
		se genera una tercera cobranza despues (recargo_aplicado ya en 1)."""
		monto_recargo_original = frappe.db.get_single_value("Configuracion App", "monto_recargo_pago_atrasado")
		frappe.db.set_single_value("Configuracion App", "monto_recargo_pago_atrasado", 5000)

		try:
			cliente = _crear_cliente_test("_Test-RUT-COB-3", "TCOB3", monto_base_fijo=100000)

			dm_mes1 = _crear_declaracion_lista(cliente.name, 2026, 5)
			cobranza1_name = frappe.db.get_value(
				"Cobranza_Cliente",
				{"cliente": dm_mes1.cliente, "periodo_ano": int(dm_mes1.ano), "periodo_mes": int(dm_mes1.mes)},
				"name",
			)
			self.assertTrue(cobranza1_name)

			# Simular pago atrasado del mes 5 (sin marcar recargo_aplicado todavia).
			frappe.db.set_value("Cobranza_Cliente", cobranza1_name, "pago_atrasado", 1)

			dm_mes2 = _crear_declaracion_lista(cliente.name, 2026, 6)
			cobranza2_name = frappe.db.get_value(
				"Cobranza_Cliente",
				{"cliente": dm_mes2.cliente, "periodo_ano": int(dm_mes2.ano), "periodo_mes": int(dm_mes2.mes)},
				"name",
			)
			cobranza2 = frappe.get_doc("Cobranza_Cliente", cobranza2_name)

			self.assertEqual(float(cobranza2.recargo_por_atraso), 5000.0)
			self.assertEqual(float(cobranza2.monto_a_cobrar), 105000.0)

			# La cobranza origen (mes 5) debe quedar marcada para no cobrarlo dos veces.
			self.assertEqual(frappe.db.get_value("Cobranza_Cliente", cobranza1_name, "recargo_aplicado"), 1)

			# Un tercer mes NO debe volver a traer el recargo (ya se aplico una vez).
			dm_mes3 = _crear_declaracion_lista(cliente.name, 2026, 7)
			cobranza3_name = frappe.db.get_value(
				"Cobranza_Cliente",
				{"cliente": dm_mes3.cliente, "periodo_ano": int(dm_mes3.ano), "periodo_mes": int(dm_mes3.mes)},
				"name",
			)
			cobranza3 = frappe.get_doc("Cobranza_Cliente", cobranza3_name)
			self.assertEqual(float(cobranza3.recargo_por_atraso or 0), 0.0)

		finally:
			frappe.db.set_single_value(
				"Configuracion App", "monto_recargo_pago_atrasado", monto_recargo_original
			)
