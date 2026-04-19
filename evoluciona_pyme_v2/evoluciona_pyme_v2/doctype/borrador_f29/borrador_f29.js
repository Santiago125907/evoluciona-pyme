// Copyright (c) 2026, Santiago Romero and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Borrador_F29", {
// 	refresh(frm) {

// 	},
// });


// Migrated from Client Script: Borrador_F29
// ===================================================================
// CLIENT SCRIPT PARA: Borrador_F29
// Versión: 6.0 (Con postergación de IVA integrada)
// ===================================================================

// ===================================================================
// FUNCIÓN: Formatear número con puntos (estilo chileno)
// ===================================================================
function formatear_numero_chileno(numero) {
    if (!numero || numero === 0) return '0';
    // Convertir a número y formatear con puntos
    let num = parseFloat(numero);
    return num.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ".");
}

// ===================================================================
// FUNCIÓN: Quitar formato y obtener número puro
// ===================================================================
function limpiar_numero(texto) {
    if (!texto) return 0;
    // Remover todo excepto números
    let limpio = texto.toString().replace(/[^0-9]/g, '');
    return parseFloat(limpio) || 0;
}

// ===================================================================
// FUNCIÓN GLOBAL: Agregar eventos a los inputs
// ===================================================================
function agregar_eventos_inputs() {
    const inputs = document.querySelectorAll('input.monto-field:not([readonly])');
    
    console.log('Agregando eventos a ' + inputs.length + ' campos editables');
    
    inputs.forEach(input => {
        // Evento: al hacer foco, quitar formato
        input.addEventListener('focus', function() {
            let monto_real = limpiar_numero(this.value);
            this.value = monto_real;
            this.select(); // Seleccionar todo el texto
        });
        
        // Evento: al perder foco, formatear y guardar
        input.addEventListener('blur', function() {
            let monto_real = limpiar_numero(this.value);
            this.value = formatear_numero_chileno(monto_real);
            this.setAttribute('data-monto-real', monto_real);
            window.actualizar_monto_f29(this);
        });
        
        // Evento: Enter
        input.addEventListener('keyup', function(e) {
            if (e.key === 'Enter') {
                this.blur(); // Dispara el blur que formatea y guarda
            }
        });
    });
}

// ===================================================================
// FUNCIÓN GLOBAL: Actualizar monto desde el HTML
// ===================================================================
window.actualizar_monto_f29 = function(input) {
    try {
        console.log('Iniciando actualizacion de monto...');
        
        let tabla_name = input.getAttribute('data-tabla');
        let idx = parseInt(input.getAttribute('data-idx'));
        let nuevo_monto = limpiar_numero(input.value);
        
        console.log('Datos: tabla=' + tabla_name + ', idx=' + idx + ', monto=' + nuevo_monto);
        
        if (!window.current_f29_form) {
            console.error('No se encontro el formulario actual');
            return;
        }
        
        let frm = window.current_f29_form;
        
        let tabla = frm.doc[tabla_name];
        if (!tabla) {
            console.error('No se encontro la tabla: ' + tabla_name);
            return;
        }
        
        let row = tabla.find(r => r.idx === idx);
        if (!row) {
            console.error('No se encontro la fila con idx: ' + idx);
            return;
        }
        
        console.log('Fila encontrada');
        console.log('Monto anterior: ' + row.monto + ' - Monto nuevo: ' + nuevo_monto);
        
        row.monto = nuevo_monto;
        
        frm.doc.__unsaved = 1;
        
        try {
            let grid_row = frm.fields_dict[tabla_name].grid.grid_rows_by_docname[row.name];
            if (grid_row) {
                grid_row.doc.monto = nuevo_monto;
                console.log('Grid actualizado');
            }
        } catch (e) {
            console.warn('No se pudo actualizar grid:', e);
        }
        
        console.log('Recalculando subtotales...');
        recalcular_subtotales_instantaneos(frm);
        
        frm.dirty();
        
        console.log('EXITO: ' + tabla_name + '[' + idx + '].monto = ' + nuevo_monto);
        
        frappe.show_alert({
            message: 'Actualizado: $' + formatear_numero_chileno(nuevo_monto),
            indicator: 'green'
        }, 1);
        
    } catch (error) {
        console.error('Error al actualizar monto:', error);
        frappe.show_alert({
            message: 'Error al actualizar el monto',
            indicator: 'red'
        }, 3);
    }
};

