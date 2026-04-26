frappe.pages['panel_app'].on_page_load = function(wrapper) {
    frappe.ui.make_app_page({ parent: wrapper, title: 'Inicio', single_column: true });

    const hoy   = new Date();
    const prev  = new Date(hoy.getFullYear(), hoy.getMonth() - 1, 1);
    const mes   = prev.getMonth() + 1;
    const ano   = prev.getFullYear();
    const meses = ['','Enero','Febrero','Marzo','Abril','Mayo','Junio',
                   'Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'];

    $(wrapper).find('.page-content').append(`
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap');

        .pa-wrap * { box-sizing: border-box; }
        .pa-wrap {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: #f0f4f8;
            min-height: 100vh;
            padding-bottom: 60px;
        }

        /* ── HERO ───────────────────────────────────────────── */
        .pa-hero {
            background: linear-gradient(135deg, #0f2027, #1a3a4a 40%, #005f6b);
            padding: 40px 36px 36px;
            position: relative;
            overflow: hidden;
        }
        .pa-hero::before {
            content: '';
            position: absolute;
            top: -60px; right: -60px;
            width: 320px; height: 320px;
            background: rgba(255,255,255,.04);
            border-radius: 50%;
        }
        .pa-hero::after {
            content: '';
            position: absolute;
            bottom: -80px; left: 20%;
            width: 200px; height: 200px;
            background: rgba(0,200,180,.07);
            border-radius: 50%;
        }
        .pa-hero-top {
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 16px;
            position: relative; z-index: 1;
        }
        .pa-logo {
            display: flex;
            align-items: center;
            gap: 14px;
        }
        .pa-logo-icon {
            width: 52px; height: 52px;
            background: linear-gradient(135deg, #17a2b8, #00d4aa);
            border-radius: 14px;
            display: flex; align-items: center; justify-content: center;
            font-size: 26px;
            box-shadow: 0 4px 20px rgba(0,212,170,.35);
        }
        .pa-logo-text h1 {
            color: #fff;
            font-size: 22px;
            font-weight: 800;
            margin: 0;
            letter-spacing: -.3px;
        }
        .pa-logo-text p {
            color: rgba(255,255,255,.55);
            font-size: 11px;
            margin: 2px 0 0;
            text-transform: uppercase;
            letter-spacing: 1.2px;
        }
        .pa-periodo-badge {
            background: rgba(255,255,255,.1);
            border: 1px solid rgba(255,255,255,.2);
            border-radius: 20px;
            padding: 6px 16px;
            color: rgba(255,255,255,.85);
            font-size: 12px;
            font-weight: 600;
            backdrop-filter: blur(4px);
        }

        /* ── STAT CHIPS en hero ─────────────────────────────── */
        .pa-hero-stats {
            display: flex;
            gap: 12px;
            margin-top: 28px;
            flex-wrap: wrap;
            position: relative; z-index: 1;
        }
        .pa-hstat {
            background: rgba(255,255,255,.09);
            border: 1px solid rgba(255,255,255,.15);
            border-radius: 12px;
            padding: 12px 20px;
            min-width: 110px;
            backdrop-filter: blur(6px);
            transition: background .2s;
        }
        .pa-hstat:hover { background: rgba(255,255,255,.15); }
        .pa-hstat strong {
            display: block;
            font-size: 26px;
            font-weight: 800;
            color: #fff;
            line-height: 1;
        }
        .pa-hstat span {
            font-size: 10px;
            color: rgba(255,255,255,.55);
            text-transform: uppercase;
            letter-spacing: .8px;
            margin-top: 4px;
            display: block;
        }
        .pa-hstat.green strong { color: #2ecc71; }
        .pa-hstat.cyan  strong { color: #17d4e8; }
        .pa-hstat.orange strong { color: #f39c12; }
        .pa-hstat.red   strong { color: #e74c3c; }

        /* ── PROGRESS BAR ───────────────────────────────────── */
        .pa-progress-wrap {
            margin-top: 20px;
            position: relative; z-index: 1;
        }
        .pa-progress-label {
            display: flex;
            justify-content: space-between;
            color: rgba(255,255,255,.6);
            font-size: 11px;
            margin-bottom: 6px;
        }
        .pa-progress-label strong { color: #fff; }
        .pa-progress-bg {
            height: 8px;
            background: rgba(255,255,255,.12);
            border-radius: 4px;
            overflow: hidden;
        }
        .pa-progress-fill {
            height: 100%;
            border-radius: 4px;
            background: linear-gradient(90deg, #17a2b8, #2ecc71);
            width: 0%;
            transition: width .8s cubic-bezier(.4,0,.2,1);
        }

        /* ── BODY ───────────────────────────────────────────── */
        .pa-body { padding: 28px 36px; }

        /* ── SECTION TITLE ──────────────────────────────────── */
        .pa-section-title {
            font-size: 11px;
            font-weight: 700;
            color: #8a9bb0;
            text-transform: uppercase;
            letter-spacing: 1.2px;
            margin: 0 0 14px;
        }

        /* ── ACCESOS RÁPIDOS ────────────────────────────────── */
        .pa-shortcuts {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
            gap: 14px;
            margin-bottom: 32px;
        }
        .pa-sc {
            background: #fff;
            border-radius: 16px;
            padding: 20px 16px;
            cursor: pointer;
            transition: all .2s cubic-bezier(.4,0,.2,1);
            box-shadow: 0 2px 8px rgba(0,0,0,.06);
            border: 2px solid transparent;
            text-align: center;
            text-decoration: none;
            display: block;
        }
        .pa-sc:hover {
            transform: translateY(-3px);
            box-shadow: 0 8px 24px rgba(0,0,0,.12);
            border-color: var(--sc-color, #17a2b8);
        }
        .pa-sc-icon {
            font-size: 32px;
            margin-bottom: 10px;
            display: block;
        }
        .pa-sc-label {
            font-size: 12px;
            font-weight: 700;
            color: #1a3a4a;
            display: block;
            line-height: 1.3;
        }
        .pa-sc-sub {
            font-size: 10px;
            color: #aaa;
            margin-top: 3px;
            display: block;
        }
        .pa-sc .pa-sc-dot {
            width: 6px; height: 6px;
            border-radius: 50%;
            background: var(--sc-color, #17a2b8);
            display: inline-block;
            margin-top: 8px;
        }

        /* ── STATS CARDS ────────────────────────────────────── */
        .pa-cards {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 14px;
            margin-bottom: 32px;
        }
        .pa-card {
            background: #fff;
            border-radius: 16px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,.06);
            border-left: 4px solid var(--card-color, #17a2b8);
            transition: box-shadow .2s;
        }
        .pa-card:hover { box-shadow: 0 6px 20px rgba(0,0,0,.1); }
        .pa-card-top {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
        }
        .pa-card strong {
            font-size: 28px;
            font-weight: 800;
            color: #1a3a4a;
            display: block;
        }
        .pa-card p {
            font-size: 11px;
            color: #888;
            margin: 4px 0 0;
            text-transform: uppercase;
            letter-spacing: .6px;
        }
        .pa-card-ico {
            font-size: 24px;
            opacity: .7;
        }
        .pa-card-sub {
            font-size: 11px;
            color: #aaa;
            margin-top: 10px;
            padding-top: 10px;
            border-top: 1px solid #f0f0f0;
        }

        /* ── COBRANZA SUMMARY ───────────────────────────────── */
        .pa-cobro-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
            margin-bottom: 32px;
        }
        .pa-cobro-card {
            background: #fff;
            border-radius: 14px;
            padding: 18px;
            box-shadow: 0 2px 8px rgba(0,0,0,.06);
            text-align: center;
        }
        .pa-cobro-card .monto {
            font-size: 20px;
            font-weight: 800;
            margin: 6px 0 2px;
        }
        .pa-cobro-card .label {
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: .8px;
            color: #888;
        }
        .pa-cobro-card .count {
            font-size: 11px;
            color: #bbb;
            margin-top: 4px;
        }

        .pa-loading { text-align:center; padding:60px; color:#aaa; font-size:14px; }
        .pa-spinner { display:inline-block; width:28px; height:28px; border:3px solid #e0e0e0;
                      border-top-color:#005f6b; border-radius:50%; animation:spin .7s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }

        @media(max-width:600px) {
            .pa-hero { padding: 24px 20px; }
            .pa-body  { padding: 20px 16px; }
            .pa-cobro-grid { grid-template-columns: 1fr; }
        }
    </style>

    <div class="pa-wrap">
        <div class="pa-hero">
            <div class="pa-hero-top">
                <div class="pa-logo">
                    <div class="pa-logo-icon">📊</div>
                    <div class="pa-logo-text">
                        <h1>Evoluciona Pyme</h1>
                        <p>Gestión contable inteligente</p>
                    </div>
                </div>
                <div class="pa-periodo-badge" id="pa-badge-periodo">Cargando...</div>
            </div>
            <div class="pa-hero-stats" id="pa-hero-stats">
                <div class="pa-loading"><div class="pa-spinner"></div></div>
            </div>
            <div class="pa-progress-wrap">
                <div class="pa-progress-label">
                    <span>Progreso del período</span>
                    <strong id="pa-pct-label">—</strong>
                </div>
                <div class="pa-progress-bg">
                    <div class="pa-progress-fill" id="pa-prog-fill"></div>
                </div>
            </div>
        </div>

        <div class="pa-body">
            <p class="pa-section-title">Acceso rápido</p>
            <div class="pa-shortcuts">
                <a class="pa-sc" style="--sc-color:#17a2b8" onclick="frappe.set_route('panel_mensual')">
                    <span class="pa-sc-icon">📋</span>
                    <span class="pa-sc-label">Panel Mensual</span>
                    <span class="pa-sc-sub">Estado del período</span>
                    <span class="pa-sc-dot"></span>
                </a>
                <a class="pa-sc" style="--sc-color:#2ecc71" onclick="frappe.set_route('List','Ficha_Cliente')">
                    <span class="pa-sc-icon">🏢</span>
                    <span class="pa-sc-label">Clientes</span>
                    <span class="pa-sc-sub">Fichas activas</span>
                    <span class="pa-sc-dot"></span>
                </a>
                <a class="pa-sc" style="--sc-color:#e74c3c" onclick="frappe.set_route('List','Declaracion_Mensual')">
                    <span class="pa-sc-icon">📝</span>
                    <span class="pa-sc-label">Declaraciones</span>
                    <span class="pa-sc-sub">Gestión mensual</span>
                    <span class="pa-sc-dot"></span>
                </a>
                <a class="pa-sc" style="--sc-color:#f39c12" onclick="frappe.set_route('List','Borrador_F29')">
                    <span class="pa-sc-icon">🧾</span>
                    <span class="pa-sc-label">F29</span>
                    <span class="pa-sc-sub">Borradores</span>
                    <span class="pa-sc-dot"></span>
                </a>
                <a class="pa-sc" style="--sc-color:#8e44ad" onclick="frappe.set_route('List','Cobranza_Cliente')">
                    <span class="pa-sc-icon">💰</span>
                    <span class="pa-sc-label">Cobranzas</span>
                    <span class="pa-sc-sub">Por cobrar</span>
                    <span class="pa-sc-dot"></span>
                </a>
                <a class="pa-sc" style="--sc-color:#1abc9c" onclick="frappe.set_route('List','Registro_Remuneraciones')">
                    <span class="pa-sc-icon">👥</span>
                    <span class="pa-sc-label">Remuneraciones</span>
                    <span class="pa-sc-sub">Previred / RRHH</span>
                    <span class="pa-sc-dot"></span>
                </a>
                <a class="pa-sc" style="--sc-color:#3498db" onclick="frappe.set_route('List','Libro_de_Ingresos_Cliente')">
                    <span class="pa-sc-icon">📈</span>
                    <span class="pa-sc-label">Libro Ventas</span>
                    <span class="pa-sc-sub">Ingresos</span>
                    <span class="pa-sc-dot"></span>
                </a>
                <a class="pa-sc" style="--sc-color:#e67e22" onclick="frappe.set_route('List','Libro_de_Compras_Cliente')">
                    <span class="pa-sc-icon">📉</span>
                    <span class="pa-sc-label">Libro Compras</span>
                    <span class="pa-sc-sub">Egresos</span>
                    <span class="pa-sc-dot"></span>
                </a>
                <a class="pa-sc" style="--sc-color:#95a5a6" onclick="frappe.set_route('List','Libro_de_Honorarios_Cliente')">
                    <span class="pa-sc-icon">📄</span>
                    <span class="pa-sc-label">Honorarios</span>
                    <span class="pa-sc-sub">Libro boletas</span>
                    <span class="pa-sc-dot"></span>
                </a>
            </div>

            <p class="pa-section-title">Estado del período — <span id="pa-mes-label">—</span></p>
            <div class="pa-cards" id="pa-cards">
                <div class="pa-loading"><div class="pa-spinner"></div></div>
            </div>

            <p class="pa-section-title">Configuración</p>
            <div class="pa-shortcuts" style="margin-bottom:32px;">
                <a class="pa-sc" style="--sc-color:#6c757d" onclick="frappe.set_route('List','Configuracion App')">
                    <span class="pa-sc-icon">⚙️</span>
                    <span class="pa-sc-label">Configuración App</span>
                    <span class="pa-sc-sub">General</span>
                    <span class="pa-sc-dot"></span>
                </a>
                <a class="pa-sc" style="--sc-color:#6c757d" onclick="frappe.set_route('List','Configuracion_Codigo_F29')">
                    <span class="pa-sc-icon">🧮</span>
                    <span class="pa-sc-label">Códigos F29</span>
                    <span class="pa-sc-sub">Configuración F29</span>
                    <span class="pa-sc-dot"></span>
                </a>
                <a class="pa-sc" style="--sc-color:#6c757d" onclick="frappe.set_route('List','Plan_Contable')">
                    <span class="pa-sc-icon">📐</span>
                    <span class="pa-sc-label">Planes Contables</span>
                    <span class="pa-sc-sub">Tramos y valores</span>
                    <span class="pa-sc-dot"></span>
                </a>
                <a class="pa-sc" style="--sc-color:#6c757d" onclick="frappe.set_route('List','Catalogo_Servicio')">
                    <span class="pa-sc-icon">🗂️</span>
                    <span class="pa-sc-label">Catálogo Servicios</span>
                    <span class="pa-sc-sub">Servicios adicionales</span>
                    <span class="pa-sc-dot"></span>
                </a>
            </div>

            <p class="pa-section-title">Cobranza del período</p>
            <div class="pa-cobro-grid" id="pa-cobro-grid">
                <div class="pa-cobro-card">
                    <div class="label">Por Cobrar</div>
                    <div class="monto" id="pa-cob-porcobrar" style="color:#e74c3c">—</div>
                    <div class="count" id="pa-cob-porcobrar-n">— cobros</div>
                </div>
                <div class="pa-cobro-card">
                    <div class="label">Facturado</div>
                    <div class="monto" id="pa-cob-facturado" style="color:#f39c12">—</div>
                    <div class="count" id="pa-cob-facturado-n">— cobros</div>
                </div>
                <div class="pa-cobro-card">
                    <div class="label">Pagado</div>
                    <div class="monto" id="pa-cob-pagado" style="color:#27ae60">—</div>
                    <div class="count" id="pa-cob-pagado-n">— cobros</div>
                </div>
            </div>
        </div>
    </div>`);

    // ── Datos ─────────────────────────────────────────────────────────────────
    const mes_nom = `${meses[mes]} ${ano}`;
    $('#pa-badge-periodo').text(mes_nom);
    $('#pa-mes-label').text(mes_nom);

    // 1. Clientes activos
    frappe.call({
        method: 'frappe.client.get_count',
        args: { doctype: 'Ficha_Cliente', filters: { estado_cliente: 'Activo' }, ignore_permissions: 1 },
        callback(r) {
            const total = r.message || 0;

            // 2. Declaraciones del período
            frappe.call({
                method: 'frappe.client.get_list',
                args: { doctype: 'Declaracion_Mensual', filters: { ano, mes },
                        fields: ['name', 'estado'], limit_page_length: 300, ignore_permissions: 1 },
                callback(r2) {
                    const decs = r2.message || [];
                    const borrador   = decs.filter(d => !d.estado || d.estado === 'Borrador').length;
                    const validacion = decs.filter(d => d.estado === 'En Validación').length;
                    const listos     = decs.filter(d => d.estado === 'Listo').length;
                    const enviados   = decs.filter(d => d.estado === 'Enviado').length;
                    const sin_dec    = total - decs.length;
                    const avance     = listos + enviados;
                    const pct        = total ? Math.round(avance / total * 100) : 0;

                    // Hero stats
                    $('#pa-hero-stats').html(`
                        <div class="pa-hstat">
                            <strong>${total}</strong><span>Clientes</span>
                        </div>
                        <div class="pa-hstat green">
                            <strong>${avance}</strong><span>Listos/Enviados</span>
                        </div>
                        <div class="pa-hstat orange">
                            <strong>${borrador + validacion}</strong><span>En proceso</span>
                        </div>
                        <div class="pa-hstat red">
                            <strong>${sin_dec}</strong><span>Sin declaración</span>
                        </div>
                    `);

                    $('#pa-pct-label').text(`${avance} de ${total} (${pct}%)`);
                    setTimeout(() => $('#pa-prog-fill').css('width', pct + '%'), 100);

                    // Cards estado
                    $('#pa-cards').html(`
                        <div class="pa-card" style="--card-color:#95a5a6">
                            <div class="pa-card-top">
                                <div><strong>${sin_dec}</strong><p>Sin declaración</p></div>
                                <span class="pa-card-ico">⬜</span>
                            </div>
                            <div class="pa-card-sub">Clientes sin declaración creada</div>
                        </div>
                        <div class="pa-card" style="--card-color:#ffc107">
                            <div class="pa-card-top">
                                <div><strong>${borrador}</strong><p>Borrador</p></div>
                                <span class="pa-card-ico">✏️</span>
                            </div>
                            <div class="pa-card-sub">Declaraciones en borrador</div>
                        </div>
                        <div class="pa-card" style="--card-color:#ff9800">
                            <div class="pa-card-top">
                                <div><strong>${validacion}</strong><p>En Validación</p></div>
                                <span class="pa-card-ico">🔍</span>
                            </div>
                            <div class="pa-card-sub">Pendientes de validar</div>
                        </div>
                        <div class="pa-card" style="--card-color:#28a745">
                            <div class="pa-card-top">
                                <div><strong>${listos}</strong><p>Listos</p></div>
                                <span class="pa-card-ico">✅</span>
                            </div>
                            <div class="pa-card-sub">Listos para enviar</div>
                        </div>
                        <div class="pa-card" style="--card-color:#17a2b8">
                            <div class="pa-card-top">
                                <div><strong>${enviados}</strong><p>Enviados</p></div>
                                <span class="pa-card-ico">📤</span>
                            </div>
                            <div class="pa-card-sub">Declaraciones enviadas</div>
                        </div>
                    `);
                }
            });

            // 3. Cobranzas
            frappe.call({
                method: 'frappe.client.get_list',
                args: { doctype: 'Cobranza_Cliente', filters: { periodo_ano: ano, periodo_mes: mes },
                        fields: ['monto_a_cobrar', 'estado_cobranza'], limit_page_length: 300, ignore_permissions: 1 },
                callback(r3) {
                    const cobros = r3.message || [];
                    const fmt = n => Math.round(n).toLocaleString('es-CL');

                    const por_cobrar = cobros.filter(c => c.estado_cobranza === 'Por Cobrar');
                    const facturado  = cobros.filter(c => c.estado_cobranza === 'Facturado');
                    const pagado     = cobros.filter(c => c.estado_cobranza === 'Pagado');

                    const sum = arr => arr.reduce((a, c) => a + parseFloat(c.monto_a_cobrar || 0), 0);

                    $('#pa-cob-porcobrar').text('$' + fmt(sum(por_cobrar)));
                    $('#pa-cob-porcobrar-n').text(por_cobrar.length + ' cobro' + (por_cobrar.length !== 1 ? 's' : ''));
                    $('#pa-cob-facturado').text('$' + fmt(sum(facturado)));
                    $('#pa-cob-facturado-n').text(facturado.length + ' cobro' + (facturado.length !== 1 ? 's' : ''));
                    $('#pa-cob-pagado').text('$' + fmt(sum(pagado)));
                    $('#pa-cob-pagado-n').text(pagado.length + ' cobro' + (pagado.length !== 1 ? 's' : ''));
                }
            });
        }
    });
};
