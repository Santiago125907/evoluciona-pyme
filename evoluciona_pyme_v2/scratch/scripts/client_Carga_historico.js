// ===================================================================
// CLIENT SCRIPT: Ficha_Cliente
// Versión: 4.2 - Con Facturación De Facto + Webhooks n8n + Visualización PDF Drive
// ===================================================================

frappe.ui.form.on('Ficha_Cliente', {
    
    refresh: function(frm) {
        
        // =====================================================
        // CONFIGURACIÓN DE WEBHOOKS
        // =====================================================

        // Webhook de Facturación
        

        // Validación de documento nuevo
        if (frm.doc.__islocal) {
            return;
        }

        // Botón: Actualizar desde SII
        frm.add_custom_button(__('🔄 Actualizar desde SII'), function() {
            
            // Validar que tenga RUT
            if (!frm.doc.rut_cliente) {
                frappe.msgprint({
                    title: 'RUT requerido',
                    message: 'Debes ingresar un RUT para consultar al SII',
                    indicator: 'orange'
                });
                return;
            }
            
            // Confirmación
            frappe.confirm(
                `¿Consultar datos del RUT <strong>${frm.doc.rut_cliente}</strong> en el SII?<br><br>
                <small>Se actualizarán: Razón Social, Giro, Dirección, etc.</small>`,
                function() {
                    
                    // Freeze UI
                    frappe.dom.freeze('🔍 Consultando al SII...<br><small>Por favor espera</small>');
                    
                    // Webhook n8n SII
                    
                    
                    frappe.db.get_single_value('Configuracion_n8n', 'webhook_sii').then(N8N_WEBHOOK_SII => { fetch(N8N_WEBHOOK_SII, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            rut: frm.doc.rut_cliente,
                            cliente_id: frm.doc.name
                        })
                    })
                    .then(response => {
                        if (!response.ok) throw new Error('Error en respuesta del SII');
                        return response.json();
                    })
                    .then(data => {
                        
                        frappe.dom.unfreeze();
                        
                        if (data.success) {
                            // Actualizar campos
                            frm.set_value('razon_social', data.razon_social);
                            frm.set_value('giro', data.giro);
                            frm.set_value('direccion_fiscal', data.direccion);
                            // ... más campos
                            
                            frappe.show_alert({
                                message: '✅ Datos actualizados desde el SII',
                                indicator: 'green'
                            }, 5);
                            
                        } else {
                            frappe.msgprint({
                                title: 'No encontrado',
                                message: data.message || 'No se encontraron datos para este RUT',
                                indicator: 'orange'
                            });
                        }
                    })
                    .catch(error => {
                        frappe.dom.unfreeze();
                        frappe.msgprint({
                            title: 'Error',
                            message: 'No se pudo consultar al SII: ' + error.message,
                            indicator: 'red'
                        });
                        }); // Cierra el then
                    });
                }
            );
            
        }).addClass('btn-primary');

    
        // =====================================================
        // BOTÓN: CARGA HISTÓRICA
        // =====================================================
        frm.add_custom_button(__('🚀 Iniciar Carga Histórica'), function() {
            
            let d = new frappe.ui.Dialog({
                title: __('Seleccionar Período de Carga'),
                fields: [
                    {
                        label: 'Año Inicio',
                        fieldname: 'ano_inicio',
                        fieldtype: 'Select',
                        options: ['2023', '2024', '2025', '2026'],
                        reqd: 1
                    },
                    {
                        label: 'Mes Inicio',
                        fieldname: 'mes_inicio',
                        fieldtype: 'Select',
                        options: '1\n2\n3\n4\n5\n6\n7\n8\n9\n10\n11\n12',
                        reqd: 1
                    },
                    {
                        label: 'Año Fin',
                        fieldname: 'ano_fin',
                        fieldtype: 'Select',
                        options: ['2023', '2024', '2025', '2026'],
                        reqd: 1
                    },
                    {
                        label: 'Mes Fin',
                        fieldname: 'mes_fin',
                        fieldtype: 'Select',
                        options: '1\n2\n3\n4\n5\n6\n7\n8\n9\n10\n11\n12',
                        reqd: 1
                    }
                ],
                primary_action_label: __('Iniciar Carga'),
                primary_action: function(values) {
                    
                    if (parseInt(values.ano_inicio) > parseInt(values.ano_fin) || 
                        (parseInt(values.ano_inicio) === parseInt(values.ano_fin) && 
                         parseInt(values.mes_inicio) > parseInt(values.mes_fin))) {
                        frappe.msgprint({
                            title: __('Error de Validación'),
                            message: __('La fecha de inicio debe ser anterior o igual a la fecha de fin.'),
                            indicator: 'red'
                        });
                        return false;
                    }
                    
                    let data_para_n8n = {
                        rut_cliente: frm.doc.rut_cliente,
                        mes_inicio: values.mes_inicio,
                        ano_inicio: values.ano_inicio,
                        mes_fin: values.mes_fin,
                        ano_fin: values.ano_fin
                    };

                    d.hide();

                    frappe.show_alert({
                        message: __('Iniciando carga histórica...'),
                        indicator: 'green'
                    }, 5);

                    frappe.db.get_single_value('Configuracion_n8n', 'webhook_carga_historica').then(N8N_WEBHOOK_URL => { fetch(N8N_WEBHOOK_URL, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(data_para_n8n)
                    })
                    .then(response => {
                        if (!response.ok) {
                            throw new Error('Error en la red o n8n no respondió.');
                        }
                        return response.json();
                    })
                    .then(data_de_n8n => {
                        frappe.msgprint({
                            title: __('Éxito'),
                            message: __('La carga histórica se ha iniciado correctamente.'),
                            indicator: 'green'
                        });
                    })
                    .catch(error => {
                        console.error('Error al llamar al Webhook de n8n:', error);
                        frappe.msgprint({
                            title: __('Error de Conexión'),
                            message: __('No se pudo conectar con el servicio de automatización (n8n).'),
                            indicator: 'red'
                        });
                        }); // Cierra el then
                    });
                }
            });

            d.show();
            d.set_value('monto_pagado', monto_sugerido);

        }).addClass('btn-primary');
        
        // =====================================================
        // RENDERIZAR PANEL DE CONTROL MENSUAL
        // =====================================================
        renderizar_panel_declaraciones(frm);
        
        // =====================================================
        // RENDERIZAR PANEL DE COBRANZA
        // =====================================================
        renderizar_panel_cobranza(frm);
        
    } // Fin refresh
});