// ===================================================================
// EVENTOS DEL FORMULARIO
// ===================================================================
frappe.ui.form.on('Borrador_F29', {
    
    refresh: function(frm) {
        if (frm.is_new()) return;
        
        // Renderizar HTML del F29
        if (frm.doc.html_renderizado) {
            frm.fields_dict.vista_f29.$wrapper.html(frm.doc.html_renderizado);
            
            window.current_f29_form = frm;
            
            setTimeout(() => {
                agregar_eventos_inputs();
            }, 100);
        }
        
        // =====================================================
        // BOTÓN: CALCULAR/RELLENAR AUTOMÁTICO
        // =====================================================
        frm.add_custom_button(__('Calcular/Rellenar Automático'), function() {
            frappe.confirm(
                'Esto calculará automáticamente los montos desde los documentos tributarios. Los campos "Calculados" se actualizarán. ¿Continuar?',
                function() {
                    frappe.show_alert({
                        message: __('Calculando F29...'),
                        indicator: 'blue'
                    }, 3);
                    
                    frappe.call({
                        method: 'recalcular_asistente_f29',
                        args: { doc_name: frm.doc.name },
                        freeze: true,
                        freeze_message: __('Calculando F29 desde documentos...'),
                        callback: function(r) {
                            if (r.message && r.message.status === "ok") {
                                frappe.show_alert({
                                    message: r.message.message,
                                    indicator: 'green'
                                }, 5);
                                frm.reload_doc();
                            } else if (r.message && r.message.status === "error") {
                                frappe.msgprint({
                                    title: __('Error en el Cálculo'),
                                    message: r.message.message,
                                    indicator: 'red'
                                });
                            }
                        },
                        error: function(r) {
                            console.error('Error completo:', r);
                            frappe.msgprint({
                                title: __('Error en el Cálculo'),
                                message: __('Error al calcular F29. Revisa el registro de errores.'),
                                indicator: 'red'
                            });
                        }
                    });
                }
            );
        }).addClass('btn-primary');
        
        // =====================================================
        // BOTÓN: REPROCESAR DOCUMENTOS
        // =====================================================
        frm.add_custom_button(__('🔄 Reprocesar Documentos'), function() {
            
            let d = new frappe.ui.Dialog({
                title: 'Reprocesar Documentos Tributarios',
                fields: [
                    {
                        label: 'Selecciona qué reprocesar:',
                        fieldname: 'tipo_reproceso',
                        fieldtype: 'Select',
                        options: [
                            '',
                            'Libro de Ingresos (Ventas)',
                            'Libro de Egresos (Compras)',
                            'Registro de Remuneraciones (RRHH)',
                            'Todo (Ingresos + Egresos + RRHH)'
                        ],
                        reqd: 1
                    },
                    {
                        fieldtype: 'HTML',
                        options: `
                            <div style="padding: 10px; background: #fff3cd; border-radius: 4px; margin-top: 10px;">
                                <strong>⚠️ Importante:</strong><br>
                                Esto enviará una solicitud a n8n para volver a obtener los documentos 
                                desde el SII/fuente externa y actualizar los registros.
                            </div>
                        `
                    }
                ],
                primary_action_label: 'Reprocesar',
                primary_action: function(values) {
                    
                    if (!values.tipo_reproceso) {
                        frappe.msgprint('Selecciona qué reprocesar');
                        return;
                    }
                    
                    d.hide();
                    
                    // Preparar payload para n8n
                    let payload = {
                        accion: 'reprocesar',
                        cliente_rut: frm.doc.cliente,
                        ano: frm.doc.ano,
                        mes: frm.doc.mes,
                        tipo_reproceso: values.tipo_reproceso,
                        timestamp: new Date().toISOString()
                    };
                    
                    frappe.show_alert({
                        message: 'Enviando solicitud de reproceso...',
                        indicator: 'blue'
                    }, 3);
                    
                    // Webhook de n8n (configurable)
                    const N8N_WEBHOOK_REPROCESO = 'https://n8n-n8n.6pe7e2.easypanel.host/webhook/reprocesar-documentos';
                    
                    fetch(N8N_WEBHOOK_REPROCESO, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(payload)
                    })
                    .then(response => response.json())
                    .then(data => {
                        frappe.msgprint({
                            title: 'Reproceso Iniciado',
                            message: `
                                <div style="padding: 15px;">
                                    <p>✅ Solicitud enviada exitosamente a n8n</p>
                                    <p><strong>Tipo:</strong> ${values.tipo_reproceso}</p>
                                    <p><strong>Período:</strong> ${frm.doc.mes}/${frm.doc.ano}</p>
                                    <hr>
                                    <p style="font-size: 12px; color: #666;">
                                        El reproceso puede tardar algunos minutos. 
                                        Actualiza el F29 después para ver los nuevos datos.
                                    </p>
                                </div>
                            `,
                            indicator: 'green',
                            primary_action: {
                                label: 'Actualizar F29 Ahora',
                                action: function() {
                                    frm.reload_doc();
                                }
                            }
                        });
                    })
                    .catch(error => {
                        console.error('Error en reproceso:', error);
                        frappe.msgprint({
                            title: 'Error',
                            message: 'No se pudo conectar con n8n. Verifica la configuración del webhook.',
                            indicator: 'red'
                        });
                    });
                }
            });
            
            d.show();
            
        }).addClass('btn-warning');
        
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
        if (frm.doc.declaracion_mensual_vinculada) {
            frm.add_custom_button(__('📋 Ir a Declaración Mensual'), function() {
                frappe.set_route('Form', 'Declaracion_Mensual', frm.doc.declaracion_mensual_vinculada);
            }).addClass('btn-info');
        }
        
    }, // Fin refresh
    
    // =====================================================
    // ANTES DE GUARDAR: Sincronizar postergación del HTML
    // =====================================================
    before_save: function(frm) {
        // Obtener valores del HTML
        const checkbox = document.getElementById('checkbox-postergar-iva');
        const input = document.getElementById('input-monto-postergacion');
        
        if (checkbox && input) {
            // Sincronizar checkbox
            frm.set_value('postergar_iva_periodo', checkbox.checked ? 1 : 0);
            
            // Sincronizar monto
            if (checkbox.checked) {
                let monto = limpiar_numero(input.value);
                frm.set_value('postergacion_del_periodo', monto);
            } else {
                frm.set_value('postergacion_del_periodo', 0);
            }
            
            console.log('Postergación sincronizada:', {
                checkbox: checkbox.checked,
                monto: frm.doc.postergacion_del_periodo
            });
        }
    }
});

