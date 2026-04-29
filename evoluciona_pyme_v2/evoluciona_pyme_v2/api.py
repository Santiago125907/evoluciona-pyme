import json
import frappe

@frappe.whitelist(allow_guest=False)
def recalcular_asistente_f29(**kwargs):
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
                        params = {"cliente": doc.cliente, "ano": str(doc.ano), "mes": str(doc.mes)}
                        if filtro:
                            query += " AND tipo_egreso = %(filtro)s"
                            params["filtro"] = filtro
                        result = frappe.db.sql(query, params, as_dict=True)
                        monto = result[0].total if result else 0

                    # =====================================================
                    # CALCULAR DESDE LIBRO DE COMPRAS
                    # =====================================================
                    elif fuente == "Libro_de_Compras_Cliente":
                        query = f"""
                            SELECT COALESCE(SUM(`{campo}`), 0) as total
                            FROM `tabLibro_de_Compras_Cliente`
                            WHERE cliente = %(cliente)s
                            AND ano_tributario = %(ano)s
                            AND mes_tributario = %(mes)s
                            AND docstatus IN (0, 1)
                        """
                        params = {"cliente": doc.cliente, "ano": str(doc.ano), "mes": str(doc.mes)}
                        if filtro:
                            query += " AND tipo_documento = %(filtro)s"
                            params["filtro"] = filtro
                        result = frappe.db.sql(query, params, as_dict=True)
                        monto = result[0].total if result else 0

                    # =====================================================
                    # CALCULAR DESDE LIBRO DE HONORARIOS
                    # =====================================================
                    elif fuente == "Libro_de_Honorarios_Cliente":
                        query = f"""
                            SELECT COALESCE(SUM(`{campo}`), 0) as total
                            FROM `tabLibro_de_Honorarios_Cliente`
                            WHERE cliente = %(cliente)s
                            AND ano_tributario = %(ano)s
                            AND mes_tributario = %(mes)s
                            AND docstatus IN (0, 1)
                        """
                        params = {"cliente": doc.cliente, "ano": str(doc.ano), "mes": str(doc.mes)}
                        result = frappe.db.sql(query, params, as_dict=True)
                        monto = result[0].total if result else 0

                    # =====================================================
                    # CALCULAR DESDE LIBRO DE GASTOS
                    # =====================================================
                    elif fuente == "Libro_de_Gastos_Cliente":
                        query = f"""
                            SELECT COALESCE(SUM(`{campo}`), 0) as total
                            FROM `tabLibro_de_Gastos_Cliente`
                            WHERE cliente = %(cliente)s
                            AND ano_tributario = %(ano)s
                            AND mes_tributario = %(mes)s
                            AND docstatus IN (0, 1)
                        """
                        params = {"cliente": doc.cliente, "ano": str(doc.ano), "mes": str(doc.mes)}
                        if filtro:
                            query += " AND tipo_gasto = %(filtro)s"
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


@frappe.whitelist(allow_guest=False)
def test_apiobtener_datos(**kwargs):
    resultado = {
        'status': 'success',
        'mensaje': 'Búsqueda iniciada',
        'timestamp': frappe.utils.now()
    }
    
    codigo_producto = frappe.form_dict.get('codigo_producto')
    
    if codigo_producto:
        # Buscar el producto - NOTA: usa 'Producto_Simple' con guión bajo
        productos = frappe.get_all('Producto_Simple', 
            filters={'codigo': codigo_producto},
            fields=['nombre_producto', 'precio', 'stock', 'codigo']
        )
        
        if productos:
            resultado['producto_encontrado'] = productos[0]
            resultado['mensaje'] = 'Producto encontrado!'
        else:
            resultado['mensaje'] = 'Producto no encontrado'
    else:
        resultado['mensaje'] = 'No se proporcionó código de producto'
    
    frappe.response['message'] = resultado


@frappe.whitelist(allow_guest=False)
def test_calcular_suma(**kwargs):
    # ================================================================
    # SERVER SCRIPT API: Test Calcular Suma
    # ================================================================
    # Script Type: API
    # API Method: test_calcular_suma
    # Allow Guest: NO
    # ================================================================
    
    # 1. OBTENER PARÁMETROS
    doc_name = frappe.form_dict.get('doc_name')
    
    # 2. VALIDAR
    if not doc_name:
        frappe.response['message'] = {
            "status": "error",
            "message": "Falta doc_name"
        }
    else:
        try:
            # Mostrar mensaje de inicio
            frappe.msgprint("=== INICIO TEST ===")
            frappe.msgprint(f"Doc Name: {doc_name}")
            
            # 3. OBTENER EL DOCUMENTO
            doc = frappe.get_doc("Test Calculadora", doc_name)
            
            frappe.msgprint(f"Documento encontrado: {doc.name}")
            
            # 4. CALCULAR LA SUMA
            suma_total = 0
            
            if doc.tabla_numeros:
                frappe.msgprint(f"Filas encontradas: {len(doc.tabla_numeros)}")
                
                for fila in doc.tabla_numeros:
                    valor = float(fila.valor or 0)
                    suma_total += valor
                    frappe.msgprint(f"+ {fila.descripcion}: ${valor}")
            else:
                frappe.msgprint("No hay filas en la tabla")
            
            # 5. ACTUALIZAR EL RESULTADO
            doc.numero_resultado = suma_total
            frappe.msgprint(f"Suma total calculada: ${suma_total}")
            
            # 6. GUARDAR
            doc.save()
            frappe.db.commit()
            
            frappe.msgprint("=== FIN TEST ===", indicator='green')
            
            # 7. RETORNAR RESPUESTA
            frappe.response['message'] = {
                "status": "ok",
                "suma": suma_total
            }
            
        except Exception as e:
            frappe.log_error(
                title="Error en Test Calcular Suma",
                message=str(e)
            )
            frappe.msgprint(f"ERROR: {str(e)}", indicator='red')
            frappe.response['message'] = {
                "status": "error",
                "message": str(e)
            }


@frappe.whitelist(allow_guest=False)
def agregar_lineas_f29test_agregar_lineas(**kwargs):
    # Server Script API para agregar líneas a Borrador F29
    # Script Type: API
    # API Method: agregar_lineas_f29.test_agregar_lineas
    
    # Variable para almacenar el resultado
    resultado = None
    
    # Cargar biblioteca de códigos
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
        resultado = {
            "success": False,
            "message": "⚠️ No hay códigos configurados en Configuracion_Codigo_F29"
        }
    else:
        # Buscar un cliente activo
        cliente = frappe.get_all(
            "Ficha_Cliente",
            filters={"estado_cliente": "Activo"},
            fields=["name", "abreviatura_cliente"],
            limit_page_length=1
        )
        
        if not cliente:
            resultado = {
                "success": False,
                "message": "❌ No hay clientes activos en el sistema"
            }
        else:
            cliente = cliente[0]
            
            # Crear IDs únicos con string aleatorio (frappe.generate_hash ya está disponible)
            timestamp = frappe.generate_hash(length=6)
            id_declaracion = f"DM-TEST-{timestamp}"
            id_borrador = f"F29-TEST-{timestamp}"
            
            try:
                # Crear Declaración Mensual
                doc_declaracion = frappe.get_doc({
                    "doctype": "Declaracion_Mensual",
                    "id_documento": id_declaracion,
                    "cliente": cliente.name,
                    "ano": "2025",
                    "mes": "10"
                })
                doc_declaracion.insert(ignore_permissions=True)
                
                # Crear Borrador F29
                doc_borrador = frappe.get_doc({
                    "doctype": "Borrador_F29",
                    "id_documento": id_borrador,
                    "cliente": cliente.name,
                    "ano": "2025",
                    "mes": "10",
                    "declaracion_mensual_vinculada": doc_declaracion.name
                })
                doc_borrador.insert(ignore_permissions=True)
                
                # Vincular bidireccionalmente
                doc_declaracion.borrador_f29_vinculado = doc_borrador.name
                doc_declaracion.save(ignore_permissions=True)
                
                frappe.db.commit()
                
                # Mapeo de tablas
                mapeo_tablas = {
                    "tabla_debitos": "Linea_F29_Debito",
                    "tabla_creditos": "Linea_F29_Credito",
                    "tabla_impuestos": "Linea_F29_Impuesto"
                }
                
                # Recargar el borrador para asegurar que existe en BD
                doc_borrador.reload()
                
                lineas_agregadas = 0
                errores = []
                
                # Agregar líneas usando append()
                for regla in biblioteca_de_codigos:
                    
                    # Validaciones
                    if not regla.tabla_destino:
                        errores.append(f"Código {regla.codigo_f29}: Sin tabla_destino")
                        continue
                    
                    if regla.tabla_destino not in mapeo_tablas:
                        errores.append(f"Código {regla.codigo_f29}: Tabla '{regla.tabla_destino}' inválida")
                        continue
                    
                    try:
                        tipo_origen = "Calculado" if regla.es_calculado else "Manual"
                        
                        # Agregar línea
                        doc_borrador.append(regla.tabla_destino, {
                            "orden": regla.orden,
                            "codigo_f29": regla.codigo_f29,
                            "descripcion": regla.descripcion,
                            "tipo_operacion_subtotal": regla.tipo_operacion_subtotal or "",
                            "monto": 0.0,
                            "tipo_origen": tipo_origen
                        })
                        
                        lineas_agregadas += 1
                        
                    except Exception as e:
                        errores.append(f"Código {regla.codigo_f29}: {str(e)}")
                        continue
                
                # Guardar el documento con todas las líneas
                doc_borrador.save(ignore_permissions=True)
                frappe.db.commit()
                
                # Log del resultado
                frappe.log_error(
                    title=f"✅ Test Líneas F29 - {doc_borrador.name}",
                    message=f"Líneas agregadas: {lineas_agregadas}\nTotal códigos: {len(biblioteca_de_codigos)}\nErrores: {len(errores)}"
                )
                
                # Resultado exitoso
                resultado = {
                    "success": True,
                    "message": f"✅ Test completado! Se agregaron {lineas_agregadas} líneas",
                    "declaracion_creada": doc_declaracion.name,
                    "borrador_creado": doc_borrador.name,
                    "lineas_agregadas": lineas_agregadas,
                    "total_codigos": len(biblioteca_de_codigos),
                    "cliente_usado": cliente.abreviatura_cliente,
                    "errores": errores if errores else None
                }
                
            except Exception as e:
                frappe.db.rollback()
                error_msg = str(e)
                
                frappe.log_error(
                    title="❌ Error en test_agregar_lineas",
                    message=error_msg
                )
                
                resultado = {
                    "success": False,
                    "message": f"❌ Error: {error_msg}"
                }
    
    # Asignar resultado a la respuesta
    frappe.response['message'] = resultado


