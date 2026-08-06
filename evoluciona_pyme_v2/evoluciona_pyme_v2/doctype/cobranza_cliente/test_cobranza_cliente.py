# Copyright (c) 2026, Santiago Romero and Contributors
# See license.txt

# import frappe
from frappe.tests.utils import FrappeTestCase

# Sales Invoice es de ERPNext (campo factura_vinculada) -- no esta instalado
# en este bench. Sin esto, cualquier test que dependa de Cobranza_Cliente
# (directo o via recursion, ej. Declaracion_Mensual -> cobranza_vinculada)
# falla al armar los fixtures automaticos con "DocType Sales Invoice not found".
IGNORE_TEST_RECORD_DEPENDENCIES = ["Sales Invoice"]


class TestCobranza_Cliente(FrappeTestCase):
	pass
