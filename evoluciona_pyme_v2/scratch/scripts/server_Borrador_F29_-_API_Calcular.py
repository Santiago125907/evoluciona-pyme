# SERVER SCRIPT API: Recalcular F29 desde Documentos Tributarios
# ================================================================
# Script Type: API
# API Method: recalcular_asistente_f29
# Allow Guest: NO
# ================================================================

# NOTA: En Server Scripts no es necesario 'import frappe', ya está disponible globalmente.

# Obtener parámetro
doc_name = frappe.form_dict.get('doc_name')

if not doc_name:
    frappe.response['message'] = {
        "status": "error",
        "message": "Falta el parámetro doc_name"
    }
else:
    try:
        # =====================================================
        # OBTENER DOCUMENTO
        # =====================================================
        doc = frappe.get_doc("Borrador_F29", doc_name)
        
        frappe.msgprint(f"""
        INICIANDO CÁLCULO F29
        Cliente: {doc.cliente}
        Periodo: {doc.mes}/{doc.ano}
        """)
        
        # =====================================================
        # OBTENER CONFIGURACIÓN
        # =====================================================
        config_f29 = frappe.db.sql("""
            SELECT 
                codigo_f29,
                fuente_doctype,
                fuente_campo_a_sumar,
                filtro_tipo,
                tabla_destino,
                descripcion
            FROM `tabConfiguracion_Codigo_F29`
            WHERE es_calculado = 1
            ORDER BY orden ASC
        """, as_dict=True)
        
        if not config_f29:
            frappe.response['message'] = {
                "status": "error",
                "message": "No se encontró configuración de códigos F29 calculados"
            }
        else:
            lineas_actualizadas = 0
            lineas_no_encontradas = []
            
            # =====================================================
            # PROCESAR CADA LÍNEA CALCULADA
            # =====================================================
            
            for config in config_f29:
                codigo = config.codigo_f29
                fuente = config.fuente_doctype
                campo = config.fuente_campo_a_sumar
                filtro = config.filtro_tipo
                tabla_destino = config.tabla_destino
                descripcion = config.descripcion
                
                # Saltar código 62 (PPM) - se procesa al final con lógica especial
                if str(codigo) == "62":
                    continue
                
                # Saltar si no tiene fuente
                if not fuente or not campo:
                    continue
                
                monto = 0
                
                # =====================================================
                # CALCULAR DESDE INGRESOS
                # =====================================================
                if fuente == "Libro_de_Ingresos_Cliente":
                    query = f"""
                        SELECT COALESCE(SUM(`{campo}`), 0) as total
                        FROM `tabLibro_de_Ingresos_Cliente`
                        WHERE cliente = %(cliente)s
                        AND ano_tributario = %(ano)s
                        AND mes_tributario = %(mes)s
                        AND docstatus IN (0, 1)
                    """
                    
                    params = {
                        "cliente": doc.cliente,
                        "ano": str(doc.ano),
                        "mes": str(doc.mes)
                    }
                    
                    if filtro:
                        query += " AND tipo_documento = %(filtro)s"
                        params["filtro"] = filtro
                    
                    result = frappe.db.sql(query, params, as_dict=True)
                    monto = result[0].total if result else 0
                
                # =====================================================
                # CALCULAR DESDE EGRESOS
                # =====================================================
                elif fuente == "Libro_de_Egresos_Cliente":
                    query = f"""
                        SELECT COALESCE(SUM(`{campo}`), 0) as total
                        FROM `tabLibro_de_Egresos_Cliente`
                        WHERE cliente = %(cliente)s
                        AND ano_tributario = %(ano)s
                        AND mes_tributario = %(mes)s
                        AND docstatus IN (0, 1)
                    """
                    
                    params = {
                        "cliente": doc.cliente,
                        "ano": str(doc.ano),
                        "mes": str(doc.mes)
                    }
                    
                    if filtro:
                        query += " AND tipo_egreso = %(filtro)s"
                        params["filtro"] = filtro
                    
                    result = frappe.db.sql(query, params, as_dict=True)
                    monto = result[0].total if result else 0
                
                # =====================================================
                # CALCULAR DESDE REMUNERACIONES
                # =====================================================
                elif fuente == "Registro_Remuneraciones":
                    query = f"""
                        SELECT COALESCE(SUM(`{campo}`), 0) as total
                        FROM `tabRegistro_Remuneraciones`
                        WHERE cliente = %(cliente)s
                        AND ano = %(ano)s
                        AND mes = %(mes)s
                        AND docstatus IN (0, 1)
                    """
                    
                    params = {
                        "cliente": doc.cliente,
                        "ano": str(doc.ano),
                        "mes": str(doc.mes)
                    }
                    
                    result = frappe.db.sql(query, params, as_dict=True)
                    monto = result[0].total if result else 0
                
                # =====================================================
                # ACTUALIZAR LÍNEA EN F29
                # =====================================================
                tabla = None
                if tabla_destino == "tabla_debitos":
                    tabla = doc.tabla_debitos
                elif tabla_destino == "tabla_creditos":
                    tabla = doc.tabla_creditos
                elif tabla_destino == "tabla_impuestos":
                    tabla = doc.tabla_impuestos
                
                if tabla:
                    linea_encontrada = False
                    for linea in tabla:
                        if str(linea.codigo_f29) == str(codigo):
                            linea.monto = monto
                            linea.tipo_origen = "Calculado"
                            lineas_actualizadas += 1
                            linea_encontrada = True
                            frappe.msgprint(f"✓ Código {codigo}: ${monto:,.0f}")
                            break
                    
                    if not linea_encontrada:
                        lineas_no_encontradas.append(f"Código {codigo} ({descripcion})")
            
            # =====================================================
            # CALCULAR PPM (Código 62) - MODIFICADO
            # =====================================================
            # Se suman Facturas, Notas debito, boletas y comprobantes
            # Se restan Notas de Crédito
            # =====================================================
            
            ventas_query = """
                SELECT COALESCE(SUM(
                    CASE 
                        WHEN tipo_documento = 'NOTA DE CRÉDITO ELECTRÓNICA' THEN -neto 
                        ELSE neto 
                    END
                ), 0) as total
                FROM `tabLibro_de_Ingresos_Cliente`
                WHERE cliente = %(cliente)s
                AND ano_tributario = %(ano)s
                AND mes_tributario = %(mes)s
                AND docstatus IN (0, 1)
                AND tipo_documento IN (
                    'FACTURA ELECTRÓNICA',
                    'NOTA DE CRÉDITO ELECTRÓNICA',
                    'NOTA DE DÉBITO ELECTRÓNICA',
                    'Total Oper. del mes Boleta Electr.(39)',
                    'Total mes Comprobantes Pago Electrónico(48)'
                )
            """
            
            ventas_result = frappe.db.sql(ventas_query, {
                "cliente": doc.cliente,
                "ano": str(doc.ano),
                "mes": str(doc.mes)
            }, as_dict=True)
            
            raw_total = ventas_result[0].total if ventas_result and ventas_result[0].total else 0
            
            # Aseguramos que la base imponible no sea negativa (si NC > Ventas, base es 0)
            ventas_totales = max(0, float(raw_total))
            
            # Obtener tasa PPM
            tasa_ppm = frappe.db.get_value("Ficha_Cliente", doc.cliente, "tasa_ppm") or 0
            tasa_ppm = float(tasa_ppm)
            
            ppm = ventas_totales * (tasa_ppm / 100)
            
            frappe.msgprint(f"PPM: Base Imponible ${ventas_totales:,.0f} * {tasa_ppm}% = ${ppm:,.0f}")
            
            # Actualizar PPM en tabla_impuestos
            if doc.tabla_impuestos:
                for linea in doc.tabla_impuestos:
                    if str(linea.codigo_f29) == "62":
                        linea.monto = ppm
                        linea.tipo_origen = "Calculado"
                        lineas_actualizadas += 1
                        frappe.msgprint(f"✓ PPM actualizado: ${ppm:,.0f}")
                        break
            
            # =====================================================
            # RECALCULAR SUBTOTALES
            # =====================================================
            CODIGO_POSTERGACION_IVA = '771'
            
            subtotal_debitos = 0
            subtotal_creditos = 0
            subtotal_postergacion = 0
            subtotal_impuestos = 0
            
            # Calcular débitos
            if doc.tabla_debitos:
                for linea in doc.tabla_debitos:
                    monto_linea = float(linea.monto or 0)
                    if linea.tipo_operacion_subtotal == 'Resta':
                        subtotal_debitos -= monto_linea
                    elif linea.tipo_operacion_subtotal != 'Informativo':
                        subtotal_debitos += monto_linea
            
            # Calcular créditos y postergación
            if doc.tabla_creditos:
                for linea in doc.tabla_creditos:
                    monto_linea = float(linea.monto or 0)
                    if str(linea.codigo_f29) == CODIGO_POSTERGACION_IVA:
                        subtotal_postergacion += monto_linea
                    else:
                        if linea.tipo_operacion_subtotal == 'Resta':
                            subtotal_creditos -= monto_linea
                        elif linea.tipo_operacion_subtotal != 'Informativo':
                            subtotal_creditos += monto_linea
            
            # Calcular otros impuestos
            if doc.tabla_impuestos:
                for linea in doc.tabla_impuestos:
                    monto_linea = float(linea.monto or 0)
                    if linea.tipo_operacion_subtotal == 'Resta':
                        subtotal_impuestos -= monto_linea
                    elif linea.tipo_operacion_subtotal != 'Informativo':
                        subtotal_impuestos += monto_linea
            
            # Calcular IVA determinado y remanente
            iva_resultante = subtotal_debitos - subtotal_creditos
            iva_determinado = max(0, iva_resultante) if iva_resultante > 0 else 0
            remanente = abs(iva_resultante) if iva_resultante < 0 else 0
            
            # Calcular total a pagar
            total_pagar = iva_determinado - subtotal_postergacion + subtotal_impuestos
            if total_pagar < 0:
                total_pagar = 0
            
            # Actualizar campos del documento
            doc.subtotal_debitos = subtotal_debitos
            doc.subtotal_creditos = subtotal_creditos
            doc.subtotal_postergacion_iva = subtotal_postergacion
            doc.subtotal_otros_impuestos = subtotal_impuestos
            doc.impuesto_determinado = iva_determinado
            doc.remanente_mes_siguiente = remanente
            doc.total_a_pagar_f29 = total_pagar
            
            # =====================================================
            # GUARDAR
            # =====================================================
            doc.save(ignore_permissions=True)
            frappe.db.commit()
            
            # =====================================================
            # RESPUESTA
            # =====================================================
            mensaje_final = f"""
✓ F29 calculado exitosamente
- {lineas_actualizadas} líneas actualizadas
- Total a pagar: ${total_pagar:,.0f}
            """
            
            if lineas_no_encontradas:
                mensaje_final += f"\n\n⚠ Códigos no encontrados:\n"
                for adv in lineas_no_encontradas[:5]:
                    mensaje_final += f"• {adv}\n"
            
            frappe.msgprint(mensaje_final)
            
            frappe.response['message'] = {
                "status": "ok",
                "message": mensaje_final,
                "lineas_actualizadas": lineas_actualizadas,
                "total_a_pagar": total_pagar
            }
        
    except Exception as e:
        error_msg = f"Error al calcular F29: {str(e)}"
        frappe.log_error(
            title=f"Error en recalcular_asistente_f29 - {doc_name}",
            message=f"{error_msg}\n{frappe.get_traceback()}"
        )
        
        frappe.response['message'] = {
            "status": "error",
            "message": error_msg
        }