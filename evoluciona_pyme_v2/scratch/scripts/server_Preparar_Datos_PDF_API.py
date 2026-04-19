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