// ===================================================================
// FUNCIÓN: Recalcular subtotales instantáneamente
// ===================================================================
function recalcular_subtotales_instantaneos(frm) {
    const CODIGO_POSTERGACION_IVA = '771';
    
    let subtotal_debitos = 0;
    let subtotal_creditos = 0;
    let subtotal_postergacion = 0;
    let subtotal_impuestos = 0;
    
    if (frm.doc.tabla_debitos) {
        frm.doc.tabla_debitos.forEach(linea => {
            let monto = flt(linea.monto);
            if (linea.tipo_operacion_subtotal === 'Resta') {
                subtotal_debitos -= monto;
            } else if (linea.tipo_operacion_subtotal !== 'Informativo') {
                subtotal_debitos += monto;
            }
        });
    }
    
    if (frm.doc.tabla_creditos) {
        frm.doc.tabla_creditos.forEach(linea => {
            let monto = flt(linea.monto);
            if (linea.codigo_f29 == CODIGO_POSTERGACION_IVA) {
                subtotal_postergacion += monto;
            } else {
                if (linea.tipo_operacion_subtotal === 'Resta') {
                    subtotal_creditos -= monto;
                } else if (linea.tipo_operacion_subtotal !== 'Informativo') {
                    subtotal_creditos += monto;
                }
            }
        });
    }
    
    if (frm.doc.tabla_impuestos) {
        frm.doc.tabla_impuestos.forEach(linea => {
            let monto = flt(linea.monto);
            if (linea.tipo_operacion_subtotal === 'Resta') {
                subtotal_impuestos -= monto;
            } else if (linea.tipo_operacion_subtotal !== 'Informativo') {
                subtotal_impuestos += monto;
            }
        });
    }
    
    let iva_resultante = subtotal_debitos - subtotal_creditos;
    let iva_determinado = iva_resultante > 0 ? iva_resultante : 0;
    let remanente = iva_resultante < 0 ? Math.abs(iva_resultante) : 0;
    
    // Obtener postergación del HTML
    let postergacion_periodo = 0;
    const input_postergacion = document.getElementById('input-monto-postergacion');
    if (input_postergacion) {
        postergacion_periodo = limpiar_numero(input_postergacion.value);
    }
    
    let total_pagar = Math.max(0, iva_determinado - postergacion_periodo + subtotal_impuestos);
    
    // Actualizar elementos HTML con formato
    actualizar_elemento_html('subtotal-debitos', subtotal_debitos);
    actualizar_elemento_html('subtotal-creditos', subtotal_creditos);
    actualizar_elemento_html('subtotal-impuestos', subtotal_impuestos);
    actualizar_elemento_html('total-pagar', total_pagar);
    
    actualizar_elemento_html('resumen-debitos', subtotal_debitos);
    actualizar_elemento_html('resumen-creditos', subtotal_creditos);
    actualizar_elemento_html('resumen-iva-determinado', iva_determinado);
    actualizar_elemento_html('resumen-remanente', remanente);
    actualizar_elemento_html('resumen-postergacion', subtotal_postergacion);
    actualizar_elemento_html('resumen-impuestos', subtotal_impuestos);
    
    // Actualizar campos del documento
    frm.doc.subtotal_debitos = subtotal_debitos;
    frm.doc.subtotal_creditos = subtotal_creditos;
    frm.doc.subtotal_postergacion_iva = subtotal_postergacion;
    frm.doc.subtotal_otros_impuestos = subtotal_impuestos;
    frm.doc.impuesto_determinado = iva_determinado;
    frm.doc.remanente_mes_siguiente = remanente;
    frm.doc.total_a_pagar_f29 = total_pagar;
    
    frm.refresh_field('subtotal_debitos');
    frm.refresh_field('subtotal_creditos');
    frm.refresh_field('subtotal_postergacion_iva');
    frm.refresh_field('subtotal_otros_impuestos');
    frm.refresh_field('impuesto_determinado');
    frm.refresh_field('remanente_mes_siguiente');
    frm.refresh_field('total_a_pagar_f29');
}

