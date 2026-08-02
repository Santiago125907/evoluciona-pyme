// Copyright (c) 2026, Santiago Romero and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Declaracion_Mensual", {
// 	refresh(frm) {

// 	},
// });


// Migrated from Client Script: Boton
// ===================================================================
// CLIENT SCRIPT: Declaracion_Mensual - Completo
// Versión: 2.0 (Navegación + Postergación)
// ===================================================================

frappe.ui.form.on('Declaracion_Mensual', {
    
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
        // BOTÓN: IR AL F29
        // =====================================================
        if (frm.doc.borrador_f29_vinculado) {
            frm.add_custom_button(__('📊 Ir al F29'), function() {
                frappe.set_route('Form', 'Borrador_F29', frm.doc.borrador_f29_vinculado);
            }).addClass('btn-info');
        }
        
        // =====================================================
        // BOTÓN: IR A COBRANZA
        // =====================================================
        if (frm.doc.cobranza_vinculada) {
            frm.add_custom_button(__('💰 Ir a Cobranza'), function() {
                frappe.set_route('Form', 'Cobranza_Cliente', frm.doc.cobranza_vinculada);
            }).addClass('btn-success');
        }
        
        // =====================================================
        // BOTÓN: PUBLICAR EN APP
        // =====================================================
        if (frm.doc.publicado_portal) {
            frm.add_custom_button(__('✅ Publicado en App'), function() {
                frappe.confirm('¿Quitar esta declaración del portal de la App?', function() {
                    frappe.call({
                        method: 'evoluciona_pyme_v2.evoluciona_pyme_v2.api.publicar_en_portal',
                        args: { doc_name: frm.doc.name },
                        freeze: true, freeze_message: 'Actualizando portal...',
                        callback: function(r) {
                            if (r.message?.status === 'ok') {
                                frappe.show_alert({ message: r.message.message, indicator: 'orange' }, 4);
                                frm.reload_doc();
                            }
                        }
                    });
                });
            }).addClass('btn-success');
        } else {
            frm.add_custom_button(__('📱 Publicar en App'), function() {
                frappe.confirm('¿Publicar esta declaración en la App del cliente? Se enviará una notificación push.', function() {
                    frappe.call({
                        method: 'evoluciona_pyme_v2.evoluciona_pyme_v2.api.publicar_en_portal',
                        args: { doc_name: frm.doc.name },
                        freeze: true, freeze_message: 'Publicando en App...',
                        callback: function(r) {
                            if (r.message?.status === 'ok') {
                                frappe.show_alert({ message: r.message.message, indicator: 'green' }, 4);
                                frm.reload_doc();
                            }
                        }
                    });
                });
            }).addClass('btn-warning');
        }

        // =====================================================
        // BOTÓN: IR A REGISTRO RRHH
        // =====================================================
        if (frm.doc.cliente && frm.doc.ano && frm.doc.mes) {
            frm.add_custom_button(__('👥 Ir a RRHH'), function() {
                // Buscar Registro_Remuneraciones del período
                frappe.call({
                    method: 'frappe.client.get_list',
                    args: {
                        doctype: 'Registro_Remuneraciones',
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
                            frappe.set_route('Form', 'Registro_Remuneraciones', r.message[0].name);
                        } else {
                            frappe.msgprint({
                                title: 'No encontrado',
                                message: 'No hay Registro de Remuneraciones para este período',
                                indicator: 'orange'
                            });
                        }
                    }
                });
            });
        }
        
    }, // Fin refresh
    
    // =================================================
    // EVENTO: Cambio en checkbox postergar_pago_iva
    // =================================================
    postergar_pago_iva: function(frm) {
        
        if (frm.doc.postergar_pago_iva) {
            // MARCAR: Aplicar postergación
            aplicar_postergacion_declaracion(frm);
        } else {
            // DESMARCAR: Quitar postergación
            quitar_postergacion_declaracion(frm);
        }
    }
    
});

