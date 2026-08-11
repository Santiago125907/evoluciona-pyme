// CLIENT SCRIPT — Borrador_F29

// ── Utilidades numéricas ────────────────────────────────────────────────────
function fmt(n) {
    if (!n || n === 0) return '0';
    return parseFloat(n).toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, '.');
}
function parse(s) {
    if (!s) return 0;
    return parseFloat(s.toString().replace(/[^0-9]/g, '')) || 0;
}

// ── Render visual del F29 ───────────────────────────────────────────────────
function renderizar_f29(frm) {
    const MESES = ['','Enero','Febrero','Marzo','Abril','Mayo','Junio',
                   'Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'];

    const subtotal_seccion = (filas) => (filas || []).reduce((acc, r) => {
        const m = flt(r.monto);
        return acc + (r.tipo_operacion_subtotal === 'Resta' ? -m : r.tipo_operacion_subtotal === 'Informativo' ? 0 : m);
    }, 0);

    const seccion = (titulo, color, tabla_key, filas, id_subtotal) => {
        if (!filas || !filas.length) return '';
        const subtotal = subtotal_seccion(filas);
        const rows = filas.map(r => {
            const es_calculado = r.tipo_origen === 'Calculado';
            const readonly    = es_calculado ? 'readonly' : '';
            const bg_input    = es_calculado ? '#f8f8f8' : '#fff';
            const tag_color   = es_calculado ? '#6c757d' : '#0a6640';
            const tag_txt     = es_calculado ? 'AUTO' : 'MANUAL';
            return `
            <tr style="border-bottom:1px solid #f0f0f0;">
              <td style="padding:6px 10px;font-size:12px;font-weight:600;color:#555;width:60px;">${r.codigo_f29}</td>
              <td style="padding:6px 10px;font-size:12px;color:#333;flex:1;">${r.descripcion || ''}</td>
              <td style="padding:6px 10px;text-align:center;width:70px;">
                <span style="font-size:9px;font-weight:700;color:${tag_color};background:${tag_color}18;border-radius:3px;padding:2px 5px;">${tag_txt}</span>
              </td>
              <td style="padding:4px 8px;width:130px;text-align:right;">
                <input type="text"
                  class="monto-field"
                  data-tabla="${tabla_key}"
                  data-idx="${r.idx}"
                  value="${fmt(r.monto)}"
                  ${readonly}
                  style="width:100%;text-align:right;border:1px solid ${readonly ? '#eee' : color+'66'};border-radius:4px;padding:4px 8px;font-size:13px;font-weight:600;background:${bg_input};color:#222;outline:none;">
              </td>
            </tr>`;
        }).join('');

        return `
        <div style="margin-bottom:16px;border-radius:8px;overflow:hidden;border:1px solid #e8e8e8;box-shadow:0 1px 4px rgba(0,0,0,0.04);">
          <div style="background:${color};padding:8px 14px;display:flex;justify-content:space-between;align-items:center;">
            <span style="color:white;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;">${titulo}</span>
            <span style="color:white;font-size:13px;font-weight:800;">$<span id="${id_subtotal}">${fmt(subtotal)}</span></span>
          </div>
          <table style="width:100%;border-collapse:collapse;background:white;">
            <thead>
              <tr style="background:#fafafa;">
                <th style="padding:5px 10px;font-size:10px;color:#888;font-weight:600;text-align:left;">Cód.</th>
                <th style="padding:5px 10px;font-size:10px;color:#888;font-weight:600;text-align:left;">Descripción</th>
                <th style="padding:5px 10px;font-size:10px;color:#888;font-weight:600;text-align:center;">Origen</th>
                <th style="padding:5px 10px;font-size:10px;color:#888;font-weight:600;text-align:right;">Monto ($)</th>
              </tr>
            </thead>
            <tbody>${rows}</tbody>
          </table>
          <div style="background:${color}18;border-top:2px solid ${color}44;padding:7px 14px;display:flex;justify-content:space-between;align-items:center;">
            <span style="font-size:11px;font-weight:600;color:${color};">Total sección</span>
            <span style="font-size:15px;font-weight:800;color:${color};">$<span id="${id_subtotal}_foot">${fmt(subtotal)}</span></span>
          </div>
        </div>`;
    };

    let deb = 0, cred = 0, imp = 0;
    (frm.doc.tabla_debitos  || []).forEach(r => { deb  += (r.tipo_operacion_subtotal === 'Resta' ? -1 : (r.tipo_operacion_subtotal === 'Informativo' ? 0 : 1)) * flt(r.monto); });
    (frm.doc.tabla_creditos || []).forEach(r => { cred += (r.tipo_operacion_subtotal === 'Resta' ? -1 : (r.tipo_operacion_subtotal === 'Informativo' ? 0 : 1)) * flt(r.monto); });
    (frm.doc.tabla_impuestos|| []).forEach(r => { imp  += (r.tipo_operacion_subtotal === 'Resta' ? -1 : (r.tipo_operacion_subtotal === 'Informativo' ? 0 : 1)) * flt(r.monto); });
    const iva_det   = Math.max(0, deb - cred);
    const remanente = Math.max(0, cred - deb);
    const total     = Math.max(0, iva_det + imp - flt(frm.doc.postergacion_del_periodo));
    const color_total = total > 0 ? '#c0392b' : '#27ae60';

    const html = `
    <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;max-width:860px;">
      <div style="background:linear-gradient(135deg,#00287a,#1a4aaf);border-radius:8px;padding:14px 20px;margin-bottom:16px;display:flex;justify-content:space-between;align-items:center;">
        <div>
          <div style="color:rgba(255,255,255,0.7);font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:2px;">Servicio de Impuestos Internos</div>
          <div style="color:white;font-size:22px;font-weight:800;letter-spacing:2px;margin-top:2px;">FORMULARIO 29</div>
          <div style="color:rgba(255,255,255,0.85);font-size:11px;margin-top:2px;">Declaración Mensual y Pago Simultáneo</div>
        </div>
        <div style="text-align:right;">
          <div style="color:rgba(255,255,255,0.7);font-size:10px;text-transform:uppercase;">Período</div>
          <div style="color:white;font-size:18px;font-weight:700;">${MESES[parseInt(frm.doc.mes)] || frm.doc.mes} ${frm.doc.ano}</div>
          <div style="color:rgba(255,255,255,0.85);font-size:11px;margin-top:2px;">${frm.doc.cliente || ''}</div>
        </div>
      </div>
      ${seccion('IVA Débito — Ventas y Servicios', '#1a4aaf', 'tabla_debitos',  frm.doc.tabla_debitos,  'subtotal-debitos')}
      ${seccion('IVA Crédito — Compras',           '#1a7a3c', 'tabla_creditos', frm.doc.tabla_creditos, 'subtotal-creditos')}
      ${seccion('Otros Impuestos y Retenciones',   '#b45309', 'tabla_impuestos',frm.doc.tabla_impuestos,'subtotal-impuestos')}
      <div style="background:#fafafa;border:1px solid #e8e8e8;border-radius:8px;padding:16px 20px;box-shadow:0 1px 4px rgba(0,0,0,0.04);">
        <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;color:#888;margin-bottom:12px;">Liquidación</div>
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-bottom:10px;">
          <div style="background:white;border:1px solid #e0e8f8;border-left:4px solid #1a4aaf;border-radius:6px;padding:10px 14px;">
            <div style="font-size:10px;color:#1a4aaf;font-weight:600;text-transform:uppercase;">Débito IVA</div>
            <div style="font-size:18px;font-weight:700;color:#222;margin-top:4px;" id="resumen-debitos">$${fmt(deb)}</div>
          </div>
          <div style="background:white;border:1px solid #dcf0e4;border-left:4px solid #1a7a3c;border-radius:6px;padding:10px 14px;">
            <div style="font-size:10px;color:#1a7a3c;font-weight:600;text-transform:uppercase;">Crédito IVA</div>
            <div style="font-size:18px;font-weight:700;color:#222;margin-top:4px;" id="resumen-creditos">$${fmt(cred)}</div>
          </div>
          <div style="background:white;border:1px solid #fde8cc;border-left:4px solid #b45309;border-radius:6px;padding:10px 14px;">
            <div style="font-size:10px;color:#b45309;font-weight:600;text-transform:uppercase;">Otros Impuestos</div>
            <div style="font-size:18px;font-weight:700;color:#222;margin-top:4px;" id="resumen-impuestos">$${fmt(imp)}</div>
          </div>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:10px;">
          <div style="background:white;border:1px solid ${iva_det > 0 ? '#fad1d1' : '#eee'};border-left:4px solid ${iva_det > 0 ? '#c0392b' : '#aaa'};border-radius:6px;padding:10px 14px;">
            <div style="font-size:10px;color:${iva_det > 0 ? '#c0392b' : '#888'};font-weight:600;text-transform:uppercase;">IVA Determinado</div>
            <div style="font-size:20px;font-weight:700;color:${iva_det > 0 ? '#c0392b' : '#555'};margin-top:4px;" id="resumen-iva-determinado">$${fmt(iva_det)}</div>
          </div>
          <div style="background:white;border:1px solid ${remanente > 0 ? '#dcf0e4' : '#eee'};border-left:4px solid ${remanente > 0 ? '#1a7a3c' : '#aaa'};border-radius:6px;padding:10px 14px;">
            <div style="font-size:10px;color:${remanente > 0 ? '#1a7a3c' : '#888'};font-weight:600;text-transform:uppercase;">Remanente Mes Siguiente</div>
            <div style="font-size:20px;font-weight:700;color:${remanente > 0 ? '#1a7a3c' : '#555'};margin-top:4px;" id="resumen-remanente">$${fmt(remanente)}</div>
          </div>
        </div>
        <div style="display:flex;justify-content:space-between;align-items:center;background:white;border:2px solid ${color_total};border-radius:8px;padding:12px 18px;">
          <div>
            ${flt(frm.doc.postergacion_del_periodo) > 0 ? `<div style="font-size:11px;color:#b45309;"><span style="font-weight:600;">Postergación IVA descontada:</span> $${fmt(frm.doc.postergacion_del_periodo)}</div>` : ''}
          </div>
          <div style="text-align:right;">
            <div style="font-size:11px;color:#666;text-transform:uppercase;letter-spacing:1px;">${total > 0 ? 'Total a Pagar' : 'Sin Pago'}</div>
            <div style="font-size:28px;font-weight:800;color:${color_total};" id="total-pagar">$${fmt(total)}</div>
          </div>
        </div>
        ${iva_det > 0 ? `
        <div style="margin-top:10px;display:flex;justify-content:flex-end;gap:8px;align-items:center;">
          ${flt(frm.doc.postergacion_del_periodo) > 0 ? `
            <div style="font-size:11px;color:#b45309;background:#fff8ec;border:1px solid #f5c97a;border-radius:6px;padding:5px 12px;">
              ⏳ Postergación activa: <strong>$${fmt(frm.doc.postergacion_del_periodo)}</strong>
            </div>
            <button onclick="window.cancelar_postergacion_iva('${frm.doc.name}')"
              style="border:1px solid #c0392b;background:white;color:#c0392b;border-radius:6px;padding:6px 14px;font-size:11px;font-weight:700;cursor:pointer;">
              ✕ Cancelar Postergación
            </button>
          ` : `
            <button onclick="window.postergar_iva_f29('${frm.doc.name}', ${iva_det})"
              style="background:#b45309;color:white;border:none;border-radius:6px;padding:8px 18px;font-size:12px;font-weight:700;cursor:pointer;box-shadow:0 2px 6px rgba(180,83,9,.3);">
              ⏳ Postergar IVA
            </button>
          `}
        </div>
        ` : ''}
      </div>
    </div>`;

    frm.fields_dict.vista_f29.$wrapper.html(html);
    window.current_f29_form = frm;
    setTimeout(() => agregar_eventos_inputs(), 100);
}

