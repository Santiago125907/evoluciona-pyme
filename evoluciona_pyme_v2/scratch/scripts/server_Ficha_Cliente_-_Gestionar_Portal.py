# ===================================================================
# SERVER SCRIPT: Ficha_Cliente - Gestionar Portal
# Event: Before Save
# Versión: COMPLETA con User Permissions
# ===================================================================

# Generar password
password_temporal = doc.rut_cliente.replace('.', '').replace('-', '').strip() if doc.rut_cliente else None

# Obtener estado anterior
doc_antes = doc.get_doc_before_save()

# ===================================================================
# CASO 1: CHECKBOX SE MARCÓ (CREAR/VINCULAR)
# ===================================================================
if doc.habilitar_portal and (not doc_antes or not doc_antes.get("habilitar_portal")):
    
    email = doc.contacto_principal_email
    
    # Validar email
    if not email:
        frappe.throw("Debes configurar el Email de Contacto Principal antes de habilitar el portal.")
    
    if not password_temporal:
        frappe.throw("El RUT del cliente no es válido para generar la contraseña.")
    
    # Verificar si ya existe el usuario
    usuario_existe = frappe.db.exists("User", email)
    
    if not usuario_existe:
        # ============================================================
        # CREAR NUEVO USUARIO
        # ============================================================
        
        nombre_completo = doc.contacto_principal_nombre or doc.razon_social
        
        # Crear User
        user = frappe.get_doc({
            "doctype": "User",
            "email": email,
            "first_name": nombre_completo,
            "enabled": 1,
            "send_welcome_email": 0,
            "user_type": "Website User",
            "new_password": password_temporal
        })
        
        user.insert(ignore_permissions=True)
        
        # Asignar rol Customer
        user.append("roles", {"role": "Customer"})
        user.reset_password_key = "debe_cambiar"
        user.save(ignore_permissions=True)
        
        # Crear Contact
        contact = frappe.get_doc({
            "doctype": "Contact",
            "first_name": nombre_completo,
            "email_id": email,
            "user": email
        })
        
        contact.append("links", {
            "link_doctype": "Ficha_Cliente",
            "link_name": doc.name,
            "link_title": doc.razon_social
        })
        
        contact.insert(ignore_permissions=True)
        
        # Actualizar campos
        doc.usuario_portal_vinculado = email
        doc.estado_portal = "Activo"
        doc.fecha_creacion_portal = frappe.utils.now()
        doc.password_portal_hint = password_temporal
        
        # Mensaje con credenciales
        mensaje = "✅ Acceso portal creado exitosamente.<br><br>"
        mensaje += "<strong>Usuario:</strong> " + email + "<br>"
        mensaje += "<strong>Contraseña temporal:</strong> " + password_temporal + "<br><br>"
        mensaje += "<strong>URL Portal:</strong> " + frappe.utils.get_url() + "/portal<br><br>"
        mensaje += "<small>⚠️ IMPORTANTE: Copia estas credenciales y envíaselas al cliente manualmente.<br>"
        mensaje += "El envío automático de emails está pendiente de configuración SMTP.</small>"
        
        frappe.msgprint(
            mensaje,
            title="Portal Creado - Envía credenciales al cliente",
            indicator="green"
        )
        
    else:
        # ============================================================
        # VINCULAR A USUARIO EXISTENTE
        # ============================================================
        
        # Buscar Contact
        contact_name = frappe.db.get_value("Contact", {"email_id": email}, "name")
        
        if contact_name:
            contact = frappe.get_doc("Contact", contact_name)
            
            # Verificar si ya está vinculado
            ya_vinculado = False
            for link in contact.links:
                if link.link_doctype == "Ficha_Cliente" and link.link_name == doc.name:
                    ya_vinculado = True
                    break
            
            # Agregar vínculo si no existe
            if not ya_vinculado:
                contact.append("links", {
                    "link_doctype": "Ficha_Cliente",
                    "link_name": doc.name,
                    "link_title": doc.razon_social
                })
                contact.save(ignore_permissions=True)
        else:
            # Crear Contact nuevo
            nombre_completo = doc.contacto_principal_nombre or doc.razon_social
            contact = frappe.get_doc({
                "doctype": "Contact",
                "first_name": nombre_completo,
                "email_id": email,
                "user": email
            })
            contact.append("links", {
                "link_doctype": "Ficha_Cliente",
                "link_name": doc.name,
                "link_title": doc.razon_social
            })
            contact.insert(ignore_permissions=True)
        
        # Actualizar campos
        doc.usuario_portal_vinculado = email
        doc.estado_portal = "Activo"
        doc.password_portal_hint = password_temporal
        
        # Mensaje
        mensaje = "✅ Empresa vinculada al usuario existente.<br><br>"
        mensaje += "<strong>Usuario:</strong> " + email + "<br>"
        mensaje += "<strong>Password alternativa:</strong> " + password_temporal + "<br><br>"
        mensaje += "<small>⚠️ Informa al cliente que se agregó esta empresa a su portal.</small>"
        
        frappe.msgprint(
            mensaje,
            title="Empresa Vinculada",
            indicator="green"
        )

