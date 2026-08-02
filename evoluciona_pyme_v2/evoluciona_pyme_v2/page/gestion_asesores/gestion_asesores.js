frappe.pages['gestion_asesores'].on_page_load = function(wrapper) {
    frappe.ui.make_app_page({ parent: wrapper, title: 'Gestión de Asesores', single_column: true });

    $(wrapper).find('.page-content').append(`
    <style>
        .ga-wrap { font-family: 'Inter', sans-serif; padding: 20px; background: #f0f4f8; min-height: 100vh; }
        .ga-header { background: linear-gradient(135deg, #0f2027, #1a3a4a 40%, #005f6b);
                     border-radius: 12px; padding: 24px 28px; margin-bottom: 20px;
                     display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; }
        .ga-header h2 { color: #fff; margin: 0; font-size: 20px; font-weight: 800; }
        .ga-header p  { color: rgba(255,255,255,.6); margin: 4px 0 0; font-size: 12px; }
        .ga-btn-nuevo { background: linear-gradient(135deg,#17a2b8,#00d4aa); color:#fff; border:none;
                        padding: 9px 18px; border-radius: 8px; font-weight: 700; font-size: 13px;
                        cursor: pointer; transition: opacity .2s; }
        .ga-btn-nuevo:hover { opacity: .85; }

        /* Barra de controles */
        .ga-controls { background:#fff; border-radius: 10px; padding: 16px 20px; margin-bottom: 16px;
                       box-shadow: 0 2px 8px rgba(0,0,0,.06); display: flex; gap: 12px; flex-wrap: wrap; align-items: flex-end; }
        .ga-ctrl-group { display: flex; flex-direction: column; gap: 4px; }
        .ga-ctrl-group label { font-size: 11px; font-weight: 700; color: #718096; text-transform: uppercase; }
        .ga-ctrl-group select, .ga-ctrl-group input {
            border: 1.5px solid #e2e8f0; border-radius: 7px; padding: 7px 12px;
            font-size: 13px; color: #2d3748; background: #f8fafc; min-width: 180px; }
        .ga-ctrl-group select:focus, .ga-ctrl-group input:focus { outline: none; border-color: #17a2b8; }
        .ga-btn-accion { padding: 8px 20px; border-radius: 8px; border: none; font-weight: 700;
                         font-size: 13px; cursor: pointer; transition: all .2s; }
        .ga-btn-asignar { background: #17a2b8; color: #fff; }
        .ga-btn-asignar:hover { background: #138496; }
        .ga-btn-quitar  { background: #e53e3e; color: #fff; }
        .ga-btn-quitar:hover  { background: #c53030; }
        .ga-btn-accion:disabled { opacity: .4; cursor: not-allowed; }

        /* Grid dos columnas */
        .ga-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
        @media (max-width: 800px) { .ga-grid { grid-template-columns: 1fr; } }

        .ga-col { background: #fff; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,.06); overflow: hidden; }
        .ga-col-head { padding: 14px 18px; border-bottom: 1.5px solid #e2e8f0;
                       display: flex; align-items: center; justify-content: space-between; }
        .ga-col-title { font-size: 13px; font-weight: 800; color: #2d3748; text-transform: uppercase; }
        .ga-col-count  { font-size: 12px; font-weight: 700; color: #17a2b8;
                         background: #e6fffa; padding: 3px 10px; border-radius: 20px; }
        .ga-col-search { width: 100%; padding: 10px 16px; border: none; border-bottom: 1.5px solid #e2e8f0;
                         font-size: 13px; outline: none; background: #fafafa; }

        /* Sel. todas checkbox */
        .ga-sel-todas { display: flex; align-items: center; gap: 8px; padding: 8px 16px;
                        border-bottom: 1px solid #e2e8f0; font-size: 12px; color: #718096; cursor: pointer; }
        .ga-sel-todas input { cursor: pointer; }

        /* Lista de clientes */
        .ga-list { max-height: 480px; overflow-y: auto; }
        .ga-item { display: flex; align-items: center; gap: 10px; padding: 10px 16px;
                   border-bottom: 1px solid #f0f4f8; cursor: pointer; transition: background .15s; }
        .ga-item:hover { background: #f7fafc; }
        .ga-item.selected { background: #e6fffa; }
        .ga-item input[type=checkbox] { flex-shrink: 0; cursor: pointer; width: 15px; height: 15px; }
        .ga-item-info { flex: 1; min-width: 0; }
        .ga-item-name { font-size: 13px; font-weight: 700; color: #2d3748;
                        white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .ga-item-rut  { font-size: 11px; color: #a0aec0; }
        .ga-item-badge { font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 20px;
                         white-space: nowrap; flex-shrink: 0; }
        .badge-asignado  { background: #e6fffa; color: #00a884; }
        .badge-libre     { background: #f0f4f8; color: #718096; }

        .ga-empty { text-align: center; padding: 40px 20px; color: #a0aec0; font-size: 13px; }

        /* Badge de rol */
        .ga-rol-badge { font-size: 10px; padding: 2px 8px; border-radius: 12px; font-weight: 700; margin-left: 6px; }
        .rol-admin      { background:#fee2e2; color:#dc2626; }
        .rol-supervisor { background:#fef3c7; color:#d97706; }
        .rol-senior     { background:#dbeafe; color:#1d4ed8; }
        .rol-asesor     { background:#f0fdf4; color:#16a34a; }
    </style>
    <div class="ga-wrap">

        <!-- Header -->
        <div class="ga-header">
            <div>
                <h2>👥 Gestión de Asesores</h2>
                <p>Asigna y administra los clientes de cada asesor</p>
            </div>
            <button class="ga-btn-nuevo" id="ga-btn-nuevo">+ Nuevo Asesor</button>
        </div>

        <!-- Controles -->
        <div class="ga-controls">
            <div class="ga-ctrl-group">
                <label>Asesor destino</label>
                <select id="ga-sel-usuario">
                    <option value="">— Selecciona un asesor —</option>
                </select>
            </div>
            <div class="ga-ctrl-group">
                <label>Filtrar lista</label>
                <select id="ga-sel-filtro">
                    <option value="todos">Todos los clientes</option>
                    <option value="sin_asignar">Sin asignar</option>
                    <option value="por_usuario">Del asesor seleccionado</option>
                </select>
            </div>
            <div style="margin-left:auto; display:flex; gap:8px; align-items:flex-end;">
                <button class="ga-btn-accion ga-btn-asignar" id="ga-btn-asignar" disabled>
                    ✓ Asignar seleccionados
                </button>
                <button class="ga-btn-accion ga-btn-quitar" id="ga-btn-quitar" disabled>
                    ✗ Quitar asignación
                </button>
            </div>
        </div>

        <!-- Grid dos columnas -->
        <div class="ga-grid">
            <!-- Columna izquierda: disponibles -->
            <div class="ga-col">
                <div class="ga-col-head">
                    <span class="ga-col-title">📋 Empresas</span>
                    <span class="ga-col-count" id="ga-left-count">0</span>
                </div>
                <input class="ga-col-search" id="ga-search-left" placeholder="🔍 Buscar empresa...">
                <div class="ga-sel-todas">
                    <input type="checkbox" id="ga-check-all-left"> Seleccionar todas las visibles
                </div>
                <div class="ga-list" id="ga-list-left">
                    <div class="ga-empty">Selecciona un asesor para comenzar</div>
                </div>
            </div>

            <!-- Columna derecha: asignadas al asesor -->
            <div class="ga-col">
                <div class="ga-col-head">
                    <span class="ga-col-title">✅ Asignadas al asesor</span>
                    <span class="ga-col-count" id="ga-right-count">0</span>
                </div>
                <input class="ga-col-search" id="ga-search-right" placeholder="🔍 Buscar en asignadas...">
                <div class="ga-sel-todas">
                    <input type="checkbox" id="ga-check-all-right"> Seleccionar todas las visibles
                </div>
                <div class="ga-list" id="ga-right-list">
                    <div class="ga-empty">Selecciona un asesor arriba</div>
                </div>
            </div>
        </div>
    </div>`);

    // ── Estado ─────────────────────────────────────────────────
    let todosClientes = [];
    let selLeft  = new Set(); // checks col izquierda
    let selRight = new Set(); // checks col derecha

    // ── Cargar asesores ────────────────────────────────────────
    frappe.call({
        method: 'evoluciona_pyme_v2.evoluciona_pyme_v2.asesores.get_asesores',
        callback(r) {
            const asesores = r.message || [];
            const sel = document.getElementById('ga-sel-usuario');
            asesores.forEach(u => {
                const etiq = { admin:'Admin', supervisor:'Supervisor', senior:'Senior', asesor:'Asesor' }[u.rol] || '';
                const opt = document.createElement('option');
                opt.value = u.name;
                opt.textContent = `${u.full_name || u.name} (${etiq}) — ${u.total_asignados} clientes`;
                sel.appendChild(opt);
            });
        }
    });

    // ── Cargar clientes ────────────────────────────────────────
    function cargarClientes() {
        const usuario = document.getElementById('ga-sel-usuario').value;
        const filtro  = document.getElementById('ga-sel-filtro').value;

        frappe.call({
            method: 'evoluciona_pyme_v2.evoluciona_pyme_v2.asesores.get_clientes_para_asignacion',
            args: { filtro, usuario_filtro: filtro === 'por_usuario' ? usuario : null },
            callback(r) {
                todosClientes = r.message || [];
                selLeft.clear();
                selRight.clear();
                renderColumnas();
                actualizarBotones();
            }
        });
    }

    // ── Render columnas ────────────────────────────────────────
    function renderColumnas() {
        const usuario    = document.getElementById('ga-sel-usuario').value;
        const busqLeft   = document.getElementById('ga-search-left').value.toLowerCase();
        const busqRight  = document.getElementById('ga-search-right').value.toLowerCase();

        const asignados  = todosClientes.filter(c => c.asesor_asignado === usuario);
        const disponibles = todosClientes.filter(c => c.asesor_asignado !== usuario || !usuario);

        renderLista('ga-list-left', 'ga-left-count', disponibles, busqLeft, selLeft, 'left');
        renderLista('ga-right-list', 'ga-right-count', asignados,  busqRight, selRight, 'right');
    }

    function renderLista(listId, countId, items, busq, selSet, lado) {
        const listEl  = document.getElementById(listId);
        const countEl = document.getElementById(countId);
        const visible = items.filter(c =>
            c.razon_social.toLowerCase().includes(busq) ||
            (c.rut_cliente || '').toLowerCase().includes(busq));

        countEl.textContent = visible.length;

        if (!visible.length) {
            listEl.innerHTML = '<div class="ga-empty">Sin resultados</div>';
            return;
        }

        listEl.innerHTML = visible.map(c => {
            const checked = selSet.has(c.name) ? 'checked' : '';
            const badge   = c.nombre_asesor
                ? `<span class="ga-item-badge badge-asignado">${c.nombre_asesor}</span>`
                : `<span class="ga-item-badge badge-libre">Sin asignar</span>`;
            return `
            <div class="ga-item ${selSet.has(c.name) ? 'selected' : ''}"
                 data-name="${c.name}" data-lado="${lado}">
                <input type="checkbox" ${checked} data-name="${c.name}" data-lado="${lado}">
                <div class="ga-item-info">
                    <div class="ga-item-name">${c.razon_social}</div>
                    <div class="ga-item-rut">${c.rut_cliente || ''}</div>
                </div>
                ${badge}
            </div>`;
        }).join('');

        // Eventos en items
        listEl.querySelectorAll('.ga-item').forEach(el => {
            el.addEventListener('click', function(e) {
                if (e.target.tagName === 'INPUT') return;
                const cb = el.querySelector('input[type=checkbox]');
                cb.checked = !cb.checked;
                toggleSel(cb.dataset.name, cb.dataset.lado, cb.checked, el);
            });
        });
        listEl.querySelectorAll('input[type=checkbox]').forEach(cb => {
            cb.addEventListener('change', e => {
                toggleSel(cb.dataset.name, cb.dataset.lado, cb.checked,
                          cb.closest('.ga-item'));
            });
        });
    }

    function toggleSel(name, lado, checked, el) {
        const set = lado === 'left' ? selLeft : selRight;
        if (checked) { set.add(name); el.classList.add('selected'); }
        else         { set.delete(name); el.classList.remove('selected'); }
        actualizarBotones();
    }

    function actualizarBotones() {
        document.getElementById('ga-btn-asignar').disabled =
            selLeft.size === 0 || !document.getElementById('ga-sel-usuario').value;
        document.getElementById('ga-btn-quitar').disabled  = selRight.size === 0;
    }

    // ── Sel. todas ─────────────────────────────────────────────
    document.getElementById('ga-check-all-left').addEventListener('change', function() {
        document.querySelectorAll('#ga-list-left .ga-item').forEach(el => {
            const cb = el.querySelector('input');
            cb.checked = this.checked;
            toggleSel(cb.dataset.name, 'left', this.checked, el);
        });
    });
    document.getElementById('ga-check-all-right').addEventListener('change', function() {
        document.querySelectorAll('#ga-right-list .ga-item').forEach(el => {
            const cb = el.querySelector('input');
            cb.checked = this.checked;
            toggleSel(cb.dataset.name, 'right', this.checked, el);
        });
    });

    // ── Búsqueda ───────────────────────────────────────────────
    document.getElementById('ga-search-left').addEventListener('input', renderColumnas);
    document.getElementById('ga-search-right').addEventListener('input', renderColumnas);

    // ── Cambios de selector ────────────────────────────────────
    document.getElementById('ga-sel-usuario').addEventListener('change', cargarClientes);
    document.getElementById('ga-sel-filtro').addEventListener('change', cargarClientes);

    // ── Asignar ────────────────────────────────────────────────
    document.getElementById('ga-btn-asignar').addEventListener('click', function() {
        const usuario = document.getElementById('ga-sel-usuario').value;
        if (!usuario || selLeft.size === 0) return;
        const lista = [...selLeft];
        frappe.confirm(
            `¿Asignar <strong>${lista.length}</strong> empresa(s) al asesor seleccionado?`,
            () => {
                frappe.call({
                    method: 'evoluciona_pyme_v2.evoluciona_pyme_v2.asesores.asignar_clientes',
                    args: { clientes: lista, usuario },
                    callback(r) {
                        frappe.show_alert({ message: `✅ ${r.message.asignados} empresa(s) asignadas`, indicator: 'green' });
                        cargarClientes();
                    }
                });
            }
        );
    });

    // ── Quitar ─────────────────────────────────────────────────
    document.getElementById('ga-btn-quitar').addEventListener('click', function() {
        if (selRight.size === 0) return;
        const lista = [...selRight];
        frappe.confirm(
            `¿Quitar la asignación de <strong>${lista.length}</strong> empresa(s)?`,
            () => {
                frappe.call({
                    method: 'evoluciona_pyme_v2.evoluciona_pyme_v2.asesores.quitar_clientes',
                    args: { clientes: lista },
                    callback(r) {
                        frappe.show_alert({ message: `🔄 ${r.message.quitados} asignación(es) removidas`, indicator: 'orange' });
                        cargarClientes();
                    }
                });
            }
        );
    });

    // ── Nuevo asesor ───────────────────────────────────────────
    document.getElementById('ga-btn-nuevo').addEventListener('click', function() {
        frappe.new_doc('User');
    });

    // Carga inicial
    cargarClientes();
};