// ── Inputs del HTML ─────────────────────────────────────────────────────────
function agregar_eventos_inputs() {
    document.querySelectorAll('input.monto-field:not([readonly])').forEach(inp => {
        inp.addEventListener('focus', function() {
            this.value = parse(this.value) || '';
            this.select();
        });
        inp.addEventListener('blur', function() {
            const v = parse(this.value);
            this.value = fmt(v);
            this.setAttribute('data-monto-real', v);
            window.actualizar_monto_f29(this);
        });
        inp.addEventListener('keyup', e => { if (e.key === 'Enter') e.target.blur(); });
    });
}

// ── Actualizar monto desde input HTML ──────────────────────────────────────
window.actualizar_monto_f29 = function(input) {
    try {
        const tabla_key  = input.getAttribute('data-tabla');
        const idx        = parseInt(input.getAttribute('data-idx'));
        const nuevo      = parse(input.value);
        const frm        = window.current_f29_form;
        if (!frm) return;
        const row = (frm.doc[tabla_key] || []).find(r => r.idx === idx);
        if (!row) return;
        row.monto = nuevo;
        frm.doc.__unsaved = 1;
        try {
            const gr = frm.fields_dict[tabla_key].grid.grid_rows_by_docname[row.name];
            if (gr) gr.doc.monto = nuevo;
        } catch(e) {}
        recalcular_subtotales_instantaneos(frm);
        frm.dirty();
        frappe.show_alert({ message: '$' + fmt(nuevo) + ' guardado', indicator: 'green' }, 1);
    } catch(e) {
        frappe.show_alert({ message: 'Error al actualizar monto', indicator: 'red' }, 2);
    }
};

