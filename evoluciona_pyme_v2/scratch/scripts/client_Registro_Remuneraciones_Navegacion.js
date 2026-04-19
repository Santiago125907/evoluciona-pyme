// ===================================================================
// CLIENT SCRIPT: Registro_Remuneraciones
// Funciones: Navegación + Calculadora Automática
// ===================================================================

frappe.ui.form.on('Registro_Remuneraciones', {
    
    refresh: function(frm) {
        
        // -----------------------------------------------------
        // PARTE 1: BOTONES DE NAVEGACIÓN (Tu código original)
        // -----------------------------------------------------
        
        // BOTÓN: IR A FICHA CLIENTE
        if (frm.doc.cliente) {
            frm.add_custom_button(__('👤 Ir a Ficha Cliente'), function() {
                frappe.set_route('Form', 'Ficha_Cliente', frm.doc.cliente);
            }).addClass('btn-primary');
        }
        
        // BOTÓN: IR A DECLARACIÓN MENSUAL
        if (frm.doc.cliente && frm.doc.ano && frm.doc.mes) {
            frm.add_custom_button(__('📋 Ir a Declaración'), function() {
                // Buscar Declaracion_Mensual del período
                frappe.call({
                    method: 'frappe.client.get_list',
                    args: {
                        doctype: 'Declaracion_Mensual',
                        filters: {
                            cliente: frm.doc.cliente,
                            ano: parseInt(frm.doc.ano),
                            mes: parseInt(frm.doc.mes)
                        },
                        fields: ['name'],
                        limit_page_length: 1
                    },
                    callback: function(r) {
                        if (r.message && r.message.length > 0) {
                            frappe.set_route('Form', 'Declaracion_Mensual', r.message[0].name);
                        } else {
                            frappe.msgprint({
                                title: 'No encontrado',
                                message: 'No hay Declaración Mensual para este período',
                                indicator: 'orange'
                            });
                        }
                    }
                });
            }).addClass('btn-info');
        }
    },

    // -----------------------------------------------------
    // PARTE 2: CALCULADORA AUTOMÁTICA (Nueva Lógica)
    // Escuchar cambios en los campos de montos
    // -----------------------------------------------------

    total_afp: function(frm) {
        calcular_total_previred(frm);
    },
    
    total_salud: function(frm) {
        calcular_total_previred(frm);
    },
    
    total_seguro_cesantia: function(frm) {
        calcular_total_previred(frm);
    },
    
    total_sis_mutual: function(frm) {
        calcular_total_previred(frm);
    }

});

// ===================================================================
// FUNCIÓN MATEMÁTICA
// ===================================================================
function calcular_total_previred(frm) {
    // Sumamos los 4 campos. Usamos (campo || 0) para que si está vacío sume 0 y no error.
    let suma = (frm.doc.total_afp || 0) + 
               (frm.doc.total_salud || 0) + 
               (frm.doc.total_seguro_cesantia || 0) + 
               (frm.doc.total_sis_mutual || 0);
    
    // Asignar resultado al campo Total
    frm.set_value('total_previred_a_pagar', suma);
}