@frappe.whitelist(allow_guest=False)
def preparar_datos_pdf(**kwargs):
    # =============================================================
    # SERVER SCRIPT: Generar PDF n8n - VERSIÓN COMPLETA + DRIVE
    # Incluye: Hojas 1-5 + preparación para Google Drive
    # =============================================================
    
    try:
        # 1. OBTENER NOMBRE DE DECLARACIÓN
        declaracion_name = frappe.form_dict.get('declaracion_name')
        if not declaracion_name:
            frappe.throw("Error: Falta el nombre de la Declaración Mensual")
        
        # 2. CARGAR DOCUMENTOS
        decl = frappe.get_doc("Declaracion_Mensual", declaracion_name)
        
        if not decl.borrador_f29_vinculado:
            frappe.throw("Error: Falta vincular el Borrador F29")
        
        cliente_doc = frappe.get_doc("Ficha_Cliente", decl.cliente)
        f29_doc = frappe.get_doc("Borrador_F29", decl.borrador_f29_vinculado)
        
        mes_actual = int(decl.mes)
        ano_actual = int(decl.ano)
        periodo_int = (ano_actual * 100) + mes_actual
        
        # =========================================================
        # DATOS DEL CLIENTE PARA DRIVE
        # =========================================================
        cliente_id = str(decl.cliente)  # Name de Ficha_Cliente
        rut_cliente = str(cliente_doc.get("rut_cliente") or cliente_doc.get("rut") or "")
        razon_social = str(cliente_doc.get("razon_social") or cliente_doc.get("nombre_empresa") or "")
        
        # Obtener drive_folder_id si existe
        cliente_drive_folder_id = str(cliente_doc.get("drive_folder_id") or "")
        
        # Nombres de meses
        meses_nombres = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                         "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        mes_nombre = meses_nombres[mes_actual - 1]
        
        frappe.log_error("DATOS CLIENTE PARA DRIVE", 
            f"ID: {cliente_id}, RUT: {rut_cliente}, Folder: {cliente_drive_folder_id}")
        
        # 3. DATOS OFICINA
        datos_oficina = {
            "nombre_empresa": "Evoluciona",
            "rut_empresa": "77.946.744-9",
            "banco": "Banco Chile",
            "tipo_cuenta": "Cuenta Corriente",
            "numero_cuenta": "408324134",
            "nombre_titular": "",
            "email_contacto": "pagos@evolucionapyme.cl",
            "telefono": "",
            "sitio_web": ""
        }
        
        try:
            oficina = frappe.get_single("Configuracion_Oficina")
            if oficina:
                datos_oficina["nombre_empresa"] = str(oficina.get("nombre_empresa") or "Evoluciona")
                datos_oficina["rut_empresa"] = str(oficina.get("rut_empresa") or "77.946.744-9")
                datos_oficina["nombre_titular"] = str(oficina.get("nombre_titular") or "")
                datos_oficina["banco"] = str(oficina.get("banco") or "Banco Chile")
                datos_oficina["tipo_cuenta"] = str(oficina.get("tipo_cuenta") or "Cuenta Corriente")
                datos_oficina["numero_cuenta"] = str(oficina.get("numero_cuenta") or "408324134")
                datos_oficina["email_contacto"] = str(oficina.get("email_contacto") or "pagos@evolucionapyme.cl")
                datos_oficina["telefono"] = str(oficina.get("telefono") or "")
                datos_oficina["sitio_web"] = str(oficina.get("sitio_web") or "")
        except:
            pass
        
        # 4. LOGO
        logo_url = "http://erp.sjscuti.cl/files/logo%20pdf.png"
        
        # 5. FECHAS
        fecha_inicio_mes = frappe.utils.getdate(f"{ano_actual}-{mes_actual}-01")
        fecha_mes_siguiente = frappe.utils.add_months(fecha_inicio_mes, 1)
        
        venc_previred = ""
        if decl.get("fecha_vencimiento_previred"):
            venc_previred = frappe.utils.formatdate(decl.fecha_vencimiento_previred, "dd/MM/yyyy")
        else:
            vp = frappe.utils.getdate(f"{fecha_mes_siguiente.year}-{fecha_mes_siguiente.month}-13")
            if vp.weekday() == 5:
                vp = frappe.utils.add_days(vp, -1)
            elif vp.weekday() == 6:
                vp = frappe.utils.add_days(vp, -2)
            venc_previred = frappe.utils.formatdate(vp, "dd/MM/yyyy")
        
        venc_f29 = ""
        if decl.get("fecha_vencimiento_f29"):
            venc_f29 = frappe.utils.formatdate(decl.fecha_vencimiento_f29, "dd/MM/yyyy")
        else:
            vf = frappe.utils.getdate(f"{fecha_mes_siguiente.year}-{fecha_mes_siguiente.month}-20")
            if vf.weekday() == 5:
                vf = frappe.utils.add_days(vf, 2)
            elif vf.weekday() == 6:
                vf = frappe.utils.add_days(vf, 1)
            venc_f29 = frappe.utils.formatdate(vf, "dd/MM/yyyy")
        
        fecha_postergacion = frappe.utils.add_months(fecha_inicio_mes, 3)
        venc_postergacion = f"20/{fecha_postergacion.month:02d}/{fecha_postergacion.year}"
        
        fechas = {
            "f29": venc_f29,
            "previred": venc_previred,
            "honorarios": venc_f29,
            "postergacion": venc_postergacion
        }
        
        # 6. DEUDA
        deuda_anterior = 0.0
        try:
            cobranzas = frappe.get_all("Cobranza_Cliente",
                filters={
                    "cliente": decl.cliente,
                    "estado_cobranza": ["in", ["Vencido", "Por Cobrar", "Facturado"]]
                },
                fields=["monto_a_cobrar", "periodo_mes", "periodo_ano"])
            
            for cob in cobranzas:
                periodo_cob = (int(cob.periodo_ano) * 100) + int(cob.periodo_mes)
                if periodo_cob < periodo_int:
                    deuda_anterior += frappe.utils.flt(cob.monto_a_cobrar)
        except:
            pass
        
        # 7. HONORARIOS
        honorarios_mes = 0.0
        try:
            cob_actual = frappe.db.exists("Cobranza_Cliente", {
                "cliente": decl.cliente,
                "periodo_mes": decl.mes,
                "periodo_ano": decl.ano
            })
            
            if cob_actual:
                cob_doc = frappe.get_doc("Cobranza_Cliente", cob_actual)
                honorarios_mes = frappe.utils.flt(cob_doc.monto_a_cobrar)
            else:
                honorarios_mes = frappe.utils.flt(cliente_doc.get("valor_plan_mensual", 0))
        except:
            pass
        
        # 8. PREVIRED
        datos_previred = {
            "total_previred": 0.0
        }
        
        try:
            remu_name = frappe.db.exists("Registro_Remuneraciones", {
                "cliente": decl.cliente,
                "mes": decl.mes,
                "ano": decl.ano
            })
            
            if remu_name:
                remu = frappe.get_doc("Registro_Remuneraciones", remu_name)
                datos_previred["total_previred"] = float(frappe.utils.flt(remu.get("total_previred_a_pagar", 0)))
        except:
            pass
        
        # 9. POSTERGACIÓN VENCIDA
        postergacion_vencida = 0.0
        postergaciones_detalle = []
        
        try:
            fecha_limite = frappe.utils.getdate(decl.get("fecha_vencimiento_f29")) if decl.get("fecha_vencimiento_f29") else fecha_mes_siguiente.replace(day=20)
            
            posts_pendientes = frappe.get_all("Postergacion_IVA",
                filters={
                    "cliente": decl.cliente,
                    "estado": ["in", ["Vigente", "Por Vencer", "Vencida"]]
                },
                fields=["monto_postergado", "fecha_vencimiento", "mes_origen", "ano_origen"],
                order_by="fecha_vencimiento asc")
            
            for post in posts_pendientes:
                if post.get("fecha_vencimiento"):
                    fv = frappe.utils.getdate(post.fecha_vencimiento)
                    if fv <= fecha_limite:
                        postergacion_vencida += frappe.utils.flt(post.monto_postergado)
                        mes_or = post.get('mes_origen', '')
                        ano_or = post.get('ano_origen', '')
                        postergaciones_detalle.append({
                            "monto": float(frappe.utils.flt(post.monto_postergado)),
                            "periodo": f"{mes_or}/{ano_or}" if mes_or and ano_or else ""
                        })
            
        except Exception as e:
            frappe.log_error("ERROR en postergación", str(e))
        
        # 10. F29
        f29_total = frappe.utils.flt(f29_doc.get("total_a_pagar_f29", 0))
        iva_determinado = frappe.utils.flt(f29_doc.get("impuesto_determinado", 0))
        monto_postergado = frappe.utils.flt(decl.get("monto_iva_postergar", 0))
        
        posible_postergacion = iva_determinado if iva_determinado > 0 else 0
        opcion1_f29 = f29_total
        opcion2_f29 = f29_total - posible_postergacion
        
        if monto_postergado == 0:
            monto_postergado = posible_postergacion
        
        opcion1_total = deuda_anterior + honorarios_mes + datos_previred["total_previred"] + postergacion_vencida + opcion1_f29
        opcion2_total = deuda_anterior + honorarios_mes + datos_previred["total_previred"] + postergacion_vencida + opcion2_f29
        
        # 11. DATOS FINANCIEROS (HOJA 2)
        data_ingresos = [0] * 12
        data_gastos = [0] * 12
        
        try:
            sql_ventas = """
                SELECT mes_tributario, tipo_documento, SUM(neto) as total
                FROM `tabLibro_de_Ingresos_Cliente`
                WHERE cliente = %s AND ano_tributario = %s
                GROUP BY mes_tributario, tipo_documento
            """
            res_ventas = frappe.db.sql(sql_ventas, (decl.cliente, decl.ano), as_dict=True)
            
            for m in range(1, 13):
                # Sumar todo lo que NO sea Nota de Crédito
                ingresos_positivos = sum([frappe.utils.flt(r.total) for r in res_ventas 
                                         if int(r.mes_tributario) == m and 
                                         "CRÉDITO" not in str(r.tipo_documento).upper()])
                
                # Sumar solo las Notas de Crédito
                notas_credito = sum([frappe.utils.flt(r.total) for r in res_ventas 
                                    if int(r.mes_tributario) == m and 
                                    "CRÉDITO" in str(r.tipo_documento).upper()])
                
                # El ingreso real es: Positivos - Notas de Crédito
                total_mes = ingresos_positivos - notas_credito
                
                if m <= mes_actual:
                    data_ingresos[m-1] = int(total_mes)
        except Exception as e:
            frappe.log_error("Error calculando ingresos", str(e))
        
        try:
            sql_compras = """
                SELECT mes_tributario, tipo_egreso, SUM(gasto_gerencial) as total_gerencial
                FROM `tabLibro_de_Egresos_Cliente`
                WHERE cliente = %s AND ano_tributario = %s
                GROUP BY mes_tributario, tipo_egreso
            """
            res_compras = frappe.db.sql(sql_compras, (decl.cliente, decl.ano), as_dict=True)
            
            sql_rrhh = """
                SELECT mes, costo_total_empleador
                FROM `tabRegistro_Remuneraciones`
                WHERE cliente = %s AND ano = %s
            """
            res_rrhh = frappe.db.sql(sql_rrhh, (decl.cliente, decl.ano), as_dict=True)
            dict_rrhh = {int(r.mes): frappe.utils.flt(r.costo_total_empleador) for r in res_rrhh}
            
            for m in range(1, 13):
                # Gastos positivos (Facturas, Boletas, etc)
                gastos_positivos = sum([frappe.utils.flt(r.total_gerencial) for r in res_compras 
                                       if int(r.mes_tributario) == m and 
                                       "CRÉDITO" not in str(r.tipo_egreso).upper()])
                
                # Notas de Crédito (deben restar)
                notas_credito = sum([frappe.utils.flt(r.total_gerencial) for r in res_compras 
                                    if int(r.mes_tributario) == m and 
                                    "CRÉDITO" in str(r.tipo_egreso).upper()])
                
                # RRHH
                remuneraciones = dict_rrhh.get(m, 0)
                
                # El gasto real es: Positivos - Notas de crédito + RRHH
                total_gasto = (gastos_positivos - notas_credito) + remuneraciones
                
                if m <= mes_actual:
                    data_gastos[m-1] = int(total_gasto)
        except Exception as e:
            frappe.log_error("Error calculando gastos", str(e))
        
        data_utilidad = [ing - gas for ing, gas in zip(data_ingresos, data_gastos)]
        
        acumulado_ingresos = sum(data_ingresos[:mes_actual])
        acumulado_gastos = sum(data_gastos[:mes_actual])
        acumulado_utilidad = acumulado_ingresos - acumulado_gastos
        
        # 12. DATOS HOJA 3 - INGRESOS POR CATEGORÍA
        categorias_mensuales = {
            "facturas": [0] * 12,
            "boletas": [0] * 12,
            "comprobantes": [0] * 12,
            "notas_debito": [0] * 12
        }
        
        try:
            sql_categorias = """
                SELECT mes_tributario, tipo_documento, SUM(neto) as total
                FROM `tabLibro_de_Ingresos_Cliente`
                WHERE cliente = %s AND ano_tributario = %s
                GROUP BY mes_tributario, tipo_documento
            """
            res_categorias = frappe.db.sql(sql_categorias, (decl.cliente, decl.ano), as_dict=True)
            
            tipos_unicos = list(set([r.tipo_documento for r in res_categorias]))
            frappe.log_error("TIPOS DE DOCUMENTO EN INGRESOS", str(tipos_unicos))
            
            for m in range(1, 13):
                facturas = sum([frappe.utils.flt(r.total) for r in res_categorias
                               if int(r.mes_tributario) == m and
                               r.tipo_documento == "FACTURA ELECTRÓNICA"])
                
                boletas = sum([frappe.utils.flt(r.total) for r in res_categorias
                              if int(r.mes_tributario) == m and
                              ("Boleta" in r.tipo_documento or "BOLETA" in r.tipo_documento) and
                              "Comprobante" not in r.tipo_documento and
                              "COMPROBANTE" not in r.tipo_documento])
                
                comprobantes = sum([frappe.utils.flt(r.total) for r in res_categorias
                                   if int(r.mes_tributario) == m and
                                   ("Comprobante" in r.tipo_documento or "COMPROBANTE" in r.tipo_documento)])
                
                notas_debito = sum([frappe.utils.flt(r.total) for r in res_categorias
                                   if int(r.mes_tributario) == m and
                                   ("DÉBITO" in r.tipo_documento or "DEBITO" in r.tipo_documento)])
                
                notas_credito = sum([frappe.utils.flt(r.total) for r in res_categorias
                                    if int(r.mes_tributario) == m and
                                    ("CRÉDITO" in r.tipo_documento or "CREDITO" in r.tipo_documento)])
                
                if notas_credito > 0:
                    max_val = max(facturas, boletas, comprobantes, notas_debito)
                    if max_val == facturas:
                        facturas -= notas_credito
                    elif max_val == boletas:
                        boletas -= notas_credito
                    elif max_val == comprobantes:
                        comprobantes -= notas_credito
                    else:
                        notas_debito -= notas_credito
                
                if m <= mes_actual:
                    categorias_mensuales["facturas"][m-1] = int(facturas)
                    categorias_mensuales["boletas"][m-1] = int(boletas)
                    categorias_mensuales["comprobantes"][m-1] = int(comprobantes)
                    categorias_mensuales["notas_debito"][m-1] = int(notas_debito)
                    
                    if m == mes_actual:
                        frappe.log_error(f"DESGLOSE INGRESOS MES {m}", 
                            f"Facturas: {facturas}, Boletas: {boletas}, Comprobantes: {comprobantes}, ND: {notas_debito}")
                    
        except Exception as e:
            frappe.log_error("Error calculando categorías comerciales", str(e))
        
        acum_facturas = sum(categorias_mensuales["facturas"][:mes_actual])
        acum_boletas = sum(categorias_mensuales["boletas"][:mes_actual])
        acum_comprobantes = sum(categorias_mensuales["comprobantes"][:mes_actual])
        acum_nd = sum(categorias_mensuales["notas_debito"][:mes_actual])
        total_acum_cat = acum_facturas + acum_boletas + acum_comprobantes + acum_nd
        
        mix_facturas = round((acum_facturas / total_acum_cat * 100), 1) if total_acum_cat > 0 else 0
        mix_boletas = round((acum_boletas / total_acum_cat * 100), 1) if total_acum_cat > 0 else 0
        mix_comprobantes = round((acum_comprobantes / total_acum_cat * 100), 1) if total_acum_cat > 0 else 0
        mix_nd = round((acum_nd / total_acum_cat * 100), 1) if total_acum_cat > 0 else 0
        
        mes_ant_facturas = categorias_mensuales["facturas"][mes_actual-2] if mes_actual > 1 else 0
        mes_ant_boletas = categorias_mensuales["boletas"][mes_actual-2] if mes_actual > 1 else 0
        mes_ant_comprobantes = categorias_mensuales["comprobantes"][mes_actual-2] if mes_actual > 1 else 0
        mes_ant_nd = categorias_mensuales["notas_debito"][mes_actual-2] if mes_actual > 1 else 0
        
        var_facturas = round(((categorias_mensuales["facturas"][mes_actual-1] - mes_ant_facturas) / mes_ant_facturas * 100), 1) if mes_ant_facturas > 0 else 0
        var_boletas = round(((categorias_mensuales["boletas"][mes_actual-1] - mes_ant_boletas) / mes_ant_boletas * 100), 1) if mes_ant_boletas > 0 else 0
        var_comprobantes = round(((categorias_mensuales["comprobantes"][mes_actual-1] - mes_ant_comprobantes) / mes_ant_comprobantes * 100), 1) if mes_ant_comprobantes > 0 else 0
        var_nd = round(((categorias_mensuales["notas_debito"][mes_actual-1] - mes_ant_nd) / mes_ant_nd * 100), 1) if mes_ant_nd > 0 else 0
        
        total_mes_anterior = mes_ant_facturas + mes_ant_boletas + mes_ant_comprobantes + mes_ant_nd
        total_mes_actual_cat = categorias_mensuales["facturas"][mes_actual-1] + categorias_mensuales["boletas"][mes_actual-1] + categorias_mensuales["comprobantes"][mes_actual-1] + categorias_mensuales["notas_debito"][mes_actual-1]
        var_total = round(((total_mes_actual_cat - total_mes_anterior) / total_mes_anterior * 100), 1) if total_mes_anterior > 0 else 0
        
        # 13. DATOS HOJA 4 - GASTOS POR CATEGORÍA
        gastos_mensuales = {
            "facturas": [0] * 12,
            "honorarios": [0] * 12,
            "otros": [0] * 12,
            "remuneraciones": [0] * 12
        }
        
        try:
            sql_gastos = """
                SELECT mes_tributario, tipo_egreso, SUM(gasto_gerencial) as total
                FROM `tabLibro_de_Egresos_Cliente`
                WHERE cliente = %s AND ano_tributario = %s
                GROUP BY mes_tributario, tipo_egreso
            """
            res_gastos = frappe.db.sql(sql_gastos, (decl.cliente, decl.ano), as_dict=True)
            
            tipos_egreso_unicos = list(set([r.tipo_egreso for r in res_gastos]))
            frappe.log_error("TIPOS DE EGRESO ENCONTRADOS", str(tipos_egreso_unicos))
            
            for m in range(1, 13):
                facturas = sum([frappe.utils.flt(r.total) for r in res_gastos
                               if int(r.mes_tributario) == m and
                               r.tipo_egreso in ["FACTURA ELECTRÓNICA", 
                                                "FACTURA NO AFECTA O EXENTA ELECTRÓNICA",
                                                "NOTA DE DÉBITO"]])
                
                notas_credito = sum([frappe.utils.flt(r.total) for r in res_gastos
                                    if int(r.mes_tributario) == m and
                                    r.tipo_egreso == "NOTA DE CRÉDITO ELECTRÓNICA"])
                
                facturas -= notas_credito
                
                honorarios = sum([frappe.utils.flt(r.total) for r in res_gastos
                                 if int(r.mes_tributario) == m and
                                 r.tipo_egreso == "Boleta de Honorarios"])
                
                otros = sum([frappe.utils.flt(r.total) for r in res_gastos
                            if int(r.mes_tributario) == m and
                            r.tipo_egreso == "Otros gastos"])
                
                remuneraciones = dict_rrhh.get(m, 0)
                
                if m <= mes_actual:
                    gastos_mensuales["facturas"][m-1] = int(facturas)
                    gastos_mensuales["honorarios"][m-1] = int(honorarios)
                    gastos_mensuales["otros"][m-1] = int(otros)
                    gastos_mensuales["remuneraciones"][m-1] = int(remuneraciones)
                    
                    if m == mes_actual:
                        frappe.log_error(f"DESGLOSE GASTOS MES {m}", 
                            f"Facturas: {facturas}, Honorarios: {honorarios}, Otros: {otros}, RRHH: {remuneraciones}")
            
        except Exception as e:
            frappe.log_error("Error calculando gastos por categoría", str(e))
        
        acum_fact_gasto = sum(gastos_mensuales["facturas"][:mes_actual])
        acum_honor = sum(gastos_mensuales["honorarios"][:mes_actual])
        acum_otros = sum(gastos_mensuales["otros"][:mes_actual])
        acum_rrhh = sum(gastos_mensuales["remuneraciones"][:mes_actual])
        total_acum_gastos = acum_fact_gasto + acum_honor + acum_otros + acum_rrhh
        
        mix_fact_gasto = round((acum_fact_gasto / total_acum_gastos * 100), 1) if total_acum_gastos > 0 else 0
        mix_honor = round((acum_honor / total_acum_gastos * 100), 1) if total_acum_gastos > 0 else 0
        mix_otros = round((acum_otros / total_acum_gastos * 100), 1) if total_acum_gastos > 0 else 0
        mix_rrhh = round((acum_rrhh / total_acum_gastos * 100), 1) if total_acum_gastos > 0 else 0
        
        mes_ant_fact = gastos_mensuales["facturas"][mes_actual-2] if mes_actual > 1 else 0
        mes_ant_honor = gastos_mensuales["honorarios"][mes_actual-2] if mes_actual > 1 else 0
        mes_ant_otros = gastos_mensuales["otros"][mes_actual-2] if mes_actual > 1 else 0
        mes_ant_rrhh = gastos_mensuales["remuneraciones"][mes_actual-2] if mes_actual > 1 else 0
        
        var_fact = round(((gastos_mensuales["facturas"][mes_actual-1] - mes_ant_fact) / mes_ant_fact * 100), 1) if mes_ant_fact > 0 else 0
        var_honor = round(((gastos_mensuales["honorarios"][mes_actual-1] - mes_ant_honor) / mes_ant_honor * 100), 1) if mes_ant_honor > 0 else 0
        var_otros = round(((gastos_mensuales["otros"][mes_actual-1] - mes_ant_otros) / mes_ant_otros * 100), 1) if mes_ant_otros > 0 else 0
        var_rrhh = round(((gastos_mensuales["remuneraciones"][mes_actual-1] - mes_ant_rrhh) / mes_ant_rrhh * 100), 1) if mes_ant_rrhh > 0 else 0
        
        total_mes_ant_gastos = mes_ant_fact + mes_ant_honor + mes_ant_otros + mes_ant_rrhh
        total_mes_act_gastos = gastos_mensuales["facturas"][mes_actual-1] + gastos_mensuales["honorarios"][mes_actual-1] + gastos_mensuales["otros"][mes_actual-1] + gastos_mensuales["remuneraciones"][mes_actual-1]
        var_total_gastos = round(((total_mes_act_gastos - total_mes_ant_gastos) / total_mes_ant_gastos * 100), 1) if total_mes_ant_gastos > 0 else 0
        
        # 14. DATOS HOJA 5 - DETALLE TRIBUTARIO Y PREVISIONAL
        iva_debito = float(frappe.utils.flt(f29_doc.get("subtotal_debitos", 0)))
        iva_credito = float(frappe.utils.flt(f29_doc.get("subtotal_creditos", 0)))
        iva_determinado = float(frappe.utils.flt(f29_doc.get("impuesto_determinado", 0)))
        subtotal_otros_impuestos = float(frappe.utils.flt(f29_doc.get("subtotal_otros_impuestos", 0)))
        total_f29 = float(frappe.utils.flt(f29_doc.get("total_a_pagar_f29", 0)))
        
        ppm = 0.0
        
        try:
            if f29_doc.get("tabla_impuestos"):
                for linea in f29_doc.tabla_impuestos:
                    codigo = str(linea.get("codigo_f29", ""))
                    monto = float(frappe.utils.flt(linea.get("monto", 0)))
                    
                    if codigo == "62":
                        ppm = monto
                        break
                
        except Exception as e:
            frappe.log_error("Error extrayendo PPM F29", str(e))
        
        # Calcular otros_impuestos restando el PPM
        otros_impuestos = subtotal_otros_impuestos - ppm
        
        haberes_imponibles = 0
        haberes_no_imponibles = 0
        cotizacion_afp = 0
        cotizacion_salud = 0
        seguro_cesantia = 0
        sis_mutual = 0
        total_previred = 0
        impuesto_unico = 0
        prestamo_solidario = 0
        
        try:
            remu_name = frappe.db.exists("Registro_Remuneraciones", {
                "cliente": decl.cliente,
                "mes": decl.mes,
                "ano": decl.ano
            })
            
            if remu_name:
                remu = frappe.get_doc("Registro_Remuneraciones", remu_name)
                haberes_imponibles = float(frappe.utils.flt(remu.get("total_haberes_imponibles", 0)))
                haberes_no_imponibles = float(frappe.utils.flt(remu.get("total_haberes_no_imponibles", 0)))
                cotizacion_afp = float(frappe.utils.flt(remu.get("total_afp", 0)))
                cotizacion_salud = float(frappe.utils.flt(remu.get("total_salud", 0)))
                seguro_cesantia = float(frappe.utils.flt(remu.get("total_seguro_cesantia", 0)))
                sis_mutual = float(frappe.utils.flt(remu.get("total_sis_mutual", 0)))
                total_previred = float(frappe.utils.flt(remu.get("total_previred_a_pagar", 0)))
                impuesto_unico = float(frappe.utils.flt(remu.get("impuesto_unico", 0)))
                prestamo_solidario = float(frappe.utils.flt(remu.get("retencion_prestamo_solidario", 0)))
                
        except Exception as e:
            frappe.log_error("Error extrayendo datos previred", str(e))
        
        # =========================================================
        # 15. CONSTRUIR PAYLOAD CON DATOS DRIVE
        # =========================================================
        payload = {
            # DATOS CLIENTE PARA DRIVE (NUEVOS)
            "cliente_id": cliente_id,
            "rut_cliente": rut_cliente,
            "razon_social": razon_social,
            "cliente_drive_folder_id": cliente_drive_folder_id if cliente_drive_folder_id else None,
            "mes_nombre": mes_nombre,
            
            # DATOS EXISTENTES
            "declaracion_id": str(decl.name),
            "cliente": razon_social,
            "periodo": f"{decl.mes}/{decl.ano}",
            "mes": int(decl.mes),
            "ano": int(decl.ano),
            "logo_url": str(logo_url),
            "oficina": datos_oficina,
            "fechas": fechas,
            "deuda_anterior": float(deuda_anterior),
            "honorarios": float(honorarios_mes),
            "previred": float(datos_previred["total_previred"]),
            "postergacion_vencida": float(postergacion_vencida),
            "postergaciones_detalle": postergaciones_detalle,
            "f29_full": float(opcion1_f29),
            "f29_rebajado": float(opcion2_f29),
            "monto_postergado": float(monto_postergado),
            "iva_determinado": float(iva_determinado),
            "op1_total": float(opcion1_total),
            "op2_total": float(opcion2_total),
            "tbl_ingresos": data_ingresos[:mes_actual],
            "tbl_gastos": data_gastos[:mes_actual],
            "tbl_utilidad": data_utilidad[:mes_actual],
            "acum_ing": float(acumulado_ingresos),
            "acum_gas": float(acumulado_gastos),
            "acum_utilidad": float(acumulado_utilidad),
            "analisis_ia": str(decl.get("insights_generados", "") or ""),
            
            "hoja3_categorias_mensuales": {
                "facturas": categorias_mensuales["facturas"][:mes_actual],
                "boletas": categorias_mensuales["boletas"][:mes_actual],
                "comprobantes": categorias_mensuales["comprobantes"][:mes_actual],
                "notas_debito": categorias_mensuales["notas_debito"][:mes_actual]
            },
            "hoja3_mes_actual": {
                "facturas": categorias_mensuales["facturas"][mes_actual-1] if mes_actual > 0 else 0,
                "boletas": categorias_mensuales["boletas"][mes_actual-1] if mes_actual > 0 else 0,
                "comprobantes": categorias_mensuales["comprobantes"][mes_actual-1] if mes_actual > 0 else 0,
                "notas_debito": categorias_mensuales["notas_debito"][mes_actual-1] if mes_actual > 0 else 0,
                "total": total_mes_actual_cat
            },
            "hoja3_acumulados": {
                "facturas": float(acum_facturas),
                "boletas": float(acum_boletas),
                "comprobantes": float(acum_comprobantes),
                "notas_debito": float(acum_nd),
                "total": float(total_acum_cat)
            },
            "hoja3_mix": {
                "facturas": float(mix_facturas),
                "boletas": float(mix_boletas),
                "comprobantes": float(mix_comprobantes),
                "notas_debito": float(mix_nd)
            },
            "hoja3_variaciones": {
                "facturas": float(var_facturas),
                "boletas": float(var_boletas),
                "comprobantes": float(var_comprobantes),
                "notas_debito": float(var_nd),
                "total": float(var_total)
            },
            
            "hoja4_gastos_mensuales": {
                "facturas": gastos_mensuales["facturas"][:mes_actual],
                "honorarios": gastos_mensuales["honorarios"][:mes_actual],
                "otros": gastos_mensuales["otros"][:mes_actual],
                "remuneraciones": gastos_mensuales["remuneraciones"][:mes_actual]
            },
            "hoja4_mes_actual": {
                "facturas": gastos_mensuales["facturas"][mes_actual-1] if mes_actual > 0 else 0,
                "honorarios": gastos_mensuales["honorarios"][mes_actual-1] if mes_actual > 0 else 0,
                "otros": gastos_mensuales["otros"][mes_actual-1] if mes_actual > 0 else 0,
                "remuneraciones": gastos_mensuales["remuneraciones"][mes_actual-1] if mes_actual > 0 else 0,
                "total": total_mes_act_gastos
            },
            "hoja4_acumulados": {
                "facturas": float(acum_fact_gasto),
                "honorarios": float(acum_honor),
                "otros": float(acum_otros),
                "remuneraciones": float(acum_rrhh),
                "total": float(total_acum_gastos)
            },
            "hoja4_mix": {
                "facturas": float(mix_fact_gasto),
                "honorarios": float(mix_honor),
                "otros": float(mix_otros),
                "remuneraciones": float(mix_rrhh)
            },
            "hoja4_variaciones": {
                "facturas": float(var_fact),
                "honorarios": float(var_honor),
                "otros": float(var_otros),
                "remuneraciones": float(var_rrhh),
                "total": float(var_total_gastos)
            },
            
            "hoja5_f29_detalle": {
                "iva_debito": iva_debito,
                "iva_credito": iva_credito,
                "iva_determinado": iva_determinado,
                "ppm": ppm,
                "otros_impuestos": otros_impuestos,
                "total_f29": total_f29
            },
            "hoja5_previred_detalle": {
                "haberes_imponibles": haberes_imponibles,
                "haberes_no_imponibles": haberes_no_imponibles,
                "cotizacion_afp": cotizacion_afp,
                "cotizacion_salud": cotizacion_salud,
                "seguro_cesantia": seguro_cesantia,
                "sis_mutual": sis_mutual,
                "impuesto_unico": impuesto_unico,
                "prestamo_solidario": prestamo_solidario,
                "total_previred": total_previred
            }
        }
        
        # 16. GENERAR PDF NATIVO CON GOTENBERG
        from evoluciona_pyme_v2.evoluciona_pyme_v2.pdf import generar_html, convertir_a_pdf

        config = frappe.get_single('Configuracion App')
        html = generar_html(payload, config)
        pdf_bytes = convertir_a_pdf(html)

        meses_nombres = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
                         "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]
        mes_nombre = meses_nombres[mes_actual - 1]
        abrev = cliente_doc.abreviatura_cliente or decl.cliente
        nombre_archivo = 'Declaracion_{}_{}_{}.pdf'.format(abrev, mes_nombre, ano_actual)

        # Guardar PDF como archivo adjunto en Frappe
        file_doc = frappe.get_doc({
            "doctype": "File",
            "file_name": nombre_archivo,
            "attached_to_doctype": "Declaracion_Mensual",
            "attached_to_name": declaracion_name,
            "content": pdf_bytes,
            "decode": False,
            "is_private": 0
        })
        file_doc.save(ignore_permissions=True)
        pdf_url = file_doc.file_url

        decl.pdf_link_cliente = pdf_url
        decl.pdf_generado_flag = 1
        decl.fecha_pdf_generado = frappe.utils.now_datetime()
        decl.save(ignore_permissions=True)
        frappe.db.commit()

        frappe.response['message'] = {
            "status": "success",
            "message": "PDF generado correctamente",
            "pdf_url": pdf_url
        }

    except Exception as e:
        frappe.log_error("Error generando PDF", str(e))
        frappe.response['message'] = {
            "status": "error",
            "message": f"Error: {str(e)}"
        }