// ── Recalcular subtotales ───────────────────────────────────────────────────
function recalcular_subtotales_instantaneos(frm) {
    const sumar = (filas) => (filas || []).reduce((acc, r) => {
        const m = flt(r.monto);
        return acc + (r.tipo_operacion_subtotal === 'Resta' ? -m : r.tipo_operacion_subtotal === 'Informativo' ? 0 : m);
    }, 0);

    const deb  = sumar(frm.doc.tabla_debitos);
    const cred = sumar(frm.doc.tabla_creditos);
    const imp  = sumar(frm.doc.tabla_impuestos);
    const iva_det   = Math.max(0, deb - cred);
    const remanente = Math.max(0, cred - deb);
    const posterg   = flt(frm.doc.postergacion_del_periodo);
    const total     = Math.max(0, iva_det - posterg + imp);

    const el = (id, v) => { const e = document.getElementById(id); if (e) e.textContent = '$' + fmt(v); };
    el('resumen-debitos',        deb);
    el('resumen-creditos',       cred);
    el('resumen-impuestos',      imp);
    el('resumen-iva-determinado',iva_det);
    el('resumen-remanente',      remanente);
    el('total-pagar',            total);
    el('subtotal-debitos',       deb);
    el('subtotal-debitos_foot',  deb);
    el('subtotal-creditos',      cred);
    el('subtotal-creditos_foot', cred);
    el('subtotal-impuestos',     imp);
    el('subtotal-impuestos_foot',imp);

    Object.assign(frm.doc, {
        subtotal_debitos: deb, subtotal_creditos: cred,
        subtotal_postergacion_iva: posterg, subtotal_otros_impuestos: imp,
        impuesto_determinado: iva_det, remanente_mes_siguiente: remanente,
        total_a_pagar_f29: total,
    });
    ['subtotal_debitos','subtotal_creditos','subtotal_postergacion_iva',
     'subtotal_otros_impuestos','impuesto_determinado','remanente_mes_siguiente',
     'total_a_pagar_f29'].forEach(f => frm.refresh_field(f));
}

