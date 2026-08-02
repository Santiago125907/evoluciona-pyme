# Copyright (c) 2026, Santiago Romero and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Declaracion_Mensual(Document):
	def before_save(self):
		self.actualizar_estado_declaracion()
		self.calcular_vencimientos_impuestos()
		if not self.is_new():
			self.crear_cobranza_si_corresponde()
		else:
			frappe.logger().info("Documento nuevo, no se crea cobranza aún")

		# Guardar en flags si se está publicando (más robusto que atributo de instancia)
		old_publicado = 0
		if not self.is_new():
			old_publicado = frappe.db.get_value("Declaracion_Mensual", self.name, "publicado_portal") or 0
		if bool(self.publicado_portal) and not bool(old_publicado):
			frappe.flags.push_declaracion = self.name

	def after_save(self):
		"""Envía push notification al publicar la declaración en el portal."""
		if frappe.flags.get("push_declaracion") == self.name:
			frappe.flags.push_declaracion = None
			frappe.enqueue(
				"evoluciona_pyme_v2.evoluciona_pyme_v2.doctype.declaracion_mensual.declaracion_mensual.enviar_push_declaracion",
				name=self.name,
				queue="short",
				timeout=120,
				enqueue_after_commit=True,
			)

	def actualizar_estado_declaracion(self):
		# No sobreescribir estados especiales gestionados manualmente
		if self.estado in ("Publicado", "Enviado", "PDF Generado"):
			return

		check_rrhh = 1 if self.get('check_gasto_rem_cargado') else 0
		check_f29 = 1 if self.get('check_f29_cuadrado') else 0
		check_prev = 1 if self.get('check_previred_cuadrado') else 0

		# Si el cliente no tiene Previred, el check de Previred no es obligatorio
		usa_previred = bool(frappe.db.get_value('Ficha_Cliente', self.cliente, 'rut_usuario'))
		checks_ok = check_rrhh and check_f29 and (check_prev if usa_previred else True)

		total_checks = check_rrhh + check_f29 + check_prev

		if total_checks == 0:
			self.estado = "Borrador"
		elif checks_ok:
			self.estado = "Listo"
		else:
			self.estado = "En Validación"

		frappe.logger().info(
			f"Checks: RRHH={check_rrhh}, F29={check_f29}, Prev={check_prev} (req={usa_previred}) → Estado: {self.estado}"
		)

	def calcular_vencimientos_impuestos(self):
		if not (self.mes and self.ano):
			return

		fecha_declaracion = frappe.utils.getdate(f"{self.ano}-{str(self.mes).zfill(2)}-01")
		fecha_pago = frappe.utils.add_months(fecha_declaracion, 1)

		# PREVIRED (Día 12)
		venc_prev = frappe.utils.getdate(f"{fecha_pago.year}-{str(fecha_pago.month).zfill(2)}-12")
		dia_sem = venc_prev.weekday()
		if dia_sem == 5:
			venc_prev = frappe.utils.add_days(venc_prev, -1)
		elif dia_sem == 6:
			venc_prev = frappe.utils.add_days(venc_prev, -2)
		self.fecha_vencimiento_previred = venc_prev

		# F29 (Día 20)
		venc_f29 = frappe.utils.getdate(f"{fecha_pago.year}-{str(fecha_pago.month).zfill(2)}-20")
		dia_sem_f29 = venc_f29.weekday()
		if dia_sem_f29 == 5:
			venc_f29 = frappe.utils.add_days(venc_f29, 2)
		elif dia_sem_f29 == 6:
			venc_f29 = frappe.utils.add_days(venc_f29, 1)
		self.fecha_vencimiento_f29 = venc_f29

	def crear_cobranza_si_corresponde(self):
		frappe.logger().info(f"Verificando creación de cobranza... Estado actual: {self.estado}")

		if self.estado not in ["Listo", "Enviado"]:
			frappe.logger().info(f"Estado '{self.estado}' no dispara creación de cobranza")
			return

		existe = frappe.db.exists("Cobranza_Cliente", {
			"cliente": self.cliente,
			"periodo_ano": int(self.ano),
			"periodo_mes": int(self.mes)
		})

		if existe:
			frappe.logger().info(f"Ya existe cobranza para este período: {existe}")
			return

		frappe.logger().info("Procediendo a crear cobranza...")

		try:
			cliente_doc = frappe.get_doc("Ficha_Cliente", self.cliente)

			monto_contable = 0
			total_ventas = 0
			numero_empleados = 0

			# 1. Obtener Ventas descontando Notas de Crédito
			documentos = frappe.db.get_list(
				"Libro_de_Ingresos_Cliente",
				filters={
					"cliente": self.cliente,
					"ano_tributario": str(self.ano),
					"mes_tributario": str(self.mes).zfill(2)
				},
				fields=["neto", "tipo_documento"]
			)
			if not documentos:
				documentos = frappe.db.get_list(
					"Libro_de_Ingresos_Cliente",
					filters={
						"cliente": self.cliente,
						"ano_tributario": str(self.ano),
						"mes_tributario": str(self.mes)
					},
					fields=["neto", "tipo_documento"]
				)

			for d in documentos:
				if d.neto:
					tipo = str(d.tipo_documento or "").upper()
					if "NOTA DE CRÉDITO" in tipo or "NOTA DE CREDITO" in tipo:
						total_ventas -= float(d.neto)
					else:
						total_ventas += float(d.neto)

			frappe.logger().info(f"Ventas Netas del Mes: ${total_ventas:,.0f}")

			# 2. Determinar monto base: precio fijo o plan por tramos
			if cliente_doc.get('precio_fijo'):
				monto_contable = float(cliente_doc.get('monto_base_fijo') or 0)
				frappe.logger().info(f"Precio Base Fijo: ${monto_contable:,.0f}")
			elif cliente_doc.get('plan_contable'):
				plan = frappe.get_doc("Plan_Contable", cliente_doc.plan_contable)
				frappe.logger().info(f"Plan Asignado: {plan.nombre_del_plan}")
				for tramo in plan.tramos:
					if tramo.venta_minima <= total_ventas <= tramo.venta_maxima:
						monto_contable = tramo.valor_mensual
						frappe.logger().info(
							f"Tramo ${tramo.venta_minima:,.0f} a ${tramo.venta_maxima:,.0f} → Valor: ${monto_contable:,.0f}"
						)
						break

				if monto_contable == 0:
					frappe.msgprint("⚠️ ADVERTENCIA: Las ventas no cayeron en ningún tramo.", indicator='red')
			else:
				monto_contable = float(cliente_doc.get('monto_base_plan') or 0)
				frappe.logger().info("Cliente no tiene Plan por Tramos. Usando Monto Base antiguo.")

			# 3. RRHH
			monto_rrhh = 0
			if float(cliente_doc.get('monto_rrhh') or 0) > 0:
				monto_rrhh = float(cliente_doc.monto_rrhh)
				frappe.logger().info(f"RRHH (Fijo): ${monto_rrhh:,.0f}")
			elif cliente_doc.get('cobra_rrhh_variable'):
				registro_rrhh = frappe.db.get_value(
					"Registro_Remuneraciones",
					{"cliente": self.cliente, "ano": int(self.ano), "mes": int(self.mes)},
					"total_empleados_activos"
				)
				if registro_rrhh:
					numero_empleados = int(registro_rrhh or 0)
					tarifa = float(cliente_doc.get('monto_por_empleado') or 0)
					monto_rrhh = numero_empleados * tarifa
					frappe.logger().info(f"RRHH Variable: {numero_empleados} x ${tarifa} = ${monto_rrhh:,.0f}")

			# 4. Servicios adicionales
			monto_adicionales = 0
			if cliente_doc.get('servicios_adicionales'):
				for adicional in cliente_doc.servicios_adicionales:
					mes_ini = int(adicional.get('mes_inicio') or 0)
					ano_ini = int(adicional.get('ano_inicio') or 0)

					if not mes_ini or not ano_ini:
						continue

					meses_transcurridos = ((int(self.ano) - ano_ini) * 12) + (int(self.mes) - mes_ini)

					if meses_transcurridos < 0:
						frappe.logger().info(
							f"Adicional omitido: {adicional.nombre_servicio} (comienza en {mes_ini}/{ano_ini})"
						)
						continue

					tipo_duracion = adicional.get('tipo_duracion') or "Infinito"

					if tipo_duracion == "Infinito":
						monto_adicionales += float(adicional.valor_mensual or 0)
						frappe.logger().info(
							f"Adicional (Mensual Fijo): {adicional.nombre_servicio} → ${adicional.valor_mensual:,.0f}"
						)
					else:
						cuotas_totales = int(adicional.get('cuotas_totales') or 1)
						if meses_transcurridos < cuotas_totales:
							monto_adicionales += float(adicional.valor_mensual or 0)
							frappe.logger().info(
								f"Adicional (Cuota {meses_transcurridos + 1} de {cuotas_totales}): {adicional.nombre_servicio} → ${adicional.valor_mensual:,.0f}"
							)
						else:
							frappe.logger().info(
								f"Adicional omitido: {adicional.nombre_servicio} (finalizó sus {cuotas_totales} cuotas)"
							)

			subtotal = monto_contable + monto_rrhh + monto_adicionales

			# 5. Descuentos
			total_descuentos = 0
			descuentos_aplicados = []

			if cliente_doc.get('descuentos_cliente'):
				periodo_ano = int(self.ano)
				periodo_mes = int(self.mes)

				for desc in cliente_doc.descuentos_cliente:
					activo = desc.get('activo')
					if activo is None:
						activo = 1
					if not activo:
						continue

					fecha_inicio_desc = frappe.utils.getdate(desc.mes_inicio)
					fecha_fin_desc = frappe.utils.getdate(desc.mes_fin)

					periodo_num = (periodo_ano * 100) + periodo_mes
					inicio_num = (fecha_inicio_desc.year * 100) + fecha_inicio_desc.month
					fin_num = (fecha_fin_desc.year * 100) + fecha_fin_desc.month

					if inicio_num <= periodo_num <= fin_num:
						if desc.get('tipo_descuento') == "Porcentaje":
							monto_desc = subtotal * (float(desc.valor) / 100)
						else:
							monto_desc = float(desc.valor)

						total_descuentos += monto_desc
						descuentos_aplicados.append({
							"descripcion": desc.descripcion,
							"tipo": desc.tipo_descuento,
							"valor": float(desc.valor),
							"monto_descuento": monto_desc
						})

			monto_a_cobrar = subtotal - total_descuentos

			# 6. Fecha de vencimiento
			fecha_emision = frappe.utils.nowdate()
			dia_venc = cliente_doc.get('dia_vencimiento') or "15 días después"
			dia_mes = None

			if dia_venc == "Vencimiento F29 (día 12)":
				dia_mes = 12
			elif dia_venc == "Vencimiento Imposiciones (día 10)":
				dia_mes = 10
			elif dia_venc == "15 días después":
				fecha_vencimiento = frappe.utils.add_days(fecha_emision, 15)
			elif dia_venc == "Personalizado":
				dia_mes = int(cliente_doc.get('dia_vencimiento_personalizado') or 30)
			else:
				dia_mes = 30

			if dia_mes:
				mes_venc = int(self.mes) + 1
				ano_venc = int(self.ano)
				if mes_venc > 12:
					mes_venc = 1
					ano_venc += 1
				try:
					fecha_vencimiento = frappe.utils.getdate(
						f"{ano_venc}-{str(mes_venc).zfill(2)}-{str(dia_mes).zfill(2)}"
					)
				except Exception:
					fecha_vencimiento = frappe.utils.getdate(
						f"{ano_venc}-{str(mes_venc).zfill(2)}-28"
					)

			# 7. Recargo por haber pagado atrasada la cobranza del mes anterior
			# (se decide al momento de marcar "Pagado", no se infiere solo de la fecha)
			mes_ant = int(self.mes) - 1
			ano_ant = int(self.ano)
			if mes_ant < 1:
				mes_ant = 12
				ano_ant -= 1

			recargo_por_atraso = 0
			cobranza_previa = frappe.db.get_value(
				"Cobranza_Cliente",
				{
					"cliente": self.cliente,
					"periodo_ano": ano_ant,
					"periodo_mes": mes_ant,
					"pago_atrasado": 1,
					"recargo_aplicado": 0,
				},
				"name",
			)
			if cobranza_previa:
				recargo_por_atraso = float(
					frappe.db.get_single_value("Configuracion App", "monto_recargo_pago_atrasado") or 0
				)
				if recargo_por_atraso:
					frappe.logger().info(
						f"Recargo por atraso de {mes_ant}/{ano_ant}: ${recargo_por_atraso:,.0f} (cobranza previa {cobranza_previa})"
					)
					monto_a_cobrar += recargo_por_atraso
					frappe.db.set_value("Cobranza_Cliente", cobranza_previa, "recargo_aplicado", 1)

			abreviatura = cliente_doc.get('abreviatura_cliente') or cliente_doc.name[:3]
			id_cob = f"COB-{abreviatura}-{self.ano}-{str(self.mes).zfill(2)}"

			frappe.logger().info(f"Creando cobranza {id_cob} por ${monto_a_cobrar:,.0f}")

			cob = frappe.get_doc({
				"doctype": "Cobranza_Cliente",
				"id_cobranza": id_cob,
				"cliente": self.cliente,
				"declaracion_mensual": self.name,
				"periodo_mes": int(self.mes),
				"periodo_ano": int(self.ano),
				"monto_base": monto_contable,
				"numero_empleados": numero_empleados,
				"monto_rrhh": monto_rrhh,
				"subtotal": subtotal,
				"total_descuentos": total_descuentos,
				"monto_adicionales": monto_adicionales,
				"recargo_por_atraso": recargo_por_atraso,
				"monto_a_cobrar": monto_a_cobrar,
				"fecha_emision": fecha_emision,
				"fecha_vencimiento": fecha_vencimiento,
				"estado_cobranza": "Por Cobrar",
				"factura_generada": 0
			})

			for d in descuentos_aplicados:
				cob.append("descuentos_aplicados", {
					"doctype": "Detalle_Descuento_Cobranza",
					"descripcion": d["descripcion"],
					"tipo": d["tipo"],
					"valor": d["valor"],
					"monto_descuento": d["monto_descuento"]
				})

			cob.insert(ignore_permissions=True)
			self.cobranza_vinculada = cob.name

			frappe.logger().info(f"Cobranza {cob.name} registrada.")

		except Exception as e:
			frappe.log_error(str(e), "Error Cobranza Declaracion_Mensual")
			frappe.msgprint(f"❌ Error al crear cobranza: {str(e)}", indicator='red')