// ===================================================================
// FUNCIÓN: RENDERIZAR PANEL DE DECLARACIONES
// ===================================================================
function renderizar_panel_declaraciones(frm) {
    
    const panel_wrapper = $(frm.fields_dict['panel_control_mensual'].wrapper);
    panel_wrapper.html('<div style="text-align:center; padding:20px;"><i class="fa fa-spinner fa-spin"></i> Cargando declaraciones...</div>');

    frappe.call({
        method: "frappe.client.get_list",
        args: {
            doctype: "Declaracion_Mensual",
            filters: {
                "cliente": frm.doc.name
            },
            fields: [
                "name", "ano", "mes", "estado",
                "check_gasto_rem_cargado", "check_f29_cuadrado", "check_previred_cuadrado",
                "pdf_link_cliente", "pdf_generado", "borrador_f29_vinculado"
            ],
            order_by: "ano desc, mes desc",
            limit_page_length: 24,
            ignore_permissions: 1
        },
        callback: function(r) {
            if (!r.message || r.message.length === 0) {
                panel_wrapper.html('<div style="text-align:center; padding:40px; color:#999;">No hay declaraciones mensuales para este cliente.</div>');
                return;
            }

            let declaraciones = r.message;
            
            let html = `
                <style>
                    .tabla-declaraciones {
                        width: 100%;
                        border-collapse: collapse;
                        font-size: 13px;
                    }
                    .tabla-declaraciones thead {
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                    }
                    .tabla-declaraciones th {
                        padding: 12px 8px;
                        text-align: left;
                        font-weight: 600;
                        font-size: 11px;
                        text-transform: uppercase;
                    }
                    .tabla-declaraciones td {
                        padding: 10px 8px;
                        border-bottom: 1px solid #e1e8ed;
                    }
                    .tabla-declaraciones tr:hover {
                        background: #f8f9fa;
                    }
                    .badge-estado {
                        padding: 4px 10px;
                        border-radius: 12px;
                        font-size: 11px;
                        font-weight: 600;
                        white-space: nowrap;
                    }
                    .estado-borrador { background: #ffc107; color: #000; }
                    .estado-validar { background: #ff9800; color: #fff; }
                    .estado-listo { background: #28a745; color: #fff; }
                    .estado-enviado { background: #17a2b8; color: #fff; }
                    .btn-accion {
                        padding: 4px 8px;
                        margin: 2px;
                        font-size: 11px;
                        border: 1px solid #ddd;
                        border-radius: 4px;
                        background: white;
                        cursor: pointer;
                        transition: all 0.2s;
                    }
                    .btn-accion:hover {
                        background: #667eea;
                        color: white;
                        border-color: #667eea;
                    }
                    .btn-ver-pdf {
                        background: linear-gradient(135deg, #00C4CC 0%, #0099A8 100%) !important;
                        color: white !important;
                        font-weight: 600;
                        border: none !important;
                        box-shadow: 0 2px 4px rgba(0,196,204,0.3);
                        transition: all 0.3s ease;
                    }
                    .btn-ver-pdf:hover {
                        background: linear-gradient(135deg, #0099A8 0%, #00C4CC 100%) !important;
                        transform: translateY(-2px);
                        box-shadow: 0 4px 8px rgba(0,196,204,0.5);
                    }
                </style>
                
                <table class="tabla-declaraciones">
                    <thead>
                        <tr>
                            <th style="width: 10%;">Período</th>
                            <th style="width: 12%;">Estado</th>
                            <th style="width: 5%; text-align:center;">RRHH</th>
                            <th style="width: 5%; text-align:center;">F29</th>
                            <th style="width: 5%; text-align:center;">Prev</th>
                            <th style="width: 5%; text-align:center;">PDF</th>
                            <th style="width: 58%;">Acciones</th>
                        </tr>
                    </thead>
                    <tbody>
            `;

            declaraciones.forEach(function(d) {
                
                // Badge de estado
                let estado_class = '';
                let estado_texto = d.estado || 'Borrador';
                
                if (estado_texto === 'Borrador') estado_class = 'estado-borrador';
                else if (estado_texto === 'En Validación') estado_class = 'estado-validar';
                else if (estado_texto === 'Listo') estado_class = 'estado-listo';
                else if (estado_texto === 'Enviado') estado_class = 'estado-enviado';
                
                // Icons de validación
                let icon_rrhh = d.check_gasto_rem_cargado ? '✅' : '⏳';
                let icon_f29 = d.check_f29_cuadrado ? '✅' : '⏳';
                let icon_prev = d.check_previred_cuadrado ? '✅' : '⏳';
                
                // Detectar si tiene PDF (busca en ambos campos por compatibilidad)
                let tiene_pdf = d.pdf_link_cliente || d.pdf_generado;
                let icon_pdf = tiene_pdf ? '📄' : '--';
                
                // Acciones según estado
                let acciones = generar_acciones_declaracion(d, frm);

                html += `
                    <tr>
                        <td><strong><a href="/app/declaracion_mensual/${d.name}">${d.mes}/${d.ano}</a></strong></td>
                        <td><span class="badge-estado ${estado_class}">${estado_texto}</span></td>
                        <td style="text-align:center; font-size:16px;">${icon_rrhh}</td>
                        <td style="text-align:center; font-size:16px;">${icon_f29}</td>
                        <td style="text-align:center; font-size:16px;">${icon_prev}</td>
                        <td style="text-align:center; font-size:16px;">${icon_pdf}</td>
                        <td>${acciones}</td>
                    </tr>
                `;
            });

            html += `</tbody></table>`;
            
            panel_wrapper.html(html);
            
            // Agregar eventos a los botones
            agregar_eventos_declaraciones(frm);
        }
    });
}

