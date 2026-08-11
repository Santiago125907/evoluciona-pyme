frappe.pages['salud_cron'].on_page_load = function(wrapper) {
    const page = frappe.ui.make_app_page({ parent: wrapper, title: 'Salud del Cron', single_column: true });

    page.add_button('🔄 Actualizar', cargar, { btn_class: 'btn-primary' });

    $(wrapper).find('.page-content').append(`
    <style>
        .sc-wrap { font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; padding:10px 0 40px; }
        .sc-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(320px,1fr)); gap:16px; margin-bottom:20px; }
        .sc-card { background:#fff; border-radius:10px; padding:18px 20px; box-shadow:0 2px 8px rgba(0,0,0,.06); }
        .sc-card h4 { margin:0 0 10px; font-size:14px; color:#1a3a4a; }
        .sc-badge { display:inline-block; padding:3px 10px; border-radius:12px; font-size:11px; font-weight:700; }
        .sc-ok   { background:#e6f7ea; color:#1e7e34; }
        .sc-bad  { background:#fdecea; color:#c0392b; }
        .sc-row  { display:flex; justify-content:space-between; font-size:12px; color:#555; padding:4px 0; border-bottom:1px solid #f0f0f0; }
        .sc-row:last-child { border-bottom:none; }
        .sc-corridas { display:flex; gap:4px; margin-top:10px; flex-wrap:wrap; }
        .sc-punto { width:10px; height:10px; border-radius:50%; }
        .sc-punto.ok { background:#27ae60; }
        .sc-punto.fail { background:#e74c3c; }
        .sc-errores { background:#fff; border-radius:10px; padding:18px 20px; box-shadow:0 2px 8px rgba(0,0,0,.06); }
        .sc-errores table { width:100%; font-size:12px; border-collapse:collapse; }
        .sc-errores th { text-align:left; padding:6px 8px; color:#888; font-weight:600; border-bottom:2px solid #eee; }
        .sc-errores td { padding:6px 8px; border-bottom:1px solid #f5f5f5; vertical-align:top; }
        .sc-sin-errores { text-align:center; padding:30px; color:#27ae60; font-size:13px; }
    </style>
    <div class="sc-wrap">
        <div class="sc-grid" id="sc-grid"><div class="sc-loading">Cargando...</div></div>
        <div class="sc-errores">
            <h4 style="margin:0 0 10px;font-size:14px;color:#1a3a4a;">Errores relacionados (últimos 30 días)</h4>
            <div id="sc-errores-content">Cargando...</div>
        </div>
    </div>`);

    function fmt_fecha(f) {
        if (!f) return '—';
        return frappe.datetime.str_to_user(f);
    }

    function tarjeta(titulo, info) {
        const badge = info.corrio_este_mes
            ? `<span class="sc-badge sc-ok">✅ Corrió este mes</span>`
            : `<span class="sc-badge sc-bad">⚠️ No ha corrido este mes</span>`;
        const puntos = (info.ultimas_corridas || []).slice().reverse().map(c =>
            `<span class="sc-punto ${c.status === 'Complete' ? 'ok' : 'fail'}" title="${fmt_fecha(c.creation)} — ${c.status}"></span>`
        ).join('');
        return `
        <div class="sc-card">
            <h4>${titulo}</h4>
            ${badge}
            <div class="sc-row"><span>Habilitado</span><span>${info.habilitado ? 'Sí' : 'No'}</span></div>
            <div class="sc-row"><span>Programado</span><span>Día ${info.dia_configurado} · ${info.hora_configurada}</span></div>
            <div class="sc-row"><span>Última ejecución exitosa</span><span>${fmt_fecha(info.ultima_ejecucion)}</span></div>
            <div class="sc-corridas" title="Últimas corridas del scheduler (más reciente a la derecha)">${puntos}</div>
        </div>`;
    }

    function cargar() {
        $('#sc-grid').html('<div class="sc-loading">Cargando...</div>');
        $('#sc-errores-content').html('Cargando...');
        frappe.call({
            method: 'evoluciona_pyme_v2.evoluciona_pyme_v2.api.get_salud_cron',
            callback(r) {
                const d = r.message || {};
                $('#sc-grid').html(
                    tarjeta('📋 Cron de Declaraciones (día 1)', d.declaraciones || {}) +
                    tarjeta('📥 Cron de RCV / Honorarios (día 5)', d.libros || {})
                );

                const errores = d.errores_recientes || [];
                if (!errores.length) {
                    $('#sc-errores-content').html('<div class="sc-sin-errores">✅ Sin errores relacionados en los últimos 30 días.</div>');
                } else {
                    const filas = errores.map(e => `
                        <tr>
                            <td style="white-space:nowrap;">${fmt_fecha(e.creation)}</td>
                            <td>${frappe.utils.escape_html(e.method || '')}</td>
                            <td>${frappe.utils.escape_html(e.error || '')}</td>
                        </tr>`).join('');
                    $('#sc-errores-content').html(`
                        <table>
                            <thead><tr><th>Fecha</th><th>Origen</th><th>Detalle</th></tr></thead>
                            <tbody>${filas}</tbody>
                        </table>`);
                }
            }
        });
    }

    cargar();
};