// ===================================================================
// FUNCIÓN: Aplicar postergación
// ===================================================================
function aplicar_postergacion_declaracion(frm) {
    
    // Validar que exista F29 vinculado
    if (!frm.doc.borrador_f29_vinculado) {
        frappe.msgprint({
            title: 'No se puede postergar',
            message: 'No hay F29 vinculado a esta declaración',
            indicator: 'red'
        });
        frm.set_value('postergar_pago_iva', 0);
        return;
    }
    
    // Mostrar mensaje de proceso
    frappe.show_alert({
        message: 'Aplicando postergación...',
        indicator: 'blue'
    }, 2);
    
    // Llamar API
    frappe.call({
        method: 'aplicar_postergacion',
        args: {
            declaracion_name: frm.doc.name
        },
        freeze: true,
        freeze_message: 'Aplicando postergación...',
        callback: function(r) {
            if (r.message && r.message.status === 'ok') {
                
                // Actualizar campos
                frm.set_value('monto_iva_postergar', r.message.monto);
                frm.set_value('fecha_vencimiento_postergacion', r.message.fecha_vencimiento);
                frm.set_value('postergacion_vinculada', r.message.postergacion_id);
                
                // Mensaje de éxito
                frappe.msgprint({
                    title: '✅ Postergación Aplicada',
                    message: r.message.message,
                    indicator: 'green'
                });
                
                // Refrescar F29 vinculado
                frappe.show_alert({
                    message: 'Actualizando F29...',
                    indicator: 'blue'
                }, 2);
                
                setTimeout(() => {
                    frm.reload_doc();
                }, 1000);
                
            } else if (r.message && r.message.status === 'error') {
                
                // Error controlado
                frappe.msgprint({
                    title: 'No se puede postergar',
                    message: r.message.message,
                    indicator: 'red'
                });
                
                frm.set_value('postergar_pago_iva', 0);
            }
        },
        error: function(r) {
            console.error('Error en aplicar_postergacion:', r);
            frappe.msgprint({
                title: 'Error',
                message: 'Error al aplicar la postergación',
                indicator: 'red'
            });
            frm.set_value('postergar_pago_iva', 0);
        }
    });
}

// ===================================================================
// FUNCIÓN: Quitar postergación
// ===================================================================
function quitar_postergacion_declaracion(frm) {
    
    frappe.confirm(
        '¿Estás seguro de quitar la postergación? Esto actualizará el F29.',
        function() {
            
            // Mostrar mensaje
            frappe.show_alert({
                message: 'Quitando postergación...',
                indicator: 'orange'
            }, 2);
            
            // Llamar API
            frappe.call({
                method: 'quitar_postergacion',
                args: {
                    declaracion_name: frm.doc.name
                },
                freeze: true,
                freeze_message: 'Quitando postergación...',
                callback: function(r) {
                    if (r.message && r.message.status === 'ok') {
                        
                        frappe.msgprint({
                            title: 'Postergación Quitada',
                            message: r.message.message,
                            indicator: 'orange'
                        });
                        
                        setTimeout(() => {
                            frm.reload_doc();
                        }, 1000);
                    }
                }
            });
        },
        function() {
            // Si cancela, volver a marcar el checkbox
            frm.set_value('postergar_pago_iva', 1);
        }
    );
}