# ===================================================================
# CASO 2: CHECKBOX SE DESMARCÓ (DESVINCULAR)
# ===================================================================
elif not doc.habilitar_portal and doc_antes and doc_antes.get("habilitar_portal"):
    
    email = doc.usuario_portal_vinculado
    
    if email:
        # Buscar Contact
        contact_name = frappe.db.get_value("Contact", {"email_id": email}, "name")
        
        if contact_name:
            contact = frappe.get_doc("Contact", contact_name)
            
            # Remover link de esta empresa
            links_actualizados = []
            for link in contact.links:
                if not (link.link_doctype == "Ficha_Cliente" and link.link_name == doc.name):
                    links_actualizados.append(link)
            
            # Si tiene otras empresas
            if len(links_actualizados) > 0:
                contact.links = links_actualizados
                contact.save(ignore_permissions=True)
                
                frappe.msgprint(
                    "⚠️ Empresa desvinculada del portal.<br><small>El cliente aún tiene acceso a sus otras empresas.</small>",
                    title="Empresa Desvinculada",
                    indicator="orange"
                )
            else:
                # Deshabilitar usuario
                user = frappe.get_doc("User", email)
                user.enabled = 0
                user.save(ignore_permissions=True)
                
                frappe.msgprint(
                    "⚠️ Acceso portal deshabilitado.<br><small>Esta era la última empresa.</small>",
                    title="Portal Deshabilitado",
                    indicator="red"
                )
        
        # Actualizar campo
        doc.estado_portal = "Deshabilitado"
        
        # Eliminar User Permission
        permisos = frappe.db.get_all("User Permission", {
            "user": email,
            "allow": "Ficha_Cliente",
            "for_value": doc.name
        }, pluck="name")
        
        for perm_name in permisos:
            frappe.delete_doc("User Permission", perm_name, ignore_permissions=True)

# ===================================================================
# CREAR/ACTUALIZAR USER PERMISSIONS
# ===================================================================

# Si el portal está activo, asegurar que exista el User Permission
if doc.usuario_portal_vinculado and doc.estado_portal == "Activo":
    
    email = doc.usuario_portal_vinculado
    
    # Verificar si ya existe el permiso
    existe = frappe.db.exists("User Permission", {
        "user": email,
        "allow": "Ficha_Cliente",
        "for_value": doc.name
    })
    
    if not existe:
        # Crear User Permission
        user_perm = frappe.get_doc({
            "doctype": "User Permission",
            "user": email,
            "allow": "Ficha_Cliente",
            "for_value": doc.name,
            "is_default": 0
        })
        
        user_perm.insert(ignore_permissions=True)