// ===================================================================
// FUNCIÓN: Actualizar elemento HTML
// ===================================================================
function actualizar_elemento_html(elemento_id, valor) {
    let elemento = document.getElementById(elemento_id);
    if (elemento) {
        elemento.textContent = '$' + formatear_numero_chileno(valor);
    }
}

// Migrated from Client Script: Borrador_F29
// ===================================================================
// CLIENT SCRIPT PARA: Borrador_F29
// Versión: 6.0 (Con postergación de IVA integrada)
// ===================================================================

// ===================================================================
// FUNCIÓN: Formatear número con puntos (estilo chileno)
// ===================================================================
function formatear_numero_chileno(numero) {
    if (!numero || numero === 0) return '0';
    // Convertir a número y formatear con puntos
    let num = parseFloat(numero);
    return num.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ".");
}

// ===================================================================
// FUNCIÓN: Quitar formato y obtener número puro
// ===================================================================
function limpiar_numero(texto) {
    if (!texto) return 0;
    // Remover todo excepto números
    let limpio = texto.toString().replace(/[^0-9]/g, '');
    return parseFloat(limpio) || 0;
}

// ===================================================================
// FUNCIÓN GLOBAL: Agregar eventos a los inputs
// ===================================================================
function agregar_eventos_inputs() {
    const inputs = document.querySelectorAll('input.monto-field:not([readonly])');
    
    console.log('Agregando eventos a ' + inputs.length + ' campos editables');
    
    inputs.forEach(input => {
        // Evento: al hacer foco, quitar formato
        input.addEventListener('focus', function() {
            let monto_real = limpiar_numero(this.value);
            this.value = monto_real;
            this.select(); // Seleccionar todo el texto
        });
        
        // Evento: al perder foco, formatear y guardar
        input.addEventListener('blur', function() {
            let monto_real = limpiar_numero(this.value);
            this.value = formatear_numero_chileno(monto_real);
            this.setAttribute('data-monto-real', monto_real);
            window.actualizar_monto_f29(this);
        });
        
        // Evento: Enter
        input.addEventListener('keyup', function(e) {
            if (e.key === 'Enter') {
                this.blur(); // Dispara el blur que formatea y guarda
            }
        });
    });
}

