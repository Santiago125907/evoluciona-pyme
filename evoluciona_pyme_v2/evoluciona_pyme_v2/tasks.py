import frappe
from frappe.utils import add_months, getdate, now_datetime, get_datetime


def _log(msg):
	try:
		frappe.logger().info(msg)
	except Exception:
		print(msg)


def _now_local():
	"""Datetime actual en la zona horaria configurada del site.

	now_datetime() ya devuelve la hora local del site (System Settings > Time Zone),
	no UTC — no hay que volver a convertirla o el horario queda corrido.
	"""
	return now_datetime()


def _cargar_cfg():
	try:
		return frappe.get_doc("Configuracion App")
	except Exception:
		return None


# ── CRON 1: Creación de tareas mensuales ────────────────────────────────────
def dispatcher_cron():
	"""
	hourly_long — Crea Declaracion_Mensual + Borrador_F29 para todos los clientes
	activos del mes anterior, según el día y hora configurados en Configuracion App.
	Se ejecuta como máximo una vez por mes calendario.
	"""
	cfg = _cargar_cfg()
	if not cfg or not cfg.habilitar_tareas_mensuales:
		return

	now        = _now_local()
	hora_cfg   = int((cfg.hora_ejecucion_tareas or "01:00").split(":")[0])
	dia_cfg    = int(cfg.dia_ejecucion_tareas or 1)

	if now.day != dia_cfg or now.hour != hora_cfg:
		return

	ultima = get_datetime(cfg.ultima_ejecucion_tareas) if cfg.ultima_ejecucion_tareas else None
	if ultima and ultima.month == now.month and ultima.year == now.year:
		return  # ya se ejecutó este mes

	try:
		crear_tareas_mensuales()
		cfg.ultima_ejecucion_tareas = now_datetime()
		cfg.save(ignore_permissions=True)
		frappe.db.commit()
	except Exception:
		frappe.log_error("dispatcher_cron", frappe.get_traceback())


# ── CRON 2: Descarga de libros contables ────────────────────────────────────
def dispatcher_libros():
	"""
	hourly — Descarga el RCV (compras y ventas) de todos los clientes activos
	directamente desde el SII vía Base API, una vez al mes el día y hora
	configurados en Configuracion App.
	"""
	cfg = _cargar_cfg()
	if not cfg or not cfg.habilitar_descarga_libros:
		return

	now      = _now_local()
	dia_cfg  = int(cfg.dia_descarga_libros or 5)
	hora_cfg = int((cfg.hora_descarga_libros or "08:00").split(":")[0])

	if now.day != dia_cfg or now.hour != hora_cfg:
		return

	ultima = get_datetime(cfg.ultima_ejecucion_libros) if cfg.ultima_ejecucion_libros else None
	if ultima and ultima.month == now.month and ultima.year == now.year:
		return  # ya se ejecutó este mes

	try:
		fecha_anterior = add_months(getdate(), -1)
		periodo = fecha_anterior.strftime("%Y-%m")
		ano  = fecha_anterior.year
		mes  = fecha_anterior.month

		from evoluciona_pyme_v2.evoluciona_pyme_v2 import rcv_api, bhe_api

		rcv_api.descargar_rcv_todos(periodo)

		for fila in (cfg.get("tabla_rcv_empresas") or []):
			if fila.descargar_honorarios:
				try:
					bhe_api.descargar_bhe_cliente(fila.empresa, ano, mes)
				except Exception as e:
					frappe.log_error(str(e), f"BHE masivo {fila.empresa}")
				frappe.db.commit()

		cfg.ultima_ejecucion_libros = now_datetime()
		cfg.save(ignore_permissions=True)
		frappe.db.commit()
	except Exception:
		frappe.log_error("dispatcher_libros", frappe.get_traceback())


def _disparar_webhook(nombre, url, payload):
	"""Envía un POST JSON a la URL indicada y registra el resultado."""
	import json
	try:
		frappe.make_post_request(
			url=url,
			data=json.dumps(payload),
			headers={"Content-Type": "application/json"}
		)
		_log(f"Webhook {nombre} enviado a {url}")
	except Exception as e:
		frappe.log_error(str(e), f"Error Webhook {nombre}")