# ── Función independiente para el worker de background ───────────────────────

def enviar_push_declaracion(name):
	"""Ejecutado por frappe.enqueue — envía push al publicar una declaración."""
	try:
		doc = frappe.get_doc("Declaracion_Mensual", name)
		if not doc.publicado_portal or not doc.cliente:
			return

		from evoluciona_pyme_v2.evoluciona_pyme_v2.portal_api import enviar_push_a_cliente

		MESES = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
				 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
		try:
			mes_num = int(doc.mes)
			mes_nombre = MESES[mes_num] if 1 <= mes_num <= 12 else str(doc.mes)
		except Exception:
			mes_nombre = str(doc.mes)

		def _fmt(v):
			return "${:,.0f}".format(v).replace(",", ".")

		cliente   = doc.cliente
		decl_mes  = int(doc.mes or 1)
		decl_ano  = int(doc.ano or 0)
		decl_per  = decl_ano * 100 + decl_mes

		f29      = float(doc.total_f29_a_pagar or 0)
		previred = float(doc.total_previred_a_pagar or 0)

		# Honorarios del mes actual + mora de períodos anteriores sin pagar
		honorarios = 0.0
		mora       = 0.0
		cobranzas  = frappe.db.sql("""
			SELECT monto_a_cobrar, periodo_mes, periodo_ano
			FROM `tabCobranza_Cliente`
			WHERE cliente = %(c)s
			  AND estado_cobranza IN ('Vencido', 'Por Cobrar', 'Facturado')
		""", {"c": cliente}, as_dict=True)
		for cob in cobranzas:
			cob_per = int(cob.periodo_ano) * 100 + int(cob.periodo_mes)
			if cob_per == decl_per:
				honorarios += float(cob.monto_a_cobrar or 0)
			elif cob_per < decl_per:
				mora += float(cob.monto_a_cobrar or 0)

		# Postergación IVA que vence este mes
		posts = frappe.db.sql("""
			SELECT monto_postergado FROM `tabPostergacion_IVA`
			WHERE cliente = %(c)s
			  AND mes_f29_pagado = %(mes)s AND ano_f29_pagado = %(ano)s
		""", {"c": cliente, "mes": decl_mes, "ano": decl_ano}, as_dict=True)
		post_vencida = sum(float(p.monto_postergado or 0) for p in posts)

		total  = f29 + previred + honorarios + mora + post_vencida
		partes = []
		if f29 > 0:          partes.append("F29 {}".format(_fmt(f29)))
		if previred > 0:     partes.append("Prev {}".format(_fmt(previred)))
		if honorarios > 0:   partes.append("Hon {}".format(_fmt(honorarios)))
		if mora > 0:         partes.append("Mora {}".format(_fmt(mora)))
		if post_vencida > 0: partes.append("IVA ant. {}".format(_fmt(post_vencida)))

		cuerpo = (" · ".join(partes) + "  |  Total: {}".format(_fmt(total))) if partes else _fmt(total)

		enviar_push_a_cliente(
			cliente=cliente,
			titulo="Tu declaración de {} está lista 📋".format(mes_nombre),
			cuerpo=cuerpo,
			data={"tipo": "declaracion", "cliente": cliente,
				  "mes": str(doc.mes), "ano": str(doc.ano)},
		)
	except Exception as e:
		import traceback
		frappe.log_error(
			"enviar_push_declaracion name={}\n{}".format(name, traceback.format_exc()),
			"Portal Push Declaracion"
		)