// ===================================================================
// FUNCIÓN GLOBAL: Actualizar monto desde el HTML
// ===================================================================
window.actualizar_monto_f29 = function(input) {
    try {
        console.log('Iniciando actualizacion de monto...');
        
        let tabla_name = input.getAttribute('data-tabla');
        let idx = parseInt(input.getAttribute('data-idx'));
        let nuevo_monto = limpiar_numero(input.value);
        
        console.log('Datos: tabla=' + tabla_name + ', idx=' + idx + ', monto=' + nuevo_monto);
        
        if (!window.current_f29_form) {
            console.error('No se encontro el formulario actual');
            return;
        }
        
        let frm = window.current_f29_form;
        
        let tabla = frm.doc[tabla_name];
        if (!tabla) {
            console.error('No se encontro la tabla: ' + tabla_name);
            return;
        }
        
        let row = tabla.find(r => r.idx === idx);
        if (!row) {
            console.error('No se encontro la fila con idx: ' + idx);
            return;
        }
        
        console.log('Fila encontrada');
        console.log('Monto anterior: ' + row.monto + ' - Monto nuevo: ' + nuevo_monto);
        
        row.monto = nuevo_monto;
        
        frm.doc.__unsaved = 1;
        
        try {
            let grid_row = frm.fields_dict[tabla_name].grid.grid_rows_by_docname[row.name];
            if (grid_row) {
                grid_row.doc.monto = nuevo_monto;
                console.log('Grid actualizado');
            }
        } catch (e) {
            console.warn('No se pudo actualizar grid:', e);
        }
        
        console.log('Recalculando subtotales...');
        recalcular_subtotales_instantaneos(frm);
        
        frm.dirty();
        
        console.log('EXITO: ' + tabla_name + '[' + idx + '].monto = ' + nuevo_monto);
        
        frappe.show_alert({
            message: 'Actualizado: $' + formatear_numero_chileno(nuevo_monto),
            indicator: 'green'
        }, 1);
        
    } catch (error) {
        console.error('Error al actualizar monto:', error);
        frappe.show_alert({
            message: 'Error al actualizar el monto',
            indicator: 'red'
        }, 3);
    }
};