// ── Postergación IVA ────────────────────────────────────────────────────────
window.postergar_iva_f29 = function(doc_name, iva_det) {
    const frm = window.current_f29_form;
    const MESES = ['','Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'];
    const mes   = parseInt(frm.doc.mes);
    const ano   = parseInt(frm.doc.ano);
    const mesLabel = (m, a) => `${MESES[((m-1)%12)+1]} ${m > 12 ? a+1 : a}`;
    const m1 = ((mes)   % 12) + 1;  const a1 = mes === 12 ? ano+1 : ano;
    const m2 = ((mes+1) % 12) + 1;  const a2 = mes >= 11 ? ano+1 : ano;

    const d = new frappe.ui.Dialog({
        title: '⏳ Postergar IVA — Art. 64 D.L. 825',
        fields: [
            { fieldtype: 'HTML', options: `<div style="background:#fff8ec;border-left:3px solid #b45309;border-radius:4px;padding:10px 14px;margin-bottom:4px;font-size:12px;color:#7d4e00;">Permite diferir el pago del IVA determinado por <b>1 o 2 meses</b>.<br>Solo disponible para contribuyentes <b>Pro Pyme</b> (Art. 64 D.L. 825).</div>` },
            { label: 'IVA Determinado del período', fieldname: 'iva_det_info', fieldtype: 'HTML', options: `<div style="font-size:22px;font-weight:800;color:#b45309;padding:6px 0 10px;">$${fmt(iva_det)}</div>` },
            { label: 'Monto a Postergar ($)', fieldname: 'monto', fieldtype: 'Currency', default: iva_det, reqd: 1, description: 'Máximo: IVA determinado del período' },
            { label: 'Diferir hasta', fieldname: 'meses_diferidos', fieldtype: 'Select', options: `1\n2`, default: '2', reqd: 1, description: `1 mes → F29 de ${mesLabel(m1,a1)} | 2 meses → F29 de ${mesLabel(m2,a2)}` }
        ],
        primary_action_label: 'Registrar Postergación',
        primary_action(values) {
            if (values.monto <= 0) { frappe.msgprint('El monto debe ser mayor a 0.'); return; }
            if (values.monto > iva_det) { frappe.msgprint('El monto no puede superar el IVA determinado.'); return; }
            d.hide();
            frappe.call({
                method: 'evoluciona_pyme_v2.evoluciona_pyme_v2.api.registrar_postergacion_iva',
                args: { doc_name, monto: values.monto, meses_diferidos: values.meses_diferidos },
                freeze: true, freeze_message: 'Registrando postergación...',
                callback(r) {
                    const res = r.message;
                    if (res?.status === 'ok') { frappe.show_alert({ message: res.message, indicator: 'orange' }, 6); frm.reload_doc(); }
                    else { frappe.msgprint({ title: 'Error', message: res?.message, indicator: 'red' }); }
                }
            });
        }
    });
    d.show();
};