def preparar_datos_pdf_payload(declaracion_name):
    """Extrae el payload de datos para generar el PDF. Reutilizable desde pdf.py."""
    import frappe as _frappe
    _frappe.form_dict['declaracion_name'] = declaracion_name
    # Llama la función completa pero sólo retorna el payload
    # Esta función es un alias liviano — la lógica real está en preparar_datos_pdf
    # Se usa internamente desde pdf.generar_y_subir_pdf
    raise NotImplementedError("Usa preparar_datos_pdf directamente")


@frappe.whitelist(allow_guest=False)
def enviar_pdf_cliente(**kwargs):
    declaracion_name = frappe.form_dict.get('declaracion_name')
    
    if not declaracion_name:
        frappe.response['message'] = {
            "status": "error",
            "message": "Falta parámetro: declaracion_name"
        }
    else:
        try:
            # 1. Obtener Declaración
            decl = frappe.get_doc("Declaracion_Mensual", declaracion_name)
            
            # Validar que exista PDF
            if not decl.pdf_link_cliente:
                frappe.response['message'] = {
                    "status": "error",
                    "message": "No hay PDF generado. Genere el PDF primero."
                }
            else:
                # 2. Obtener datos del Cliente
                cliente = frappe.get_doc("Ficha_Cliente", decl.cliente)
                
                # Validar contacto
                if not cliente.email_contacto:
                    frappe.response['message'] = {
                        "status": "error",
                        "message": "El cliente no tiene email configurado"
                    }
                else:
                    # 3. Preparar payload para n8n
                    periodo = "{}/{}".format(decl.mes_declaracion, decl.ano_declaracion)
                    
                    payload = {
                        "declaracion_id": decl.name,
                        "cliente_rut": cliente.rut_cliente,
                        "cliente_nombre": cliente.razon_social,
                        "email_contacto": cliente.email_contacto,
                        "whatsapp_contacto": cliente.whatsapp_contacto or "",
                        "pdf_url_drive": decl.pdf_link_cliente,
                        "periodo": periodo,
                        "total_pagar_f29": float(decl.total_a_pagar_f29 or 0),
                        "total_pagar_previred": float(decl.total_previred or 0),
                        "tipo_envio": "declaracion_mensual"
                    }
                    
                    payload_json = json.dumps(payload)
                    
                    # 4. Llamar webhook n8n de ENVÍO
                    N8N_ENVIO_URL = frappe.db.get_single_value('Configuracion App', 'webhook_envio_declaracion')
                    if not N8N_ENVIO_URL:
                        frappe.throw("URL del webhook 'Envío Declaración' no configurada en Configuracion App")
                    
                    response = frappe.make_post_request(
                        url=N8N_ENVIO_URL,
                        data=payload_json,
                        headers={"Content-Type": "application/json"}
                    )
                    
                    frappe.log_error("Respuesta n8n envío", str(response))
                    
                    # 5. Actualizar documento
                    if response and isinstance(response, dict) and response.get("status") == "ok":
                        decl.estado = "Enviado"
                        decl.fecha_ultimo_envio = frappe.utils.now_datetime()
                        
                        # Guardar detalles del envío
                        if response.get("email_enviado"):
                            decl.fecha_ultimo_email = frappe.utils.now_datetime()
                        
                        if response.get("whatsapp_enviado"):
                            decl.fecha_ultimo_whatsapp = frappe.utils.now_datetime()
                        
                        decl.save(ignore_permissions=True)
                        frappe.db.commit()
                        
                        frappe.response['message'] = {
                            "status": "success",
                            "message": "Declaración enviada exitosamente",
                            "email_enviado": response.get("email_enviado", False),
                            "whatsapp_enviado": response.get("whatsapp_enviado", False)
                        }
                    else:
                        frappe.response['message'] = {
                            "status": "error",
                            "message": "Error al comunicar con servicio de envío",
                            "response": str(response)
                        }
                        
        except Exception as e:
            frappe.log_error("Error enviando PDF", str(e))
            frappe.response['message'] = {
                "status": "error",
                "message": "Error: {}".format(str(e))
            }