// ===================================================================
// FUNCIÓN: GENERAR ACCIONES SEGÚN ESTADO
// ===================================================================
function generar_acciones_declaracion(d, frm) {
    let acciones = '';
    
    // Siempre mostrar botones de vista
    acciones += `<button class="btn-accion btn-declaracion" data-action="ing-rrhh" data-doc="${d.name}">Ing.RRHH</button>`;
    acciones += `<button class="btn-accion btn-declaracion" data-action="ver-f29" data-doc="${d.name}" data-f29="${d.borrador_f29_vinculado || ''}">Ver F29</button>`;
    acciones += `<button class="btn-accion btn-declaracion" data-action="ver-prev" data-doc="${d.name}">Ver Prev</button>`;
    
    // Acciones según estado y validaciones
    if (!d.check_gasto_rem_cargado) {
        acciones += `<button class="btn-accion btn-declaracion" data-action="check-rrhh" data-doc="${d.name}" style="background:#ffc107;">✓RRHH</button>`;
    }
    
    if (!d.check_f29_cuadrado) {
        acciones += `<button class="btn-accion btn-declaracion" data-action="check-f29" data-doc="${d.name}" style="background:#ffc107;">✓F29</button>`;
    }
    
    if (!d.check_previred_cuadrado) {
        acciones += `<button class="btn-accion btn-declaracion" data-action="check-prev" data-doc="${d.name}" style="background:#ffc107;">✓Prev</button>`;
    }
    
    // Detectar si tiene PDF (verificar ambos campos)
    let tiene_pdf = d.pdf_link_cliente || d.pdf_generado;
    let pdf_url = d.pdf_link_cliente || d.pdf_generado;
    
    // Si está listo
    if (d.estado === 'Listo') {
        
        if (!tiene_pdf) {
            // No tiene PDF → Botón para generarlo
            acciones += `<button class="btn-accion btn-declaracion" data-action="gen-pdf" data-doc="${d.name}" style="background:#28a745; color:white;">Gen.PDF</button>`;
        } else {
            // Tiene PDF → Botón para verlo Y botón para enviarlo
            acciones += `<button class="btn-accion btn-declaracion" data-action="ver-pdf" data-doc="${d.name}" data-pdf="${pdf_url}">Ver PDF</button>`;
            acciones += `<button class="btn-accion btn-declaracion" data-action="enviar" data-doc="${d.name}" style="background:#17a2b8; color:white;">Enviar</button>`;
        }
    }
    
    // Si está enviado
    if (d.estado === 'Enviado') {
        if (tiene_pdf) {
            acciones += `<button class="btn-accion btn-declaracion" data-action="ver-pdf" data-doc="${d.name}" data-pdf="${pdf_url}">Ver PDF</button>`;
        }
        acciones += `<button class="btn-accion btn-declaracion" data-action="reenviar" data-doc="${d.name}" style="background:#17a2b8; color:white;">Reenviar</button>`;
    }
    
    return acciones;
}

// ===================================================================
// FUNCIÓN: AGREGAR EVENTOS A BOTONES DECLARACIONES
// ===================================================================
function agregar_eventos_declaraciones(frm) {
    
    $('.btn-declaracion').off('click').on('click', function() {
        let action = $(this).data('action');
        let doc_name = $(this).data('doc');
        let f29_name = $(this).data('f29');
        let pdf_url = $(this).data('pdf');
        
        ejecutar_accion_declaracion(action, doc_name, f29_name, pdf_url, frm);
    });
}

// ===================================================================
// FUNCIÓN: EJECUTAR ACCIÓN DECLARACIÓN
// ===================================================================
function ejecutar_accion_declaracion(action, doc_name, f29_name, pdf_url, frm) {
    
    console.log('🎯 Ejecutando acción:', action, 'Doc:', doc_name, 'PDF URL:', pdf_url);
    
    switch(action) {
        
        case 'ing-rrhh':
            // Buscar y abrir Registro_Remuneraciones
            frappe.call({
                method: 'frappe.client.get_list',
                args: {
                    doctype: 'Registro_Remuneraciones',
                    filters: {
                        cliente: frm.doc.name
                    },
                    fields: ['name', 'ano', 'mes'],
                    limit_page_length: 100,
                    ignore_permissions: 1
                },
                callback: function(r) {
                    if (r.message && r.message.length > 0) {
                        // Buscar el que coincida con el período
                        let ano = doc_name.split('-')[2];
                        let mes = doc_name.split('-')[3];
                        
                        let registro = r.message.find(reg => 
                            reg.ano == ano && reg.mes == mes
                        );
                        
                        if (registro) {
                            frappe.set_route('Form', 'Registro_Remuneraciones', registro.name);
                        } else {
                            frappe.msgprint('No se encontró Registro de Remuneraciones para este período.');
                        }
                    } else {
                        frappe.msgprint('No se encontró Registro de Remuneraciones para este período.');
                    }
                }
            });
            break;
            
        case 'ver-f29':
            if (f29_name) {
                frappe.set_route('Form', 'Borrador_F29', f29_name);
            } else {
                frappe.msgprint('No hay F29 vinculado.');
            }
            break;
            
        case 'ver-prev':
            // Igual que ing-rrhh
            ejecutar_accion_declaracion('ing-rrhh', doc_name, '', '', frm);
            break;
            
        case 'check-rrhh':
            marcar_check(doc_name, 'check_gasto_rem_cargado', frm);
            break;
            
        case 'check-f29':
            marcar_check(doc_name, 'check_f29_cuadrado', frm);
            break;
            
        case 'check-prev':
            marcar_check(doc_name, 'check_previred_cuadrado', frm);
            break;
            
        case 'gen-pdf':
            generar_pdf_declaracion(doc_name, frm);
            break;
            
        case 'enviar':
            enviar_declaracion(doc_name, frm);
            break;
            
        case 'ver-pdf':
            // Método robusto: siempre buscar el PDF en el documento
            console.log('📄 Buscando PDF para:', doc_name);
            
            frappe.call({
                method: 'frappe.client.get',
                args: {
                    doctype: 'Declaracion_Mensual',
                    name: doc_name
                },
                callback: function(r) {
                    if (r.message) {
                        let doc = r.message;
                        let url = doc.pdf_link_cliente || doc.pdf_generado;
                        
                        console.log('📄 PDF encontrado:', url);
                        
                        if (url) {
                            // Abrir en nueva pestaña
                            let nuevaVentana = window.open(url, '_blank');
                            
                            // Verificar si se abrió (puede estar bloqueado por popup blocker)
                            if (!nuevaVentana || nuevaVentana.closed || typeof nuevaVentana.closed == 'undefined') {
                                frappe.msgprint({
                                    title: 'Ventana bloqueada',
                                    message: 'Por favor permite ventanas emergentes y vuelve a intentar.<br><br>' +
                                             '<a href="' + url + '" target="_blank">O haz click aquí para abrir el PDF</a>',
                                    indicator: 'orange'
                                });
                            }
                        } else {
                            frappe.msgprint({
                                title: 'PDF no disponible',
                                message: 'No se encontró el PDF para esta declaración.',
                                indicator: 'orange'
                            });
                        }
                    }
                },
                error: function(err) {
                    console.error('❌ Error obteniendo PDF:', err);
                    frappe.msgprint({
                        title: 'Error',
                        message: 'No se pudo obtener el PDF.',
                        indicator: 'red'
                    });
                }
            });
            break;
            
        case 'reenviar':
            reenviar_declaracion(doc_name, frm);
            break;
    }
}

// ===================================================================
// FUNCIÓN: MARCAR CHECK
// ===================================================================
function marcar_check(doc_name, field_name, frm) {
    
    // Mostrar progreso
    frappe.show_alert({
        message: 'Marcando validación...',
        indicator: 'blue'
    }, 2);
    
    // Llamar a frappe.client.set_value
    frappe.call({
        method: 'frappe.client.set_value',
        args: {
            doctype: 'Declaracion_Mensual',
            name: doc_name,
            fieldname: field_name,
            value: 1
        },
        callback: function(r) {
            
            if (r.message) {
                // Mensaje de éxito
                frappe.show_alert({
                    message: '✅ Validación marcada',
                    indicator: 'green'
                }, 3);
                
                // Refrescar panel
                setTimeout(function() {
                    renderizar_panel_declaraciones(frm);
                }, 500);
            }
        },
        error: function(err) {
            console.error('Error en marcar_check:', err);
            frappe.msgprint({
                title: 'Error',
                message: 'No se pudo marcar la validación. Revisa permisos.',
                indicator: 'red'
            });
        }
    });
}

