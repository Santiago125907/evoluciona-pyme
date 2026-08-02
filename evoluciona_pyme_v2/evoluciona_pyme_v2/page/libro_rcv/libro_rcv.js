frappe.pages['libro_rcv'].on_page_load = function(wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Libros RCV',
        single_column: true
    });

    // ── Estilos ────────────────────────────────────────────────────────────────
    $(wrapper).find('.page-content').append(`
    <style>
        .lrcv-wrap { padding: 12px 16px; }
        .lrcv-resumen { display:flex; flex-wrap:wrap; gap:10px; margin-bottom:16px; }
        .lrcv-card {
            background:#fff; border:1px solid #e2e8f0; border-radius:8px;
            padding:10px 16px; min-width:160px; flex:1;
        }
        .lrcv-card .tipo { font-size:11px; color:#64748b; font-weight:600; text-transform:uppercase; }
        .lrcv-card .cant { font-size:12px; color:#94a3b8; margin:2px 0; }
        .lrcv-card .monto { font-size:16px; font-weight:700; color:#0f172a; }
        .lrcv-card .total-lbl { font-size:10px; color:#94a3b8; }
        .lrcv-card-total { border-color:#3b82f6; background:#eff6ff; }
        .lrcv-card-total .monto { color:#1d4ed8; }
        .lrcv-table-wrap { overflow-x:auto; border:1px solid #e2e8f0; border-radius:8px; background:#fff; }
        .lrcv-table { width:100%; border-collapse:collapse; font-size:12px; }
        .lrcv-table thead th {
            background:#f8fafc; color:#475569; font-weight:600;
            padding:8px 10px; border-bottom:2px solid #e2e8f0;
            white-space:nowrap; text-align:left;
        }
        .lrcv-table tbody tr:hover { background:#f1f5f9; }
        .lrcv-table tbody td { padding:7px 10px; border-bottom:1px solid #f1f5f9; vertical-align:middle; }
        .lrcv-table tbody tr:last-child td { border-bottom:none; }
        .lrcv-monto { text-align:right; font-variant-numeric:tabular-nums; }
        .lrcv-badge {
            display:inline-block; padding:2px 7px; border-radius:20px;
            font-size:10px; font-weight:600; white-space:nowrap;
            background:#e0f2fe; color:#0369a1;
        }
        .lrcv-btn { border:none; border-radius:5px; padding:4px 9px; cursor:pointer; font-size:12px; }
        .lrcv-btn-edit { background:#e0f2fe; color:#0369a1; margin-right:4px; }
        .lrcv-btn-del  { background:#fee2e2; color:#b91c1c; }
        .lrcv-btn:hover { opacity:0.8; }
        .lrcv-empty { text-align:center; padding:40px; color:#94a3b8; font-size:14px; }
        .lrcv-loading { text-align:center; padding:30px; color:#64748b; }
        .lrcv-total-row td { background:#f8fafc; font-weight:700; border-top:2px solid #e2e8f0; }
    </style>
    <div class="lrcv-wrap">
        <div class="lrcv-resumen" id="lrcv-resumen"></div>
        <div class="lrcv-table-wrap">
            <div class="lrcv-loading" id="lrcv-tabla">Selecciona un cliente y período.</div>
        </div>
    </div>`);

    // ── Opciones por libro ─────────────────────────────────────────────────────
    const TIPOS_COMPRA = [
        'FACTURA ELECTRÓNICA','FACTURA NO ELECTRÓNICA','FACTURA EXENTA ELECTRÓNICA',
        'NOTA DE CRÉDITO ELECTRÓNICA','NOTA DE DÉBITO ELECTRÓNICA','LIQUIDACIÓN FACTURA','OTRO'
    ];
    const TIPOS_VENTA = [
        'FACTURA ELECTRÓNICA','FACTURA NO ELECTRÓNICA','NOTA DE CRÉDITO ELECTRÓNICA',
        'NOTA DE DÉBITO ELECTRÓNICA','Total Oper. del mes Boleta Electr.(39)',
        'Total Oper. del mes Boleta Exenta Electr.(41)','Total mes Comprobantes Pago Electrónico(48)'
    ];
    const TIPOS_HON = ['Recibida','Emitida'];

    const ANO_OPTS = ['2023','2024','2025','2026','2027'].join('\n');
    const MES_OPTS = ['1','2','3','4','5','6','7','8','9','10','11','12'].join('\n');
    const MESES_NOM = ['Enero','Febrero','Marzo','Abril','Mayo','Junio',
                       'Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'];

    // ── Filtros ────────────────────────────────────────────────────────────────
    const hoy = new Date();
    // params se leen después de inicializar los filtros

    let sel_cliente = page.add_field({
        fieldname:'cliente', label:'Cliente', fieldtype:'Link',
        options:'Ficha_Cliente', change() { cargar(); }
    });
    let sel_ano = page.add_field({
        fieldname:'ano', label:'Año', fieldtype:'Select',
        options: ANO_OPTS, default: String(hoy.getFullYear()),
        change() { cargar(); }
    });
    let sel_mes = page.add_field({
        fieldname:'mes', label:'Mes', fieldtype:'Select',
        options: MES_OPTS, default: String(hoy.getMonth() + 1),
        change() { cargar(); }
    });
    let sel_libro = page.add_field({
        fieldname:'libro', label:'Libro', fieldtype:'Select',
        options:'Compras\nVentas\nHonorarios', default:'Compras',
        change() { actualizar_tipo_opts(); cargar(); }
    });
    let sel_tipo = page.add_field({
        fieldname:'tipo_doc', label:'Tipo Documento', fieldtype:'Select',
        options:'\n' + TIPOS_COMPRA.join('\n'),
        change() { cargar(); }
    });

    page.add_button(__('+ Agregar'), () => abrir_dialog_crear(), {btn_class:'btn-primary'});
    page.add_button(__('↺ Recargar'), () => cargar());

    // Pre-llenar desde route_options (venimos del F29) o URL args
    const params = frappe.route_options || frappe.utils.get_url_args() || {};
    frappe.route_options = null;  // limpiar para no reusar en navegaciones futuras
    if (params.cliente) sel_cliente.set_value(params.cliente);
    if (params.ano)     sel_ano.set_value(String(params.ano));
    if (params.mes)     sel_mes.set_value(String(params.mes));
    if (params.libro) {
        const l = String(params.libro);
        sel_libro.set_value(l.charAt(0).toUpperCase() + l.slice(1));
    }

    // ── Helpers ────────────────────────────────────────────────────────────────
    function fmt(n) {
        const v = parseFloat(n || 0);
        if (!v) return '—';
        return '$' + v.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, '.');
    }
    function esc(s) { return frappe.utils.escape_html(String(s || '')); }

    function libro_actual() { return (sel_libro.get_value() || 'Compras').toLowerCase(); }

    function actualizar_tipo_opts() {
        const libro = libro_actual();
        const tipos = libro === 'compras' ? TIPOS_COMPRA :
                      libro === 'ventas'  ? TIPOS_VENTA  : TIPOS_HON;
        sel_tipo.df.options = '\n' + tipos.join('\n');
        sel_tipo.refresh();
        sel_tipo.set_value('');
        const lbl = libro === 'honorarios' ? 'Tipo Boleta' : 'Tipo Documento';
        sel_tipo.$wrapper.find('label').text(lbl);
    }

    // ── Carga de datos ─────────────────────────────────────────────────────────
    function cargar() {
        const cliente  = sel_cliente.get_value();
        const ano      = sel_ano.get_value();
        const mes      = sel_mes.get_value();
        const libro    = libro_actual();
        const tipo_doc = sel_tipo.get_value() || '';

        if (!cliente || !ano || !mes) {
            $('#lrcv-resumen').html('');
            $('#lrcv-tabla').html('<div class="lrcv-empty">Selecciona cliente, año y mes.</div>');
            return;
        }

        $('#lrcv-tabla').html('<div class="lrcv-loading">⏳ Cargando...</div>');
        $('#lrcv-resumen').html('');

        // Cargar resumen y documentos en paralelo
        Promise.all([
            new Promise(resolve => {
                frappe.call({
                    method: 'evoluciona_pyme_v2.evoluciona_pyme_v2.api.get_resumen_libros',
                    args: { cliente, ano, mes, libro },
                    callback(r) { resolve(r.message || []); }
                });
            }),
            new Promise(resolve => {
                frappe.call({
                    method: 'evoluciona_pyme_v2.evoluciona_pyme_v2.api.get_documentos_libro',
                    args: { cliente, ano, mes, libro, tipo_doc },
                    callback(r) { resolve(r.message || []); }
                });
            })
        ]).then(([resumen, docs]) => {
            render_resumen(resumen, libro);
            render_tabla(docs, libro);
        });
    }

    // ── Render resumen ─────────────────────────────────────────────────────────
    function render_resumen(rows, libro) {
        if (!rows.length) { $('#lrcv-resumen').html(''); return; }

        let total_docs = 0, total_monto = 0;
        let cards = rows.map(r => {
            total_docs  += parseInt(r.cantidad || 0);
            total_monto += parseFloat(r.total || 0);
            return `<div class="lrcv-card">
                <div class="tipo">${esc(r.tipo || '—')}</div>
                <div class="cant">${r.cantidad} documento${r.cantidad != 1 ? 's' : ''}</div>
                <div class="monto">${fmt(r.total)}</div>
                <div class="total-lbl">Neto: ${fmt(r.total_neto)}</div>
            </div>`;
        }).join('');

        cards += `<div class="lrcv-card lrcv-card-total">
            <div class="tipo">TOTAL ${libro.toUpperCase()}</div>
            <div class="cant">${total_docs} documentos</div>
            <div class="monto">${fmt(total_monto)}</div>
        </div>`;

        $('#lrcv-resumen').html(cards);
    }

    // ── Render tabla ───────────────────────────────────────────────────────────
    function render_tabla(docs, libro) {
        if (!docs.length) {
            $('#lrcv-tabla').html('<div class="lrcv-empty">Sin documentos para este período.</div>');
            return;
        }

        let header = '', rows = '', totales = {};

        if (libro === 'compras') {
            header = `<tr>
                <th>Fecha</th><th>Tipo</th><th>Folio</th>
                <th>RUT Proveedor</th><th>Razón Social</th>
                <th class="lrcv-monto">Exento</th><th class="lrcv-monto">Neto</th>
                <th class="lrcv-monto">IVA Cred.</th><th class="lrcv-monto">Total</th>
                <th class="lrcv-monto">Costo</th><th></th>
            </tr>`;
            let t_exento=0, t_neto=0, t_iva=0, t_total=0, t_costo=0;
            rows = docs.map(d => {
                t_exento += parseFloat(d.monto_exento||0);
                t_neto   += parseFloat(d.neto||0);
                t_iva    += parseFloat(d.iva_credito||0);
                t_total  += parseFloat(d.total_documento||0);
                t_costo  += parseFloat(d.costo_empresa||0);
                return `<tr>
                    <td>${esc(d.fecha_documento||'')}</td>
                    <td><span class="lrcv-badge">${esc(d.tipo_documento||'')}</span></td>
                    <td>${esc(d.folio||'')}</td>
                    <td style="font-size:11px">${esc(d.rut_proveedor||'')}</td>
                    <td style="max-width:150px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${esc(d.razon_social_proveedor||'')}">${esc(d.razon_social_proveedor||'')}</td>
                    <td class="lrcv-monto">${fmt(d.monto_exento)}</td>
                    <td class="lrcv-monto">${fmt(d.neto)}</td>
                    <td class="lrcv-monto">${fmt(d.iva_credito)}</td>
                    <td class="lrcv-monto">${fmt(d.total_documento)}</td>
                    <td class="lrcv-monto">${fmt(d.costo_empresa)}</td>
                    <td>
                        <button class="lrcv-btn lrcv-btn-edit" onclick="lrcv_editar('${esc(d.name)}','compras')">✏️</button>
                        <button class="lrcv-btn lrcv-btn-del"  onclick="lrcv_eliminar('${esc(d.name)}','Libro_de_Compras_Cliente')">🗑️</button>
                    </td>
                </tr>`;
            }).join('');
            rows += `<tr class="lrcv-total-row">
                <td colspan="5">TOTALES (${docs.length} docs)</td>
                <td class="lrcv-monto">${fmt(t_exento)}</td>
                <td class="lrcv-monto">${fmt(t_neto)}</td>
                <td class="lrcv-monto">${fmt(t_iva)}</td>
                <td class="lrcv-monto">${fmt(t_total)}</td>
                <td class="lrcv-monto">${fmt(t_costo)}</td>
                <td></td>
            </tr>`;

        } else if (libro === 'ventas') {
            header = `<tr>
                <th>Fecha</th><th>Tipo</th><th>Folio</th>
                <th>RUT Receptor</th><th>Razón Social</th>
                <th class="lrcv-monto">Exento</th><th class="lrcv-monto">Neto</th>
                <th class="lrcv-monto">IVA</th><th class="lrcv-monto">Total</th><th></th>
            </tr>`;
            let t_exento=0, t_neto=0, t_iva=0, t_total=0;
            rows = docs.map(d => {
                t_exento += parseFloat(d.monto_exento||0);
                t_neto   += parseFloat(d.neto||0);
                t_iva    += parseFloat(d.iva||0);
                t_total  += parseFloat(d.total||0);
                return `<tr>
                    <td>${esc(d.fecha_documento||'')}</td>
                    <td><span class="lrcv-badge">${esc(d.tipo_documento||'')}</span></td>
                    <td>${esc(d.folio||'')}</td>
                    <td style="font-size:11px">${esc(d.rut_receptor||'')}</td>
                    <td style="max-width:150px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${esc(d.razon_social_receptor||'')}">${esc(d.razon_social_receptor||'')}</td>
                    <td class="lrcv-monto">${fmt(d.monto_exento)}</td>
                    <td class="lrcv-monto">${fmt(d.neto)}</td>
                    <td class="lrcv-monto">${fmt(d.iva)}</td>
                    <td class="lrcv-monto">${fmt(d.total)}</td>
                    <td>
                        <button class="lrcv-btn lrcv-btn-edit" onclick="lrcv_editar('${esc(d.name)}','ventas')">✏️</button>
                        <button class="lrcv-btn lrcv-btn-del"  onclick="lrcv_eliminar('${esc(d.name)}','Libro_de_Ingresos_Cliente')">🗑️</button>
                    </td>
                </tr>`;
            }).join('');
            rows += `<tr class="lrcv-total-row">
                <td colspan="5">TOTALES (${docs.length} docs)</td>
                <td class="lrcv-monto">${fmt(t_exento)}</td>
                <td class="lrcv-monto">${fmt(t_neto)}</td>
                <td class="lrcv-monto">${fmt(t_iva)}</td>
                <td class="lrcv-monto">${fmt(t_total)}</td>
                <td></td>
            </tr>`;

        } else { // honorarios
            header = `<tr>
                <th>Fecha</th><th>Tipo Boleta</th><th>N° Boleta</th>
                <th>RUT Prestador</th><th>Nombre Prestador</th>
                <th class="lrcv-monto">Bruto</th><th class="lrcv-monto">Retención</th>
                <th class="lrcv-monto">Líquido</th><th class="lrcv-monto">Costo</th><th></th>
            </tr>`;
            let t_bruto=0, t_ret=0, t_liq=0, t_costo=0;
            rows = docs.map(d => {
                t_bruto += parseFloat(d.monto_bruto||0);
                t_ret   += parseFloat(d.retencion_honorarios||0);
                t_liq   += parseFloat(d.monto_liquido||0);
                t_costo += parseFloat(d.costo_empresa||0);
                return `<tr>
                    <td>${esc(d.fecha_documento||'')}</td>
                    <td><span class="lrcv-badge">${esc(d.tipo_boleta||'')}</span></td>
                    <td>${esc(d.folio||'')}</td>
                    <td style="font-size:11px">${esc(d.rut_prestador||'')}</td>
                    <td style="max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${esc(d.nombre_prestador||'')}">${esc(d.nombre_prestador||'')}</td>
                    <td class="lrcv-monto">${fmt(d.monto_bruto)}</td>
                    <td class="lrcv-monto">${fmt(d.retencion_honorarios)}</td>
                    <td class="lrcv-monto">${fmt(d.monto_liquido)}</td>
                    <td class="lrcv-monto">${fmt(d.costo_empresa)}</td>
                    <td>
                        <button class="lrcv-btn lrcv-btn-edit" onclick="lrcv_editar('${esc(d.name)}','honorarios')">✏️</button>
                        <button class="lrcv-btn lrcv-btn-del"  onclick="lrcv_eliminar('${esc(d.name)}','Libro_de_Honorarios_Cliente')">🗑️</button>
                    </td>
                </tr>`;
            }).join('');
            rows += `<tr class="lrcv-total-row">
                <td colspan="5">TOTALES (${docs.length} docs)</td>
                <td class="lrcv-monto">${fmt(t_bruto)}</td>
                <td class="lrcv-monto">${fmt(t_ret)}</td>
                <td class="lrcv-monto">${fmt(t_liq)}</td>
                <td class="lrcv-monto">${fmt(t_costo)}</td>
                <td></td>
            </tr>`;
        }

        $('#lrcv-tabla').html(`
            <table class="lrcv-table">
                <thead>${header}</thead>
                <tbody>${rows}</tbody>
            </table>`);
    }

    // ── CRUD — Dialog crear/editar ─────────────────────────────────────────────
    function campos_dialog(libro, vals) {
        vals = vals || {};
        const cliente = sel_cliente.get_value();
        const ano     = sel_ano.get_value();
        const mes     = sel_mes.get_value();

        if (libro === 'compras') return [
            { label:'Fecha Documento', fieldname:'fecha_documento', fieldtype:'Date',
              reqd:1, default: vals.fecha_documento||'' },
            { label:'Tipo Documento', fieldname:'tipo_documento', fieldtype:'Select',
              options: TIPOS_COMPRA.join('\n'), reqd:1, default: vals.tipo_documento||'FACTURA ELECTRÓNICA' },
            { label:'Folio', fieldname:'folio', fieldtype:'Data', default: vals.folio||'' },
            { fieldtype:'Column Break' },
            { label:'RUT Proveedor', fieldname:'rut_proveedor', fieldtype:'Data', default: vals.rut_proveedor||'' },
            { label:'Razón Social Proveedor', fieldname:'razon_social_proveedor', fieldtype:'Data', default: vals.razon_social_proveedor||'' },
            { fieldtype:'Section Break', label:'Montos' },
            { label:'Monto Exento', fieldname:'monto_exento', fieldtype:'Currency', default: vals.monto_exento||0 },
            { label:'Neto', fieldname:'neto', fieldtype:'Currency', default: vals.neto||0 },
            { fieldtype:'Column Break' },
            { label:'IVA Crédito', fieldname:'iva_credito', fieldtype:'Currency', default: vals.iva_credito||0 },
            { label:'Total Documento', fieldname:'total_documento', fieldtype:'Currency', default: vals.total_documento||0 },
            { label:'Costo Empresa', fieldname:'costo_empresa', fieldtype:'Currency', default: vals.costo_empresa||0 },
        ];

        if (libro === 'ventas') return [
            { label:'Fecha Documento', fieldname:'fecha_documento', fieldtype:'Date',
              reqd:1, default: vals.fecha_documento||'' },
            { label:'Tipo Documento', fieldname:'tipo_documento', fieldtype:'Select',
              options: TIPOS_VENTA.join('\n'), reqd:1, default: vals.tipo_documento||'FACTURA ELECTRÓNICA' },
            { label:'Folio', fieldname:'folio', fieldtype:'Data', default: vals.folio||'' },
            { fieldtype:'Column Break' },
            { label:'RUT Receptor', fieldname:'rut_receptor', fieldtype:'Data', default: vals.rut_receptor||'' },
            { label:'Razón Social Receptor', fieldname:'razon_social_receptor', fieldtype:'Data', default: vals.razon_social_receptor||'' },
            { fieldtype:'Section Break', label:'Montos' },
            { label:'Monto Exento', fieldname:'monto_exento', fieldtype:'Currency', default: vals.monto_exento||0 },
            { label:'Neto', fieldname:'neto', fieldtype:'Currency', default: vals.neto||0 },
            { fieldtype:'Column Break' },
            { label:'IVA', fieldname:'iva', fieldtype:'Currency', default: vals.iva||0 },
            { label:'Total', fieldname:'total', fieldtype:'Currency', default: vals.total||0 },
        ];

        // honorarios
        return [
            { label:'Fecha Documento', fieldname:'fecha_documento', fieldtype:'Date',
              reqd:1, default: vals.fecha_documento||'' },
            { label:'Tipo Boleta', fieldname:'tipo_boleta', fieldtype:'Select',
              options:'Recibida\nEmitida', reqd:1, default: vals.tipo_boleta||'Recibida' },
            { label:'N° Boleta', fieldname:'folio', fieldtype:'Data', default: vals.folio||'' },
            { fieldtype:'Column Break' },
            { label:'RUT Prestador', fieldname:'rut_prestador', fieldtype:'Data', default: vals.rut_prestador||'' },
            { label:'Nombre Prestador', fieldname:'nombre_prestador', fieldtype:'Data', default: vals.nombre_prestador||'' },
            { fieldtype:'Section Break', label:'Montos' },
            { label:'Monto Bruto', fieldname:'monto_bruto', fieldtype:'Currency', default: vals.monto_bruto||0 },
            { label:'Retención', fieldname:'retencion_honorarios', fieldtype:'Currency', default: vals.retencion_honorarios||0 },
            { fieldtype:'Column Break' },
            { label:'Monto Líquido', fieldname:'monto_liquido', fieldtype:'Currency', default: vals.monto_liquido||0 },
            { label:'Total Documento', fieldname:'total_documento', fieldtype:'Currency', default: vals.total_documento||0 },
            { label:'Costo Empresa', fieldname:'costo_empresa', fieldtype:'Currency', default: vals.costo_empresa||0 },
        ];
    }

    function doctype_de(libro) {
        return libro === 'compras' ? 'Libro_de_Compras_Cliente' :
               libro === 'ventas' ? 'Libro_de_Ingresos_Cliente' : 'Libro_de_Honorarios_Cliente';
    }

    function abrir_dialog_crear() {
        const libro   = libro_actual();
        const cliente = sel_cliente.get_value();
        const ano     = sel_ano.get_value();
        const mes     = sel_mes.get_value();
        if (!cliente) { frappe.msgprint('Selecciona un cliente primero.'); return; }

        const d = new frappe.ui.Dialog({
            title: `Agregar — ${libro.charAt(0).toUpperCase() + libro.slice(1)}`,
            fields: campos_dialog(libro),
            primary_action_label: 'Guardar',
            primary_action(vals) {
                d.hide();
                const doc = Object.assign(vals, {
                    doctype: doctype_de(libro),
                    cliente, ano_tributario: String(ano), mes_tributario: String(mes)
                });
                frappe.call({
                    method: 'frappe.client.insert', args: { doc },
                    callback(r) {
                        if (!r.exc) {
                            frappe.show_alert({ message:'Documento agregado', indicator:'green' }, 3);
                            cargar();
                        }
                    }
                });
            }
        });
        d.show();
    }

    // Exponer globalmente para los botones onclick inline
    window.lrcv_editar = function(name, libro) {
        frappe.call({
            method: 'frappe.client.get',
            args: { doctype: doctype_de(libro), name },
            callback(r) {
                if (!r.message) return;
                const vals = r.message;
                const d = new frappe.ui.Dialog({
                    title: `Editar — ${libro.charAt(0).toUpperCase() + libro.slice(1)}`,
                    fields: campos_dialog(libro, vals),
                    primary_action_label: 'Guardar',
                    primary_action(nuevos) {
                        d.hide();
                        const doc = Object.assign(vals, nuevos);
                        frappe.call({
                            method: 'frappe.client.save', args: { doc },
                            callback(r2) {
                                if (!r2.exc) {
                                    frappe.show_alert({ message:'Documento actualizado', indicator:'green' }, 3);
                                    cargar();
                                }
                            }
                        });
                    }
                });
                d.show();
            }
        });
    };

    window.lrcv_eliminar = function(name, doctype) {
        frappe.confirm('¿Eliminar este documento? Esta acción no se puede deshacer.', () => {
            frappe.call({
                method: 'frappe.client.delete',
                args: { doctype, name },
                callback(r) {
                    frappe.show_alert({ message:'Documento eliminado', indicator:'orange' }, 3);
                    cargar();
                }
            });
        });
    };

    // Carga inicial si vienen parámetros
    setTimeout(() => {
        if (sel_cliente.get_value()) cargar();
    }, 400);
};
