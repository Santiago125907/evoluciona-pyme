// ===================================================================
// CLIENT SCRIPT: Cobranza_Cliente - Navegación
// ===================================================================

frappe.ui.form.on('Cobranza_Cliente', {
    
    refresh: function(frm) {
        
        // =====================================================
        // BOTÓN: IR A FICHA CLIENTE
        // =====================================================
        if (frm.doc.cliente) {
            frm.add_custom_button(__('👤 Ir a Ficha Cliente'), function() {
                frappe.set_route('Form', 'Ficha_Cliente', frm.doc.cliente);
            }).addClass('btn-primary');
        }
        
        // =====================================================
        // BOTÓN: IR A DECLARACIÓN MENSUAL
        // =====================================================
        if (frm.doc.declaracion_mensual) {
            frm.add_custom_button(__('📋 Ir a Declaración'), function() {
                frappe.set_route('Form', 'Declaracion_Mensual', frm.doc.declaracion_mensual);
            }).addClass('btn-info');
        }
        
        // =====================================================
        // BOTÓN: IR A FACTURA
        // =====================================================
        if (frm.doc.factura_vinculada) {
            frm.add_custom_button(__('🧾 Ver Factura'), function() {
                frappe.set_route('Form', 'Sales Invoice', frm.doc.factura_vinculada);
            }).addClass('btn-success');
        }
        
    } // Fin refresh
});