window.cancelar_postergacion_iva = function(doc_name) {
    frappe.confirm('¿Cancelar la postergación de IVA de este período?', () => {
        frappe.call({
            method: 'evoluciona_pyme_v2.evoluciona_pyme_v2.api.cancelar_postergacion_iva',
            args: { doc_name }, freeze: true, freeze_message: 'Cancelando postergación...',
            callback(r) {
                const res = r.message;
                if (res?.status === 'ok') { frappe.show_alert({ message: 'Postergación cancelada.', indicator: 'green' }, 4); window.current_f29_form.reload_doc(); }
                else { frappe.msgprint({ title: 'Error', message: res?.message, indicator: 'red' }); }
            }
        });
    });
};

// ── Eventos del formulario ──────────────────────────────────────────────────
frappe.ui.form.on('Borrador_F29', {

    refresh(frm) {
        if (frm.is_new()) return;

        frm.clear_custom_buttons();
        renderizar_f29(frm);

        frm.add_custom_button(__('◀ Panel Mensual'), () => {
            frappe.set_route('panel_mensual');
        });

        frm.add_custom_button(__('📋 Ver Libros'), () => {
            frappe.route_options = { cliente: frm.doc.cliente, ano: frm.doc.ano, mes: frm.doc.mes, libro: 'compras' };
            frappe.set_route('libro_rcv');
        });

        frm.add_custom_button(__('Calcular Automático'), () => {
            frappe.call({
                method: 'evoluciona_pyme_v2.evoluciona_pyme_v2.api.recalcular_asistente_f29',
                args: { doc_name: frm.doc.name },
                freeze: true, freeze_message: __('Calculando F29…'),
                callback(r) {
                    if (r.message?.status === 'ok') {
                        frappe.show_alert({ message: r.message.message, indicator: 'green' }, 5);
                        frm.reload_doc();
                        // Notificar a Ficha Cliente para que refresque el panel
                        frappe.realtime.publish('f29_calculado', { cliente: frm.doc.cliente });
                    } else {
                        frappe.msgprint({ title: 'Error', message: r.message?.message, indicator: 'red' });
                    }
                }
            });
        }).addClass('btn-primary');

        frm.add_custom_button(__('Cargar desde API SII'), () => {
            const d = new frappe.ui.Dialog({
                title: 'Cargar documentos desde API SII',
                fields: [
                    { fieldtype: 'HTML', options: `<div style="margin-bottom:12px;padding:8px 12px;background:#e8f4fd;border-left:3px solid #1a4aaf;border-radius:4px;font-size:12px;color:#1a4aaf;">Selecciona los libros a cargar para el período <b>${frm.doc.mes}/${frm.doc.ano}</b>. Se eliminarán y reemplazarán los registros existentes.</div>` },
                    { label: 'Libro de Compras', fieldname: 'compras', fieldtype: 'Check', default: 1 },
                    { label: 'Libro de Ventas', fieldname: 'ventas', fieldtype: 'Check', default: 1 },
                    { label: 'Honorarios (BHE/BTE)', fieldname: 'honorarios', fieldtype: 'Check', default: 0 },
                ],
                primary_action_label: 'Procesar',
                primary_action(values) {
                    if (!values.compras && !values.ventas && !values.honorarios) {
                        frappe.msgprint({ title: 'Sin selección', message: 'Selecciona al menos un libro para cargar.', indicator: 'orange' });
                        return;
                    }
                    d.hide();
                    frappe.dom.freeze(`⏳ Descargando desde SII…<br><small>Período ${frm.doc.mes}/${frm.doc.ano} — por favor espera.</small>`);
                    frappe.call({
                        method: 'evoluciona_pyme_v2.evoluciona_pyme_v2.rcv_api.cargar_documentos_api',
                        args: {
                            doc_name: frm.doc.name,
                            compras: values.compras ? 1 : 0,
                            ventas: values.ventas ? 1 : 0,
                            honorarios: values.honorarios ? 1 : 0,
                        },
                        callback(r) {
                            frappe.dom.unfreeze();
                            if (r.exc) return;
                            const res = r.message || {};
                            frappe.msgprint({
                                title: '✅ Carga completada',
                                message: res.detalle || 'Documentos cargados correctamente.',
                                indicator: 'green',
                                primary_action: { label: 'Recargar F29', action: () => frm.reload_doc() }
                            });
                        },
                        error() { frappe.dom.unfreeze(); }
                    });
                }
            });
            d.show();
        }).addClass('btn-primary');

        // Importar CSV — Compras
        frm.add_custom_button(__('Importar Compras CSV'), () => {
            _dlg_importar(frm, 'Importar Libro de Compras — CSV SII',
                `<div style="padding:8px 12px;background:#e8f4fd;border-left:3px solid #1a4aaf;border-radius:4px;font-size:12px;color:#1a4aaf;margin-bottom:8px;">Sube el archivo <b>RCV_COMPRA_REGISTRO_*.csv</b>. Se reemplazarán los registros del período <b>${frm.doc.mes}/${frm.doc.ano}</b>.</div>`,
                'evoluciona_pyme_v2.evoluciona_pyme_v2.api.importar_libro_compras_csv',
                (res) => `<b>${res.insertados}</b> importados, <b>${res.eliminados}</b> eliminados${res.errores ? `, <span style="color:#c0392b;">${res.errores} errores</span>` : ''}`
            );
        }, 'Importar');

        // Importar CSV — Ventas (dos archivos)
        frm.add_custom_button(__('Importar Ventas CSV'), () => {
            const d = new frappe.ui.Dialog({
                title: 'Importar Libro de Ventas — CSV SII',
                fields: [
                    { fieldtype: 'HTML', options: `<div style="padding:8px 12px;background:#e8f8f0;border-left:3px solid #1a7a3c;border-radius:4px;font-size:12px;color:#1a7a3c;margin-bottom:8px;">Sube uno o ambos archivos del período <b>${frm.doc.mes}/${frm.doc.ano}</b>.</div>` },
                    { label: 'Detalle de documentos (RCV_VENTA_*.csv)', fieldname: 'archivo_detalle', fieldtype: 'Attach', description: 'Facturas, NC, ND individuales' },
                    { label: 'Resumen del mes (RCV_RESUMEN_VENTA_*.csv)', fieldname: 'archivo_resumen', fieldtype: 'Attach', description: 'Totales de boletas' }
                ],
                primary_action_label: 'Importar',
                primary_action(values) {
                    if (!values.archivo_detalle && !values.archivo_resumen) { frappe.msgprint('Sube al menos uno de los dos archivos.'); return; }
                    d.hide();
                    frappe.show_alert({ message: 'Importando ventas...', indicator: 'blue' }, 5);
                    frappe.call({
                        method: 'evoluciona_pyme_v2.evoluciona_pyme_v2.api.importar_libro_ventas_csv',
                        args: { doc_name: frm.doc.name, file_url_detalle: values.archivo_detalle||'', file_url_resumen: values.archivo_resumen||'' },
                        freeze: true, freeze_message: 'Procesando CSV del SII...',
                        callback(r) {
                            const res = r.message;
                            if (res?.status === 'ok') { frappe.msgprint({ title: 'Importación exitosa', message: `<b>${res.insertados}</b> importados, <b>${res.eliminados}</b> eliminados`, indicator: 'green' }); frm.reload_doc(); }
                            else { frappe.msgprint({ title: 'Error', message: res?.message, indicator: 'red' }); }
                        }
                    });
                }
            });
            d.show();
        }, 'Importar');

        // Importar CSV — Honorarios
        frm.add_custom_button(__('Importar Honorarios CSV'), () => {
            _dlg_importar(frm, 'Importar Libro de Honorarios — CSV SII',
                `<div style="padding:8px 12px;background:#fef6e8;border-left:3px solid #e67e22;border-radius:4px;font-size:12px;color:#7d5a1e;margin-bottom:8px;">Sube el CSV del Informe de Honorarios del SII. Se reemplazarán las boletas del período <b>${frm.doc.mes}/${frm.doc.ano}</b>.</div>`,
                'evoluciona_pyme_v2.evoluciona_pyme_v2.api.importar_libro_honorarios_csv',
                (res) => `<b>${res.insertados}</b> boletas importadas, <b>${res.eliminados}</b> eliminadas${res.errores ? `, <span style="color:#c0392b;">${res.errores} errores</span>` : ''}`
            );
        }, 'Importar');

        // Importar CSV — LRE Remuneraciones
        frm.add_custom_button(__('Importar Remuneraciones (LRE)'), () => {
            _dlg_importar(frm, 'Importar LRE — Libro de Remuneraciones Electrónico',
                `<div style="padding:8px 12px;background:#f0f4ff;border-left:3px solid #3b5bdb;border-radius:4px;font-size:12px;color:#2c3a8c;margin-bottom:8px;">Sube el CSV del LRE descargado de Previred. Período <b>${frm.doc.mes}/${frm.doc.ano}</b>.</div>`,
                'evoluciona_pyme_v2.evoluciona_pyme_v2.api.importar_lre_csv',
                (res) => `<b>${res.empleados}</b> trabajadores, Total Previred: <b>$${(res.total_previred||0).toLocaleString('es-CL')}</b>, Imp. Único: <b>$${(res.imp_unico||0).toLocaleString('es-CL')}</b>`
            );
        }, 'Importar');

        if (frm.doc.cliente) {
            frm.add_custom_button(__('Ficha Cliente'), () => frappe.set_route('Form', 'Ficha_Cliente', frm.doc.cliente), 'Navegar');
        }
        if (frm.doc.declaracion_mensual_vinculada) {
            frm.add_custom_button(__('Declaración Mensual'), () => frappe.set_route('Form', 'Declaracion_Mensual', frm.doc.declaracion_mensual_vinculada), 'Navegar');
        }
    },

});