// ===================================================================
// FUNCIÓN: GENERAR PDF
// ===================================================================
function generar_pdf_declaracion(doc_name, frm) {
    
    // Confirmación
    frappe.confirm(
        '¿Generar el Informe Mensual en PDF?<br><br>' +
        '<small>Este proceso creará un PDF profesional con:<br>' +
        '• Resumen de pagos (2 opciones)<br>' +
        '• Análisis financiero del mes<br>' +
        '• Desglose de ventas y gastos<br>' +
        '• Detalle tributario (F29 + RRHH)<br>' +
        '• Programa de socios</small>',
        function() {
            
            // Mostrar progreso
            frappe.show_alert({
                message: 'Generando PDF en Google Drive...',
                indicator: 'blue'
            }, 5);
            
            // Llamar API para generar PDF
            frappe.call({
                method: 'preparar_datos_pdf',
                args: {
                    declaracion_name: doc_name
                },
                freeze: true,
                freeze_message: __('Generando PDF... Por favor espera (puede tomar 30-60 segundos)'),
                callback: function(r) {
                    
                    if (r.message && r.message.status === 'success') {
                        
                        frappe.show_alert({
                            message: '✅ PDF generado exitosamente en Google Drive',
                            indicator: 'green'
                        }, 5);
                        
                        // Refrescar panel
                        setTimeout(function() {
                            renderizar_panel_declaraciones(frm);
                        }, 1000);
                        
                        // Si hay URL del PDF, ofrecer abrirlo
                        if (r.message.pdf_url) {
                            frappe.confirm(
                                '¿Deseas abrir el PDF en Google Drive?',
                                function() {
                                    window.open(r.message.pdf_url, '_blank');
                                }
                            );
                        }
                        
                    } else if (r.message && r.message.status === 'error') {
                        
                        frappe.msgprint({
                            title: 'Error al generar PDF',
                            message: r.message.message || 'Error desconocido',
                            indicator: 'red'
                        });
                        
                    }
                },
                error: function(err) {
                    console.error('Error en generar_pdf_declaracion:', err);
                    frappe.msgprint({
                        title: 'Error',
                        message: 'Ocurrió un error al generar el PDF. Revisa la consola.',
                        indicator: 'red'
                    });
                }
            });
        }
    );
}

