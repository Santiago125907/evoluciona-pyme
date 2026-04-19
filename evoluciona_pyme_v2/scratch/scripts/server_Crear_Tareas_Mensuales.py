# ================================================================
# Script para crear Tareas Mensuales - VERSIÓN CON WEBHOOK N8N
# ================================================================
# Se ejecuta el día 1 de cada mes
# Crea Declaraciones Mensuales y Borradores F29 pre-rellenados
# + Envía Webhook para descarga masiva de documentos
# ================================================================

def crear_tareas_mensuales():
    """Función principal para crear tareas mensuales"""
    
    # --- 1. Calcular el Período a Crear ---
    today = frappe.utils.nowdate()
    fecha_mes_anterior = frappe.utils.add_months(frappe.utils.getdate(today), -1)
    año_a_crear = str(fecha_mes_anterior.year)
    mes_a_crear = str(fecha_mes_anterior.month)
    
    frappe.log_error(
        title="Inicio Creación Tareas",
        message=f"📅 Iniciando creación de tareas para período: {mes_a_crear}/{año_a_crear}"
    )
    
    # --- 2. Cargar la Biblioteca de Códigos (UNA SOLA VEZ) ---
    try:
        biblioteca_de_codigos = frappe.get_all(
            "Configuracion_Codigo_F29",
            fields=[
                "orden",
                "codigo_f29",
                "descripcion",
                "tabla_destino",
                "tipo_operacion_subtotal",
                "es_calculado"
            ],
            order_by="orden asc"
        )
        
        if not biblioteca_de_codigos:
            mensaje_error = "⚠️ La 'Configuracion_Codigo_F29' está vacía. Los F29 se crearán sin líneas."
            frappe.log_error(mensaje_error, title="Biblioteca Vacía")
            biblioteca_de_codigos = []
            
    except Exception as e:
        frappe.log_error(f"❌ Error fatal: No se pudo cargar 'Configuracion_Codigo_F29'. {str(e)}", title="Error Carga Biblioteca")
        raise
    
    # --- 3. Buscar Clientes Activos ---
    try:
        clientes_activos = frappe.get_all(
            "Ficha_Cliente",
            filters={"estado_cliente": "Activo"},
            fields=["name", "abreviatura_cliente"],
            order_by="abreviatura_cliente asc"
        )
    except Exception as e:
        frappe.log_error(f"Error al buscar clientes: {str(e)}", title="Error Consulta Clientes")
        raise
    
    if not clientes_activos:
        return
    
    # --- 4. Contadores para Resumen ---
    creados = 0
    ya_existian = 0
    errores = 0
    clientes_con_error = []
    
    # --- 5. Mapeo de tablas (FIJO) ---
    mapeo_tablas = {
        "tabla_debitos": "Linea_F29_Debito",
        "tabla_creditos": "Linea_F29_Credito",
        "tabla_impuestos": "Linea_F29_Impuesto"
    }
    
    # --- 6. Bucle Principal de Creación ---
    for cliente in clientes_activos:
        id_declaracion = f"DM-{cliente.abreviatura_cliente}-{año_a_crear}-{mes_a_crear}"
        id_borrador = f"F29-{cliente.abreviatura_cliente}-{año_a_crear}-{mes_a_crear}"
        
        if frappe.db.exists("Declaracion_Mensual", {"id_documento": id_declaracion}):
            ya_existian += 1
            continue
        
        try:
            # Crear Declaracion_Mensual
            doc_declaracion = frappe.get_doc({
                "doctype": "Declaracion_Mensual",
                "id_documento": id_declaracion,
                "cliente": cliente.name,
                "ano": año_a_crear,
                "mes": mes_a_crear
            })
            doc_declaracion.insert(ignore_permissions=True)
            
            # Crear Borrador_F29
            doc_borrador = frappe.get_doc({
                "doctype": "Borrador_F29",
                "id_documento": id_borrador,
                "cliente": cliente.name,
                "ano": año_a_crear,
                "mes": mes_a_crear,
                "declaracion_mensual_vinculada": doc_declaracion.name
            })
            doc_borrador.insert(ignore_permissions=True)
            
            # Vincular Bidireccionalmente
            doc_declaracion.borrador_f29_vinculado = doc_borrador.name
            doc_declaracion.save(ignore_permissions=True)
            
            # Pre-rellenar con la Biblioteca
            if biblioteca_de_codigos:
                for regla in biblioteca_de_codigos:
                    if regla.tabla_destino in mapeo_tablas:
                        tipo_origen = "Calculado" if regla.es_calculado else "Manual"
                        doc_borrador.append(regla.tabla_destino, {
                            "orden": regla.orden,
                            "codigo_f29": regla.codigo_f29,
                            "descripcion": regla.descripcion,
                            "tipo_operacion_subtotal": regla.tipo_operacion_subtotal or "Suma",
                            "monto": 0.0,
                            "tipo_origen": tipo_origen
                        })
                doc_borrador.save(ignore_permissions=True)
            
            frappe.db.commit()
            creados += 1
            
        except Exception as e:
            errores += 1
            clientes_con_error.append(f"{cliente.abreviatura_cliente}: {str(e)[:80]}")
            frappe.db.rollback()
    
    # --- 7. NUEVO: Enviar Webhook de Descarga Masiva a n8n ---
    try:
        url_webhook = frappe.db.get_single_value('Configuracion_n8n', 'webhook_descarga_masiva')
        if url_webhook:
            import json
            payload = {
                "mes": mes_a_crear,
                "ano": año_a_crear,
                "accion": "descarga_masiva",
                "clientes_procesados": len(clientes_activos),
                "nuevas_tareas_creadas": creados
            }
            frappe.make_post_request(url=url_webhook, data=payload)
            frappe.log_error(f"Webhook Descarga Masiva enviado a: {url_webhook}", "INFO - Automatización")
    except Exception as e:
        frappe.log_error(f"Error enviando webhook descarga masiva: {str(e)}", "ERROR - Webhook n8n")

    # --- 8. Resumen Final ---
    mostrar_resumen(
        mes_a_crear,
        año_a_crear,
        creados,
        ya_existian,
        errores,
        len(clientes_activos),
        clientes_con_error
    )


def mostrar_resumen(mes, año, creados, ya_existian, errores, total, clientes_con_error):
    mensaje_resumen = (
        f"✅ Creación de tareas mensuales completada\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📅 Período: {mes}/{año}\n"
        f"📋 Creados nuevos: {creados}\n"
        f"⏭️ Ya existían: {ya_existian}\n"
        f"❌ Con errores: {errores}\n"
        f"👥 Total clientes: {total}"
    )
    
    frappe.log_error(title="📊 Resumen Creación Tareas Mensuales", message=mensaje_resumen)
    
    try:
        frappe.msgprint(
            mensaje_resumen,
            title="📊 Resumen Creación Tareas Mensuales",
            indicator="green" if errores == 0 else ("orange" if creados > 0 else "red")
        )
    except:
        pass


# ========== EJECUTAR LA FUNCIÓN ==========
crear_tareas_mensuales()