// ===================================================================
// LIST VIEW: Acciones masivas
// ===================================================================
frappe.listview_settings['Declaracion_Mensual'] = {
    onload: function(listview) {

        // ── Calcular F29 masivo ──────────────────────────────────
        listview.page.add_action_item(__('⚙️ Calcular F29'), function() {
            let docs = listview.get_checked_items(true);
            if (!docs.length) { frappe.msgprint('Selecciona al menos una declaración.'); return; }
            frappe.confirm(
                `¿Calcular F29 para <b>${docs.length}</b> declaración(es)?`,
                function() {
                    let procesadas = 0, errores = 0;
                    let total = docs.length;
                    frappe.show_alert({ message: `Calculando ${total} declaraciones...`, indicator: 'blue' }, 5);

                    function procesar_siguiente(i) {
                        if (i >= total) {
                            frappe.show_alert({ message: `✅ ${procesadas} calculadas, ${errores} errores.`, indicator: procesadas > 0 ? 'green' : 'red' }, 6);
                            listview.refresh();
                            return;
                        }
                        let nombre = docs[i];
                        // Obtener el borrador f29 vinculado
                        frappe.db.get_value('Declaracion_Mensual', nombre, 'borrador_f29_vinculado').then(r => {
                            let f29 = r.message && r.message.borrador_f29_vinculado;
                            if (!f29) { errores++; procesar_siguiente(i + 1); return; }
                            frappe.call({
                                method: 'evoluciona_pyme_v2.evoluciona_pyme_v2.api.recalcular_asistente_f29',
                                args: { doc_name: f29 },
                                callback: function(res) {
                                    if (res.message?.status === 'ok') procesadas++;
                                    else errores++;
                                    procesar_siguiente(i + 1);
                                },
                                error: function() { errores++; procesar_siguiente(i + 1); }
                            });
                        });
                    }
                    procesar_siguiente(0);
                }
            );
        });

        // ── Publicar en App masivo ───────────────────────────────
        listview.page.add_action_item(__('📱 Publicar en App'), function() {
            let docs = listview.get_checked_items(true);
            if (!docs.length) { frappe.msgprint('Selecciona al menos una declaración.'); return; }
            frappe.confirm(
                `¿Publicar <b>${docs.length}</b> declaración(es) en la App del cliente?`,
                function() {
                    let ok = 0, err = 0, total = docs.length;
                    function procesar_siguiente(i) {
                        if (i >= total) {
                            frappe.show_alert({ message: `📱 ${ok} publicadas, ${err} errores.`, indicator: ok > 0 ? 'green' : 'red' }, 6);
                            listview.refresh();
                            return;
                        }
                        frappe.call({
                            method: 'evoluciona_pyme_v2.evoluciona_pyme_v2.api.publicar_en_portal',
                            args: { doc_name: docs[i] },
                            callback: function(res) {
                                if (res.message?.status === 'ok') ok++;
                                else err++;
                                procesar_siguiente(i + 1);
                            },
                            error: function() { err++; procesar_siguiente(i + 1); }
                        });
                    }
                    procesar_siguiente(0);
                }
            );
        });

        // ── Enviar declaraciones masivo ──────────────────────────
        listview.page.add_action_item(__('📧 Enviar por Email'), function() {
            let docs = listview.get_checked_items(true);
            if (!docs.length) { frappe.msgprint('Selecciona al menos una declaración.'); return; }
            frappe.confirm(
                `¿Enviar <b>${docs.length}</b> declaración(es) por email?`,
                function() {
                    let ok = 0, err = 0, total = docs.length;
                    function procesar_siguiente(i) {
                        if (i >= total) {
                            frappe.show_alert({ message: `📧 ${ok} enviadas, ${err} errores.`, indicator: ok > 0 ? 'green' : 'red' }, 6);
                            listview.refresh();
                            return;
                        }
                        frappe.call({
                            method: 'evoluciona_pyme_v2.evoluciona_pyme_v2.api.enviar_pdf_cliente',
                            args: { declaracion_name: docs[i] },
                            callback: function(res) {
                                if (res.message?.status === 'ok') ok++;
                                else err++;
                                procesar_siguiente(i + 1);
                            },
                            error: function() { err++; procesar_siguiente(i + 1); }
                        });
                    }
                    procesar_siguiente(0);
                }
            );
        });

        // ── Resetear declaraciones masivo ────────────────────────
        listview.page.add_action_item(__('🔄 Resetear a Borrador'), function() {
            let docs = listview.get_checked_items(true);
            if (!docs.length) { frappe.msgprint('Selecciona al menos una declaración.'); return; }
            frappe.confirm(
                `⚠️ ¿Resetear <b>${docs.length}</b> declaración(es) a estado Borrador?<br><small>Esto limpiará validaciones y publicación en portal.</small>`,
                function() {
                    let ok = 0, err = 0, total = docs.length;
                    function procesar_siguiente(i) {
                        if (i >= total) {
                            frappe.show_alert({ message: `🔄 ${ok} reseteadas, ${err} errores.`, indicator: ok > 0 ? 'orange' : 'red' }, 6);
                            listview.refresh();
                            return;
                        }
                        frappe.call({
                            method: 'evoluciona_pyme_v2.evoluciona_pyme_v2.api.resetear_declaracion',
                            args: { doc_name: docs[i] },
                            callback: function(res) {
                                if (res.message?.status === 'ok') ok++;
                                else err++;
                                procesar_siguiente(i + 1);
                            },
                            error: function() { err++; procesar_siguiente(i + 1); }
                        });
                    }
                    procesar_siguiente(0);
                }
            );
        });
    }
};