// ===================================================================
// FUNCIÓN: ENVIAR DECLARACIÓN (N8N) - CON ESPERA Y FREEZE
// ===================================================================
function enviar_declaracion(doc_name, frm, es_reenvio = false) {
    
    
    
    // Mensaje de confirmación
    let mensaje_confirmacion = es_reenvio 
        ? '¿Reenviar declaración al cliente por Email y WhatsApp?<br><br><small>Se enviará nuevamente el PDF con el resumen del mes.</small>'
        : '¿Enviar declaración al cliente por Email y WhatsApp?<br><br><small>Se enviará el PDF con el resumen financiero del mes.<br>Este proceso puede tomar 10-20 segundos.</small>';
    
    frappe.confirm(mensaje_confirmacion, function() {
        
        // PASO 1: Obtener datos de la Declaracion_Mensual
        frappe.call({
            method: 'frappe.client.get',
            args: {
                doctype: 'Declaracion_Mensual',
                name: doc_name
            },
            callback: function(r_decl) {
                
                if (!r_decl.message) {
                    frappe.msgprint({
                        title: 'Error',
                        message: 'No se pudo obtener los datos de la declaración.',
                        indicator: 'red'
                    });
                    return;
                }
                
                let decl = r_decl.message;
                
                // PASO 2: Obtener datos del Cliente
                frappe.call({
                    method: 'frappe.client.get',
                    args: {
                        doctype: 'Ficha_Cliente',
                        name: decl.cliente
                    },
                    callback: function(r_cliente) {
                        
                        if (!r_cliente.message) {
                            frappe.msgprint({
                                title: 'Error',
                                message: 'No se pudo obtener los datos del cliente.',
                                indicator: 'red'
                            });
                            return;
                        }
                        
                        let cliente = r_cliente.message;
                        
                        // VALIDACIÓN 1: Verificar que tenga PDF
                        let pdf_url = decl.pdf_link_cliente || decl.pdf_generado;
                        if (!pdf_url) {
                            frappe.msgprint({
                                title: '📄 PDF no disponible',
                                message: 'Debes generar el PDF antes de enviar la declaración.<br><br>Usa el botón <strong>"Gen.PDF"</strong> primero.',
                                indicator: 'orange'
                            });
                            return;
                        }
                        
                        // VALIDACIÓN 2: Verificar email del cliente
                        if (!cliente.contacto_principal_email) {
                            frappe.msgprint({
                                title: '📧 Email no configurado',
                                message: 'El cliente no tiene email de contacto configurado.<br><br>Por favor agrega un email en la <strong>Ficha del Cliente</strong>.',
                                indicator: 'orange'
                            });
                            return;
                        }
                        
                        // PASO 3: Calcular fechas de vencimiento
                        let mes_vencimiento = parseInt(decl.mes) + 1;
                        let ano_vencimiento = parseInt(decl.ano);
                        if (mes_vencimiento > 12) {
                            mes_vencimiento = 1;
                            ano_vencimiento += 1;
                        }
                        
                        let fecha_venc_f29 = `${ano_vencimiento}-${String(mes_vencimiento).padStart(2, '0')}-12`;
                        let fecha_venc_previred = `${ano_vencimiento}-${String(mes_vencimiento).padStart(2, '0')}-10`;
                        
                        // PASO 4: Nombre del mes para mensaje
                        const meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                                     'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];
                        let periodo_texto = `${meses[parseInt(decl.mes) - 1]} ${decl.ano}`;
                        
                        // PASO 5: Construir payload completo
                        let payload = {
                            // Identificación
                            declaracion_id: decl.name,
                            tipo_envio: "declaracion_mensual",
                            
                            // Período
                            periodo_mes: parseInt(decl.mes),
                            periodo_ano: parseInt(decl.ano),
                            periodo_texto: periodo_texto,
                            
                            // Cliente
                            cliente_id: cliente.name,
                            cliente_rut: cliente.rut_cliente,
                            cliente_razon_social: cliente.razon_social,
                            
                            // Contacto
                            contacto_nombre: cliente.contacto_principal_nombre || cliente.razon_social,
                            contacto_email: cliente.contacto_principal_email,
                            contacto_whatsapp: cliente.contacto_principal_whatsapp || "",
                            
                            // PDF
                            pdf_url: pdf_url,
                            pdf_drive_file_id: decl.pdf_drive_file_id || "",
                            pdf_generado_fecha: decl.fecha_pdf_generado || decl.modified || frappe.datetime.now_datetime(),
                            
                            // Montos
                            total_f29: decl.total_f29_a_pagar || 0,
                            total_previred: decl.total_previred_a_pagar || 0,
                            total_a_pagar: (decl.total_f29_a_pagar || 0) + (decl.total_previred_a_pagar || 0),
                            
                            // Fechas importantes
                            fecha_vencimiento_f29: fecha_venc_f29,
                            fecha_vencimiento_previred: fecha_venc_previred,
                            
                            // Metadatos
                            es_reenvio: es_reenvio,
                            contador_envios: (decl.emails_enviados || 0) + 1,
                            fecha_envio: frappe.datetime.now_datetime()
                        };
                        
                        console.log('📧 Payload completo para n8n:', payload);
                        
                        // PASO 6: FREEZE UI y enviar a n8n
                        frappe.dom.freeze('📤 Enviando declaración por Email y WhatsApp...<br><small>Por favor espera 10-20 segundos</small>');
                        
                        frappe.db.get_single_value('Configuracion_n8n', 'webhook_envio_declaracion').then(N8N_WEBHOOK_ENVIO => { fetch(N8N_WEBHOOK_ENVIO, {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify(payload)
                        })
                        .then(response => {
                            if (!response.ok) {
                                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                            }
                            return response.json();
                        })
                        .then(data => {
                            console.log('✅ Respuesta de n8n:', data);
                            
                            // PASO 7: Actualizar documento en ERPNext
                            let campos_actualizar = {
                                'estado': 'Enviado',
                                'fecha_ultimo_email': frappe.datetime.now_datetime(),
                                'emails_enviados': (decl.emails_enviados || 0) + 1
                            };
                            
                            // Si tiene WhatsApp configurado
                            if (cliente.contacto_principal_whatsapp) {
                                campos_actualizar['fecha_ultimo_whatsapp'] = frappe.datetime.now_datetime();
                                campos_actualizar['whatsapps_enviados'] = (decl.whatsapps_enviados || 0) + 1;
                            }
                            
                            frappe.call({
                                method: 'frappe.client.set_value',
                                args: {
                                    doctype: 'Declaracion_Mensual',
                                    name: doc_name,
                                    fieldname: campos_actualizar
                                },
                                callback: function() {
                                    
                                    frappe.dom.unfreeze();
                                    
                                    let mensaje_exito = cliente.contacto_principal_whatsapp
                                        ? '✅ Declaración enviada exitosamente por Email y WhatsApp'
                                        : '✅ Declaración enviada exitosamente por Email';
                                    
                                    frappe.show_alert({
                                        message: mensaje_exito,
                                        indicator: 'green'
                                    }, 5);
                                    
                                    // Refrescar panel
                                    setTimeout(function() {
                                        renderizar_panel_declaraciones(frm);
                                    }, 500);
                                }
                            });
                        })
                        .catch(error => {
                            frappe.dom.unfreeze();
                            console.error('❌ Error enviando a n8n:', error);
                            
                            frappe.msgprint({
                                title: '❌ Error de Envío',
                                message: `No se pudo conectar con el servicio de mensajería.<br><br>
                                         <strong>Error:</strong> ${error.message}<br><br>
                                         <small>Verifica que n8n esté activo y la URL del webhook sea correcta.</small>`,
                                indicator: 'red',
                                primary_action: {
                                    label: 'Reintentar',
                                    action: function() {
                                        enviar_declaracion(doc_name, frm, es_reenvio);
                                    }
                                }
                            });
                            }); // Cierra el then
                        });
                    },
                    error: function(err) {
                        console.error('❌ Error obteniendo cliente:', err);
                        frappe.msgprint({
                            title: 'Error',
                            message: 'No se pudo obtener los datos del cliente.',
                            indicator: 'red'
                        });
                    }
                });
            },
            error: function(err) {
                console.error('❌ Error obteniendo declaración:', err);
                frappe.msgprint({
                    title: 'Error',
                    message: 'No se pudo obtener los datos de la declaración.',
                    indicator: 'red'
                });
            }
        });
    });
}

// ===================================================================
// FUNCIÓN: VER PDF (Actualizada para Drive)
// ===================================================================
function ver_pdf_declaracion(doc_name, pdf_url) {
    if (pdf_url) {
        window.open(pdf_url, '_blank');
    } else {
        frappe.call({
            method: 'frappe.client.get_value',
            args: {
                doctype: 'Declaracion_Mensual',
                filters: { name: doc_name },
                fieldname: ['pdf_link_cliente', 'pdf_generado']
            },
            callback: function(r) {
                if (r.message) {
                    let url = r.message.pdf_link_cliente || r.message.pdf_generado;
                    if (url) {
                        window.open(url, '_blank');
                    } else {
                        frappe.msgprint('No hay PDF generado para esta declaración.');
                    }
                } else {
                    frappe.msgprint('No hay PDF generado para esta declaración.');
                }
            }
        });
    }
}

// ===================================================================
// FUNCIÓN: REENVIAR DECLARACIÓN
// ===================================================================
function reenviar_declaracion(doc_name, frm) {
    enviar_declaracion(doc_name, frm, true);  // Pasar flag es_reenvio=true
}