# ── Creación de tareas mensuales ─────────────────────────────────────────────
def crear_tareas_mensuales():
	"""
	Crea Declaracion_Mensual + Borrador_F29 para todos los clientes activos
	del mes anterior, pre-rellena las líneas F29 y dispara el webhook de
	descarga masiva en n8n.
	"""
	fecha_anterior = add_months(getdate(), -1)
	año  = str(fecha_anterior.year)
	mes  = str(fecha_anterior.month)

	_log(f"Creando tareas mensuales para {mes}/{año}")

	try:
		codigos = frappe.get_all(
			"Configuracion_Codigo_F29",
			fields=["orden", "codigo_f29", "descripcion", "tabla_destino",
					"tipo_operacion_subtotal", "es_calculado"],
			order_by="orden asc"
		)
	except Exception as e:
		frappe.log_error(str(e), "Error carga Configuracion_Codigo_F29")
		raise

	if not codigos:
		frappe.log_error("Configuracion_Codigo_F29 está vacía.", "Tareas — Biblioteca Vacía")

	try:
		clientes = frappe.get_all(
			"Ficha_Cliente",
			filters={"estado_cliente": "Activo"},
			fields=["name", "abreviatura_cliente"],
			order_by="abreviatura_cliente asc"
		)
	except Exception as e:
		frappe.log_error(str(e), "Error consulta clientes activos")
		raise

	if not clientes:
		_log("No hay clientes activos. Proceso terminado.")
		return

	mapeo = {
		"tabla_debitos":   "Linea_F29_Debito",
		"tabla_creditos":  "Linea_F29_Credito",
		"tabla_impuestos": "Linea_F29_Impuesto",
	}

	creados = ya_existian = errores = 0
	errores_detalle = []

	for cliente in clientes:
		id_dec = f"DM-{cliente.abreviatura_cliente}-{año}-{mes}"
		id_f29 = f"F29-{cliente.abreviatura_cliente}-{año}-{mes}"

		if frappe.db.exists("Declaracion_Mensual", {"id_documento": id_dec}):
			ya_existian += 1
			continue

		try:
			doc_dec = frappe.get_doc({
				"doctype": "Declaracion_Mensual",
				"id_documento": id_dec,
				"cliente": cliente.name,
				"ano": año,
				"mes": mes,
			})
			doc_dec.insert(ignore_permissions=True)

			doc_f29 = frappe.get_doc({
				"doctype": "Borrador_F29",
				"id_documento": id_f29,
				"cliente": cliente.name,
				"ano": año,
				"mes": mes,
				"declaracion_mensual_vinculada": doc_dec.name,
			})
			doc_f29.insert(ignore_permissions=True)

			doc_dec.borrador_f29_vinculado = doc_f29.name
			doc_dec.save(ignore_permissions=True)

			for regla in codigos:
				if regla.tabla_destino in mapeo:
					doc_f29.append(regla.tabla_destino, {
						"orden":                   regla.orden,
						"codigo_f29":              regla.codigo_f29,
						"descripcion":             regla.descripcion,
						"tipo_operacion_subtotal": regla.tipo_operacion_subtotal or "Suma",
						"monto":                   0.0,
						"tipo_origen":             "Calculado" if regla.es_calculado else "Manual",
					})
			doc_f29.save(ignore_permissions=True)
			frappe.db.commit()
			creados += 1

		except Exception as e:
			errores += 1
			errores_detalle.append(f"{cliente.abreviatura_cliente}: {str(e)[:100]}")
			frappe.db.rollback()
			frappe.log_error(str(e), f"Error creando tarea {id_dec}")

	resumen = (
		f"Período: {mes}/{año} | Creados: {creados} | "
		f"Ya existían: {ya_existian} | Errores: {errores} | Total: {len(clientes)}"
	)
	_log(f"Tareas mensuales completadas — {resumen}")
	if errores_detalle:
		frappe.log_error("\n".join(errores_detalle), "Errores en creación de tareas mensuales")