// ===================================================================
// EVENTOS DEL FORMULARIO
// ===================================================================
frappe.ui.form.on('Borrador_F29', {
    
    refresh: function(frm) {
        if (frm.is_new()) return;
        
        // Renderizar HTML del F29
        if (frm.doc.html_renderizado) {
            frm.fields_dict.vista_f29.$wrapper.html(frm.doc.html_renderizado);
            
            window.current_f29_form = frm;
            
            setTimeout(() => {
                agregar_eventos_inputs();
            }, 100);
        }
        
        // =====================================================
        // BOTÓN: CALCULAR/RELLENAR AUTOMÁTICO
        // =====================================================
        frm.add_custom_button(__('Calcular/Rellenar Automático'), function() {
            frappe.confirm(
                'Esto calculará automáticamente los montos desde los documentos tributarios. Los campos "Calculados" se actualizarán. ¿Continuar?',
                function() {
                    frappe.show_alert({
                        message: __('Calculando F29...'),
                        indicator: 'blue'
                    }, 3);
                    
                    frappe.call({
                        method: 'recalcular_asistente_f29',
                        args: { doc_name: frm.doc.name },
                        freeze: true,
                        freeze_message: __('Calculando F29 desde documentos...'),
                        callback: function(r) {
                            if (r.message && r.message.status === "ok") {
                                frappe.show_alert({
                                    message: r.message.message,
                                    indicator: 'green'
                                }, 5);
                                frm.reload_doc();
                            } else if (r.message && r.message.status === "error") {
                                frappe.msgprint({
                                    title: __('Error en el Cálculo'),
                                    message: r.message.message,
                                    indicator: 'red'
                                });
                            }
                        },
                        error: function(r) {
                            console.error('Error completo:', r);
                            frappe.msgprint({
                                title: __('Error en el Cálculo'),
                                message: __('Error al calcular F29. Revisa el registro de errores.'),
                                indicator: 'red'
                            });
                        }
                    });
                }
            );
        }).addClass('btn-primary');
        
        // =====================================================
        // BOTÓN: REPROCESAR DOCUMENTOS
        // =====================================================
        frm.add_custom_button(__('🔄 Reprocesar Documentos'), function() {
            
            let d = new frappe.ui.Dialog({
                title: 'Reprocesar Documentos Tributarios',
                fields: [
                    {
                        label: 'Selecciona qué reprocesar:',
                        fieldname: 'tipo_reproceso',
                        fieldtype: 'Select',
                        options: [
                            '',
                            'Libro de Ingresos (Ventas)',
                            'Libro de Egresos (Compras)',
                            'Registro de Remuneraciones (RRHH)',
                            'Todo (Ingresos + Egresos + RRHH)'
                        ],
                        reqd: 1
                    },
                    {
                        fieldtype: 'HTML',
                        options: `
                            <div style="padding: 10px; background: #fff3cd; border-radius: 4px; margin-top: 10px;">
                                <strong>⚠️ Importante:</strong><br>
                                Esto enviará una solicitud a n8n para volver a obtener los documentos 
                                desde el SII/fuente externa y actualizar los registros.
                            </div>
                        `
                    }
                ],
                primary_action_label: 'Reprocesar',
                primary_action: function(values) {
                    
                    if (!values.tipo_reproceso) {
                        frappe.msgprint('Selecciona qué reprocesar');
                        return;
                    }
                    
                    d.hide();
                    
                    // Preparar payload para n8n
                    let payload = {
                        accion: 'reprocesar',
                        cliente_rut: frm.doc.cliente,
                        ano: frm.doc.ano,
                        mes: frm.doc.mes,
                        tipo_reproceso: values.tipo_reproceso,
                        timestamp: new Date().toISOString()
                    };
                    
                    frappe.show_alert({
                        message: 'Enviando solicitud de reproceso...',
                        indicator: 'blue'
                    }, 3);
                    
                    // Webhook de n8n (configurable)
                    const N8N_WEBHOOK_REPROCESO = 'https://n8n-n8n.6pe7e2.easypanel.host/webhook/reprocesar-documentos';
                    
                    fetch(N8N_WEBHOOK_REPROCESO, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(payload)
                    })
                    .then(response => response.json())
                    .then(data => {
                        frappe.msgprint({
                            title: 'Reproceso Iniciado',
                            message: `
                                <div style="padding: 15px;">
                                    <p>✅ Solicitud enviada exitosamente a n8n</p>
                                    <p><strong>Tipo:</strong> ${values.tipo_reproceso}</p>
                                    <p><strong>Período:</strong> ${frm.doc.mes}/${frm.doc.ano}</p>
                                    <hr>
                                    <p style="font-size: 12px; color: #666;">
                                        El reproceso puede tardar algunos minutos. 
                                        Actualiza el F29 después para ver los nuevos datos.
                                    </p>
                                </div>
                            `,
                            indicator: 'green',
                            primary_action: {
                                label: 'Actualizar F29 Ahora',
                                action: function() {
                                    frm.reload_doc();
                                }
                            }
                        });
                    })
                    .catch(error => {
                        console.error('Error en reproceso:', error);
                        frappe.msgprint({
                            title: 'Error',
                            message: 'No se pudo conectar con n8n. Verifica la configuración del webhook.',
                            indicator: 'red'
                        });
                    });
                }
            });
            
            d.show();
            
        }).addClass('btn-warning');
        
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
        if (frm.doc.declaracion_mensual_vinculada) {
            frm.add_custom_button(__('📋 Ir a Declaración Mensual'), function() {
                frappe.set_route('Form', 'Declaracion_Mensual', frm.doc.declaracion_mensual_vinculada);
            }).addClass('btn-info');
        }
        
    }, // Fin refresh
    
    // =====================================================
    // ANTES DE GUARDAR: Sincronizar postergación del HTML
    // =====================================================
    before_save: function(frm) {
        // Obtener valores del HTML
        const checkbox = document.getElementById('checkbox-postergar-iva');
        const input = document.getElementById('input-monto-postergacion');
        
        if (checkbox && input) {
            // Sincronizar checkbox
            frm.set_value('postergar_iva_periodo', checkbox.checked ? 1 : 0);
            
            // Sincronizar monto
            if (checkbox.checked) {
                let monto = limpiar_numero(input.value);
                frm.set_value('postergacion_del_periodo', monto);
            } else {
                frm.set_value('postergacion_del_periodo', 0);
            }
            
            console.log('Postergación sincronizada:', {
                checkbox: checkbox.checked,
                monto: frm.doc.postergacion_del_periodo
            });
        }
    }
});