# ── Importador CSV SII — Libro de Compras ───────────────────────────────────

# Mapa de códigos de tipo de documento SII → opciones del DocType
TIPO_DOC_SII = {
    "33": "FACTURA ELECTRÓNICA",
    "34": "FACTURA NO ELECTRÓNICA",
    "46": "FACTURA DE COMPRA ELECTRÓNICA",
    "43": "LIQUIDACIÓN FACTURA",
    "56": "NOTA DE DÉBITO ELECTRÓNICA",
    "61": "NOTA DE CRÉDITO ELECTRÓNICA",
}

def _parse_int(val):
    try:
        return int(str(val).strip().replace(".", "").replace(",", "") or 0)
    except Exception:
        return 0

def _parse_fecha(val):
    # Fecha Docto viene como DD/MM/YYYY, Fecha Recepcion como DD/MM/YYYY HH:MM:SS
    try:
        return frappe.utils.datetime.datetime.strptime(val.strip()[:10], "%d/%m/%Y").date()
    except Exception:
        return None


def _resolver_periodo(doc_name=None, cliente=None, mes=None, ano=None):
    """Returns (cliente, mes_str, ano_str) from either a Borrador_F29 or direct params."""
    if doc_name:
        f29 = frappe.get_doc("Borrador_F29", doc_name)
        return f29.cliente, str(f29.mes), str(f29.ano)
    if cliente and mes and ano:
        return str(cliente), str(mes), str(ano)
    frappe.throw("Se requiere doc_name o cliente+mes+ano.")