// ===================================================================
// FUNCIÓN: RENDERIZAR PANEL DE COBRANZA
// ===================================================================
function renderizar_panel_cobranza(frm) {
    
    const panel_wrapper = $(frm.fields_dict['panel_facturacion_cobranza'].wrapper);
    panel_wrapper.html('<div style="text-align:center; padding:20px;"><i class="fa fa-spinner fa-spin"></i> Cargando cobranzas...</div>');

    frappe.call({
        method: "frappe.client.get_list",
        args: {
            doctype: "Cobranza_Cliente",
            filters: {
                "cliente": frm.doc.name
            },
            fields: [
                "name", "periodo_mes", "periodo_ano", "monto_a_cobrar",
                "estado_cobranza", "fecha_vencimiento", "dias_para_vencer",
                "factura_vinculada", "numero_factura", "pdf_factura_drive_url" // <--- AGREGADO PARA PDF DRIVE
            ],
            order_by: "periodo_ano desc, periodo_mes desc",
            limit_page_length: 24,
            ignore_permissions: 1
        },
        callback: function(r) {
            if (!r.message || r.message.length === 0) {
                panel_wrapper.html('<div style="text-align:center; padding:40px; color:#999;">No hay cobranzas para este cliente.</div>');
                return;
            }

            let cobranzas = r.message;
            
            // Calcular resumen
            let total_por_cobrar = 0;
            let total_vencido = 0;
            let total_pagado_anio = 0;
            
            cobranzas.forEach(c => {
                if (c.estado_cobranza === 'Por Cobrar' || c.estado_cobranza === 'Facturado') {
                    total_por_cobrar += c.monto_a_cobrar || 0;
                }
                if (c.estado_cobranza === 'Vencido') {
                    total_vencido += c.monto_a_cobrar || 0;
                }
                if (c.estado_cobranza === 'Pagado') {
                    total_pagado_anio += c.monto_a_cobrar || 0;
                }
            });
            
            let html = `
                <style>
                    .resumen-cobranza {
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                        padding: 20px;
                        border-radius: 8px;
                        margin-bottom: 20px;
                        display: flex;
                        justify-content: space-around;
                    }
                    .resumen-item {
                        text-align: center;
                    }
                    .resumen-label {
                        font-size: 11px;
                        opacity: 0.9;
                        text-transform: uppercase;
                    }
                    .resumen-valor {
                        font-size: 24px;
                        font-weight: 700;
                        margin-top: 5px;
                    }
                    .tabla-cobranza {
                        width: 100%;
                        border-collapse: collapse;
                        font-size: 13px;
                    }
                    .tabla-cobranza thead {
                        background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
                        color: white;
                    }
                    .tabla-cobranza th {
                        padding: 12px 8px;
                        text-align: left;
                        font-weight: 600;
                        font-size: 11px;
                        text-transform: uppercase;
                    }
                    .tabla-cobranza td {
                        padding: 10px 8px;
                        border-bottom: 1px solid #e1e8ed;
                    }
                    .tabla-cobranza tr:hover {
                        background: #f8f9fa;
                    }
                    .badge-cobranza {
                        padding: 4px 10px;
                        border-radius: 12px;
                        font-size: 11px;
                        font-weight: 600;
                        white-space: nowrap;
                    }
                    .cobranza-porcobrar { background: #ffc107; color: #000; }
                    .cobranza-facturado { background: #17a2b8; color: #fff; }
                    .cobranza-pagado { background: #28a745; color: #fff; }
                    .cobranza-vencido { background: #dc3545; color: #fff; }
                </style>
                
                <div class="resumen-cobranza">
                    <div class="resumen-item">
                        <div class="resumen-label">Por Cobrar</div>
                        <div class="resumen-valor">${frappe.format(total_por_cobrar, {fieldtype: 'Currency'})}</div>
                    </div>
                    <div class="resumen-item">
                        <div class="resumen-label">Vencido</div>
                        <div class="resumen-valor">${frappe.format(total_vencido, {fieldtype: 'Currency'})}</div>
                    </div>
                    <div class="resumen-item">
                        <div class="resumen-label">Pagado (este año)</div>
                        <div class="resumen-valor">${frappe.format(total_pagado_anio, {fieldtype: 'Currency'})}</div>
                    </div>
                </div>
                
                <table class="tabla-cobranza">
                    <thead>
                        <tr>
                            <th style="width: 10%;">Período</th>
                            <th style="width: 15%;">A Cobrar</th>
                            <th style="width: 15%;">Estado</th>
                            <th style="width: 10%;">Factura</th>
                            <th style="width: 10%;">Vencim</th>
                            <th style="width: 8%;">Días</th>
                            <th style="width: 32%;">Acciones</th>
                        </tr>
                    </thead>
                    <tbody>
            `;

            cobranzas.forEach(function(c) {
                
                let estado_class = '';
                if (c.estado_cobranza === 'Por Cobrar') estado_class = 'cobranza-porcobrar';
                else if (c.estado_cobranza === 'Facturado') estado_class = 'cobranza-facturado';
                else if (c.estado_cobranza === 'Pagado') estado_class = 'cobranza-pagado';
                else if (c.estado_cobranza === 'Vencido') estado_class = 'cobranza-vencido';
                
                let dias_texto = c.dias_para_vencer || '--';
                if (c.dias_para_vencer > 0) {
                    dias_texto = `+${c.dias_para_vencer}`;
                } else if (c.dias_para_vencer < 0) {
                    dias_texto = c.dias_para_vencer;
                }
                
                let factura_texto = c.numero_factura || '--';
                
                let acciones = generar_acciones_cobranza(c);

                html += `
                    <tr>
                        <td><strong><a href="/app/cobranza_cliente/${c.name}">${c.periodo_mes}/${c.periodo_ano}</a></strong></td>
                        <td><strong>${frappe.format(c.monto_a_cobrar, {fieldtype: 'Currency'})}</strong></td>
                        <td><span class="badge-cobranza ${estado_class}">${c.estado_cobranza}</span></td>
                        <td>${factura_texto}</td>
                        <td>${frappe.format(c.fecha_vencimiento, {fieldtype: 'Date'})}</td>
                        <td style="text-align:center;">${dias_texto}</td>
                        <td>${acciones}</td>
                    </tr>
                `;
            });

            html += `</tbody></table>`;
            
            panel_wrapper.html(html);
            
            // Agregar eventos
            agregar_eventos_cobranza(frm);
        }
    });
}

// ===================================================================
// FUNCIÓN: GENERAR ACCIONES COBRANZA
// ===================================================================
function generar_acciones_cobranza(c) {
    let acciones = '';
    
    if (c.estado_cobranza === 'Por Cobrar') {
        acciones += `<button class="btn-accion btn-cobranza" data-action="facturar-cob" data-doc="${c.name}" style="background:#28a745; color:white;">Facturar</button>`;
        acciones += `<button class="btn-accion btn-cobranza" data-action="email-cob" data-doc="${c.name}">Email</button>`;
        acciones += `<button class="btn-accion btn-cobranza" data-action="pagado-cob" data-doc="${c.name}" >Pagar</button>`;
    } else if (c.estado_cobranza === 'Facturado' || c.estado_cobranza === 'Vencido') {
        // CORREGIDO: SE PASA EL PDF_URL A DATA-PDF
        acciones += `<button class="btn-accion btn-cobranza" data-action="ver-fact-cob" data-doc="${c.name}" data-factura="${c.factura_vinculada || ''}" data-pdf="${c.pdf_factura_drive_url || ''}">Ver Fact</button>`;
        acciones += `<button class="btn-accion btn-cobranza" data-action="recordar-cob" data-doc="${c.name}" style="background:#ff9800; color:white;">Recordar</button>`;
        acciones += `<button class="btn-accion btn-cobranza" data-action="pagado-cob" data-doc="${c.name}" >Pagar</button>`;
    } else if (c.estado_cobranza === 'Pagado') {
        // CORREGIDO: SE PASA EL PDF_URL A DATA-PDF
        acciones += `<button class="btn-accion btn-cobranza" data-action="ver-fact-cob" data-doc="${c.name}" data-factura="${c.factura_vinculada || ''}" data-pdf="${c.pdf_factura_drive_url || ''}">Ver Fact</button>`;
        acciones += `<button class="btn-accion btn-cobranza" data-action="ver-comp-cob" data-doc="${c.name}">Ver Comp</button>`;
    }
    
    acciones += `<button class="btn-accion btn-cobranza" data-action="ver-det-cob" data-doc="${c.name}">Ver Detalle</button>`;
    
    return acciones;
}