// ── Helper diálogo importar CSV ─────────────────────────────────────────────
function _dlg_importar(frm, titulo, info_html, method, msg_fn) {
    const d = new frappe.ui.Dialog({
        title: titulo,
        fields: [
            { fieldtype: 'HTML', options: info_html },
            { label: 'Archivo CSV', fieldname: 'archivo', fieldtype: 'Attach', reqd: 1, options: { restrictions: { allowed_file_types: ['.csv', '.CSV'] } } }
        ],
        primary_action_label: 'Importar',
        primary_action(values) {
            if (!values.archivo) { frappe.msgprint('Selecciona un archivo CSV.'); return; }
            d.hide();
            frappe.show_alert({ message: 'Importando...', indicator: 'blue' }, 5);
            frappe.call({
                method: method,
                args: { doc_name: frm.doc.name, file_url: values.archivo },
                freeze: true, freeze_message: 'Procesando archivo...',
                callback(r) {
                    const res = r.message;
                    if (res?.status === 'ok') { frappe.msgprint({ title: 'Importación exitosa', message: msg_fn(res), indicator: 'green' }); frm.reload_doc(); }
                    else { frappe.msgprint({ title: 'Error', message: res?.message, indicator: 'red' }); }
                }
            });
        }
    });
    d.show();
}
