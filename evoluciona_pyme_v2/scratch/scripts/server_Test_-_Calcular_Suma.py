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