// ===================================================================
// FUNCIÓN: EVENTOS COBRANZA
// ===================================================================
function agregar_eventos_cobranza(frm) {
    $('.btn-cobranza').off('click').on('click', function() {
        let action = $(this).data('action');
        let doc_name = $(this).data('doc');
        let factura_name = $(this).data('factura');
        let pdf_url = $(this).data('pdf'); // CORREGIDO: CAPTURAR PDF URL
        
        ejecutar_accion_cobranza(action, doc_name, factura_name, frm, pdf_url);
    });
}

// ===================================================================
// FUNCIÓN: EJECUTAR ACCIÓN COBRANZA
// ===================================================================
function ejecutar_accion_cobranza(action, doc_name, factura_name, frm, pdf_url) {
    
    switch(action) {
        
        case 'facturar-cob':
            facturar_cobranza(doc_name, frm);
            break;
            
        case 'email-cob':
            frappe.msgprint('Función de email en desarrollo');
            // TODO: Implementar envío de email
            break;
            
        case 'ver-fact-cob':
            // LÓGICA CORREGIDA: PRIORIZAR PDF DE DRIVE
            if (pdf_url) {
                window.open(pdf_url, '_blank');
            } else if (factura_name) {
                frappe.set_route('Form', 'Sales Invoice', factura_name);
            } else {
                frappe.msgprint({
                    title: 'No disponible',
                    message: 'No hay factura vinculada ni PDF generado en Drive.',
                    indicator: 'orange'
                });
            }
            break;
            
        case 'recordar-cob':
            frappe.msgprint('Función de recordatorio en desarrollo');
            // TODO: Implementar recordatorio
            break;
            
        case 'pagado-cob':
            marcar_como_pagado(doc_name, frm);
            break;
            
        case 'ver-comp-cob':
            ver_comprobante(doc_name);
            break;
            
        case 'ver-det-cob':
            frappe.set_route('Form', 'Cobranza_Cliente', doc_name);
            break;
    }
}

// ===================================================================
// FUNCIÓN: MARCAR COMO PAGADO
// ===================================================================
function marcar_como_pagado(doc_name, frm) {
    
    let d = new frappe.ui.Dialog({
        title: 'Marcar como Pagado',
        fields: [
            {
                label: 'Fecha de Pago',
                fieldname: 'fecha_pago',
                fieldtype: 'Date',
                reqd: 1,
                default: frappe.datetime.get_today()
            },
            {
                label: 'Monto Pagado',
                fieldname: 'monto_pagado',
                fieldtype: 'Currency',
                reqd: 1
            },
            {
                label: 'Método de Pago',
                fieldname: 'metodo_pago',
                fieldtype: 'Select',
                options: 'Transferencia\nEfectivo\nCheque\nTarjeta\nOtro',
                reqd: 1
            },
            {
                label: 'Comprobante',
                fieldname: 'comprobante_pago',
                fieldtype: 'Attach'
            }
        ],
        primary_action_label: 'Marcar Pagado',
        primary_action: function(values) {
            
            frappe.call({
                method: 'frappe.client.set_value',
                args: {
                    doctype: 'Cobranza_Cliente',
                    name: doc_name,
                    fieldname: {
                        'estado_cobranza': 'Pagado',
                        'fecha_pago': values.fecha_pago,
                        'monto_pagado': values.monto_pagado,
                        'metodo_pago': values.metodo_pago,
                        'comprobante_pago': values.comprobante_pago || ''
                    }
                },
                callback: function() {
                    frappe.show_alert({
                        message: '✅ Marcado como pagado',
                        indicator: 'green'
                    }, 3);
                    
                    d.hide();
                    renderizar_panel_cobranza(frm);
                }
            });
        }
    });
    
    d.show();
            d.set_value('monto_pagado', monto_sugerido);
}