@frappe.whitelist(allow_guest=False)
def importar_libro_compras_csv(**kwargs):
    """
    Importa el CSV de Libro de Compras descargado del SII al DocType
    Libro_de_Compras_Cliente, eliminando primero los registros existentes
    del cliente/período.

    Args:
        doc_name  : name del Borrador_F29 (entrega cliente, mes, año)
        file_url  : URL del archivo subido (frappe file)
    """
    import csv, io

    doc_name  = frappe.form_dict.get("doc_name")
    file_url  = frappe.form_dict.get("file_url")
    cliente_p = frappe.form_dict.get("cliente")
    mes_p     = frappe.form_dict.get("mes")
    ano_p     = frappe.form_dict.get("ano")

    if not file_url:
        frappe.response["message"] = {"status": "error", "message": "Faltan parámetros."}
        return

    # 1. Resolver cliente/mes/año
    try:
        cliente, mes, ano = _resolver_periodo(doc_name=doc_name, cliente=cliente_p, mes=mes_p, ano=ano_p)
    except Exception as e:
        frappe.response["message"] = {"status": "error", "message": str(e)}
        return

    # 2. Leer configuración IVA del cliente
    usa_iva = frappe.db.get_value("Ficha_Cliente", cliente, "usa_iva_credito")
    usa_iva = int(usa_iva or 1)

    # 3. Leer archivo
    try:
        file_doc  = frappe.get_doc("File", {"file_url": file_url})
        file_path = file_doc.get_full_path()
        with open(file_path, encoding="utf-8-sig") as f:
            contenido = f.read()
    except Exception as e:
        frappe.response["message"] = {"status": "error", "message": f"Error leyendo archivo: {e}"}
        return

    # 4. Eliminar registros existentes del período
    existentes = frappe.get_all(
        "Libro_de_Compras_Cliente",
        filters={"cliente": cliente, "mes_tributario": mes, "ano_tributario": ano},
        fields=["name"]
    )
    for r in existentes:
        frappe.delete_doc("Libro_de_Compras_Cliente", r.name, ignore_permissions=True, force=True)
    frappe.db.commit()

    # 5. Parsear CSV
    reader    = csv.DictReader(io.StringIO(contenido), delimiter=";")
    insertados = 0
    errores    = []

    for i, row in enumerate(reader, start=1):
        try:
            tipo_codigo  = str(row.get("Tipo Doc", "")).strip()
            tipo_doc     = TIPO_DOC_SII.get(tipo_codigo, "OTRO")
            rut          = str(row.get("RUT Proveedor", "")).strip()
            razon        = str(row.get("Razon Social", "")).strip()
            folio        = str(row.get("Folio", "")).strip()
            fecha        = _parse_fecha(row.get("Fecha Docto", ""))
            neto         = _parse_int(row.get("Monto Neto", 0))
            iva_rec      = _parse_int(row.get("Monto IVA Recuperable", 0))
            iva_no_rec   = _parse_int(row.get("Monto Iva No Recuperable", 0))
            exento       = _parse_int(row.get("Monto Exento", 0))
            total        = _parse_int(row.get("Monto Total", 0))

            # IVA crédito solo si el cliente es afecto
            iva_credito = iva_rec if usa_iva else 0

            # Costo empresa
            if usa_iva:
                costo = neto + exento + iva_no_rec
            else:
                costo = neto + iva_rec + exento + iva_no_rec

            doc = frappe.get_doc({
                "doctype":          "Libro_de_Compras_Cliente",
                "cliente":          cliente,
                "mes_tributario":   mes,
                "ano_tributario":   ano,
                "tipo_documento":   tipo_doc,
                "folio":            folio,
                "fecha_documento":  fecha,
                "rut_proveedor":    rut,
                "razon_social_proveedor": razon,
                "neto":             neto,
                "iva_credito":      iva_credito,
                "monto_exento":     exento,
                "total_documento":  total,
                "costo_empresa":    costo,
            })
            doc.insert(ignore_permissions=True)
            insertados += 1

        except Exception as e:
            errores.append(f"Fila {i}: {str(e)[:80]}")

    frappe.db.commit()

    frappe.response["message"] = {
        "status":     "ok",
        "insertados": insertados,
        "eliminados": len(existentes),
        "errores":    len(errores),
        "detalle_errores": errores[:10],
        "message":    f"Importación completada: {insertados} registros cargados, {len(existentes)} anteriores eliminados."
                      + (f" {len(errores)} errores." if errores else ""),
    }


