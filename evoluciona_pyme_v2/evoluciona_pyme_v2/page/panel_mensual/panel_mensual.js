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

    // "Crear Todas" — creación masiva para el período seleccionado arriba.
    // Solo visible para rol admin: crea registros reales para todos los clientes.
    let btn_crear_todas = page.add_button('🗓️ Crear Todas', crear_todas_periodo, {btn_class: 'btn-default'});
    btn_crear_todas.hide();
    frappe.call({
        method: 'evoluciona_pyme_v2.evoluciona_pyme_v2.asesores.get_rol_usuario',
        callback(r) {
            if (r.message === 'admin') btn_crear_todas.show();
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
        .badge-est { padding:3px 8px; border-radius:10px; font-size:10px; font-weight:700; white-space:nowrap; }
        .est-borrador { background:#ffc107; color:#000; }
        .est-validar  { background:#ff9800; color:#fff; }
        .est-listo    { background:#28a745; color:#fff; }
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
        .pm-f29-wrap { position:relative; display:inline-block; cursor:help; }
        .pm-f29-total { font-size:11px; font-weight:700; }
        .pm-f29-positivo { color:#c0392b; }
        .pm-f29-cero     { color:#27ae60; }
        .pm-f29-hint { font-size:10px; color:#bbb; margin-left:2px; }
        .pm-f29-wrap:hover .pm-f29-hint { color:#005f6b; }
        .pm-f29-wrap[title]:hover::after {
            content: attr(title); white-space:pre;
            position:absolute; left:0; top:100%; z-index:999;
            background:#2c3e50; color:#fff; font-size:11px; line-height:1.6;
            padding:6px 10px; border-radius:6px; min-width:160px;
            box-shadow:0 4px 12px rgba(0,0,0,.3); pointer-events:none;
        }
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
    let _clientes = [], _dec_map = {}, _cobro_map = {}, _f29_map = {}, _remu_map = {}, _ano, _mes;

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
                                    fields:['name','cliente','monto_a_cobrar','estado_cobranza'],
                                    limit_page_length:300, ignore_permissions:1 },
                            callback(r3) {
                                _cobro_map = {};
                                (r3.message||[]).forEach(c => _cobro_map[c.cliente] = c);

                                frappe.call({
                                    method: 'evoluciona_pyme_v2.evoluciona_pyme_v2.api.get_f29_panel_data',
                                    args: { ano:_ano, mes:_mes },
                                    callback(r4) {
                                        _f29_map = r4.message || {};
                                        frappe.call({
                                            method: 'frappe.client.get_list',
                                            args: { doctype:'Registro_Remuneraciones',
                                                    filters:{ano:_ano, mes:_mes},
                                                    fields:['name','cliente','total_previred_a_pagar'],
                                                    limit_page_length:300, ignore_permissions:1 },
                                            callback(r5) {
                                                _remu_map = {};
                                                (r5.message||[]).forEach(r => _remu_map[r.cliente] = r);
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
                ? `<div class="cobro-monto" style="color:#2980b9;">$${fmt_num(prev_monto)}</div>`
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
                return `<div class="pm-f29-wrap" title="${lines}">
                    <span class="pm-f29-total ${cls}">$${fmt_num(pagar)}</span>
                    <span class="pm-f29-hint"> ℹ</span>
                </div>`;
            })();

            const cobro_html = co
                ? `<div class="cobro-monto">$${fmt_num(co.monto_a_cobrar)}</div>
                   <div class="cobro-est">${co.estado_cobranza||'Pendiente'}</div>`
                : '<span style="color:#ddd">—</span>';

            const total_mes = (f29_pagar !== null ? f29_pagar : 0) + (prev_monto !== null ? prev_monto : 0);
            const total_html = (f29_pagar !== null || prev_monto !== null)
                ? `<div style="font-size:12px;font-weight:800;color:#1a3a4a;">$${fmt_num(total_mes)}</div>
                   <div style="font-size:9px;color:#aaa;">F29+Prev</div>`
                : '<span style="color:#ddd">—</span>';

            const acciones = d ? gen_acciones(d, c, co) : gen_sin_dec(c);

            const estado_key = d ? (d.estado||'Borrador') : 'Sin declaración';

            return `<tr data-estado="${esc(estado_key)}" data-cliente="${esc(c.name)}">
                <td><input class="pm-chk" type="checkbox" data-cliente="${esc(c.name)}" data-doc="${d?esc(d.name):''}" onchange="pm_chk_change()"></td>
                <td><a href="#" onclick="frappe.set_route('Form','Ficha_Cliente','${esc(c.name)}');return false;" style="font-weight:600;color:#005f6b;">${esc(c.razon_social||c.name)}</a><br>
                    <small style="color:#aaa;font-size:10px;">${esc(c.name)}</small></td>
                <td>${cred_sii}</td>
                <td>${estado_html}</td>
                <td style="white-space:nowrap;font-size:13px;letter-spacing:2px;">${checks}</td>
                <td>${f29_html}</td>
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

        aplicar_filtro();
    }

    // ── Generar botones de acción ─────────────────────────────────────────────
    function gen_acciones(d, c, co) {
        let a = '';
        const tiene_pdf = d.pdf_link_cliente || d.pdf_generado;
        const est_cobro = co ? co.estado_cobranza : null;

        a += btn('ver-f29',  d.name, d.borrador_f29_vinculado||'', c.name, 'F29');
        a += btn('ing-rrhh', d.name, '', c.name, 'RRHH');
        if (!d.check_f29_cuadrado && d.estado !== 'Listo' && d.estado !== 'Enviado')
            a += btn('calc-f29', d.name, d.borrador_f29_vinculado||'', c.name, '⚡Calc', '#1a6e3c');

        if (!d.check_gasto_rem_cargado) a += btn('check-rrhh', d.name, '', c.name, '✓RRHH', '#e67e22');
        if (!d.check_f29_cuadrado)      a += btn('check-f29',  d.name, '', c.name, '✓F29',  '#e67e22');
        if (!d.check_previred_cuadrado) a += btn('check-prev', d.name, '', c.name, '✓Prev', '#e67e22');

        if (d.estado === 'Listo') {
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
                frappe.confirm('¿Calcular F29 automáticamente desde documentos tributarios?', () => {
                    frappe.show_alert({message:'Calculando...', indicator:'blue'}, 3);
                    frappe.call({
                        method:'evoluciona_pyme_v2.evoluciona_pyme_v2.api.recalcular_asistente_f29', args:{doc_name:f29},
                        callback(r) {
                            const res = r.message||{};
                            frappe.show_alert({message: res.status==='ok'?'✅ F29 calculado':'Error al calcular',
                                               indicator: res.status==='ok'?'green':'red'}, 4);
                        }
                    });
                }); break;

            case 'check-rrhh': set_check(doc,'check_gasto_rem_cargado'); break;
            case 'check-f29':  set_check(doc,'check_f29_cuadrado');      break;
            case 'check-prev': set_check(doc,'check_previred_cuadrado'); break;

            case 'gen-pdf':
                frappe.confirm('¿Generar PDF del informe mensual?', () => {
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
                    });
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
                const es_reenvio = action==='reenviar';
                frappe.confirm(es_reenvio?'¿Reenviar al cliente?':'¿Enviar declaración al cliente?', () => {
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
                                                                 declaracion_data:r_dm.message,es_reenvio})
                                        }).then(()=>{frappe.show_alert({message:'✅ Enviado',indicator:'green'},4);setTimeout(cargar_panel,1000);})
                                          .catch(e=>frappe.msgprint({message:'Error: '+e,indicator:'red'}));
                                    });
                                }
                            });
                        }
                    });
                }); break;

            case 'publicar': {
                const dec_actual = _dec_map[cliente];
                const ya_publicado = dec_actual && dec_actual.estado === 'Publicado';
                frappe.confirm(ya_publicado ? '¿Despublicar esta declaración del portal?' : '¿Publicar en la App del cliente? Se enviará notificación push.', () => {
                    frappe.call({
                        method:'evoluciona_pyme_v2.evoluciona_pyme_v2.api.publicar_en_portal',
                        args:{doc_name:doc},
                        callback(res) {
                            const ok = res.message && res.message.status === 'ok';
                            frappe.show_alert({message: ok ? (ya_publicado?'🔒 Despublicado':'📱 Publicado en App') : 'Error al publicar',
                                               indicator: ok ? (ya_publicado?'orange':'green') : 'red'}, 4);
                            if (ok) setTimeout(cargar_panel, 600);
                        }
                    });
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
                frappe.confirm(`¿Crear Declaración Mensual + F29 para este cliente en ${_mes}/${_ano}?`, () => {
                    frappe.call({
                        method:'evoluciona_pyme_v2.evoluciona_pyme_v2.api.crear_declaraciones_periodo',
                        args:{cliente, mes:_mes, ano:_ano},
                        callback(r) {
                            const res = r.message||{};
                            frappe.show_alert({message:res.status==='exists'?'Ya existe para este período.':'✅ Creado.',
                                               indicator:res.status==='exists'?'orange':'green'}, 4);
                            setTimeout(cargar_panel, 800);
                        }
                    });
                }); break;

            case 'facturar':
                if (!cobro) { frappe.msgprint('Sin cobranza vinculada.'); break; }
                frappe.confirm('¿Marcar cobranza como <b>Facturada</b>?', () => {
                    frappe.call({
                        method:'frappe.client.set_value',
                        args:{doctype:'Cobranza_Cliente', name:cobro, fieldname:'estado_cobranza', value:'Facturado'},
                        callback() { frappe.show_alert({message:'🧾 Marcado como Facturado',indicator:'purple'},3); setTimeout(cargar_panel,500); }
                    });
                }); break;

            case 'pagar':
                if (!cobro) { frappe.msgprint('Sin cobranza vinculada.'); break; }
                frappe.confirm('¿Marcar cobranza como <b>Pagada</b>?', () => {
                    frappe.call({
                        method:'frappe.client.set_value',
                        args:{doctype:'Cobranza_Cliente', name:cobro, fieldname:'estado_cobranza', value:'Pagado'},
                        callback() { frappe.show_alert({message:'💰 Marcado como Pagado',indicator:'green'},3); setTimeout(cargar_panel,500); }
                    });
                }); break;
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
