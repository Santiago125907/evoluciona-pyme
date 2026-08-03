frappe.pages['panel_mensual'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Panel Mensual',
        single_column: true
    });

    // ── Período por defecto: mes anterior ────────────────────────────────────
    const hoy  = new Date();
    const prev = new Date(hoy.getFullYear(), hoy.getMonth() - 1, 1);
    const mes_def = prev.getMonth() + 1;
    const ano_def = prev.getFullYear();

    let sel_ano = page.add_field({
        fieldname: 'ano', label: 'Año', fieldtype: 'Select',
        options: ['2023','2024','2025','2026','2027'].join('\n'),
        default: String(ano_def),
        change() { cargar_panel(); }
    });
    let sel_mes = page.add_field({
        fieldname: 'mes', label: 'Mes', fieldtype: 'Select',
        options: Array.from({length:12},(_,i)=>String(i+1)).join('\n'),
        default: String(mes_def),
        change() { cargar_panel(); }
    });
    let sel_filtro = page.add_field({
        fieldname: 'filtro', label: 'Filtrar por', fieldtype: 'Select',
        options: 'Todos\nSin declaración\nBorrador\nEn Validación\nListo\nPublicado\nEnviado',
        default: 'Todos',
        change() { aplicar_filtro(); }
    });

    page.add_button('Cargar', cargar_panel, {btn_class: 'btn-primary'});

    // "Crear Todas" / "Calcular Todas" — masivo para el período seleccionado arriba.
    // Solo visibles para rol admin: escriben datos reales para todos los clientes.
    let btn_crear_todas = page.add_button('🗓️ Crear Todas', crear_todas_periodo, {btn_class: 'btn-default'});
    let btn_calcular_todas = page.add_button('🧮 Calcular Todas', calcular_todos_periodo, {btn_class: 'btn-default'});
    btn_crear_todas.hide();
    btn_calcular_todas.hide();
    frappe.call({
        method: 'evoluciona_pyme_v2.evoluciona_pyme_v2.asesores.get_rol_usuario',
        callback(r) {
            if (r.message === 'admin') {
                btn_crear_todas.show();
                btn_calcular_todas.show();
            }
        }
    });

    // ── HTML base ─────────────────────────────────────────────────────────────
    $(wrapper).find('.page-content').append(`
    <style>
        .pm-wrap { font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; padding:0 0 40px; }
        .pm-stats { background:#fff; border-radius:10px; padding:14px 20px; margin-bottom:12px;
                    box-shadow:0 2px 8px rgba(0,0,0,.06); display:flex; align-items:center;
                    justify-content:space-around; flex-wrap:wrap; gap:10px; }
        .pm-stat strong { display:block; font-size:20px; color:#005f6b; font-weight:800; }
        .pm-stat span   { font-size:10px; color:#888; text-transform:uppercase; letter-spacing:.5px; }
        .pm-progress-wrap { background:#fff; border-radius:10px; padding:12px 20px; margin-bottom:12px;
                            box-shadow:0 2px 8px rgba(0,0,0,.06); }
        .pm-progress-bar  { height:10px; border-radius:5px; background:#e9ecef; overflow:hidden; margin-top:6px; }
        .pm-progress-fill { height:100%; border-radius:5px;
                            background:linear-gradient(90deg,#27ae60,#17a2b8); transition:width .4s; }
        .pm-bulk { background:#fff3cd; border:1px solid #ffc107; border-radius:8px; padding:8px 14px;
                   margin-bottom:10px; display:none; align-items:center; gap:10px; flex-wrap:wrap; }
        .pm-bulk span { font-size:12px; font-weight:600; color:#856404; }
        .pm-table-wrap { background:#fff; border-radius:10px; box-shadow:0 2px 8px rgba(0,0,0,.06); overflow:hidden; }
        .pm-table { width:100%; border-collapse:collapse; font-size:12px; }
        .pm-table thead tr { background:linear-gradient(135deg,#1a3a4a,#005f6b); color:#fff; }
        .pm-table th { padding:10px 8px; font-size:10px; font-weight:700; text-transform:uppercase;
                       letter-spacing:.8px; white-space:nowrap; }
        .pm-table td { padding:8px 7px; border-bottom:1px solid #eef0f3; vertical-align:middle; }
        .pm-table tr:hover td { background:#f7fafc; }
        .pm-table tr.pm-hidden { display:none; }

        /* ── Fila expandida ─────────────────────────────────────────── */
        .pm-expand-toggle { display:inline-flex; align-items:center; gap:3px; cursor:pointer; user-select:none;
                             background:#e8f0f2; color:#005f6b; border:1px solid #cfe0e3; border-radius:12px;
                             padding:2px 8px; font-size:10px; font-weight:700; margin-bottom:3px; }
        .pm-expand-toggle:hover { background:#d7e6e9; }
        .pm-expand-toggle .arrow { transition:transform .15s; display:inline-block; }
        .pm-expand-toggle.open .arrow { transform:rotate(90deg); }
        .pm-expand-toggle.open { background:#005f6b; color:#fff; border-color:#005f6b; }
        .pm-detail-row td { background:#f4f7f9; padding:16px 20px; border-bottom:2px solid #dde3e8; }
        .pm-detail-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(230px,1fr)); gap:14px; }
        .pm-detail-card { background:#fff; border-radius:8px; padding:12px 14px; box-shadow:0 1px 4px rgba(0,0,0,.06); }
        .pm-detail-card h5 { margin:0 0 8px; font-size:11px; text-transform:uppercase; letter-spacing:.5px;
                              color:#8a9bb0; font-weight:700; }
        .pm-cred-row { display:flex; align-items:center; gap:6px; margin-bottom:6px; font-size:12px; }
        .pm-cred-label { color:#888; width:38px; flex-shrink:0; }
        .pm-cred-val { font-family:monospace; background:#f0f2f5; padding:3px 8px; border-radius:4px;
                       flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
        .pm-copy-btn { border:none; background:#e9ecef; border-radius:4px; padding:3px 7px; cursor:pointer;
                       font-size:11px; flex-shrink:0; }
        .pm-copy-btn:hover { background:#dde1e5; }
        .pm-open-btn { display:inline-block; margin-top:4px; font-size:11px; padding:4px 10px; border-radius:5px;
                       background:#005f6b; color:#fff; text-decoration:none; }
        .pm-open-btn:hover { background:#004a54; color:#fff; }
        .pm-import-btn { display:block; width:100%; text-align:left; border:none; background:#f0f2f5;
                         border-radius:6px; padding:7px 10px; margin-bottom:6px; cursor:pointer; font-size:12px; }
        .pm-import-btn:hover { background:#e4e8ec; }
        .pm-import-btn:last-child { margin-bottom:0; }
        .badge-est { padding:3px 8px; border-radius:10px; font-size:10px; font-weight:700; white-space:nowrap; }
        .est-borrador { background:#ffc107; color:#000; }
        .est-validar  { background:#ff9800; color:#fff; }
        .est-listo    { background:#28a745; color:#fff; }
        .est-pdf      { background:#0984e3; color:#fff; }
        .est-publicado{ background:#6f42c1; color:#fff; }
        .est-enviado  { background:#17a2b8; color:#fff; }
        .est-sin      { background:#e9ecef; color:#888; }
        .btn-pm { padding:3px 7px; margin:1px; font-size:11px; border-radius:4px;
                  border:1px solid #ddd; background:#fff; cursor:pointer; transition:all .15s; white-space:nowrap; }
        .btn-pm:hover { background:#005f6b; color:#fff; border-color:#005f6b; }
        .btn-pm.danger:hover { background:#c0392b; border-color:#c0392b; }
        .cred-val    { font-family:monospace; font-size:11px; color:#555; }
        .cred-toggle { font-size:10px; color:#aaa; cursor:pointer; text-decoration:underline; margin-left:3px; }
        .pm-loading  { text-align:center; padding:40px; color:#999; }
        /* Hover-detail genérico: usado en Total F29, Postergación, Previred y Cobranza */
        .pm-hover-wrap { position:relative; display:inline-block; cursor:help; }
        .pm-hover-wrap:hover, .pm-hover-wrap:hover * { color:#005f6b !important; }
        .pm-hover-wrap[title]:hover::after {
            content: attr(title); white-space:pre;
            position:absolute; left:0; top:100%; z-index:999;
            background:#2c3e50; color:#fff !important; font-size:11px; line-height:1.6;
            padding:6px 10px; border-radius:6px; min-width:160px;
            box-shadow:0 4px 12px rgba(0,0,0,.3); pointer-events:none;
        }
        .pm-f29-total { font-size:11px; font-weight:700; }
        .pm-f29-positivo { color:#c0392b; }
        .pm-f29-cero     { color:#27ae60; }
        .cobro-monto { font-size:11px; font-weight:700; color:#005f6b; }
        .cobro-est   { font-size:10px; color:#888; }
        input.pm-chk { width:15px; height:15px; cursor:pointer; }
        .btn-bulk { padding:4px 12px; font-size:11px; border-radius:5px; border:none;
                    cursor:pointer; font-weight:600; }
    </style>
    <div class="pm-wrap">
        <div id="pm-stats"  class="pm-stats"  style="display:none;">
            <div class="pm-stat"><strong id="pm-total">—</strong><span>Clientes</span></div>
            <div class="pm-stat"><strong id="pm-con-dec">—</strong><span>Con declaración</span></div>
            <div class="pm-stat"><strong id="pm-listos">—</strong><span>Listos</span></div>
            <div class="pm-stat"><strong id="pm-publicados" style="color:#6f42c1;">—</strong><span>Publicados</span></div>
            <div class="pm-stat"><strong id="pm-enviados">—</strong><span>Enviados</span></div>
            <div class="pm-stat"><strong id="pm-sin-dec">—</strong><span>Sin declaración</span></div>
        </div>
        <div id="pm-progress" class="pm-progress-wrap" style="display:none;">
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <span style="font-size:11px;font-weight:600;color:#555;">Progreso del período</span>
                <span id="pm-pct" style="font-size:11px;font-weight:700;color:#005f6b;"></span>
            </div>
            <div class="pm-progress-bar"><div id="pm-fill" class="pm-progress-fill" style="width:0%"></div></div>
        </div>
        <div id="pm-bulk" class="pm-bulk">
            <span id="pm-bulk-count">0 seleccionados</span>
            <button class="btn-bulk" style="background:#ffc107;color:#000;" onclick="pm_bulk('check-rrhh')">✓ RRHH</button>
            <button class="btn-bulk" style="background:#ffc107;color:#000;" onclick="pm_bulk('check-f29')">✓ F29</button>
            <button class="btn-bulk" style="background:#ffc107;color:#000;" onclick="pm_bulk('check-prev')">✓ Prev</button>
            <button class="btn-bulk" style="background:#6f42c1;color:#fff;"  onclick="pm_bulk('publicar')">📱 Publicar</button>
            <button class="btn-bulk" style="background:#c0392b;color:#fff;"  onclick="pm_bulk('reset')">↩ Resetear</button>
        </div>
        <div id="pm-content"><div class="pm-loading">Selecciona un período y haz clic en <b>Cargar</b></div></div>
    </div>`);

    // ── Estado global ─────────────────────────────────────────────────────────
    let _clientes = [], _dec_map = {}, _cobro_map = {}, _cobro_pendiente_map = {}, _f29_map = {}, _remu_map = {},
        _post_map = {}, _post_vence_map = {}, _ano, _mes, _expandido = null;

    // ── Cargar datos ──────────────────────────────────────────────────────────
    // Crea Declaracion_Mensual + Borrador_F29 para TODOS los clientes activos del
    // período seleccionado (año/mes de arriba). Idempotente — no duplica lo que ya existe.
    function crear_todas_periodo() {
        if (!_ano || !_mes) { frappe.msgprint('Selecciona un período primero.'); return; }

        frappe.confirm(
            `Esto va a crear la Declaración Mensual y el Borrador F29 de <b>${_mes}/${_ano}</b> para ` +
            `todos los clientes activos que todavía no lo tengan. No duplica los que ya existen. ¿Continuar?`,
            () => {
                frappe.dom.freeze(`Creando declaraciones de ${_mes}/${_ano}...`);
                frappe.call({
                    method: 'evoluciona_pyme_v2.evoluciona_pyme_v2.api.procesar_mes_actual',
                    args: { mes: _mes, ano: _ano },
                    callback(r) {
                        frappe.dom.unfreeze();
                        const res = r.message || {};
                        frappe.msgprint({
                            title: __('Listo'),
                            indicator: res.errores ? 'orange' : 'green',
                            message: res.message || 'Proceso terminado.'
                        });
                        cargar_panel();
                    },
                    error() { frappe.dom.unfreeze(); }
                });
            }
        );
    }

    // Corre "Calcular F29" para TODOS los Borrador_F29 del período seleccionado arriba.
    function calcular_todos_periodo() {
        if (!_ano || !_mes) { frappe.msgprint('Selecciona un período primero.'); return; }

        frappe.confirm(
            `Esto va a calcular el F29 de <b>${_mes}/${_ano}</b> para todos los clientes que ya ` +
            `tengan declaración creada, usando los documentos tributarios ya cargados. ¿Continuar?`,
            () => {
                frappe.dom.freeze(`Calculando F29 de ${_mes}/${_ano}...`);
                frappe.call({
                    method: 'evoluciona_pyme_v2.evoluciona_pyme_v2.api.calcular_todos_periodo',
                    args: { mes: _mes, ano: _ano },
                    callback(r) {
                        frappe.dom.unfreeze();
                        const res = r.message || {};
                        frappe.msgprint({
                            title: __('Listo'),
                            indicator: res.errores ? 'orange' : 'green',
                            message: res.message || 'Proceso terminado.'
                        });
                        cargar_panel();
                    },
                    error() { frappe.dom.unfreeze(); }
                });
            }
        );
    }

    // Marca una Cobranza_Cliente como Pagada. Si llegó atrasada, pregunta si
    // aplicar el recargo configurado a la cobranza del mes siguiente -- lo
    // decide quien paga, no se infiere solo de la fecha.
    function pagar_cobranza(cobro) {
        frappe.call({
            method: 'frappe.client.get',
            args: { doctype:'Cobranza_Cliente', name:cobro },
            callback(r_cob) {
                const venc = r_cob.message && r_cob.message.fecha_vencimiento;
                const atrasado = venc && frappe.datetime.get_diff(frappe.datetime.nowdate(), venc) > 0;

                const marcar = (aplicar_recargo) => {
                    frappe.call({
                        method: 'evoluciona_pyme_v2.evoluciona_pyme_v2.api.marcar_cobranza_pagada',
                        args: { cobranza_name:cobro, aplicar_recargo: aplicar_recargo ? 1 : 0 },
                        callback() {
                            frappe.show_alert({message:'💰 Marcado como Pagado',indicator:'green'},3);
                            setTimeout(cargar_panel,500);
                        }
                    });
                };

                if (!atrasado) { marcar(false); return; }

                frappe.db.get_single_value('Configuracion App','monto_recargo_pago_atrasado').then(monto => {
                    frappe.confirm(
                        `Este pago llegó atrasado (vencía el ${frappe.datetime.str_to_user(venc)}).<br><br>` +
                        `¿Agregar recargo de <b>$${(monto||0).toLocaleString('es-CL')}</b> a la cobranza del próximo mes?`,
                        () => marcar(true),
                        () => marcar(false)
                    );
                });
            }
        });
    }

    // ── Fila expandida por cliente (solo una a la vez) ──────────────────────────
    function toggle_expand_cliente(cliente, $toggle) {
        const fila_existente = $(`#pm-content tr.pm-detail-row[data-cliente="${cliente}"]`);

        if (_expandido === cliente) {
            fila_existente.remove();
            $toggle.removeClass('open');
            _expandido = null;
            return;
        }

        // Colapsar cualquier otra fila abierta
        $('#pm-content tr.pm-detail-row').remove();
        $('#pm-content .pm-expand-toggle').removeClass('open');
        _expandido = cliente;
        $toggle.addClass('open');

        const $fila_cliente = $(`#pm-content tr[data-cliente="${cliente}"]`).not('.pm-detail-row');
        const $detalle = $(`<tr class="pm-detail-row" data-cliente="${esc(cliente)}">
            <td colspan="11"><div class="pm-loading"><i class="fa fa-spinner fa-spin"></i> Cargando...</div></td>
        </tr>`);
        $fila_cliente.after($detalle);

        cargar_detalle_cliente(cliente, $detalle);
    }

    function cargar_detalle_cliente(cliente, $detalle) {
        frappe.call({
            method: 'evoluciona_pyme_v2.evoluciona_pyme_v2.api.get_credenciales_cliente',
            args: { cliente },
            callback(r) {
                const cred = r.message || {};
                const d = _dec_map[cliente];
                const f29_name = d ? d.borrador_f29_vinculado : null;

                const fila_copiable = (label, val, id) => val
                    ? `<div class="pm-cred-row">
                           <span class="pm-cred-label">${label}</span>
                           <span class="pm-cred-val" id="${id}">${esc(val)}</span>
                           <button class="pm-copy-btn" onclick="pm_copiar('${id}')">📋</button>
                       </div>`
                    : `<div class="pm-cred-row"><span class="pm-cred-label">${label}</span><span style="color:#ccc;">—</span></div>`;

                const sii_html = `
                    <div class="pm-detail-card">
                        <h5>Acceso SII</h5>
                        ${fila_copiable('RUT', cred.rut_sii, `sii-rut-${cliente}`)}
                        ${fila_copiable('Clave', cred.clave_sii, `sii-clave-${cliente}`)}
                        ${cred.rut_sii ? `<a class="pm-open-btn" href="https://zeusr.sii.cl/AUT2000/InicioAutenticacion/IngresoRutClave.html" target="_blank">Abrir SII ↗</a>` : ''}
                    </div>`;

                // Solo se muestra si el cliente tiene obligación real de Previred este
                // período (monto > 0) -- tener las credenciales guardadas no basta, puede
                // no tener empleados ese mes.
                const remu = _remu_map[cliente];
                const tiene_previred_este_mes = remu && parseFloat(remu.total_previred_a_pagar || 0) > 0;
                const previred_html = tiene_previred_este_mes
                    ? `<div class="pm-detail-card">
                        <h5>Acceso Previred</h5>
                        ${fila_copiable('RUT', cred.rut_previred, `prev-rut-${cliente}`)}
                        ${fila_copiable('Clave', cred.clave_previred, `prev-clave-${cliente}`)}
                        ${cred.rut_previred ? `<a class="pm-open-btn" href="https://www.previred.com" target="_blank">Abrir Previred ↗</a>` : ''}
                    </div>`
                    : '';

                const ESTADOS_PAGO = ['Pendiente de Pago','Pagado','Postergado','Vencido sin Pagar'];
                const select_estado = (doctype, name, valor_actual, extra) => `
                    <select class="form-control" style="font-size:12px;padding:3px 6px;height:auto;"
                            onchange="pm_set_estado_pago('${doctype}','${name}',this.value,'${valor_actual}',${extra})">
                        ${ESTADOS_PAGO.map(v => `<option value="${v}" ${v===valor_actual?'selected':''}>${v}</option>`).join('')}
                    </select>`;

                // El estado de pago del F29 solo tiene sentido una vez que la declaración
                // está lista (evita marcar pagado/postergado algo que ni siquiera está calculado).
                const f29_data = f29_name ? _f29_map[f29_name] : null;
                const mostrar_estado_f29 = f29_name && d && ['Listo','PDF Generado','Publicado'].includes(d.estado);

                // La postergación solo se muestra si existe (tiene monto) para este período,
                // y bajo la misma regla de estado que el F29 -- son parte del mismo flujo.
                const post_detalle = _post_map[cliente];
                const mostrar_postergacion = mostrar_estado_f29 && post_detalle;
                const postergacion_html = mostrar_postergacion ? `
                    <div class="pm-cred-row"><span class="pm-cred-label" style="width:55px;">Posterg.</span>
                        <button class="form-control" style="font-size:12px;padding:3px 6px;height:auto;text-align:left;cursor:pointer;"
                                onclick="pm_toggle_postergacion_pagada('${post_detalle.name}','${post_detalle.estado}')">
                            ${post_detalle.estado === 'Pagada' ? '✅ Pagada' : '⏳ Pendiente'} — $${fmt_num(post_detalle.monto_postergado||0)}
                        </button>
                    </div>` : '';

                const estado_pago_html = (mostrar_estado_f29 || tiene_previred_este_mes)
                    ? `<div class="pm-detail-card">
                        <h5>Estado de Pago</h5>
                        ${mostrar_estado_f29 ? `<div class="pm-cred-row"><span class="pm-cred-label" style="width:55px;">F29</span>
                            ${select_estado('Borrador_F29', f29_name, f29_data ? f29_data.estado_pago_f29 : 'Pendiente de Pago', f29_data ? (f29_data.impuesto_determinado||0) : 0)}</div>` : ''}
                        ${postergacion_html}
                        ${tiene_previred_este_mes ? `<div class="pm-cred-row"><span class="pm-cred-label" style="width:55px;">Previred</span>
                            ${select_estado('Registro_Remuneraciones', remu.name, remu.estado_pago_previred || 'Pendiente de Pago', 0)}</div>` : ''}
                    </div>`
                    : '';

                const import_html = `
                    <div class="pm-detail-card">
                        <h5>Cargar Documentos — ${_mes}/${_ano}</h5>
                        <button class="pm-import-btn" ${f29_name?'':'disabled'} onclick="pm_cargar_api('${cliente}','${f29_name||''}','compras')">📥 Compras (API SII)</button>
                        <button class="pm-import-btn" ${f29_name?'':'disabled'} onclick="pm_cargar_api('${cliente}','${f29_name||''}','ventas')">📥 Ventas (API SII)</button>
                        <button class="pm-import-btn" ${f29_name?'':'disabled'} onclick="pm_cargar_api('${cliente}','${f29_name||''}','honorarios')">📥 Honorarios (API SII)</button>
                        <button class="pm-import-btn" onclick="pm_importar_lre('${cliente}')">📄 Remuneraciones (CSV LRE)</button>
                        ${f29_name?'':'<small style="color:#e67e22;">Crea la declaración primero para cargar por API.</small>'}
                    </div>`;

                const cobranza_html = `
                    <div class="pm-detail-card">
                        <h5>Cobranza</h5>
                        <button class="pm-import-btn" onclick="pm_ver_cobranzas_pendientes('${cliente}')">💰 Ver cobranzas pendientes</button>
                    </div>`;

                $detalle.find('td').html(`<div class="pm-detail-grid">${sii_html}${previred_html}${estado_pago_html}${import_html}${cobranza_html}</div>`);
            }
        });
    }

    // Botones de importar API para una sola de las 3 fuentes a la vez
    window.pm_cargar_api = function(cliente, f29_name, fuente) {
        if (!f29_name) { frappe.msgprint('Este cliente no tiene declaración creada para este período.'); return; }
        const args = { doc_name: f29_name, compras:0, ventas:0, honorarios:0 };
        args[fuente] = 1;
        frappe.show_alert({message:`Cargando ${fuente}...`, indicator:'blue'}, 3);
        frappe.call({
            method: 'evoluciona_pyme_v2.evoluciona_pyme_v2.rcv_api.cargar_documentos_api',
            args,
            callback(r) {
                const res = r.message || {};
                frappe.show_alert({message: res.ok!==false ? `✅ ${res.detalle||'Cargado'}` : 'Error al cargar', indicator: res.ok!==false?'green':'red'}, 5);
            }
        });
    };

    window.pm_importar_lre = function(cliente) {
        const d = new frappe.ui.Dialog({
            title: 'Importar LRE — Libro de Remuneraciones Electrónico',
            fields: [
                { fieldtype:'HTML', options:`<div style="margin-bottom:8px;font-size:12px;color:#555;">Sube el CSV del LRE descargado de Previred. Período <b>${_mes}/${_ano}</b>.</div>` },
                { label:'Archivo CSV', fieldname:'archivo', fieldtype:'Attach', reqd:1, options:{restrictions:{allowed_file_types:['.csv','.CSV']}} }
            ],
            primary_action_label: 'Importar',
            primary_action(values) {
                if (!values.archivo) { frappe.msgprint('Selecciona un archivo CSV.'); return; }
                d.hide();
                frappe.dom.freeze('Procesando archivo...');
                frappe.call({
                    method: 'evoluciona_pyme_v2.evoluciona_pyme_v2.api.importar_lre_csv',
                    args: { cliente, mes:_mes, ano:_ano, file_url: values.archivo },
                    callback(r) {
                        frappe.dom.unfreeze();
                        const res = r.message || {};
                        if (res.status === 'ok') {
                            frappe.msgprint({title:'Importación exitosa', indicator:'green',
                                message:`<b>${res.empleados}</b> trabajadores, Total Previred: <b>$${(res.total_previred||0).toLocaleString('es-CL')}</b>`});
                            cargar_panel();
                        } else {
                            frappe.msgprint({title:'Error', message:res.message, indicator:'red'});
                        }
                    },
                    error() { frappe.dom.unfreeze(); }
                });
            }
        });
        d.show();
    };

    window.pm_ver_cobranzas_pendientes = function(cliente) {
        frappe.call({
            method: 'frappe.client.get_list',
            args: { doctype:'Cobranza_Cliente', filters:{cliente, estado_cobranza:['not in',['Pagado','Anulado']]},
                     fields:['name','periodo_mes','periodo_ano','monto_a_cobrar','estado_cobranza','fecha_vencimiento'],
                     order_by:'periodo_ano asc, periodo_mes asc', limit_page_length:50, ignore_permissions:1 },
            callback(r) {
                const filas = r.message || [];
                if (!filas.length) { frappe.msgprint('Este cliente no tiene cobranzas pendientes.'); return; }

                const html = filas.map(f => `
                    <tr>
                        <td>${f.periodo_mes}/${f.periodo_ano}</td>
                        <td>$${fmt_num(f.monto_a_cobrar)}</td>
                        <td>${esc(f.estado_cobranza)}</td>
                        <td>${f.fecha_vencimiento||''}</td>
                        <td><button class="btn btn-xs btn-primary" onclick="pm_pagar_desde_dialog('${f.name}')">Pagar</button></td>
                    </tr>`).join('');

                frappe.msgprint({
                    title: `Cobranzas pendientes — ${cliente}`,
                    message: `<table class="table table-bordered" style="font-size:12px;">
                        <thead><tr><th>Período</th><th>Monto</th><th>Estado</th><th>Vence</th><th></th></tr></thead>
                        <tbody>${html}</tbody></table>`,
                    wide: true
                });
            }
        });
    };

    window.pm_pagar_desde_dialog = function(cobro) {
        if (cur_dialog) cur_dialog.hide();
        pagar_cobranza(cobro);
    };

    window.pm_copiar = function(id) {
        const texto = document.getElementById(id).innerText;
        navigator.clipboard.writeText(texto).then(() => {
            frappe.show_alert({message:'Copiado', indicator:'green'}, 1.5);
        });
    };

    // Botón de la columna "Post.": alterna la postergación entre pendiente (Vigente) y Pagada.
    window.pm_toggle_postergacion_pagada = function(post_name, estado_actual) {
        const nuevo = estado_actual === 'Pagada' ? 'Vigente' : 'Pagada';
        frappe.call({
            method: 'frappe.client.set_value',
            args: { doctype:'Postergacion_IVA', name:post_name, fieldname:'estado', value:nuevo },
            callback() {
                frappe.show_alert({message:`✅ Postergación ${nuevo === 'Pagada' ? 'marcada como pagada' : 'marcada como pendiente'}`, indicator:'green'}, 3);
                cargar_panel();
            }
        });
    };

    // valor_anterior e iva_det solo aplican a Borrador_F29 (Previred no tiene postergación).
    window.pm_set_estado_pago = function(doctype, name, valor, valor_anterior, iva_det) {
        const fieldname = doctype === 'Borrador_F29' ? 'estado_pago_f29' : 'estado_pago_previred';

        const set_simple = () => {
            frappe.call({
                method: 'frappe.client.set_value',
                args: { doctype, name, fieldname, value: valor },
                callback() { frappe.show_alert({message:`✅ ${valor}`, indicator:'green'}, 2); }
            });
        };

        if (doctype !== 'Borrador_F29') { set_simple(); return; }

        // Pasar A Postergado: pide monto y meses, y crea la Postergacion_IVA real.
        if (valor === 'Postergado') {
            pm_dialog_postergar_iva(name, iva_det);
            return;
        }

        // Salir de Postergado hacia otro estado (se corrigió un error): cancela
        // la Postergacion_IVA asociada para que quede coordinado.
        if (valor_anterior === 'Postergado') {
            frappe.confirm(
                `Este F29 tenía una postergación de IVA registrada. Cambiar a "${valor}" la va a <b>cancelar</b>. ¿Continuar?`,
                () => {
                    frappe.call({
                        method: 'evoluciona_pyme_v2.evoluciona_pyme_v2.api.cancelar_postergacion_iva',
                        args: { doc_name: name },
                        callback() {
                            // La cancelación ya deja estado_pago_f29 en "Pendiente de Pago";
                            // si el usuario eligió otro valor distinto, lo aplicamos encima.
                            if (valor !== 'Pendiente de Pago') set_simple();
                            else { frappe.show_alert({message:'Postergación cancelada', indicator:'orange'}, 3); cargar_panel(); }
                        }
                    });
                },
                () => cargar_panel() // canceló el confirm -> refresca para volver a dejar el select en "Postergado"
            );
            return;
        }

        set_simple();
    };

    window.pm_dialog_postergar_iva = function(f29_name, iva_det) {
        const MESES = ['','Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'];
        const mes = parseInt(_mes), ano = parseInt(_ano);
        const m2 = ((mes+1) % 12) + 1; const a2 = mes >= 11 ? ano+1 : ano;

        const d = new frappe.ui.Dialog({
            title: '⏳ Postergar IVA — Art. 64 D.L. 825',
            fields: [
                { fieldtype:'HTML', options:`<div style="background:#fff8ec;border-left:3px solid #b45309;border-radius:4px;padding:10px 14px;margin-bottom:4px;font-size:12px;color:#7d4e00;">Difiere el pago del IVA determinado por <b>2 meses</b> (F29 de ${MESES[m2]} ${a2}). Solo Pro Pyme.</div>` },
                { label:'IVA Determinado del período', fieldname:'iva_det_info', fieldtype:'HTML', options:`<div style="font-size:22px;font-weight:800;color:#b45309;padding:6px 0 10px;">$${(iva_det||0).toLocaleString('es-CL')}</div>` },
                { label:'Monto a Postergar ($)', fieldname:'monto', fieldtype:'Currency', default: iva_det||0, reqd:1, description:'Máximo: IVA determinado del período' }
            ],
            primary_action_label: 'Registrar Postergación',
            primary_action(values) {
                if (values.monto <= 0) { frappe.msgprint('El monto debe ser mayor a 0.'); return; }
                if (values.monto > (iva_det||0)) { frappe.msgprint('El monto no puede superar el IVA determinado.'); return; }
                d.hide();
                frappe.call({
                    method: 'evoluciona_pyme_v2.evoluciona_pyme_v2.api.registrar_postergacion_iva',
                    args: { doc_name: f29_name, monto: values.monto, meses_diferidos: 2 },
                    freeze: true, freeze_message: 'Registrando postergación...',
                    callback(r) {
                        const res = r.message;
                        if (res?.status === 'ok') { frappe.show_alert({message:res.message, indicator:'orange'}, 6); cargar_panel(); }
                        else { frappe.msgprint({title:'Error', message:res?.message, indicator:'red'}); cargar_panel(); }
                    }
                });
            }
        });
        d.onhide = () => cargar_panel(); // si cancela el dialog, refresca para no dejar el select mal seleccionado
        d.show();
    };

    function cargar_panel() {
        _ano = sel_ano.get_value();
        _mes = sel_mes.get_value();
        if (!_ano || !_mes) return;

        $('#pm-content').html('<div class="pm-loading"><i class="fa fa-spinner fa-spin"></i> Cargando...</div>');
        $('#pm-stats,#pm-progress,#pm-bulk').hide();

        frappe.call({
            method: 'frappe.client.get_list',
            args: { doctype:'Ficha_Cliente', filters:{estado_cliente:'Activo'},
                    fields:['name','razon_social','clave_sii','rut_usuario'],
                    order_by:'razon_social asc', limit_page_length:200, ignore_permissions:1 },
            callback(r) {
                _clientes = r.message || [];
                if (!_clientes.length) { $('#pm-content').html('<div class="pm-loading">Sin clientes activos.</div>'); return; }

                frappe.call({
                    method: 'frappe.client.get_list',
                    args: { doctype:'Declaracion_Mensual', filters:{ano:_ano, mes:_mes},
                            fields:['name','cliente','estado','check_gasto_rem_cargado','check_f29_cuadrado',
                                    'check_previred_cuadrado','pdf_link_cliente','pdf_generado','borrador_f29_vinculado'],
                            limit_page_length:300, ignore_permissions:1 },
                    callback(r2) {
                        _dec_map = {};
                        (r2.message||[]).forEach(d => _dec_map[d.cliente] = d);

                        frappe.call({
                            method: 'frappe.client.get_list',
                            args: { doctype:'Cobranza_Cliente', filters:{periodo_ano:_ano, periodo_mes:_mes},
                                    fields:['name','cliente','monto_a_cobrar','estado_cobranza','monto_base',
                                            'monto_rrhh','monto_adicionales','total_descuentos',
                                            'recargo_por_atraso','fecha_vencimiento'],
                                    limit_page_length:300, ignore_permissions:1 },
                            callback(r3) {
                                _cobro_map = {};
                                (r3.message||[]).forEach(c => _cobro_map[c.cliente] = c);

                                // Todas las cobranzas pendientes del cliente, no solo las de este período.
                                frappe.call({
                                    method: 'frappe.client.get_list',
                                    args: { doctype:'Cobranza_Cliente',
                                            filters:{estado_cobranza:['not in', ['Pagado','Anulado']]},
                                            fields:['cliente','monto_a_cobrar','estado_cobranza'],
                                            limit_page_length:1000, ignore_permissions:1 },
                                    callback(r3b) {
                                        _cobro_pendiente_map = {};
                                        (r3b.message||[]).forEach(c => {
                                            const acc = _cobro_pendiente_map[c.cliente] || {monto:0, n:0};
                                            acc.monto += parseFloat(c.monto_a_cobrar||0);
                                            acc.n += 1;
                                            _cobro_pendiente_map[c.cliente] = acc;
                                        });

                                        frappe.call({
                                            method: 'evoluciona_pyme_v2.evoluciona_pyme_v2.api.get_f29_panel_data',
                                            args: { ano:_ano, mes:_mes },
                                            callback(r4) {
                                                _f29_map = r4.message || {};
                                                frappe.call({
                                                    method: 'frappe.client.get_list',
                                                    args: { doctype:'Registro_Remuneraciones',
                                                            filters:{ano:_ano, mes:_mes},
                                                            fields:['name','cliente','total_previred_a_pagar','estado_pago_previred',
                                                                    'total_empleados_activos','costo_total_empleador'],
                                                            limit_page_length:300, ignore_permissions:1 },
                                                    callback(r5) {
                                                        _remu_map = {};
                                                        (r5.message||[]).forEach(r => _remu_map[r.cliente] = r);

                                                        frappe.call({
                                                            method: 'frappe.client.get_list',
                                                            args: { doctype:'Postergacion_IVA',
                                                                    filters:{ano_origen:_ano, mes_origen:_mes},
                                                                    fields:['name','cliente','estado','monto_postergado',
                                                                            'fecha_vencimiento','mes_f29_pagado','ano_f29_pagado'],
                                                                    limit_page_length:300, ignore_permissions:1 },
                                                            callback(r6) {
                                                                _post_map = {};
                                                                (r6.message||[]).forEach(p => _post_map[p.cliente] = p);

                                                                // Postergaciones que vencen (hay que pagarlas) justo en el período seleccionado.
                                                                frappe.call({
                                                                    method: 'frappe.client.get_list',
                                                                    args: { doctype:'Postergacion_IVA',
                                                                            filters:{ano_f29_pagado:_ano, mes_f29_pagado:_mes,
                                                                                     estado:['not in', ['Pagada']]},
                                                                            fields:['cliente','monto_postergado'],
                                                                            limit_page_length:300, ignore_permissions:1 },
                                                                    callback(r7) {
                                                                        _post_vence_map = {};
                                                                        (r7.message||[]).forEach(p => {
                                                                            _post_vence_map[p.cliente] = (_post_vence_map[p.cliente]||0) + parseFloat(p.monto_postergado||0);
                                                                        });
                                                                        renderizar();
                                                                    }
                                                                });
                                                            }
                                                        });
                                                    }
                                                });
                                            }
                                        });
                                    }
                                });
                            }
                        });
                    }
                });
            }
        });
    }

    // ── Renderizar tabla ──────────────────────────────────────────────────────
    function renderizar() {
        let con_dec=0, listos=0, publicados=0, enviados=0, sin_dec=0;

        const rows = _clientes.map(c => {
            const d = _dec_map[c.name];
            const co = _cobro_map[c.name];
            if (d) con_dec++; else sin_dec++;
            if (d && d.estado==='Listo')      listos++;
            if (d && d.estado==='Publicado')  publicados++;
            if (d && d.estado==='Enviado')    enviados++;

            const estado_html = d
                ? `<span class="badge-est ${clase_estado(d.estado)}">${d.estado||'Borrador'}</span>`
                : `<span class="badge-est est-sin">Sin decl.</span>`;

            const checks = d
                ? `${d.check_gasto_rem_cargado?'✅':'⬜'} ${d.check_f29_cuadrado?'✅':'⬜'} ${d.check_previred_cuadrado?'✅':'⬜'} ${(d.pdf_link_cliente||d.pdf_generado)?'📄':'—'}`
                : '<span style="color:#ddd">— — — —</span>';

            const cred_sii = c.clave_sii
                ? `<span class="cred-val" data-val="${esc(c.clave_sii)}">●●●●</span><span class="cred-toggle" onclick="pm_toggle_cred(this)">ver</span>`
                : '<span style="color:#ddd">—</span>';

            // Previred desde Registro_Remuneraciones
            const remu = _remu_map[c.name];
            const prev_monto = remu ? parseFloat(remu.total_previred_a_pagar || 0) : null;
            const prev_html = prev_monto !== null
                ? (() => {
                    const lineas_prev = [
                        `N° empleados:   ${remu.total_empleados_activos||0}`,
                        `Costo empleador:$${fmt_num(remu.costo_total_empleador||0)}`,
                        `──────────────────────`,
                        `Total Previred: $${fmt_num(prev_monto)}`,
                        `Estado:         ${remu.estado_pago_previred||'Pendiente de Pago'}`,
                    ].join('\n');
                    return `<div class="pm-hover-wrap" title="${lineas_prev}">
                        <span class="cobro-monto" style="color:#2980b9;">$${fmt_num(prev_monto)}</span>
                    </div>`;
                })()
                : '<span style="color:#ddd">—</span>';

            // F29 totales con tooltip
            const f29_data = d && d.borrador_f29_vinculado ? _f29_map[d.borrador_f29_vinculado] : null;
            const f29_pagar = f29_data ? parseFloat(f29_data.total_a_pagar_f29 || 0) : null;
            const f29_honor = f29_data ? parseFloat(f29_data.honorarios_a_pagar || 0) : 0;
            const f29_html = (() => {
                if (!f29_data) return '<span style="color:#ddd;font-size:11px;">—</span>';
                const deb   = f29_data.subtotal_debitos       || 0;
                const cred  = f29_data.subtotal_creditos      || 0;
                const rem   = f29_data.remanente_mes_siguiente|| 0;
                const otros = f29_data.subtotal_otros_impuestos||0;
                const det   = f29_data.impuesto_determinado   || 0;
                const pagar = f29_data.total_a_pagar_f29      || 0;
                const honor = f29_honor;
                const ppm   = Math.round(f29_data.ppm_a_pagar  || 0);
                const total_mes_tt = pagar + (prev_monto || 0);
                const iva_neto = deb - cred;
                const rem_label = rem > 0 ? `Remanente sig:  $${fmt_num(rem)}` : `IVA neto:       $${fmt_num(iva_neto)}`;
                const lines = [
                    `Déb. IVA:       $${fmt_num(deb)}`,
                    `Créd. IVA:      $${fmt_num(cred)}`,
                    rem_label,
                    honor > 0 ? `Honorarios:     $${fmt_num(honor)}` : null,
                    ppm   > 0 ? `PPM:            $${fmt_num(ppm)}`   : null,
                    otros > 0 ? `Otros imp.:     $${fmt_num(otros)}` : null,
                    det   > 0 ? `Imp. det.:      $${fmt_num(det)}`   : null,
                    `──────────────────────`,
                    `Total F29:      $${fmt_num(pagar)}`,
                    prev_monto !== null ? `Previred:       $${fmt_num(prev_monto)}` : null,
                    `══════════════════════`,
                    `TOTAL MES:      $${fmt_num(total_mes_tt)}`,
                ].filter(Boolean).join('\n');
                const cls = pagar > 0 ? 'pm-f29-positivo' : 'pm-f29-cero';
                return `<div class="pm-hover-wrap" title="${lines}">
                    <span class="pm-f29-total ${cls}">$${fmt_num(pagar)}</span>
                </div>`;
            })();

            // Cobranza: todo lo pendiente del cliente (no solo lo de este período), con
            // detalle del cobro de ESTE período en el hover si existe.
            const cobro_pend = _cobro_pendiente_map[c.name];
            const co_periodo = _cobro_map[c.name];
            const cobro_html = cobro_pend
                ? (() => {
                    const lineas_cob = co_periodo ? [
                        `Base:           $${fmt_num(co_periodo.monto_base||0)}`,
                        `RRHH:           $${fmt_num(co_periodo.monto_rrhh||0)}`,
                        co_periodo.monto_adicionales   ? `Adicionales:    $${fmt_num(co_periodo.monto_adicionales)}` : null,
                        co_periodo.total_descuentos     ? `Descuentos:    -$${fmt_num(co_periodo.total_descuentos)}` : null,
                        co_periodo.recargo_por_atraso   ? `Recargo atraso: $${fmt_num(co_periodo.recargo_por_atraso)}` : null,
                        `──────────────────────`,
                        `Este período:   $${fmt_num(co_periodo.monto_a_cobrar||0)}`,
                        `Vence:          ${co_periodo.fecha_vencimiento||'—'}`,
                        `══════════════════════`,
                        `Total pendiente:$${fmt_num(cobro_pend.monto)} (${cobro_pend.n} período${cobro_pend.n>1?'s':''})`,
                    ].filter(Boolean).join('\n') : `Total pendiente: $${fmt_num(cobro_pend.monto)} (${cobro_pend.n} período${cobro_pend.n>1?'s':''})`;
                    return `<div class="pm-hover-wrap" title="${lineas_cob}">
                        <div class="cobro-monto">$${fmt_num(cobro_pend.monto)}</div>
                        <div class="cobro-est">${cobro_pend.n>1 ? cobro_pend.n+' pendientes' : 'Pendiente'}</div>
                    </div>`;
                })()
                : '<span style="color:#ddd">—</span>';

            // Postergación de IVA: ¿el cliente postergó el pago de este período?
            // Solo indicador visual acá -- el control para cambiarla vive junto a
            // F29/Previred en la tarjeta "Estado de Pago" de la fila expandida.
            const post = _post_map[c.name];
            const post_clase = { Vigente:'#2980b9', 'Por Vencer':'#f39c12', Vencida:'#e74c3c', Pagada:'#95a5a6' };
            const post_html = post
                ? (() => {
                    const lineas_post = [
                        `Monto postergado:$${fmt_num(post.monto_postergado||0)}`,
                        `Estado:          ${post.estado}`,
                        `Se paga en F29:  ${post.mes_f29_pagado}/${post.ano_f29_pagado}`,
                        `Vence:           ${post.fecha_vencimiento||'—'}`,
                    ].join('\n');
                    return `<div class="pm-hover-wrap" title="${lineas_post}">
                        <span style="font-size:10px;font-weight:700;color:${post_clase[post.estado]||'#888'};">${esc(post.estado)}</span>
                    </div>`;
                })()
                : '<span style="color:#ddd">—</span>';

            // Postergación que vence (hay que pagarla) justo este período.
            const post_vence = _post_vence_map[c.name] || 0;

            const total_mes = (f29_pagar !== null ? f29_pagar : 0) + (prev_monto !== null ? prev_monto : 0)
                             + (cobro_pend ? cobro_pend.monto : 0) + post_vence;
            const total_html = (f29_pagar !== null || prev_monto !== null || cobro_pend || post_vence)
                ? `<div style="font-size:12px;font-weight:800;color:#1a3a4a;">$${fmt_num(total_mes)}</div>
                   <div style="font-size:9px;color:#aaa;">F29+Prev+Cobr${post_vence ? '+Post' : ''}</div>`
                : '<span style="color:#ddd">—</span>';

            const acciones = d ? gen_acciones(d, c, co) : gen_sin_dec(c);

            const estado_key = d ? (d.estado||'Borrador') : 'Sin declaración';

            return `<tr data-estado="${esc(estado_key)}" data-cliente="${esc(c.name)}">
                <td><input class="pm-chk" type="checkbox" data-cliente="${esc(c.name)}" data-doc="${d?esc(d.name):''}" onchange="pm_chk_change()"></td>
                <td>
                    <span class="pm-expand-toggle" data-cliente="${esc(c.name)}" title="Ver más"><span class="arrow">▶</span> Ver más</span><br>
                    <a href="#" onclick="frappe.set_route('Form','Ficha_Cliente','${esc(c.name)}');return false;" style="font-weight:600;color:#005f6b;">${esc(c.razon_social||c.name)}</a><br>
                    <small style="color:#aaa;font-size:10px;">${esc(c.name)}</small>
                </td>
                <td>${cred_sii}</td>
                <td>${estado_html}</td>
                <td style="white-space:nowrap;font-size:13px;letter-spacing:2px;">${checks}</td>
                <td>${f29_html}</td>
                <td>${post_html}</td>
                <td>${prev_html}</td>
                <td>${cobro_html}</td>
                <td>${total_html}</td>
                <td>${acciones}</td>
            </tr>`;
        }).join('');

        const total = _clientes.length;
        const avance = listos + publicados + enviados;
        const pct = total ? Math.round(avance / total * 100) : 0;

        $('#pm-total').text(total);
        $('#pm-con-dec').text(con_dec);
        $('#pm-listos').text(listos);
        $('#pm-publicados').text(publicados);
        $('#pm-enviados').text(enviados);
        $('#pm-sin-dec').text(sin_dec);
        $('#pm-fill').css('width', pct + '%');
        $('#pm-pct').text(`${avance} / ${total} (${pct}%)`);
        $('#pm-stats,#pm-progress').show();

        $('#pm-content').html(`
            <div class="pm-table-wrap">
            <table class="pm-table">
                <thead><tr>
                    <th style="width:30px;"><input type="checkbox" id="pm-chk-all" onclick="pm_chk_all(this)" style="width:15px;height:15px;cursor:pointer;"></th>
                    <th style="width:13%;">Cliente</th>
                    <th style="width:7%;">SII</th>
                    <th style="width:7%;">Estado</th>
                    <th style="width:9%;">RRHH · F29 · Prev · PDF</th>
                    <th style="width:7%;">Total F29</th>
                    <th style="width:6%;">Post.</th>
                    <th style="width:7%;">Previred</th>
                    <th style="width:7%;">Cobranza</th>
                    <th style="width:7%;">Total Mes</th>
                    <th>Acciones</th>
                </tr></thead>
                <tbody>${rows}</tbody>
            </table></div>`);

        $('#pm-content').off('click','.btn-pm-accion').on('click','.btn-pm-accion', function() {
            ejecutar_accion($(this).data('action'), $(this).data('doc'),
                            $(this).data('f29')||'', $(this).data('cliente'),
                            $(this).data('cobro')||'');
        });

        $('#pm-content').off('click','.pm-expand-toggle').on('click','.pm-expand-toggle', function() {
            toggle_expand_cliente($(this).data('cliente'), $(this));
        });

        aplicar_filtro();
        _expandido = null;
    }

    // ── Generar botones de acción ─────────────────────────────────────────────
    function gen_acciones(d, c, co) {
        let a = '';
        const tiene_pdf = d.pdf_link_cliente || d.pdf_generado;
        const est_cobro = co ? co.estado_cobranza : null;

        a += btn('ver-f29',  d.name, d.borrador_f29_vinculado||'', c.name, 'F29');
        a += btn('ing-rrhh', d.name, '', c.name, 'RRHH');
        if (!d.check_f29_cuadrado && d.estado !== 'Listo' && d.estado !== 'PDF Generado' && d.estado !== 'Enviado')
            a += btn('calc-f29', d.name, d.borrador_f29_vinculado||'', c.name, '⚡Calc', '#1a6e3c');

        if (!d.check_gasto_rem_cargado) a += btn('check-rrhh', d.name, '', c.name, '✓RRHH', '#e67e22');
        if (!d.check_f29_cuadrado)      a += btn('check-f29',  d.name, '', c.name, '✓F29',  '#e67e22');
        if (!d.check_previred_cuadrado) a += btn('check-prev', d.name, '', c.name, '✓Prev', '#e67e22');

        if (d.estado === 'Listo' || d.estado === 'PDF Generado') {
            if (!tiene_pdf) a += btn('gen-pdf', d.name, '', c.name, 'Gen.PDF', '#27ae60');
            else            a += btn('ver-pdf', d.name, '', c.name, 'PDF', '#0984e3');
            a += btn('publicar', d.name, '', c.name, '📱 Publicar', '#6f42c1');
            a += btn('enviar',   d.name, '', c.name, 'Enviar', '#17a2b8');
        }
        if (d.estado === 'Publicado') {
            if (tiene_pdf) a += btn('ver-pdf', d.name, '', c.name, 'PDF', '#0984e3');
            a += btn('publicar', d.name, '', c.name, '✅ Publicado', '#28a745');
            a += btn('enviar',   d.name, '', c.name, 'Enviar', '#17a2b8');
        }
        if (d.estado === 'Enviado') {
            if (tiene_pdf) a += btn('ver-pdf',  d.name, '', c.name, 'PDF', '#0984e3');
            a += btn('reenviar', d.name, '', c.name, 'Reenviar', '#17a2b8');
        }

        // Botones cobranza — independientes, sin orden obligatorio
        if (co) {
            const cobro_id = esc(co.name);
            if (est_cobro !== 'Facturado' && est_cobro !== 'Pagado') {
                a += `<button class="btn-pm btn-pm-accion" data-action="facturar"
                        data-doc="${esc(d.name)}" data-cobro="${cobro_id}" data-cliente="${esc(c.name)}"
                        style="border-color:#8e44ad;color:#8e44ad;" title="Marcar como Facturado">🧾 Fact.</button>`;
            }
            if (est_cobro !== 'Pagado') {
                a += `<button class="btn-pm btn-pm-accion" data-action="pagar"
                        data-doc="${esc(d.name)}" data-cobro="${cobro_id}" data-cliente="${esc(c.name)}"
                        style="border-color:#27ae60;color:#27ae60;" title="Marcar como Pagado">💰 Pagar</button>`;
            }
        }

        // Botón reset
        const tiene_algo = d.check_gasto_rem_cargado || d.check_f29_cuadrado ||
                           d.check_previred_cuadrado || tiene_pdf || d.estado !== 'Borrador';
        if (tiene_algo) {
            a += `<button class="btn-pm btn-pm-accion danger"
                    data-action="reset" data-doc="${esc(d.name)}" data-cliente="${esc(c.name)}"
                    title="Regresa a Borrador, borra PDF y elimina cobro"
                    style="border-color:#e74c3c;color:#e74c3c;">↩ Reset</button>`;
        }
        return a;
    }

    function gen_sin_dec(c) {
        return `<button class="btn-pm btn-pm-accion"
                    data-action="crear-dec" data-doc="" data-cliente="${esc(c.name)}"
                    style="border-color:#6c757d;color:#6c757d;">+ Crear</button>`;
    }

    function btn(action, doc, f29, cliente, label, color) {
        const style = color ? `style="border-color:${color};color:${color};"` : '';
        return `<button class="btn-pm btn-pm-accion" data-action="${action}"
                    data-doc="${esc(doc)}" data-f29="${esc(f29)}" data-cliente="${esc(cliente)}"
                    ${style}>${label}</button>`;
    }

    // ── Filtro ────────────────────────────────────────────────────────────────
    function aplicar_filtro() {
        const f = sel_filtro.get_value() || 'Todos';
        $('#pm-content tbody tr').each(function() {
            const est = $(this).data('estado') || '';
            const show = f === 'Todos' || est === f;
            $(this).toggleClass('pm-hidden', !show);
        });
    }

    // ── Checkboxes y acciones masivas ─────────────────────────────────────────
    window.pm_chk_all = function(el) {
        $('#pm-content tbody tr:not(.pm-hidden) input.pm-chk').prop('checked', el.checked);
        pm_chk_change();
    };

    window.pm_chk_change = function() {
        const sel = $('#pm-content input.pm-chk:checked');
        const n = sel.length;
        if (n > 0) {
            $('#pm-bulk-count').text(`${n} seleccionado${n>1?'s':''}`);
            $('#pm-bulk').css('display','flex');
        } else {
            $('#pm-bulk').hide();
        }
    };

    window.pm_bulk = function(action) {
        const docs = [];
        $('#pm-content input.pm-chk:checked').each(function() {
            const doc = $(this).data('doc');
            if (doc) docs.push(doc);
        });
        if (!docs.length) { frappe.msgprint('Selecciona declaraciones (no clientes sin declaración).'); return; }

        const label_map = {'check-rrhh':'Marcar ✓RRHH','check-f29':'Marcar ✓F29','check-prev':'Marcar ✓Previred','publicar':'Publicar en App','reset':'Resetear a Borrador'};
        frappe.confirm(`¿${label_map[action]||action} para ${docs.length} declaración(es)?`, () => {
            let pending = docs.length;
            docs.forEach(doc => {
                if (action === 'reset') {
                    frappe.call({
                        method:'evoluciona_pyme_v2.evoluciona_pyme_v2.api.resetear_declaracion',
                        args:{doc_name:doc}, callback() { if(--pending===0) { frappe.show_alert({message:'Listo',indicator:'green'},3); setTimeout(cargar_panel,600); } }
                    });
                } else if (action === 'publicar') {
                    frappe.call({
                        method:'evoluciona_pyme_v2.evoluciona_pyme_v2.api.publicar_en_portal',
                        args:{doc_name:doc}, callback() { if(--pending===0) { frappe.show_alert({message:'📱 Publicadas',indicator:'green'},3); setTimeout(cargar_panel,600); } }
                    });
                } else {
                    const field_map = {'check-rrhh':'check_gasto_rem_cargado','check-f29':'check_f29_cuadrado','check-prev':'check_previred_cuadrado'};
                    frappe.call({
                        method:'frappe.client.set_value',
                        args:{doctype:'Declaracion_Mensual', name:doc, fieldname:field_map[action], value:1},
                        callback() { if(--pending===0) { frappe.show_alert({message:'Listo',indicator:'green'},3); setTimeout(cargar_panel,600); } }
                    });
                }
            });
        });
    };

    // ── Ejecutar acción individual ────────────────────────────────────────────
    function ejecutar_accion(action, doc, f29, cliente, cobro) {
        switch(action) {

            case 'ver-f29':
                if (f29) frappe.set_route('Form','Borrador_F29',f29);
                else frappe.msgprint('Sin F29 vinculado.'); break;

            case 'ing-rrhh':
                frappe.call({
                    method:'frappe.client.get_list',
                    args:{doctype:'Registro_Remuneraciones',filters:{cliente,ano:_ano,mes:_mes},
                          fields:['name'],limit_page_length:1,ignore_permissions:1},
                    callback(r) {
                        if (r.message&&r.message[0]) frappe.set_route('Form','Registro_Remuneraciones',r.message[0].name);
                        else frappe.msgprint('Sin Registro de Remuneraciones para este período.');
                    }
                }); break;

            case 'calc-f29':
                if (!f29) { frappe.msgprint('Sin F29 vinculado.'); break; }
                frappe.show_alert({message:'Calculando...', indicator:'blue'}, 3);
                frappe.call({
                    method:'evoluciona_pyme_v2.evoluciona_pyme_v2.api.recalcular_asistente_f29', args:{doc_name:f29},
                    callback(r) {
                        const res = r.message||{};
                        frappe.show_alert({message: res.status==='ok'?'✅ F29 calculado':'Error al calcular',
                                           indicator: res.status==='ok'?'green':'red'}, 4);
                        if (res.status==='ok') setTimeout(cargar_panel, 600);
                    }
                }); break;

            case 'check-rrhh': set_check(doc,'check_gasto_rem_cargado'); break;
            case 'check-f29':  set_check(doc,'check_f29_cuadrado');      break;
            case 'check-prev': set_check(doc,'check_previred_cuadrado'); break;

            case 'gen-pdf':
                frappe.show_alert({message:'Generando PDF...', indicator:'blue'}, 5);
                frappe.call({
                    method:'evoluciona_pyme_v2.evoluciona_pyme_v2.api.preparar_datos_pdf', args:{declaracion_name:doc},
                    freeze:true, freeze_message:'Generando PDF... puede tomar 30-60 segundos',
                    callback(r) {
                        const res = r.message||{};
                        frappe.show_alert({message:res.status==='success'?'✅ PDF generado':'Error al generar PDF',
                                           indicator:res.status==='success'?'green':'red'}, 4);
                        if (res.status==='success') setTimeout(cargar_panel, 1200);
                    }
                }); break;

            case 'ver-pdf':
                frappe.call({
                    method:'frappe.client.get', args:{doctype:'Declaracion_Mensual',name:doc},
                    callback(r) {
                        const url = (r.message||{}).pdf_link_cliente||(r.message||{}).pdf_generado;
                        if (url) window.open(url,'_blank');
                        else frappe.msgprint({message:'PDF no disponible.',indicator:'orange'});
                    }
                }); break;

            case 'enviar':
            case 'reenviar':
                frappe.call({
                    method:'frappe.client.get', args:{doctype:'Declaracion_Mensual',name:doc},
                    callback(r_dm) {
                        frappe.call({
                            method:'frappe.client.get', args:{doctype:'Ficha_Cliente',name:cliente},
                            callback(r_cli) {
                                frappe.db.get_single_value('Configuracion App','webhook_envio_declaracion').then(wh => {
                                    if (!wh) { frappe.msgprint('Webhook no configurado.'); return; }
                                    frappe.show_alert({message:'Enviando...',indicator:'blue'},5);
                                    fetch(wh,{method:'POST',headers:{'Content-Type':'application/json'},
                                        body:JSON.stringify({declaracion:doc,cliente:r_cli.message,
                                                             declaracion_data:r_dm.message,es_reenvio:action==='reenviar'})
                                    }).then(()=>{frappe.show_alert({message:'✅ Enviado',indicator:'green'},4);setTimeout(cargar_panel,1000);})
                                      .catch(e=>frappe.msgprint({message:'Error: '+e,indicator:'red'}));
                                });
                            }
                        });
                    }
                }); break;

            case 'publicar': {
                const dec_actual = _dec_map[cliente];
                const ya_publicado = dec_actual && dec_actual.estado === 'Publicado';
                frappe.call({
                    method:'evoluciona_pyme_v2.evoluciona_pyme_v2.api.publicar_en_portal',
                    args:{doc_name:doc},
                    callback(res) {
                        const ok = res.message && res.message.status === 'ok';
                        frappe.show_alert({message: ok ? (ya_publicado?'🔒 Despublicado':'📱 Publicado en App') : 'Error al publicar',
                                           indicator: ok ? (ya_publicado?'orange':'green') : 'red'}, 4);
                        if (ok) setTimeout(cargar_panel, 600);
                    }
                }); break;
            }

            case 'reset':
                frappe.confirm(`¿Resetear declaración a <b>Borrador</b>?<br><small>Se borrarán los checks, el PDF y el cobro asociado.</small>`, () => {
                    frappe.call({
                        method:'evoluciona_pyme_v2.evoluciona_pyme_v2.api.resetear_declaracion',
                        args:{doc_name:doc},
                        callback(r) {
                            const res = r.message||{};
                            frappe.show_alert({message: res.status==='ok'?'✅ '+res.message:'Error: '+res.message,
                                               indicator: res.status==='ok'?'green':'red'}, 4);
                            if (res.status==='ok') setTimeout(cargar_panel, 600);
                        }
                    });
                }); break;

            case 'crear-dec':
                frappe.call({
                    method:'evoluciona_pyme_v2.evoluciona_pyme_v2.api.crear_declaraciones_periodo',
                    args:{cliente, mes:_mes, ano:_ano},
                    callback(r) {
                        const res = r.message||{};
                        frappe.show_alert({message:res.status==='exists'?'Ya existe para este período.':'✅ Creado.',
                                           indicator:res.status==='exists'?'orange':'green'}, 4);
                        setTimeout(cargar_panel, 800);
                    }
                }); break;

            case 'facturar':
                if (!cobro) { frappe.msgprint('Sin cobranza vinculada.'); break; }
                frappe.call({
                    method:'frappe.client.set_value',
                    args:{doctype:'Cobranza_Cliente', name:cobro, fieldname:'estado_cobranza', value:'Facturado'},
                    callback() { frappe.show_alert({message:'🧾 Marcado como Facturado',indicator:'purple'},3); setTimeout(cargar_panel,500); }
                }); break;

            case 'pagar':
                if (!cobro) { frappe.msgprint('Sin cobranza vinculada.'); break; }
                pagar_cobranza(cobro); break;
        }
    }

    function set_check(doc, field) {
        frappe.call({
            method:'frappe.client.set_value',
            args:{doctype:'Declaracion_Mensual',name:doc,fieldname:field,value:1},
            callback(r) {
                if (r && r.message) {
                    frappe.show_alert({message:'✅ Marcado',indicator:'green'},2);
                    setTimeout(cargar_panel,400);
                }
            },
            error(err) {
                const msg = (err && err.responseJSON && err.responseJSON._server_messages)
                    ? JSON.parse(err.responseJSON._server_messages||'[]').join('<br>')
                    : 'No se pudo marcar. Intenta recargar el panel.';
                frappe.msgprint({title:'Error al marcar',message:msg,indicator:'red'});
            }
        });
    }

    // ── Helpers ───────────────────────────────────────────────────────────────
    function clase_estado(e) {
        if (!e||e==='Borrador')      return 'est-borrador';
        if (e==='En Validación')     return 'est-validar';
        if (e==='Listo')             return 'est-listo';
        if (e==='PDF Generado')      return 'est-pdf';
        if (e==='Publicado')         return 'est-publicado';
        if (e==='Enviado')           return 'est-enviado';
        return 'est-borrador';
    }
    function esc(s) {
        return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
    }
    function fmt_num(n) {
        return Math.round(Number(n||0)).toLocaleString('es-CL');
    }

    window.pm_toggle_cred = function(el) {
        const sp = $(el).prev('.cred-val');
        if (sp.text().startsWith('●')) { sp.text(sp.data('val')); $(el).text('ocultar'); }
        else                            { sp.text('●●●●');         $(el).text('ver'); }
    };

    // Carga automática al abrir
    setTimeout(cargar_panel, 300);
};
