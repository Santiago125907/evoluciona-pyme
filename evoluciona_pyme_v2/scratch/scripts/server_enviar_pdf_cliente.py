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