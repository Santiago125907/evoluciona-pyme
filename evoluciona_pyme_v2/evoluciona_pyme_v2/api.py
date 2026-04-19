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
        
        # 16. ENVIAR A N8N
        N8N_URL = frappe.db.get_single_value('Configuracion_n8n', 'webhook_preparar_pdf')
        if not N8N_URL:
            # Fallback por si no lo han llenado
            N8N_URL = "https://n8n-n8n.6pe7e2.easypanel.host/webhook/f4f3ccd0-0155-4068-9f81-63cb9d715cee"
        
        payload_json = json.dumps(payload)
        
        frappe.log_error("Payload enviado a n8n", payload_json)
        
        response = frappe.make_post_request(
            url=N8N_URL,
            data=payload_json,
            headers={"Content-Type": "application/json"}
        )
        
        frappe.log_error("Respuesta de n8n", str(response))
        
        # =========================================================
        # 17. GUARDAR RESPUESTA DE N8N EN DECLARACIÓN
        # =========================================================
        if response and isinstance(response, dict):
            if response.get("status") == "ok":
                # Guardar URLs del PDF
                if response.get("pdf_url_drive"):
                    decl.pdf_link_cliente = response.get("pdf_url_drive")
                
                if response.get("pdf_file_id"):
                    decl.pdf_drive_file_id = response.get("pdf_file_id")
                
                # Si la carpeta del cliente fue creada, actualizar Ficha_Cliente
                if response.get("carpeta_cliente_creada") == True and response.get("folder_cliente_id"):
                    try:
                        cliente_doc.drive_folder_id = response.get("folder_cliente_id")
                        cliente_doc.drive_folder_url = response.get("folder_cliente_url")
                        cliente_doc.save(ignore_permissions=True)
                        frappe.log_error("CARPETA CLIENTE CREADA", f"ID guardado: {response.get('folder_cliente_id')}")
                    except Exception as e:
                        frappe.log_error("Error guardando folder_id en cliente", str(e))
        
        decl.pdf_generado_flag = 1 if response.get("status") == "ok" else 0
        decl.fecha_pdf_generado = frappe.utils.now_datetime()
        decl.save(ignore_permissions=True)
        frappe.db.commit()
        
        frappe.response['message'] = {
            "status": "success",
            "message": "PDF enviado a n8n correctamente",
            "pdf_url": response.get("pdf_url_drive") if response else None
        }
        
    except Exception as e:
        frappe.log_error("Error en Server Script PDF", str(e))
        frappe.response['message'] = {
            "status": "error",
            "message": f"Error: {str(e)}"
        }


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
                    
                    # Serializar a JSON manualmente
                    import json
                    payload_json = json.dumps(payload)
                    
                    # 4. Llamar webhook n8n de ENVÍO
                    N8N_ENVIO_URL = "https://n8n-n8n.6pe7e2.easypanel.host/webhook/enviar-pdf"
                    
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