# ── Importador CSV SII — Libro de Ventas ────────────────────────────────────

TIPO_DOC_VENTA_SII = {
    "33": "FACTURA ELECTRÓNICA",
    "34": "FACTURA NO ELECTRÓNICA",
    "56": "NOTA DE DÉBITO ELECTRÓNICA",
    "61": "NOTA DE CRÉDITO ELECTRÓNICA",
}

# Mapa del resumen: texto del SII (puede venir con encoding roto) → tipo_documento
RESUMEN_TIPO_MAP = {
    "boleta":        "Total Oper. del mes Boleta Electr.(39)",
    "comprobante":   "Total mes Comprobantes Pago Electrónico(48)",
}

def _normalizar_tipo_resumen(texto):
    """Devuelve el tipo_documento correcto a partir del texto del resumen SII."""
    t = texto.lower()
    if "boleta" in t:
        return "Total Oper. del mes Boleta Electr.(39)"
    if "comprobante" in t or "pago" in t:
        return "Total mes Comprobantes Pago Electrónico(48)"
    return None  # Factura Electrónica del resumen → ignorar

@frappe.whitelist(allow_guest=False)
def importar_libro_ventas_csv(**kwargs):
    """
    Importa el CSV de Libro de Ventas descargado del SII.
    Acepta dos archivos opcionales:
      - file_url_detalle  : RCV_VENTA_*.csv  (facturas, NC, ND individuales)
      - file_url_resumen  : RCV_RESUMEN_VENTA_*.csv (totales boletas/comprobantes)

    Elimina todos los registros existentes del cliente/período antes de importar.
    """
    import csv, io

    doc_name         = frappe.form_dict.get("doc_name")
    file_url_detalle = frappe.form_dict.get("file_url_detalle")
    file_url_resumen = frappe.form_dict.get("file_url_resumen")
    cliente_p        = frappe.form_dict.get("cliente")
    mes_p            = frappe.form_dict.get("mes")
    ano_p            = frappe.form_dict.get("ano")

    if not file_url_detalle and not file_url_resumen:
        frappe.response["message"] = {"status": "error", "message": "Debes subir al menos un archivo."}
        return

    try:
        cliente, mes, ano = _resolver_periodo(doc_name=doc_name, cliente=cliente_p, mes=mes_p, ano=ano_p)
    except Exception as e:
        frappe.response["message"] = {"status": "error", "message": str(e)}
        return

    # Eliminar registros existentes del período
    existentes = frappe.get_all(
        "Libro_de_Ingresos_Cliente",
        filters={"cliente": cliente, "mes_tributario": mes, "ano_tributario": ano},
        fields=["name"]
    )
    for r in existentes:
        frappe.delete_doc("Libro_de_Ingresos_Cliente", r.name, ignore_permissions=True, force=True)
    frappe.db.commit()

    insertados = 0
    errores    = []

    def _leer_archivo(file_url, encoding="utf-8-sig"):
        file_doc  = frappe.get_doc("File", {"file_url": file_url})
        file_path = file_doc.get_full_path()
        with open(file_path, encoding=encoding, errors="replace") as f:
            return f.read()

    def _insertar(tipo_doc, folio, fecha, rut, razon, exento, neto, iva, total):
        doc = frappe.get_doc({
            "doctype":              "Libro_de_Ingresos_Cliente",
            "cliente":              cliente,
            "mes_tributario":       mes,
            "ano_tributario":       ano,
            "tipo_documento":       tipo_doc,
            "folio":                folio or "",
            "fecha_documento":      fecha,
            "rut_receptor":         rut or "",
            "razon_social_receptor": razon or "",
            "monto_exento":         exento,
            "neto":                 neto,
            "iva":                  iva,
            "total":                total,
        })
        doc.insert(ignore_permissions=True)

    # ── Archivo detalle (RCV_VENTA) ──────────────────────────────────────────
    if file_url_detalle:
        try:
            contenido = _leer_archivo(file_url_detalle)
            reader    = csv.DictReader(io.StringIO(contenido), delimiter=";")
            for i, row in enumerate(reader, start=1):
                try:
                    tipo_codigo = str(row.get("Tipo Doc", "")).strip()
                    tipo_doc    = TIPO_DOC_VENTA_SII.get(tipo_codigo)
                    if not tipo_doc:
                        continue  # tipo no reconocido, saltar
                    exento = _parse_int(row.get("Monto Exento", 0))
                    neto   = _parse_int(row.get("Monto Neto", 0))
                    iva    = _parse_int(row.get("Monto IVA", 0))
                    total  = _parse_int(row.get("Monto total", 0))
                    _insertar(
                        tipo_doc  = tipo_doc,
                        folio     = str(row.get("Folio", "")).strip(),
                        fecha     = _parse_fecha(row.get("Fecha Docto", "")),
                        rut       = str(row.get("Rut cliente", "")).strip(),
                        razon     = str(row.get("Razon Social", "")).strip(),
                        exento    = exento,
                        neto      = neto,
                        iva       = iva,
                        total     = total,
                    )
                    insertados += 1
                except Exception as e:
                    errores.append(f"Detalle fila {i}: {str(e)[:80]}")
        except Exception as e:
            frappe.response["message"] = {"status": "error", "message": f"Error leyendo archivo detalle: {e}"}
            return

    # ── Archivo resumen (RCV_RESUMEN_VENTA) ──────────────────────────────────
    if file_url_resumen:
        try:
            contenido = _leer_archivo(file_url_resumen, encoding="latin-1")
            reader    = csv.DictReader(io.StringIO(contenido), delimiter=";")
            for i, row in enumerate(reader, start=1):
                try:
                    tipo_txt = str(row.get("Tipo Documento", "")).strip()
                    tipo_doc = _normalizar_tipo_resumen(tipo_txt)
                    if not tipo_doc:
                        continue  # fila de facturas → ignorar (ya vienen en detalle)
                    exento = _parse_int(row.get("Monto Exento", 0))
                    neto   = _parse_int(row.get("Monto Neto", 0))
                    iva    = _parse_int(row.get("Monto IVA", 0))
                    total  = _parse_int(row.get("Monto Total", 0))
                    _insertar(
                        tipo_doc = tipo_doc,
                        folio    = "",
                        fecha    = frappe.utils.today(),
                        rut      = "",
                        razon    = "",
                        exento   = exento,
                        neto     = neto,
                        iva      = iva,
                        total    = total,
                    )
                    insertados += 1
                except Exception as e:
                    errores.append(f"Resumen fila {i}: {str(e)[:80]}")
        except Exception as e:
            frappe.response["message"] = {"status": "error", "message": f"Error leyendo archivo resumen: {e}"}
            return

    frappe.db.commit()

    frappe.response["message"] = {
        "status":          "ok",
        "insertados":      insertados,
        "eliminados":      len(existentes),
        "errores":         len(errores),
        "detalle_errores": errores[:10],
        "message":         f"Importación completada: {insertados} registros cargados, {len(existentes)} anteriores eliminados."
                           + (f" {len(errores)} errores." if errores else ""),
    }


# ── Importador CSV SII — Libro de Honorarios ────────────────────────────────

@frappe.whitelist()
def importar_libro_honorarios_csv(doc_name=None, file_url=None, cliente=None, mes=None, ano=None):
    """
    Importa el CSV de Honorarios descargado del SII (guardado desde Excel/HTML como CSV).
    Acepta doc_name (Borrador_F29) o cliente+mes+ano directamente.
    """
    import csv, io

    doc_name = doc_name or frappe.form_dict.get("doc_name")
    file_url = file_url or frappe.form_dict.get("file_url")
    cliente  = cliente  or frappe.form_dict.get("cliente")
    mes      = mes      or frappe.form_dict.get("mes")
    ano      = ano      or frappe.form_dict.get("ano")

    try:
        cliente, mes, ano = _resolver_periodo(doc_name=doc_name, cliente=cliente, mes=mes, ano=ano)
    except Exception as e:
        frappe.response["message"] = {"status": "error", "message": str(e)}
        return

    # Eliminar registros existentes del período
    existentes = frappe.get_all(
        "Libro_de_Honorarios_Cliente",
        filters={"cliente": cliente, "mes_tributario": mes, "ano_tributario": ano},
        fields=["name"],
    )
    for r in existentes:
        frappe.delete_doc("Libro_de_Honorarios_Cliente", r.name, ignore_permissions=True, force=True)
    frappe.db.commit()

    # Leer archivo
    file_doc  = frappe.get_doc("File", {"file_url": file_url})
    file_path = file_doc.get_full_path()

    # Intentar latin-1 primero (el SII genera este formato en Excel/HTML)
    for enc in ("latin-1", "utf-8-sig", "utf-8"):
        try:
            with open(file_path, encoding=enc, errors="strict") as f:
                contenido = f.read()
            break
        except (UnicodeDecodeError, LookupError):
            continue
    else:
        with open(file_path, encoding="latin-1", errors="replace") as f:
            contenido = f.read()

    lines = contenido.splitlines()

    # Encontrar la fila de encabezados (contiene "N°" o "N" en primera columna)
    header_idx = None
    for idx, line in enumerate(lines):
        primera = line.split(";")[0].strip().replace("﻿", "")
        if primera in ("N°", "N"):
            header_idx = idx
            break

    if header_idx is None:
        frappe.response["message"] = {"status": "error", "message": "No se encontró la fila de encabezados en el archivo."}
        return

    data_lines = "\n".join(lines[header_idx:])
    reader = csv.DictReader(io.StringIO(data_lines), delimiter=";")

    insertados = 0
    errores    = []

    for i, row in enumerate(reader, start=1):
        try:
            folio = str(row.get("N°", "") or row.get("N", "")).strip()
            # Saltar totales, filas vacías y sin folio numérico
            if not folio or not folio.isdigit():
                continue

            estado = str(row.get("Estado", "")).strip().upper()
            if estado == "ANULADA":
                continue

            fecha_str = str(row.get("Fecha", "")).strip()
            # Formato DD-MM-YYYY o DD/MM/YYYY
            fecha_str = fecha_str.replace("-", "/")
            fecha = _parse_fecha(fecha_str)

            bruto    = _parse_int(row.get("Brutos", 0))
            retenido = _parse_int(row.get("Retenido", 0))
            pagado   = _parse_int(row.get("Pagado", 0))

            frappe.get_doc({
                "doctype":             "Libro_de_Honorarios_Cliente",
                "cliente":             cliente,
                "mes_tributario":      mes,
                "ano_tributario":      ano,
                "folio":               folio,
                "fecha_documento":     fecha,
                "rut_prestador":       str(row.get("Rut", "") or row.get("RUT", "")).strip(),
                "nombre_prestador":    str(row.get("Nombre o Razón Social", "") or row.get("Nombre o Razon Social", "")).strip(),
                "monto_bruto":         bruto,
                "retencion_honorarios": retenido,
                "monto_liquido":       pagado,
                "total_documento":     bruto,
                "costo_empresa":       bruto,
            }).insert(ignore_permissions=True)
            insertados += 1

        except Exception as e:
            errores.append(f"Fila {i}: {str(e)[:80]}")

    frappe.db.commit()

    frappe.response["message"] = {
        "status":          "ok",
        "insertados":      insertados,
        "eliminados":      len(existentes),
        "errores":         len(errores),
        "detalle_errores": errores[:10],
        "message":         f"Importación honorarios completada: {insertados} boletas cargadas, {len(existentes)} anteriores eliminadas."
                           + (f" {len(errores)} errores." if errores else ""),
    }


