# ================================================================
# SERVER SCRIPT: Cobranza_Cliente - Before Save
# ================================================================
# Tipo: DocType Event
# Reference DocType: Cobranza_Cliente
# Event: Before Save
# ================================================================

# =====================================================
# FUNCIÓN: CALCULAR DÍAS PARA VENCER
# =====================================================
def calcular_dias_vencimiento(doc):
    """
    Calcula días para vencer y actualiza estado si está vencido
    """
    
    if not doc.fecha_vencimiento:
        return
    
    # Obtener fecha actual
    hoy = frappe.utils.getdate(frappe.utils.nowdate())
    fecha_venc = frappe.utils.getdate(doc.fecha_vencimiento)
    
    # Calcular diferencia en días
    diferencia = frappe.utils.date_diff(fecha_venc, hoy)
    
    # Actualizar campo
    doc.dias_para_vencer = int(diferencia)
    
    # Si está vencido y no está pagado, cambiar estado
    if diferencia < 0 and doc.estado_cobranza not in ["Pagado", "Anulado"]:
        doc.estado_cobranza = "Vencido"


# =====================================================
# EJECUCIÓN PRINCIPAL
# =====================================================

calcular_dias_vencimiento(doc)