// ===================================================================
// FUNCIÓN: FACTURAR COBRANZA (De Facto)
// ===================================================================
function facturar_cobranza(doc_name, frm) {
    
    // Webhook de Facturación
    

    frappe.confirm(
        '¿Generar factura electrónica en De Facto?<br><br>' +
        '<small>Se creará un borrador de factura.</small>',
        function() {
            
            frappe.dom.freeze('📄 Generando factura en De Facto...<br><small>Por favor espera 10-20 segundos</small>');
            
            // PASO 1: Obtener Cobranza
            frappe.call({
                method: 'frappe.client.get',
                args: {
                    doctype: 'Cobranza_Cliente',
                    name: doc_name,
                    fields: ['*']
                },
                callback: function(r_cob) {
                    
                    if (!r_cob.message) {
                        frappe.dom.unfreeze();
                        frappe.msgprint('Error obteniendo cobranza');
                        return;
                    }
                    
                    let cob = r_cob.message;
                    
                    // PASO 2: Obtener Cliente
                    frappe.call({
                        method: 'frappe.client.get',
                        args: {
                            doctype: 'Ficha_Cliente',
                            name: cob.cliente,
                            fields: ['*']
                        },
                        callback: function(r_cliente) {
                            
                            if (!r_cliente.message) {
                                frappe.dom.unfreeze();
                                frappe.msgprint('Error obteniendo cliente');
                                return;
                            }
                            
                            let cliente = r_cliente.message;
                            
                            // VALIDACIONES
                            if (!cliente.rut_cliente) {
                                frappe.dom.unfreeze();
                                frappe.msgprint('Cliente no tiene RUT configurado');
                                return;
                            }
                            
                            if (!cliente.comuna || !cliente.ciudad) {
                                frappe.dom.unfreeze();
                                frappe.msgprint({
                                    title: 'Datos incompletos',
                                    message: 'El cliente necesita tener Comuna y Ciudad configurados.',
                                    indicator: 'orange'
                                });
                                return;
                            }
                            
                            // PASO 3: Construir details array
                            let details = [];
                            
                            // Línea 1: Plan Base
                            if (cob.monto_base > 0) {
                                details.push({
                                    quantity: 1,
                                    sku: "PLAN-BASE",
                                    line_description: "Plan Servicio Contable Mensual",
                                    unit_measure: "UN",
                                    unit_price: cob.monto_base,
                                    total_amount_line: cob.monto_base,
                                    total_taxes: 0
                                });
                            }
                            
                            // Línea 2: RRHH Variable
                            if (cob.monto_rrhh > 0 && cob.numero_empleados > 0) {
                                let precio_unitario = cob.monto_rrhh / cob.numero_empleados;
                                details.push({
                                    quantity: cob.numero_empleados,
                                    sku: "RRHH-VAR",
                                    line_description: "RRHH Variable - Procesamiento de Remuneraciones",
                                    unit_measure: "UN",
                                    unit_price: precio_unitario,
                                    total_amount_line: cob.monto_rrhh,
                                    total_taxes: 0
                                });
                            }
                            
                            // Línea 3: Descuentos
                            // Línea 2.5: Adicionales y Cuotas Extraordinarias
                            if (cob.monto_adicionales > 0) {
                                details.push({
                                    quantity: 1,
                                    sku: "ADICIONALES",
                                    line_description: "Servicios Adicionales y/o Cuotas Mensuales",
                                    unit_measure: "UN",
                                    unit_price: cob.monto_adicionales,
                                    total_amount_line: cob.monto_adicionales,
                                    total_taxes: 0
                                });
                            }
                            
                            if (cob.total_descuentos > 0) {
                                
                                frappe.call({
                                    method: 'frappe.client.get',
                                    args: {
                                        doctype: 'Cobranza_Cliente',
                                        name: doc_name,
                                        fields: ['descuentos_aplicados']
                                    },
                                    callback: function(r_desc) {
                                        
                                        let desc_text = "Descuento aplicado";
                                        
                                        if (r_desc.message && r_desc.message.descuentos_aplicados) {
                                            let nombres = r_desc.message.descuentos_aplicados.map(d => d.descripcion);
                                            if (nombres.length > 0) {
                                                desc_text = nombres.join(", ");
                                            }
                                        }
                                        
                                        details.push({
                                            quantity: 1,
                                            sku: "DESC-001",
                                            line_description: `Descuento: ${desc_text}`,
                                            unit_measure: "UN",
                                            unit_price: -(cob.total_descuentos),
                                            total_amount_line: -(cob.total_descuentos),
                                            total_taxes: 0
                                        });
                                        
                                        enviar_a_defacto();
                                    }
                                });
                                
                            } else {
                                enviar_a_defacto();
                            }
                            
                            function enviar_a_defacto() {
                                
                                // PASO 4: Payload completo (SIN observaciones - se manejan en n8n)
                                let payload = {
                                    cobranza_id: cob.name,
                                    cliente_id: cliente.name,
                                    drive_folder_id: cliente.drive_folder_id || "",
                                    
                                    rut: cliente.rut_cliente,
                                    razon_social: cliente.razon_social,
                                    giro: cliente.giro || "SERVICIOS",
                                    direccion: cliente.direccion_fiscal || "Sin direccion",
                                    comuna: cliente.comuna,
                                    ciudad: cliente.ciudad,
                                    
                                    monto_base: cob.monto_base || 0,
                                    monto_rrhh: cob.monto_rrhh || 0,
                                    numero_empleados: cob.numero_empleados || 0,
                                    total_descuentos: cob.total_descuentos || 0,
                                    monto_total: cob.monto_a_cobrar,
                                    
                                    details: details,
                                    
                                    periodo_mes: cob.periodo_mes,
                                    periodo_ano: cob.periodo_ano
                                };
                                
                                console.log('📤 Payload a De Facto:', payload);
                                
                                // PASO 5: Enviar a n8n
                                frappe.db.get_single_value('Configuracion_n8n', 'webhook_facturacion').then(N8N_WEBHOOK_FACTURACION => { fetch(N8N_WEBHOOK_FACTURACION, {
                                    method: 'POST',
                                    headers: {'Content-Type': 'application/json'},
                                    body: JSON.stringify(payload)
                                })
                                .then(response => {
                                    if (!response.ok) {
                                        throw new Error(`HTTP ${response.status}`);
                                    }
                                    return response.json();
                                })
                                .then(data => {
                                    
                                    frappe.dom.unfreeze();
                                    console.log('✅ Respuesta de De Facto:', data);
                                    
                                    if (data.success) {
                                        
                                        // PASO 6: Actualizar Cobranza
                                        frappe.call({
                                            method: 'frappe.client.set_value',
                                            args: {
                                                doctype: 'Cobranza_Cliente',
                                                name: doc_name,
                                                fieldname: {
                                                    'estado_cobranza': 'Facturado',
                                                    'factura_generada': 1,
                                                    'fecha_facturacion': frappe.datetime.nowdate(),
                                                    'folio_factura': data.folio || '',
                                                    'numero_factura': data.numero_factura || '',
                                                    'pdf_factura_url': data.pdf_url || '',
                                                    'pdf_factura_drive_id': data.drive_file_id || '',
                                                    'pdf_factura_drive_url': data.drive_url || ''
                                                }
                                            },
                                            callback: function() {
                                                frappe.msgprint({
                                                    title: '✅ Factura creada',
                                                    message: `Factura borrador creada exitosamente.<br><br>
                                                             <strong>Folio:</strong> ${data.folio || 'N/A'}<br>
                                                             <strong>Número:</strong> ${data.numero_factura || 'N/A'}<br><br>
                                                             <small>PDF guardado en Google Drive.</small>`,
                                                    indicator: 'green'
                                                });
                                                
                                                renderizar_panel_cobranza(frm);
                                            }
                                        });
                                        
                                    } else {
                                        frappe.msgprint({
                                            title: '❌ Error en De Facto',
                                            message: data.message || 'No se pudo crear la factura',
                                            indicator: 'red'
                                        });
                                    }
                                })
                                .catch(error => {
                                    frappe.dom.unfreeze();
                                    console.error('❌ Error:', error);
                                    frappe.msgprint({
                                        title: '❌ Error de conexión',
                                        message: `No se pudo conectar con De Facto.<br><br>${error.message}`,
                                        indicator: 'red'
                                    });
                                    }); // Cierra el then
                                });
                            }
                        }
                    });
                }
            });
        }
    );
}

// ===================================================================
// FUNCIÓN: VER COMPROBANTE
// ===================================================================
function ver_comprobante(doc_name) {
    frappe.call({
        method: 'frappe.client.get_value',
        args: {
            doctype: 'Cobranza_Cliente',
            filters: { name: doc_name },
            fieldname: 'comprobante_pago'
        },
        callback: function(r) {
            if (r.message && r.message.comprobante_pago) {
                window.open(r.message.comprobante_pago, '_blank');
            } else {
                frappe.msgprint('No hay comprobante de pago cargado.');
            }
        }
    });
}