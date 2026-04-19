# ================================================================
# SERVER SCRIPT: Declaracion_Mensual - Before Save (V6 NUEVOS PLANES)
# ================================================================
# Tipo: DocType Event
# Reference DocType: Declaracion_Mensual
# Event: Before Save
# ================================================================

def actualizar_estado_declaracion(doc):
    check_rrhh = 1 if doc.get('check_gasto_rem_cargado') else 0
    check_f29 = 1 if doc.get('check_f29_cuadrado') else 0
    check_prev = 1 if doc.get('check_previred_cuadrado') else 0
    
    total_checks = check_rrhh + check_f29 + check_prev
    
    if total_checks == 0:
        doc.estado = "Borrador"
    elif total_checks == 3:
        doc.estado = "Listo"
    else:
        doc.estado = "En Validación"
    
    frappe.msgprint(f"📊 Checks: RRHH={check_rrhh}, F29={check_f29}, Prev={check_prev} → Estado: {doc.estado}", indicator='blue')

def calcular_vencimientos_impuestos(doc):
    if not (doc.mes and doc.ano):
        return

    fecha_declaracion = frappe.utils.getdate(f"{doc.ano}-{str(doc.mes).zfill(2)}-01")
    fecha_pago = frappe.utils.add_months(fecha_declaracion, 1)
    
    # PREVIRED (Día 12)
    venc_prev = frappe.utils.getdate(f"{fecha_pago.year}-{str(fecha_pago.month).zfill(2)}-12")
    dia_sem = venc_prev.weekday() 
    if dia_sem == 5: 
        venc_prev = frappe.utils.add_days(venc_prev, -1)
    elif dia_sem == 6:
        venc_prev = frappe.utils.add_days(venc_prev, -2)
    doc.fecha_vencimiento_previred = venc_prev

    # F29 (Día 20)
    venc_f29 = frappe.utils.getdate(f"{fecha_pago.year}-{str(fecha_pago.month).zfill(2)}-20")
    dia_sem_f29 = venc_f29.weekday()
    if dia_sem_f29 == 5: 
        venc_f29 = frappe.utils.add_days(venc_f29, 2)
    elif dia_sem_f29 == 6: 
        venc_f29 = frappe.utils.add_days(venc_f29, 1)
    doc.fecha_vencimiento_f29 = venc_f29