# ── Importador CSV Previred — Libro de Remuneraciones Electrónico (LRE) ────────

@frappe.whitelist()
def importar_lre_csv(doc_name=None, file_url=None, cliente=None, mes=None, ano=None):
    """
    Importa el CSV del LRE (Libro de Remuneraciones Electrónico) de Previred.
    Acepta doc_name (Borrador_F29) o cliente+mes+ano directamente.
    """
    import csv, io, re

    doc_name = doc_name or frappe.form_dict.get("doc_name")
    file_url = file_url or frappe.form_dict.get("file_url")
    cliente  = cliente  or frappe.form_dict.get("cliente")
    mes      = mes      or frappe.form_dict.get("mes")
    ano      = ano      or frappe.form_dict.get("ano")

    try:
        cliente, mes, ano = _resolver_periodo(doc_name=doc_name, cliente=cliente, mes=mes, ano=ano)
    except Exception as e:
        frappe.response["message"] = {"status": "error", "message": str(e)}
        return

    # Leer archivo (Previred usa utf-8 o latin-1)
    file_doc  = frappe.get_doc("File", {"file_url": file_url})
    file_path = file_doc.get_full_path()
    for enc in ("utf-8-sig", "latin-1", "utf-8"):
        try:
            with open(file_path, encoding=enc, errors="strict") as f:
                contenido = f.read()
            break
        except (UnicodeDecodeError, LookupError):
            continue
    else:
        with open(file_path, encoding="latin-1", errors="replace") as f:
            contenido = f.read()

    reader = csv.reader(io.StringIO(contenido), delimiter=";")
    rows   = list(reader)
    if len(rows) < 2:
        frappe.response["message"] = {"status": "error", "message": "Archivo vacío o sin datos."}
        return

    # Construir mapa código → índice de columna
    header = rows[0]
    col_map = {}
    for idx, h in enumerate(header):
        m = re.search(r'\((\d+)\)', h)
        if m:
            col_map[int(m.group(1))] = idx

    def _col(row, code, default=0):
        idx = col_map.get(code)
        if idx is None or idx >= len(row):
            return default
        return _parse_int(row[idx]) if default == 0 else str(row[idx]).strip()

    def _col_str(row, code):
        return _col(row, code, default="")

    # Eliminar detalles existentes del período
    existentes = frappe.get_all(
        "Detalle_LRE_Cliente",
        filters={"cliente": cliente, "mes_tributario": mes, "ano_tributario": ano},
        fields=["name"],
    )
    for r in existentes:
        frappe.delete_doc("Detalle_LRE_Cliente", r.name, ignore_permissions=True, force=True)
    frappe.db.commit()

    insertados = 0
    errores    = []

    # Acumuladores para Registro_Remuneraciones
    acc = {k: 0 for k in [
        "empleados", "hab_5201", "imp_5210", "no_imp_5230",
        "afp_3141", "salud_3143", "afc_trab_3151",
        "afc_emp_4151", "mutual_4152", "sis_4155",
        "imp_unico_3161", "prestamo_3166", "aportes_emp_5410",
    ]}

    for i, row in enumerate(rows[1:], start=1):
        if not row or not str(row[0]).strip():
            continue
        rut = str(row[0]).strip()
        if not rut or rut.lower() in ("rut trabajador(1101)", "totales", "total"):
            continue

        try:
            frappe.get_doc({
                "doctype":              "Detalle_LRE_Cliente",
                "cliente":              cliente,
                "ano_tributario":       ano,
                "mes_tributario":       mes,
                "rut_trabajador":       rut,
                "dias_trabajados":      _col(row, 1115),
                "sueldo":               _col(row, 2101),
                "sobresueldo":          _col(row, 2102),
                "gratificacion":        _col(row, 2106),
                "colacion":             _col(row, 2301),
                "movilizacion":         _col(row, 2302),
                "total_haberes":        _col(row, 5201),
                "total_imponible":      _col(row, 5210),
                "total_no_imponible":   _col(row, 5230),
                "total_descuentos":     _col(row, 5301),
                "total_aportes_empleador": _col(row, 5410),
                "total_liquido":        _col(row, 5501),
                "afp":                  _col(row, 3141),
                "salud":                _col(row, 3143),
                "afc_trabajador":       _col(row, 3151),
                "impuesto_unico":       _col(row, 3161),
                "retencion_prestamo":   _col(row, 3166),
                "afc_empleador":        _col(row, 4151),
                "mutual_sanna":         _col(row, 4152) + _col(row, 4155),
            }).insert(ignore_permissions=True)

            acc["empleados"]      += 1
            acc["hab_5201"]       += _col(row, 5201)
            acc["imp_5210"]       += _col(row, 5210)
            acc["no_imp_5230"]    += _col(row, 5230)
            acc["afp_3141"]       += _col(row, 3141)
            acc["salud_3143"]     += _col(row, 3143)
            acc["afc_trab_3151"]  += _col(row, 3151)
            acc["afc_emp_4151"]   += _col(row, 4151)
            acc["mutual_4152"]    += _col(row, 4152)
            acc["sis_4155"]       += _col(row, 4155)
            acc["imp_unico_3161"] += _col(row, 3161)
            acc["prestamo_3166"]  += _col(row, 3166)
            acc["aportes_emp_5410"] += _col(row, 5410)
            insertados += 1

        except Exception as e:
            errores.append(f"Fila {i} ({rut}): {str(e)[:80]}")

    frappe.db.commit()

    # ── Actualizar Registro_Remuneraciones ────────────────────────────────────
    total_afp      = acc["afp_3141"]
    total_salud    = acc["salud_3143"]
    total_cesantia = acc["afc_trab_3151"] + acc["afc_emp_4151"]
    total_mutual   = acc["mutual_4152"] + acc["sis_4155"]
    total_previred = total_afp + total_salud + total_cesantia + total_mutual

    rr_name = frappe.db.get_value(
        "Registro_Remuneraciones",
        {"cliente": cliente, "ano": ano, "mes": mes},
        "name"
    )
    if rr_name:
        rr = frappe.get_doc("Registro_Remuneraciones", rr_name)
    else:
        rr = frappe.get_doc({"doctype": "Registro_Remuneraciones", "cliente": cliente, "ano": ano, "mes": mes})

    rr.total_empleados_activos    = acc["empleados"]
    rr.total_haberes_imponibles   = acc["imp_5210"]
    rr.total_haberes_no_imponibles = acc["no_imp_5230"]
    rr.costo_total_empleador      = acc["hab_5201"] + acc["aportes_emp_5410"]
    rr.total_afp                  = total_afp
    rr.total_salud                = total_salud
    rr.total_seguro_cesantia      = total_cesantia
    rr.total_sis_mutual           = total_mutual
    rr.total_previred_a_pagar     = total_previred
    rr.impuesto_unico             = acc["imp_unico_3161"]
    rr.retencion_prestamo_solidario = acc["prestamo_3166"]

    if rr_name:
        rr.save(ignore_permissions=True)
    else:
        rr.insert(ignore_permissions=True)
    frappe.db.commit()

    frappe.response["message"] = {
        "status":      "ok",
        "insertados":  insertados,
        "eliminados":  len(existentes),
        "errores":     len(errores),
        "detalle_errores": errores[:10],
        "empleados":   acc["empleados"],
        "total_previred": total_previred,
        "imp_unico":   acc["imp_unico_3161"],
        "message":     f"LRE importado: {insertados} trabajadores cargados. "
                       f"Registro_Remuneraciones actualizado — Previred: ${total_previred:,.0f}, Imp.Único: ${acc['imp_unico_3161']:,.0f}."
                       + (f" {len(errores)} errores." if errores else ""),
    }


# ── Postergación IVA ─────────────────────────────────────────────────────────

