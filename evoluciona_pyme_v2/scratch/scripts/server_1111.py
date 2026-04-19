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