def crear_cobranza_si_corresponde(doc):
    frappe.msgprint(f"🔍 Verificando creación de cobranza...<br>Estado actual: <strong>{doc.estado}</strong>", indicator='blue')
    
    if doc.estado not in ["Listo", "Enviado"]:
        frappe.msgprint(f"⏸️ Estado '{doc.estado}' no dispara creación de cobranza", indicator='orange')
        return
    
    existe = frappe.db.exists("Cobranza_Cliente", {
        "cliente": doc.cliente, 
        "periodo_ano": int(doc.ano), 
        "periodo_mes": int(doc.mes)
    })
    
    if existe:
        frappe.msgprint(f"⚠️ Ya existe cobranza para este período: {existe}", indicator='orange')
        return
    
    frappe.msgprint(f"✅ Procediendo a crear cobranza...", indicator='green')
    
    try:
        cliente_doc = frappe.get_doc("Ficha_Cliente", doc.cliente)
        
        monto_contable = 0
        total_ventas = 0
        
        # 1. Obtener Ventas descontando Notas de Crédito
        documentos = frappe.db.get_list("Libro_de_Ingresos_Cliente", 
            filters={"cliente": doc.cliente, "ano_tributario": str(doc.ano), "mes_tributario": str(doc.mes).zfill(2)},
            fields=["neto", "tipo_documento"]
        )
        if not documentos:
            documentos = frappe.db.get_list("Libro_de_Ingresos_Cliente", 
                filters={"cliente": doc.cliente, "ano_tributario": str(doc.ano), "mes_tributario": str(doc.mes)},
                fields=["neto", "tipo_documento"]
            )
            
        total_ventas = 0
        for d in documentos:
            if d.neto:
                tipo = str(d.tipo_documento or "").upper()
                if "NOTA DE CRÉDITO" in tipo or "NOTA DE CREDITO" in tipo:
                    total_ventas -= float(d.neto)
                else:
                    total_ventas += float(d.neto)
        
        frappe.msgprint(f"📈 Ventas Netas del Mes: ${total_ventas:,.0f}", indicator='blue')
        
        # 2. Buscar en el plan de tramos
        if cliente_doc.get('plan_contable'):
            plan = frappe.get_doc("Plan_Contable", cliente_doc.plan_contable)
            frappe.msgprint(f"📑 Plan Asignado: {plan.nombre_del_plan}", indicator='blue')
            for tramo in plan.tramos:
                if tramo.venta_minima <= total_ventas <= tramo.venta_maxima:
                    monto_contable = tramo.valor_mensual
                    frappe.msgprint(f"🎯 Cayó en el tramo de ${tramo.venta_minima:,.0f} a ${tramo.venta_maxima:,.0f} -> Valor: ${monto_contable:,.0f}", indicator='blue')
                    break
            
            if monto_contable == 0:
                frappe.msgprint("⚠️ ADVERTENCIA: Las ventas no cayeron en ningún tramo o cobranza es Cero.", indicator='red')
        else:
            monto_contable = float(cliente_doc.get('monto_base_plan') or 0)
            frappe.msgprint("⚠️ Cliente no tiene Plan por Tramos. Usando Monto Base antiguo.", indicator='orange')
            
        monto_rrhh = 0
        numero_empleados = 0
        if float(cliente_doc.get('monto_rrhh') or 0) > 0:
            monto_rrhh = float(cliente_doc.monto_rrhh)
            frappe.msgprint(f"👥 RRHH (Fijo): ${monto_rrhh:,.0f}", indicator='blue')
        elif cliente_doc.get('cobra_rrhh_variable'):
            registro_rrhh = frappe.db.get_value("Registro_Remuneraciones", 
                {"cliente": doc.cliente, "ano": int(doc.ano), "mes": int(doc.mes)}, 
                "total_empleados_activos"
            )
            if registro_rrhh:
                numero_empleados = int(registro_rrhh or 0)
                tarifa = float(cliente_doc.get('monto_por_empleado') or 0)
                monto_rrhh = numero_empleados * tarifa
                frappe.msgprint(f"👥 RRHH Variable: {numero_empleados} x ${tarifa} = ${monto_rrhh:,.0f}", indicator='blue')

        monto_adicionales = 0
        if cliente_doc.get('servicios_adicionales'):
            for adicional in cliente_doc.servicios_adicionales:
                mes_ini = int(adicional.get('mes_inicio') or 0)
                ano_ini = int(adicional.get('ano_inicio') or 0)
                
                if not mes_ini or not ano_ini:
                    continue
                    
                meses_transcurridos = ((int(doc.ano) - ano_ini) * 12) + (int(doc.mes) - mes_ini)
                
                if meses_transcurridos < 0:
                    frappe.msgprint(f"⏭️ Adicional omitido: {adicional.nombre_servicio} (El cobro comienza a futuro en {mes_ini}/{ano_ini})", indicator='gray')
                    continue
                
                tipo_duracion = adicional.get('tipo_duracion') or "Infinito"
                
                if tipo_duracion == "Infinito":
                    monto_adicionales += float(adicional.valor_mensual or 0)
                    frappe.msgprint(f"➕ Adicional (Mensual Fijo): {adicional.nombre_servicio} -> ${adicional.valor_mensual:,.0f}", indicator='blue')
                else: 
                    cuotas_totales = int(adicional.get('cuotas_totales') or 1)
                    if meses_transcurridos < cuotas_totales:
                        monto_adicionales += float(adicional.valor_mensual or 0)
                        frappe.msgprint(f"➕ Adicional (Cuota {meses_transcurridos + 1} de {cuotas_totales}): {adicional.nombre_servicio} -> ${adicional.valor_mensual:,.0f}", indicator='blue')
                    else:
                        frappe.msgprint(f"⏭️ Adicional omitido: {adicional.nombre_servicio} (Ya finalizó sus {cuotas_totales} cuotas históricas)", indicator='gray')
        
        subtotal = monto_contable + monto_rrhh + monto_adicionales
        
        total_descuentos = 0
        descuentos_aplicados = []
        
        if cliente_doc.get('descuentos_cliente'):
            periodo_ano = int(doc.ano)
            periodo_mes = int(doc.mes)
            
            for desc in cliente_doc.descuentos_cliente:
                # Usar valor real o por defecto
                activo = desc.get('activo')
                if activo is None: activo = 1 # checkbox por defecto true si no sabemos
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
        
        fecha_emision = frappe.utils.nowdate()
        dia_venc = cliente_doc.get('dia_vencimiento') or "15 días después"
        if dia_venc == "Vencimiento F29 (día 12)": dia_mes = 12
        elif dia_venc == "Vencimiento Imposiciones (día 10)": dia_mes = 10
        elif dia_venc == "15 días después":
            fecha_vencimiento = frappe.utils.add_days(fecha_emision, 15)
            dia_mes = None
        elif dia_venc == "Personalizado":
            dia_mes = int(cliente_doc.get('dia_vencimiento_personalizado') or 30)
        else:
            dia_mes = 30

        if dia_mes:
            mes_venc = int(doc.mes) + 1
            ano_venc = int(doc.ano)
            if mes_venc > 12:
                mes_venc = 1
                ano_venc += 1
            try:
                fecha_vencimiento = frappe.utils.getdate(f"{ano_venc}-{str(mes_venc).zfill(2)}-{str(dia_mes).zfill(2)}")
            except:
                fecha_vencimiento = frappe.utils.getdate(f"{ano_venc}-{str(mes_venc).zfill(2)}-28")

        abreviatura = cliente_doc.get('abreviatura_cliente') or cliente_doc.name[:3]
        id_cob = f"COB-{abreviatura}-{doc.ano}-{str(doc.mes).zfill(2)}"
        
        frappe.msgprint(f"📝 Creando cobranza {id_cob} por ${monto_a_cobrar:,.0f} (Contabilidad: ${monto_contable:,.0f} | Adicionales: ${monto_adicionales:,.0f})", indicator='green')
        
        cob = frappe.get_doc({
            "doctype": "Cobranza_Cliente",
            "id_cobranza": id_cob,
            "cliente": doc.cliente,
            "declaracion_mensual": doc.name,
            "periodo_mes": int(doc.mes),
            "periodo_ano": int(doc.ano),
            "monto_base": monto_contable, 
            "numero_empleados": numero_empleados,
            "monto_rrhh": monto_rrhh,
            "subtotal": subtotal,
            "total_descuentos": total_descuentos,
            "monto_adicionales": monto_adicionales,
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
        doc.cobranza_vinculada = cob.name
        
        frappe.msgprint(f"✅ Cobranza {cob.name} registrada.", indicator='green')

    except Exception as e:
        frappe.log_error(str(e), "Error Cobranza V6")
        frappe.msgprint(f"❌ Error al crear cobranza: {str(e)}", indicator='red')

# =====================================================
actualizar_estado_declaracion(doc)
calcular_vencimientos_impuestos(doc)

if not doc.is_new():
    crear_cobranza_si_corresponde(doc)
else:
    frappe.msgprint("ℹ️ Documento nuevo, no se crea cobranza aún", indicator='blue')