@frappe.whitelist()
def registrar_postergacion_iva(doc_name, monto, meses_diferidos=2):
    """
    Crea o actualiza un registro Postergacion_IVA y actualiza el Borrador_F29.
    meses_diferidos: 1 o 2 (Art. 64 D.L. 825 permite hasta 2 meses).
    fecha_vencimiento: día 20 del mes siguiente al mes de pago en el F29.
    """
    import datetime
    from frappe.utils import add_months

    doc_f29 = frappe.get_doc("Borrador_F29", doc_name)
    cliente = doc_f29.cliente
    mes     = int(doc_f29.mes)
    ano     = int(doc_f29.ano)
    monto   = float(monto)
    meses_diferidos = int(meses_diferidos)

    # Mes/año en que se paga el F29 diferido
    fecha_origen  = datetime.date(ano, mes, 1)
    fecha_pago    = add_months(fecha_origen, meses_diferidos)
    mes_pago      = fecha_pago.month
    ano_pago      = fecha_pago.year

    # Vencimiento: día 20 del mes siguiente al de pago
    fecha_sig     = add_months(fecha_pago, 1)
    fecha_venc    = datetime.date(fecha_sig.year, fecha_sig.month, 20)

    id_post = f"POST-{cliente}-{ano}-{mes}"

    existing_name = frappe.db.get_value("Postergacion_IVA", {"id_postergacion": id_post}, "name")
    if existing_name:
        post_doc = frappe.get_doc("Postergacion_IVA", existing_name)
        post_doc.monto_postergado  = monto
        post_doc.mes_f29_pagado    = mes_pago
        post_doc.ano_f29_pagado    = ano_pago
        post_doc.fecha_vencimiento = fecha_venc
        post_doc.save(ignore_permissions=True)
    else:
        post_doc = frappe.get_doc({
            "doctype":          "Postergacion_IVA",
            "id_postergacion":  id_post,
            "cliente":          cliente,
            "mes_origen":       mes,
            "ano_origen":       ano,
            "monto_postergado": monto,
            "mes_f29_pagado":   mes_pago,
            "ano_f29_pagado":   ano_pago,
            "fecha_vencimiento": fecha_venc,
        })
        post_doc.insert(ignore_permissions=True)

    # Actualizar Borrador_F29
    doc_f29.postergar_iva_periodo    = 1
    doc_f29.postergacion_del_periodo = monto
    doc_f29.save(ignore_permissions=True)
    frappe.db.commit()

    frappe.response["message"] = {
        "status":            "ok",
        "id_postergacion":   id_post,
        "monto":             monto,
        "mes_pago":          mes_pago,
        "ano_pago":          ano_pago,
        "fecha_vencimiento": str(fecha_venc),
        "message": f"Postergación registrada: ${monto:,.0f} — vence el {fecha_venc.strftime('%d/%m/%Y')}.",
    }


@frappe.whitelist()
def cancelar_postergacion_iva(doc_name):
    """Elimina la Postergacion_IVA del período y limpia el Borrador_F29."""
    doc_f29  = frappe.get_doc("Borrador_F29", doc_name)
    cliente  = doc_f29.cliente
    mes      = int(doc_f29.mes)
    ano      = int(doc_f29.ano)
    id_post  = f"POST-{cliente}-{ano}-{mes}"

    existing_name = frappe.db.get_value("Postergacion_IVA", {"id_postergacion": id_post}, "name")
    if existing_name:
        frappe.delete_doc("Postergacion_IVA", existing_name, ignore_permissions=True, force=True)

    doc_f29.postergar_iva_periodo    = 0
    doc_f29.postergacion_del_periodo = 0
    doc_f29.save(ignore_permissions=True)
    frappe.db.commit()

    frappe.response["message"] = {"status": "ok", "message": "Postergación cancelada."}


# ── Creación de Declaraciones + Borrador F29 ─────────────────────────────────

def _crear_par_declaracion_f29(cliente, mes, ano, biblioteca):
    """
    Crea Declaracion_Mensual + Borrador_F29 para un cliente/período.
    Retorna (creado: bool, mensaje: str).
    """
    abrev = frappe.db.get_value("Ficha_Cliente", cliente, "abreviatura_cliente") or cliente
    id_dm  = f"DM-{abrev}-{ano}-{mes}"
    id_f29 = f"F29-{abrev}-{ano}-{mes}"

    if frappe.db.exists("Declaracion_Mensual", {"id_documento": id_dm}):
        return False, f"Ya existe: {id_dm}"

    dm = frappe.get_doc({
        "doctype":      "Declaracion_Mensual",
        "id_documento": id_dm,
        "cliente":      cliente,
        "ano":          ano,
        "mes":          mes,
    })
    dm.insert(ignore_permissions=True)

    mapeo = {
        "tabla_debitos":   "Linea_F29_Debito",
        "tabla_creditos":  "Linea_F29_Credito",
        "tabla_impuestos": "Linea_F29_Impuesto",
    }
    f29 = frappe.get_doc({
        "doctype":                       "Borrador_F29",
        "id_documento":                  id_f29,
        "cliente":                       cliente,
        "ano":                           ano,
        "mes":                           mes,
        "declaracion_mensual_vinculada": dm.name,
    })
    f29.insert(ignore_permissions=True)

    if biblioteca:
        for regla in biblioteca:
            if regla.tabla_destino in mapeo:
                f29.append(regla.tabla_destino, {
                    "orden":                  regla.orden,
                    "codigo_f29":             regla.codigo_f29,
                    "descripcion":            regla.descripcion,
                    "tipo_operacion_subtotal": regla.tipo_operacion_subtotal or "Suma",
                    "monto":                  0.0,
                    "tipo_origen":            "Calculado" if regla.es_calculado else "Manual",
                })
        f29.save(ignore_permissions=True)

    dm.borrador_f29_vinculado = f29.name
    dm.save(ignore_permissions=True)
    frappe.db.commit()
    return True, f"Creado: {id_dm}"


def _cargar_biblioteca_f29():
    return frappe.get_all(
        "Configuracion_Codigo_F29",
        fields=["orden", "codigo_f29", "descripcion", "tabla_destino",
                "tipo_operacion_subtotal", "es_calculado"],
        order_by="orden asc",
    )


@frappe.whitelist()
def crear_declaraciones_periodo(cliente, mes, ano):
    """
    Crea Declaracion_Mensual + Borrador_F29 para un cliente y período específico.
    Usado desde la pestaña Carga Histórica de Ficha_Cliente.
    """
    try:
        biblioteca = _cargar_biblioteca_f29()
        creado, msg = _crear_par_declaracion_f29(str(cliente), str(mes), str(ano), biblioteca)
        frappe.response["message"] = {
            "status":  "ok" if creado else "exists",
            "creado":  creado,
            "message": msg,
        }
    except Exception as e:
        frappe.response["message"] = {"status": "error", "message": str(e)}


@frappe.whitelist()
def procesar_mes_actual():
    """
    Crea Declaracion_Mensual + Borrador_F29 para TODOS los clientes activos
    en el período del mes anterior (misma lógica que el cron mensual).
    Idempotente — omite los que ya existen.
    Llamado manualmente desde el Workspace para procesar clientes nuevos.
    """
    from frappe.utils import add_months, getdate, nowdate

    hoy           = getdate(nowdate())
    fecha_periodo = add_months(hoy, -1)
    mes           = str(fecha_periodo.month)
    ano           = str(fecha_periodo.year)

    clientes = frappe.get_all(
        "Ficha_Cliente",
        filters={"estado_cliente": "Activo"},
        fields=["name", "abreviatura_cliente"],
        order_by="abreviatura_cliente asc",
    )

    if not clientes:
        frappe.response["message"] = {"status": "ok", "message": "No hay clientes activos.", "creados": 0}
        return

    biblioteca = _cargar_biblioteca_f29()
    creados = omitidos = errores = 0
    detalle_errores = []

    for c in clientes:
        try:
            creado, _ = _crear_par_declaracion_f29(c.name, mes, ano, biblioteca)
            if creado:
                creados += 1
            else:
                omitidos += 1
        except Exception as e:
            errores += 1
            detalle_errores.append(f"{c.abreviatura_cliente}: {str(e)[:80]}")

    frappe.response["message"] = {
        "status":   "ok",
        "periodo":  f"{mes}/{ano}",
        "creados":  creados,
        "omitidos": omitidos,
        "errores":  errores,
        "detalle_errores": detalle_errores[:10],
        "message":  f"Período {mes}/{ano} — {creados} creados, {omitidos} ya existían."
                    + (f" {errores} errores." if errores else ""),
    }


# ── Datos F29 para Panel Mensual ─────────────────────────────────────────────

@frappe.whitelist()
def get_f29_panel_data(ano, mes):
    """Devuelve datos F29 del período con honorarios y PPM desde las líneas hijas."""
    rows = frappe.db.sql("""
        SELECT
            f.name,
            f.cliente,
            f.subtotal_debitos,
            f.subtotal_creditos,
            f.remanente_mes_siguiente,
            f.subtotal_otros_impuestos,
            f.impuesto_determinado,
            f.total_a_pagar_f29,
            SUM(CASE WHEN i.codigo_f29 = '151' THEN i.monto ELSE 0 END) AS honorarios_a_pagar,
            SUM(CASE WHEN i.codigo_f29 = '62'  THEN i.monto ELSE 0 END) AS ppm_a_pagar
        FROM `tabBorrador_F29` f
        LEFT JOIN `tabLinea_F29_Impuesto` i ON i.parent = f.name
        WHERE f.ano = %(ano)s AND f.mes = %(mes)s
        GROUP BY f.name
    """, {"ano": ano, "mes": mes}, as_dict=True)

    return {r.name: r for r in rows}


# ── Resetear Declaración Mensual ─────────────────────────────────────────────

@frappe.whitelist()
def resetear_declaracion(doc_name):
    """
    Regresa una Declaracion_Mensual a estado Borrador:
    - Limpia checks (RRHH, F29, Previred)
    - Limpia campos PDF
    - Elimina Cobranza_Cliente vinculada del período
    - Estado → Borrador
    """
    try:
        dm = frappe.get_doc("Declaracion_Mensual", doc_name)

        # Eliminar Cobranza_Cliente del período
        cobros = frappe.get_all(
            "Cobranza_Cliente",
            filters={"cliente": dm.cliente, "periodo_mes": dm.mes, "periodo_ano": dm.ano},
            fields=["name"]
        )
        eliminados = 0
        for c in cobros:
            frappe.delete_doc("Cobranza_Cliente", c.name, ignore_permissions=True, force=True)
            eliminados += 1

        # Actualizar campos directamente en DB (sin before_save ni validación de links)
        frappe.db.set_value("Declaracion_Mensual", doc_name, {
            "check_gasto_rem_cargado": 0,
            "check_f29_cuadrado":      0,
            "check_previred_cuadrado": 0,
            "pdf_link_cliente":        "",
            "pdf_generado":            "",
            "pdf_generado_flag":       0,
            "cobranza_vinculada":      "",
            "estado":                  "Borrador",
        })

        frappe.db.commit()
        frappe.response["message"] = {
            "status":    "ok",
            "cobros_eliminados": eliminados,
            "message":   f"Declaración regresada a Borrador. {eliminados} cobro(s) eliminado(s).",
        }
    except Exception as e:
        frappe.response["message"] = {"status": "error", "message": str(e)}


@frappe.whitelist()
def has_app_permission():
	return frappe.session.user != "Guest"