// ===================================================================
// FUNCIÓN: Recalcular subtotales instantáneamente
// ===================================================================
function recalcular_subtotales_instantaneos(frm) {
    const CODIGO_POSTERGACION_IVA = '771';
    
    let subtotal_debitos = 0;
    let subtotal_creditos = 0;
    let subtotal_postergacion = 0;
    let subtotal_impuestos = 0;
    
    if (frm.doc.tabla_debitos) {
        frm.doc.tabla_debitos.forEach(linea => {
            let monto = flt(linea.monto);
            if (linea.tipo_operacion_subtotal === 'Resta') {
                subtotal_debitos -= monto;
            } else if (linea.tipo_operacion_subtotal !== 'Informativo') {
                subtotal_debitos += monto;
            }
        });
    }
    
    if (frm.doc.tabla_creditos) {
        frm.doc.tabla_creditos.forEach(linea => {
            let monto = flt(linea.monto);
            if (linea.codigo_f29 == CODIGO_POSTERGACION_IVA) {
                subtotal_postergacion += monto;
            } else {
                if (linea.tipo_operacion_subtotal === 'Resta') {
                    subtotal_creditos -= monto;
                } else if (linea.tipo_operacion_subtotal !== 'Informativo') {
                    subtotal_creditos += monto;
                }
            }
        });
    }
    
    if (frm.doc.tabla_impuestos) {
        frm.doc.tabla_impuestos.forEach(linea => {
            let monto = flt(linea.monto);
            if (linea.tipo_operacion_subtotal === 'Resta') {
                subtotal_impuestos -= monto;
            } else if (linea.tipo_operacion_subtotal !== 'Informativo') {
                subtotal_impuestos += monto;
            }
        });
    }
    
    let iva_resultante = subtotal_debitos - subtotal_creditos;
    let iva_determinado = iva_resultante > 0 ? iva_resultante : 0;
    let remanente = iva_resultante < 0 ? Math.abs(iva_resultante) : 0;
    
    // Obtener postergación del HTML
    let postergacion_periodo = 0;
    const input_postergacion = document.getElementById('input-monto-postergacion');
    if (input_postergacion) {
        postergacion_periodo = limpiar_numero(input_postergacion.value);
    }
    
    let total_pagar = Math.max(0, iva_determinado - postergacion_periodo + subtotal_impuestos);
    
    // Actualizar elementos HTML con formato
    actualizar_elemento_html('subtotal-debitos', subtotal_debitos);
    actualizar_elemento_html('subtotal-creditos', subtotal_creditos);
    actualizar_elemento_html('subtotal-impuestos', subtotal_impuestos);
    actualizar_elemento_html('total-pagar', total_pagar);
    
    actualizar_elemento_html('resumen-debitos', subtotal_debitos);
    actualizar_elemento_html('resumen-creditos', subtotal_creditos);
    actualizar_elemento_html('resumen-iva-determinado', iva_determinado);
    actualizar_elemento_html('resumen-remanente', remanente);
    actualizar_elemento_html('resumen-postergacion', subtotal_postergacion);
    actualizar_elemento_html('resumen-impuestos', subtotal_impuestos);
    
    // Actualizar campos del documento
    frm.doc.subtotal_debitos = subtotal_debitos;
    frm.doc.subtotal_creditos = subtotal_creditos;
    frm.doc.subtotal_postergacion_iva = subtotal_postergacion;
    frm.doc.subtotal_otros_impuestos = subtotal_impuestos;
    frm.doc.impuesto_determinado = iva_determinado;
    frm.doc.remanente_mes_siguiente = remanente;
    frm.doc.total_a_pagar_f29 = total_pagar;
    
    frm.refresh_field('subtotal_debitos');
    frm.refresh_field('subtotal_creditos');
    frm.refresh_field('subtotal_postergacion_iva');
    frm.refresh_field('subtotal_otros_impuestos');
    frm.refresh_field('impuesto_determinado');
    frm.refresh_field('remanente_mes_siguiente');
    frm.refresh_field('total_a_pagar_f29');
}

// ===================================================================
// FUNCIÓN: Actualizar elemento HTML
// ===================================================================
function actualizar_elemento_html(elemento_id, valor) {
    let elemento = document.getElementById(elemento_id);
    if (elemento) {
        elemento.textContent = '$' + formatear_numero_chileno(valor);
    }
}