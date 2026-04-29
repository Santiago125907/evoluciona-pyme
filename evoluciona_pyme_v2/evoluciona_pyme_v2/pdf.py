import json
import frappe
import requests
from datetime import date, timedelta


# ──────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────

def _fmt(num, unit=None, force_neg=False):
    if num is None:
        return '$0'
    try:
        num = float(num)
    except (TypeError, ValueError):
        return '$0'
    abs_num = abs(int(num))
    fmt = '{:,}'.format(abs_num).replace(',', '.')
    if unit == 'M':
        return '${:.1f}M'.format(num / 1_000_000)
    if unit == 'k':
        return '${:,}k'.format(abs(int(num / 1000))).replace(',', '.')
    if force_neg:
        return '($' + fmt + ')'
    if num < 0:
        return '($' + fmt + ')'
    return '$' + fmt


def _pct(num):
    try:
        num = float(num or 0)
    except Exception:
        return '0%'
    sign = '+' if num >= 0 else ''
    return '{}{:.1f}%'.format(sign, num)


def _cls(val, invert=False):
    pos = float(val or 0) >= 0
    if invert:
        pos = not pos
    return 'positive' if pos else 'negative'


def _calcular_fechas(mes, ano):
    mes, ano = int(mes), int(ano)
    ms, as_ = (mes + 1, ano) if mes < 12 else (1, ano + 1)

    d_prev = date(as_, ms, 13)
    if d_prev.weekday() == 5:
        d_prev -= timedelta(1)
    elif d_prev.weekday() == 6:
        d_prev -= timedelta(2)

    d_f29 = date(as_, ms, 20)
    if d_f29.weekday() == 5:
        d_f29 += timedelta(2)
    elif d_f29.weekday() == 6:
        d_f29 += timedelta(1)

    mp, ap = mes + 3, ano
    if mp > 12:
        mp -= 12
        ap += 1
    d_post = date(ap, mp, 20)

    fmt = lambda d: d.strftime('%d/%m/%Y')
    return {'previred': fmt(d_prev), 'f29': fmt(d_f29),
            'honorarios': fmt(d_f29), 'postergacion': fmt(d_post)}


def _jlist(lst):
    return json.dumps([float(x or 0) for x in (lst or [])])


def _jstr(lst):
    return json.dumps(lst or [])


# ──────────────────────────────────────────────────────────
# CSS
# ──────────────────────────────────────────────────────────

def _get_css(cp, cs):
    return """
    :root { --primary: CP; --secondary: CS; --success: #10B981; --accent: #FF6F61;
            --txt: #4A4A4A; --gray: #718096; --bg-alt: #F8F9FA; --border: #E2E8F0; }
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: 'Open Sans', sans-serif; color: var(--txt); font-size: 14px; line-height: 1.5; background: white; }
    .page { padding: 10mm; box-sizing: border-box; }
    .header { display: flex; justify-content: space-between; align-items: center;
              margin-bottom: 18px; padding-bottom: 12px; border-bottom: 3px solid var(--primary); }
    .logo img { max-height: 50px; max-width: 160px; object-fit: contain; }
    .logo h1 { font-family: 'Montserrat', sans-serif; color: var(--primary); font-size: 20px; font-weight: 800; }
    .header-info { text-align: right; }
    .doc-title { font-family: 'Montserrat', sans-serif; font-size: 16px; font-weight: 700; text-transform: uppercase; }
    .client-name { font-size: 14px; font-weight: 700; color: var(--primary); margin-top: 2px; }
    .periodo { font-size: 12px; color: var(--gray); }
    .alert { padding: 10px 14px; border-radius: 6px; margin-bottom: 12px; background: #FFF5F5;
             color: var(--accent); border-left: 4px solid var(--accent); font-weight: 600; font-size: 11px; }
    .cards { display: flex; gap: 16px; margin-bottom: 16px; }
    .card { flex: 1; background: white; border: 1px solid var(--border); border-radius: 10px;
            overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
    .card-head { padding: 10px 14px; color: white; text-align: center; font-family: 'Montserrat', sans-serif;
                 font-weight: 800; font-size: 14px; text-transform: uppercase; }
    .card-head small { display: block; font-size: 10px; font-weight: 600; opacity: 0.9; margin-top: 2px; text-transform: none; }
    .card-body { padding: 12px; }
    .row { display: flex; justify-content: space-between; align-items: flex-start;
           padding: 7px 0; border-bottom: 1px dashed var(--border); font-size: 11px; }
    .row-left { flex: 1; }
    .row-label { color: var(--txt); font-weight: 600; margin-bottom: 2px; font-size: 11px; }
    .venc { background: #FFF5E6; color: #D97706; padding: 2px 6px; border-radius: 4px;
            font-size: 9px; font-weight: 700; display: inline-block; margin-top: 2px; }
    .row-val { font-weight: 700; color: var(--txt); font-size: 14px; text-align: right; white-space: nowrap; }
    .row.highlight { background: #FFF5F5; padding: 7px 10px; margin: 0 -10px; border-radius: 5px; }
    .row.highlight .row-label, .row.highlight .row-val { color: var(--accent); }
    .total { display: flex; justify-content: space-between; align-items: center;
             margin-top: 12px; padding-top: 12px; border-top: 2px solid var(--border); }
    .total-label { font-family: 'Montserrat', sans-serif; font-size: 10px; font-weight: 700;
                   color: var(--gray); text-transform: uppercase; }
    .total-val { font-family: 'Montserrat', sans-serif; font-size: 18px; font-weight: 800; }
    .opt1 .card-head { background: linear-gradient(135deg, var(--primary), #00B3BB); }
    .opt1 .total-val { color: var(--primary); }
    .opt2 .card-head { background: linear-gradient(135deg, var(--secondary), #FF8C42); }
    .opt2 .total-val { color: var(--secondary); }
    .alert-post { margin-top: 12px; padding: 9px 11px; background: #E6FFFA;
                  border: 1px solid var(--primary); border-radius: 6px; font-size: 11px; line-height: 1.5; }
    .section-title { font-family: 'Montserrat', sans-serif; font-size: 14px; font-weight: 800;
                     color: var(--txt); margin: 16px 0 12px; text-transform: uppercase;
                     border-left: 4px solid var(--primary); padding-left: 8px; }
    .instr-grid { display: flex; gap: 16px; margin-bottom: 16px; }
    .instr-box { flex: 1; background: var(--bg-alt); border-radius: 10px; padding: 12px; }
    .instr-header { display: flex; align-items: center; margin-bottom: 10px; }
    .instr-icon { font-size: 22px; margin-right: 8px; }
    .instr-title { font-family: 'Montserrat', sans-serif; font-size: 14px; font-weight: 800; color: var(--primary); }
    .instr-subtitle { font-size: 11px; color: var(--gray); }
    .instr-step { margin-top: 8px; }
    .instr-step-title { font-weight: 700; font-size: 11px; margin-bottom: 4px; }
    .instr-step-text { font-size: 11px; color: var(--gray); line-height: 1.4; }
    .banco { display: flex; gap: 16px; background: var(--bg-alt); padding: 12px; border-radius: 10px; }
    .banco-left, .banco-right { flex: 1; }
    .banco-label { font-size: 10px; color: var(--gray); text-transform: uppercase; font-weight: 700; margin-bottom: 4px; }
    .banco-main { font-size: 13px; font-weight: 700; color: var(--txt); }
    .banco-detail { font-size: 11px; color: var(--gray); }
    .chart-box { height: 240px; background: white; border: 1px solid var(--border); border-radius: 8px;
                 padding: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 12px; }
    .chart-barras { height: 230px; }
    .chart-lineas { height: 210px; }
    .chart-dona { height: 220px; }
    .table-title { font-size: 13px; font-weight: 800; text-transform: uppercase; margin-bottom: 8px;
                   padding-left: 8px; border-left: 4px solid var(--primary); }
    table { width: 100%; border-collapse: collapse; font-size: 10px; margin-bottom: 12px; }
    thead { background: linear-gradient(135deg, var(--primary), #00B3BB); color: white; }
    th { padding: 7px 4px; text-align: right; font-weight: 700; font-size: 9px; text-transform: uppercase; }
    th:first-child { text-align: left; padding-left: 8px; }
    td { padding: 5px 4px; border-bottom: 1px solid var(--border); text-align: right; font-weight: 600; font-size: 10px; }
    td:first-child { text-align: left; font-weight: 700; padding-left: 8px; }
    tbody tr:nth-child(even) { background: var(--bg-alt); }
    .positive { color: #38A169; }
    .negative { color: #E53E3E; }
    .analisis { background: linear-gradient(135deg, #E6FFFA, #B2F5EA); border: 2px solid var(--primary);
                border-radius: 8px; padding: 12px; margin-top: 12px; }
    .analisis-title { font-size: 13px; font-weight: 800; text-transform: uppercase; color: var(--primary);
                      margin-bottom: 8px; }
    .analisis-content { font-size: 10px; line-height: 1.6; }
    .kpis { display: flex; gap: 8px; margin-bottom: 8px; }
    .kpi { flex: 1; background: linear-gradient(135deg, #E6FFFA, #B2F5EA); border: 2px solid var(--primary);
           border-radius: 6px; padding: 7px; text-align: center; }
    .kpi-label { font-size: 8px; font-weight: 700; text-transform: uppercase; color: var(--gray); margin-bottom: 2px; }
    .kpi-value { font-size: 15px; font-weight: 800; color: var(--txt); }
    .kpi-subtitle { font-size: 8px; color: var(--gray); }
    .bottom-section { display: flex; gap: 10px; }
    .dona-container { flex: 0 0 38%; }
    .tabla-container { flex: 1; }
    .table-container { background: white; border: 1px solid var(--border); border-radius: 6px;
                       padding: 16px; margin-bottom: 8px; }
    .table-container .table-title { border-left: none; padding-left: 0; font-size: 13px; }
    .table-container td:first-child { font-weight: 600; width: 70%; }
    .table-container td:last-child { text-align: right; font-weight: 700; font-size: 14px; width: 30%; }
    .row-add td:first-child::before { content: '(+) '; color: var(--secondary); font-weight: 800; }
    .row-subtract td:first-child::before { content: '(-) '; color: #EF4444; font-weight: 800; }
    .row-subtract td:last-child { color: #EF4444; }
    .row-equals { background: var(--bg-alt); font-weight: 700; }
    .row-equals td:first-child::before { content: '(=) '; color: var(--primary); font-weight: 800; }
    .row-total { background: linear-gradient(135deg, #EEF2FF, #DBEAFE); border-top: 2px solid var(--primary); }
    .row-total td { font-weight: 800; font-size: 14px; padding: 8px; }
    .row-total td:first-child::before { content: '(=) '; color: var(--primary); }
    .row-info { background: #FFFBEB; }
    .row-info td:first-child { color: #92400E; }
    .hero { text-align: center; padding: 10px 20px; background: linear-gradient(135deg, #E0F7FA, #B2EBF2);
            border-radius: 10px; margin-bottom: 10px; }
    .hero-title { font-family: 'Montserrat', sans-serif; font-size: 15px; font-weight: 900;
                  color: var(--primary); margin-bottom: 6px; text-transform: uppercase; }
    .greeting { font-size: 14px; font-weight: 700; color: var(--txt); margin-bottom: 5px; }
    .intro { font-size: 12px; line-height: 1.4; color: var(--gray); max-width: 600px; margin: 0 auto; }
    .steps { display: flex; gap: 10px; margin-bottom: 12px; }
    .step { flex: 1; background: white; border: 2px solid var(--border); border-radius: 8px;
            padding: 10px; text-align: center; }
    .step-number { font-size: 22px; margin-bottom: 4px; }
    .step-title { font-size: 12px; font-weight: 800; color: var(--primary); margin-bottom: 3px; text-transform: uppercase; }
    .step-desc { font-size: 11px; color: var(--gray); line-height: 1.3; }
    .premios { display: flex; gap: 12px; margin-bottom: 12px; }
    .premio-card { flex: 1; background: white; border: 3px solid var(--border); border-radius: 10px;
                   padding: 12px; text-align: center; position: relative; overflow: hidden; }
    .premio-card.opcion-a { border-color: var(--secondary); }
    .premio-card.opcion-a::before { content: ''; position: absolute; top: 0; left: 0; right: 0;
                                    height: 4px; background: linear-gradient(90deg, var(--secondary), #FF8C42); }
    .premio-card.opcion-b { border-color: var(--success); }
    .premio-card.opcion-b::before { content: ''; position: absolute; top: 0; left: 0; right: 0;
                                    height: 4px; background: linear-gradient(90deg, var(--success), #34D399); }
    .premio-icon { font-size: 26px; margin-bottom: 5px; }
    .premio-label { font-size: 9px; font-weight: 700; text-transform: uppercase; margin-bottom: 3px; }
    .opcion-a .premio-label { color: var(--secondary); }
    .opcion-b .premio-label { color: var(--success); }
    .premio-title { font-size: 13px; font-weight: 800; color: var(--txt); margin-bottom: 5px; }
    .premio-value { font-size: 18px; font-weight: 900; margin-bottom: 5px; }
    .opcion-a .premio-value { color: var(--secondary); }
    .opcion-b .premio-value { color: var(--success); }
    .premio-detail { font-size: 11px; color: var(--gray); line-height: 1.3; }
    .cta { background: linear-gradient(135deg, #FFF4E6, #FFE0B2); border: 2px solid var(--accent);
           border-radius: 10px; padding: 12px; text-align: center; }
    .cta-title { font-size: 14px; font-weight: 800; color: var(--txt); margin-bottom: 5px; }
    .cta-text { font-size: 12px; color: var(--gray); margin-bottom: 6px; line-height: 1.4; }
    .cta-contact { font-size: 13px; font-weight: 700; color: var(--primary); margin-bottom: 5px; }
    .cta-final { font-size: 12px; font-weight: 700; color: var(--txt); font-style: italic; }
    @media print {
        .page { page-break-after: always; height: 297mm; width: 210mm; overflow: hidden;
                padding: 10mm; box-sizing: border-box; }
        @page { size: A4; margin: 0; }
    }
    """.replace('CP', cp).replace('CS', cs)


# ──────────────────────────────────────────────────────────
# COMPONENTES HTML
# ──────────────────────────────────────────────────────────

def _header(titulo, d, logo_src):
    if logo_src:
        logo_html = '<img src="{}" alt="Logo">'.format(logo_src)
    else:
        ofi = d.get('oficina', {})
        logo_html = '<h1>{}</h1>'.format(ofi.get('nombre_empresa', 'EVOLUCIONA'))
    return (
        '<div class="header">'
        '<div class="logo">{}</div>'
        '<div class="header-info">'
        '<div class="doc-title">{}</div>'
        '<div class="client-name">{}</div>'
        '<div class="periodo">Período: {}</div>'
        '</div></div>'
    ).format(logo_html, titulo, d.get('cliente', ''), d.get('periodo', ''))


def _hoja1(d, f, ofi, logo_src):
    h = _header('Resumen de Pagos', d, logo_src)

    if float(d.get('deuda_anterior') or 0) > 0:
        h += '<div class="alert">&#9888; <strong>Deuda Pendiente:</strong> {} del período anterior</div>'.format(
            _fmt(d.get('deuda_anterior')))

    def card(cls, titulo, sub, f29_val, use_full):
        items = ''
        if float(d.get('deuda_anterior') or 0) > 0:
            items += ('<div class="row highlight"><div class="row-left">'
                      '<div class="row-label">Deuda Anterior</div></div>'
                      '<div class="row-val">{}</div></div>').format(_fmt(d.get('deuda_anterior')))
        items += ('<div class="row"><div class="row-left">'
                  '<div class="row-label">Servicios {}</div>'
                  '<div class="venc">&#128197; {}</div></div>'
                  '<div class="row-val">{}</div></div>').format(
            d.get('periodo', ''), f.get('honorarios', ''), _fmt(d.get('honorarios')))
        items += ('<div class="row"><div class="row-left">'
                  '<div class="row-label">Previred</div>'
                  '<div class="venc">&#128197; {}</div></div>'
                  '<div class="row-val">{}</div></div>').format(
            f.get('previred', ''), _fmt(d.get('previred')))
        if float(d.get('postergacion_vencida') or 0) > 0:
            det = d.get('postergaciones_detalle') or []
            per = ' ({})'.format(det[0].get('periodo', '')) if det else ''
            items += ('<div class="row highlight"><div class="row-left">'
                      '<div class="row-label">&#9888; Cuota Postergación{}</div></div>'
                      '<div class="row-val">{}</div></div>').format(per, _fmt(d.get('postergacion_vencida')))
        f29_label = 'F29 (Total)' if use_full else 'F29 (Rebajado)'
        items += ('<div class="row"><div class="row-left">'
                  '<div class="row-label">{}</div>'
                  '<div class="venc">&#128197; {}</div></div>'
                  '<div class="row-val">{}</div></div>').format(
            f29_label, f.get('f29', ''), _fmt(f29_val))
        total_key = 'op1_total' if use_full else 'op2_total'
        items += ('<div class="total"><div class="total-label">Total</div>'
                  '<div class="total-val">{}</div></div>').format(_fmt(d.get(total_key)))
        if not use_full and float(d.get('monto_postergado') or 0) > 0:
            items += ('<div class="alert-post">&#128161; <strong>Postergas {}</strong> de IVA del período '
                      '<strong>{}</strong><br>&#128197; Nueva fecha: <strong>{}</strong></div>').format(
                _fmt(d.get('monto_postergado')), d.get('periodo', ''), f.get('postergacion', '--'))
        return ('<div class="card {}">'
                '<div class="card-head">{}<small>{}</small></div>'
                '<div class="card-body">{}</div></div>').format(cls, titulo, sub, items)

    h += '<div class="cards">'
    h += card('opt1', 'Opción 1: Pago Total', 'Quedas al día', d.get('f29_full'), True)
    h += card('opt2', 'Opción 2: Con Postergación', 'Cuidas flujo', d.get('f29_rebajado'), False)
    h += '</div>'

    h += '<div class="section-title">Instrucciones para Pagos</div>'
    h += (
        '<div class="instr-grid">'
        '<div class="instr-box">'
        '<div class="instr-header"><div class="instr-icon">&#129309;</div>'
        '<div><div class="instr-title">Opción A</div><div class="instr-subtitle">Nosotros lo hacemos</div></div></div>'
        '<div class="instr-step"><div class="instr-step-title">Transfiere el monto total</div>'
        '<div class="instr-step-text">con 2 días hábiles de anticipación. Nosotros realizamos los pagos y '
        'enviamos comprobantes.</div></div></div>'
        '<div class="instr-box">'
        '<div class="instr-header"><div class="instr-icon">&#129300;</div>'
        '<div><div class="instr-title">Opción B</div><div class="instr-subtitle">Autogestión</div></div></div>'
        '<div class="instr-step"><div class="instr-step-title">&#128196; F29:</div>'
        '<div class="instr-step-text">Declaración guardada en SII. Ingresa y paga.</div></div>'
        '<div class="instr-step"><div class="instr-step-title">&#128188; Previred:</div>'
        '<div class="instr-step-text">Nómina guardada en Previred.cl. Revisa y paga.</div></div>'
        '</div></div>'
    )

    h += ('<div class="banco">'
          '<div class="banco-left"><div class="banco-label">Transferir a</div>'
          '<div class="banco-main">{} &bull; {}</div>'
          '<div class="banco-detail">N° {} &bull; {}</div></div>'
          '<div class="banco-right"><div class="banco-label">Beneficiario</div>'
          '<div class="banco-main">RUT {}</div>'
          '<div class="banco-detail">{}</div></div></div>').format(
        ofi.get('banco', ''), ofi.get('tipo_cuenta', ''),
        ofi.get('numero_cuenta', ''), ofi.get('nombre_titular', ''),
        ofi.get('rut_empresa', ''), ofi.get('email_contacto', ''))
    return h


def _hoja2(d, meses, logo_src):
    h = _header('Análisis Financiero y Tendencias', d, logo_src)
    h += '<div class="chart-box"><div id="chartUtilidad" style="width:100%;height:100%;"></div></div>'
    h += '<div class="chart-box"><div id="chartComparativo" style="width:100%;height:100%;"></div></div>'

    ingresos = d.get('tbl_ingresos') or []
    gastos = d.get('tbl_gastos') or []
    utilidad = d.get('tbl_utilidad') or []

    h += '<div class="table-title">Detalle Mensual (en miles)</div><table><thead><tr><th>Concepto</th>'
    for m in meses:
        h += '<th>{}</th>'.format(m)
    h += '<th>Total</th></tr></thead><tbody>'

    h += '<tr><td>Ingresos</td>'
    for v in ingresos:
        h += '<td>{}</td>'.format(_fmt(v, 'k'))
    h += '<td style="font-weight:800">{}</td></tr>'.format(_fmt(d.get('acum_ing'), 'k'))

    h += '<tr><td>Gastos</td>'
    for v in gastos:
        h += '<td>({}) </td>'.format(_fmt(v, 'k'))
    h += '<td style="font-weight:800">({}) </td></tr>'.format(_fmt(d.get('acum_gas'), 'k'))

    h += '<tr><td>Utilidad</td>'
    for v in utilidad:
        fv = float(v or 0)
        cls = 'positive' if fv >= 0 else 'negative'
        val = _fmt(abs(fv), 'k')
        h += '<td class="{}">{}</td>'.format(cls, val if fv >= 0 else '(' + val + ')')
    tu = float(d.get('acum_utilidad') or 0)
    cls = 'positive' if tu >= 0 else 'negative'
    val = _fmt(abs(tu), 'k')
    h += '<td class="{}" style="font-weight:800">{}</td></tr>'.format(cls, val if tu >= 0 else '(' + val + ')')
    h += '</tbody></table>'

    if d.get('analisis_ia'):
        h += ('<div class="analisis"><div class="analisis-title">&#129302; Análisis Inteligente</div>'
              '<div class="analisis-content">{}</div></div>').format(d.get('analisis_ia'))
    return h


def _hoja3(d, meses, logo_src):
    h = _header('Detalle Comercial - Ingresos por Categoría', d, logo_src)
    m3 = d.get('hoja3_mes_actual') or {}
    a3 = d.get('hoja3_acumulados') or {}
    mix3 = d.get('hoja3_mix') or {}
    var3 = d.get('hoja3_variaciones') or {}

    h += ('<div class="kpis">'
          '<div class="kpi"><div class="kpi-label">Ingresos Totales</div>'
          '<div class="kpi-value">{}</div><div class="kpi-subtitle">Acumulado {}</div></div>'
          '<div class="kpi"><div class="kpi-label">Mes Actual</div>'
          '<div class="kpi-value">{}</div><div class="kpi-subtitle">{}</div></div>'
          '<div class="kpi"><div class="kpi-label">Variación Mensual</div>'
          '<div class="kpi-value {}">{}</div><div class="kpi-subtitle">Vs mes anterior</div></div>'
          '</div>').format(
        _fmt(a3.get('total'), 'M'), d.get('ano', ''),
        _fmt(m3.get('total'), 'M'), d.get('periodo', ''),
        _cls(var3.get('total')), _pct(var3.get('total')))

    h += '<div class="chart-box"><div id="chartBarrasHoja3" class="chart-barras" style="width:100%;height:100%;"></div></div>'
    h += '<div class="bottom-section"><div class="dona-container"><div id="chartDonaHoja3" class="chart-dona" style="width:100%;height:100%;"></div></div>'
    h += '<div class="tabla-container"><table><thead><tr><th>Categoría</th><th>Mes</th><th>Acumulado</th><th>Mix%</th><th>Var.</th></tr></thead><tbody>'

    cats = [
        ('Facturas', 'facturas', '#00C4CC'),
        ('Boletas', 'boletas', '#FF9A00'),
        ('Comprobantes', 'comprobantes', '#4CAF50'),
        ('Notas Débito', 'notas_debito', '#9C27B0'),
    ]
    for label, key, color in cats:
        h += '<tr><td style="color:{}">{}</td><td>{}</td><td>{}</td><td>{:.1f}%</td><td class="{}">{}</td></tr>'.format(
            color, label, _fmt(m3.get(key)), _fmt(a3.get(key)),
            float(mix3.get(key) or 0), _cls(var3.get(key)), _pct(var3.get(key)))
    h += '<tr><td><strong>TOTAL</strong></td><td><strong>{}</strong></td><td><strong>{}</strong></td><td><strong>100%</strong></td><td class="{}"><strong>{}</strong></td></tr>'.format(
        _fmt(m3.get('total')), _fmt(a3.get('total')), _cls(var3.get('total')), _pct(var3.get('total')))
    h += '</tbody></table></div></div>'
    return h


def _hoja4(d, meses, logo_src):
    h = _header('Análisis de Gastos - Desglose Operacional', d, logo_src)
    m4 = d.get('hoja4_mes_actual') or {}
    a4 = d.get('hoja4_acumulados') or {}
    mix4 = d.get('hoja4_mix') or {}
    var4 = d.get('hoja4_variaciones') or {}

    h += ('<div class="kpis">'
          '<div class="kpi"><div class="kpi-label">Total Gastos Año</div>'
          '<div class="kpi-value">{}</div><div class="kpi-subtitle">Acumulado {}</div></div>'
          '<div class="kpi"><div class="kpi-label">Gasto Mes Actual</div>'
          '<div class="kpi-value">{}</div><div class="kpi-subtitle">{}</div></div>'
          '<div class="kpi"><div class="kpi-label">Variación Mensual</div>'
          '<div class="kpi-value {}">{}</div><div class="kpi-subtitle">Vs mes anterior</div></div>'
          '</div>').format(
        _fmt(a4.get('total'), 'M'), d.get('ano', ''),
        _fmt(m4.get('total'), 'M'), d.get('periodo', ''),
        _cls(var4.get('total'), invert=True), _pct(var4.get('total')))

    h += '<div class="chart-box"><div id="chartBarrasHoja4" class="chart-barras" style="width:100%;height:100%;"></div></div>'
    h += '<div class="chart-box"><div id="chartLineasHoja4" class="chart-lineas" style="width:100%;height:100%;"></div></div>'
    h += '<div class="bottom-section"><div class="dona-container"><div id="chartDonaHoja4" class="chart-dona" style="width:100%;height:100%;"></div></div>'
    h += '<div class="tabla-container"><table><thead><tr><th>Categoría</th><th>Mes</th><th>Acumulado</th><th>Mix%</th><th>Var.</th></tr></thead><tbody>'

    cats = [
        ('Remuneraciones', 'remuneraciones', '#10B981'),
        ('Facturas', 'facturas', '#00C4CC'),
        ('Honorarios', 'honorarios', '#FF9A00'),
        ('Otros Gastos', 'otros', '#8B5CF6'),
    ]
    for label, key, color in cats:
        h += '<tr><td style="color:{}">{}</td><td>{}</td><td>{}</td><td>{:.1f}%</td><td class="{}">{}</td></tr>'.format(
            color, label, _fmt(m4.get(key)), _fmt(a4.get(key)),
            float(mix4.get(key) or 0), _cls(var4.get(key), invert=True), _pct(var4.get(key)))
    h += '<tr><td><strong>TOTAL</strong></td><td><strong>{}</strong></td><td><strong>{}</strong></td><td><strong>100%</strong></td><td class="{}"><strong>{}</strong></td></tr>'.format(
        _fmt(m4.get('total')), _fmt(a4.get('total')), _cls(var4.get('total'), invert=True), _pct(var4.get('total')))
    h += '</tbody></table></div></div>'
    return h


def _hoja5(d, logo_src):
    h = _header('Detalle Tributario y Previsional', d, logo_src)
    f29 = d.get('hoja5_f29_detalle') or {}
    prev = d.get('hoja5_previred_detalle') or {}

    h += '<div class="table-container"><div class="table-title">&#128196; Formulario 29</div><table><tbody>'
    h += '<tr class="row-add"><td>IVA Débito Fiscal (Ventas)</td><td>{}</td></tr>'.format(_fmt(f29.get('iva_debito')))
    h += '<tr class="row-subtract"><td>IVA Crédito Fiscal (Compras)</td><td>{}</td></tr>'.format(_fmt(f29.get('iva_credito'), force_neg=True))
    h += '<tr class="row-equals"><td>IVA Determinado</td><td>{}</td></tr>'.format(_fmt(f29.get('iva_determinado')))
    if float(f29.get('ppm') or 0) > 0:
        h += '<tr class="row-add"><td>PPM</td><td>{}</td></tr>'.format(_fmt(f29.get('ppm')))
    if float(f29.get('otros_impuestos') or 0) > 0:
        h += '<tr class="row-add"><td>Otros Impuestos</td><td>{}</td></tr>'.format(_fmt(f29.get('otros_impuestos')))
    h += '<tr class="row-total"><td>TOTAL A PAGAR F29</td><td>{}</td></tr>'.format(_fmt(f29.get('total_f29')))
    h += '</tbody></table></div>'

    h += '<div class="table-container"><div class="table-title">&#128101; Previred - Cotizaciones</div><table><tbody>'
    if float(prev.get('haberes_imponibles') or 0) > 0:
        h += '<tr class="row-info"><td>Total Haberes Imponibles</td><td>{}</td></tr>'.format(_fmt(prev.get('haberes_imponibles')))
    if float(prev.get('haberes_no_imponibles') or 0) > 0:
        h += '<tr class="row-info"><td>Total Haberes No Imponibles</td><td>{}</td></tr>'.format(_fmt(prev.get('haberes_no_imponibles')))
    if float(prev.get('impuesto_unico') or 0) > 0:
        h += '<tr class="row-info"><td>Impuesto Único (se paga con F29)</td><td>{}</td></tr>'.format(_fmt(prev.get('impuesto_unico')))
    if float(prev.get('prestamo_solidario') or 0) > 0:
        h += '<tr class="row-info"><td>Préstamo Solidario 3%</td><td>{}</td></tr>'.format(_fmt(prev.get('prestamo_solidario')))
    h += '<tr class="row-add"><td>Cotizaciones AFP</td><td>{}</td></tr>'.format(_fmt(prev.get('cotizacion_afp')))
    h += '<tr class="row-add"><td>Cotizaciones Salud</td><td>{}</td></tr>'.format(_fmt(prev.get('cotizacion_salud')))
    h += '<tr class="row-add"><td>Seguro de Cesantía</td><td>{}</td></tr>'.format(_fmt(prev.get('seguro_cesantia')))
    h += '<tr class="row-add"><td>Mutual / SIS / SANNA</td><td>{}</td></tr>'.format(_fmt(prev.get('sis_mutual')))
    h += '<tr class="row-total"><td>TOTAL A PAGAR PREVIRED</td><td>{}</td></tr>'  .format(_fmt(prev.get('total_previred')))
    h += '</tbody></table></div>'
    return h


def _hoja6(d, ofi, logo_src, texto_promo):
    h = _header('Programa de Socios Evoluciona', d, logo_src)
    texto = texto_promo or (
        'Sabemos que tu confianza en nosotros es invaluable. Por eso, queremos recompensarte '
        'por ayudarnos a crecer juntos. Cada vez que nos recomiendas, no solo ayudas a otro '
        'emprendedor, sino que también obtienes beneficios increíbles.'
    )
    h += ('<div class="hero">'
          '<div class="hero-title">&#129309; Programa de Socios Evoluciona</div>'
          '<div class="greeting">¡Hola {}!</div>'
          '<div class="intro">{}</div></div>').format(d.get('cliente', 'estimado cliente'), texto)

    h += '<div class="section-title">¿Cómo Funciona?</div>'
    h += ('<div class="steps">'
          '<div class="step"><div class="step-number">1️⃣</div>'
          '<div class="step-title">Recomiéndanos</div>'
          '<div class="step-desc">Preséntanos a un emprendedor que necesite Contabilidad o RRHH</div></div>'
          '<div class="step"><div class="step-number">2️⃣</div>'
          '<div class="step-title">Ambos Ganan</div>'
          '<div class="step-desc">Tu referido recibe 25% de descuento en su primer mes</div></div>'
          '<div class="step"><div class="step-number">3️⃣</div>'
          '<div class="step-title">Elige tu Premio</div>'
          '<div class="step-desc">Tú decides cómo quieres recibir tu recompensa</div></div>'
          '</div>')

    h += '<div class="section-title">Elige Tu Premio</div>'
    h += ('<div class="premios">'
          '<div class="premio-card opcion-a">'
          '<div class="premio-icon">⚡</div>'
          '<div class="premio-label">Opción A</div>'
          '<div class="premio-title">Premio Inmediato</div>'
          '<div class="premio-value">50% OFF</div>'
          '<div class="premio-detail">Descuento del 50% en tu próxima factura mensual</div></div>'
          '<div class="premio-card opcion-b">'
          '<div class="premio-icon">&#128279;</div>'
          '<div class="premio-label">Opción B</div>'
          '<div class="premio-title">Premio a Largo Plazo</div>'
          '<div class="premio-value">10% MENSUAL</div>'
          '<div class="premio-detail">10% de descuento mensual durante 6 meses</div></div>'
          '</div>')

    h += ('<div class="cta">'
          '<div class="cta-title">&#128072; ¿Tienes a alguien en mente?</div>'
          '<div class="cta-text">Responde a tu asesor por WhatsApp o escríbenos a:<br>'
          '<strong>{}</strong></div>'
          '<div class="cta-contact">WhatsApp: {}</div>'
          '<div class="cta-final">No hay límites en la cantidad de referidos. ¡Gracias por ser parte!</div>'
          '</div>').format(ofi.get('email_contacto', ''), ofi.get('telefono', ''))
    return h


# ──────────────────────────────────────────────────────────
# JAVASCRIPT CHARTS
# ──────────────────────────────────────────────────────────

def _chart_script(d, meses, cp, cs):
    ingresos = _jlist(d.get('tbl_ingresos'))
    gastos = _jlist(d.get('tbl_gastos'))
    utilidad = _jlist(d.get('tbl_utilidad'))
    meses_json = _jstr(meses)

    cat = d.get('hoja3_categorias_mensuales') or {}
    a3 = d.get('hoja3_acumulados') or {}
    gas = d.get('hoja4_gastos_mensuales') or {}
    a4 = d.get('hoja4_acumulados') or {}
    ano = d.get('ano', '')

    return """
    function fmtM(v) {{
        if (!v) return '$0';
        return '$' + Math.abs(parseInt(v)).toLocaleString('es-CL');
    }}

    const _echarts_opts = {{ renderer: 'canvas' }};

    // HOJA 2 - Utilidad
    const cUtil = echarts.init(document.getElementById('chartUtilidad'), null, _echarts_opts);
    cUtil.setOption({{
        title: {{ text: 'Evolución de Utilidad', left: 'center', textStyle: {{ fontSize: 14, color: '#4A4A4A' }} }},
        tooltip: {{ trigger: 'axis', textStyle: {{ fontSize: 11 }} }},
        legend: {{ data: ['Utilidad', 'Tendencia'], bottom: 0, textStyle: {{ fontSize: 11 }} }},
        grid: {{ left: '5%', right: '8%', bottom: '15%', top: '15%', containLabel: true }},
        xAxis: {{ type: 'category', data: {meses}, axisLabel: {{ fontSize: 11 }} }},
        yAxis: {{ type: 'value', axisLabel: {{ formatter: v => '$' + (v/1000000).toFixed(1) + 'M', fontSize: 10 }} }},
        series: [
            {{ name: 'Utilidad', type: 'bar', data: {utilidad},
               itemStyle: {{ color: p => p.value >= 0 ? '{cp}' : '#FF6F61', borderRadius: [3,3,0,0] }}, barWidth: '55%' }},
            {{ name: 'Tendencia', type: 'line', data: {utilidad},
               lineStyle: {{ type: 'dashed', width: 2, color: '#718096' }},
               itemStyle: {{ color: '#718096' }}, smooth: true, symbol: 'circle', symbolSize: 6 }}
        ]
    }});

    // HOJA 2 - Comparativo
    const cComp = echarts.init(document.getElementById('chartComparativo'), null, _echarts_opts);
    cComp.setOption({{
        title: {{ text: 'Ingresos vs Gastos', left: 'center', textStyle: {{ fontSize: 14, color: '#4A4A4A' }} }},
        tooltip: {{ trigger: 'axis', textStyle: {{ fontSize: 11 }} }},
        legend: {{ data: ['Ingresos', 'Gastos'], bottom: 0, textStyle: {{ fontSize: 11 }} }},
        grid: {{ left: '5%', right: '8%', bottom: '15%', top: '15%', containLabel: true }},
        xAxis: {{ type: 'category', data: {meses}, boundaryGap: false, axisLabel: {{ fontSize: 11 }} }},
        yAxis: {{ type: 'value', axisLabel: {{ formatter: v => '$' + (v/1000000).toFixed(1) + 'M', fontSize: 10 }} }},
        series: [
            {{ name: 'Ingresos', type: 'line', data: {ingresos}, smooth: true,
               lineStyle: {{ width: 3, color: '{cp}' }}, itemStyle: {{ color: '{cp}' }}, symbolSize: 8,
               areaStyle: {{ color: {{ type: 'linear', x:0, y:0, x2:0, y2:1,
                   colorStops: [{{ offset:0, color:'rgba(0,196,204,0.35)' }}, {{ offset:1, color:'rgba(0,196,204,0.02)' }}] }} }} }},
            {{ name: 'Gastos', type: 'line', data: {gastos}, smooth: true,
               lineStyle: {{ width: 3, color: '{cs}' }}, itemStyle: {{ color: '{cs}' }}, symbolSize: 8,
               areaStyle: {{ color: {{ type: 'linear', x:0, y:0, x2:0, y2:1,
                   colorStops: [{{ offset:0, color:'rgba(255,154,0,0.35)' }}, {{ offset:1, color:'rgba(255,154,0,0.02)' }}] }} }} }}
        ]
    }});

    // HOJA 3 - Barras
    const cB3 = echarts.init(document.getElementById('chartBarrasHoja3'), null, _echarts_opts);
    cB3.setOption({{
        title: {{ text: 'Evolución Mensual por Categoría', left: 'center', textStyle: {{ fontSize: 12 }} }},
        tooltip: {{ trigger: 'axis', axisPointer: {{ type: 'shadow' }},
            formatter: params => {{ let r = params[0].axisValue + '<br/>'; let t=0;
                params.forEach(p => {{ r += p.marker+' '+p.seriesName+': '+fmtM(p.value)+'<br/>'; t+=p.value; }});
                return r+'<b>Total: '+fmtM(t)+'</b>'; }} }},
        legend: {{ bottom: 0, textStyle: {{ fontSize: 9 }} }},
        grid: {{ left: '4%', right: '4%', bottom: '14%', top: '14%', containLabel: true }},
        xAxis: {{ type: 'category', data: {meses}, axisLabel: {{ fontSize: 10 }} }},
        yAxis: {{ type: 'value', axisLabel: {{ formatter: v => '$'+(v/1000000).toFixed(1)+'M', fontSize: 9 }} }},
        series: [
            {{ name: 'Facturas', type: 'bar', stack: 'total', data: {facturas3}, itemStyle: {{ color: '#00C4CC' }}, barWidth:'60%' }},
            {{ name: 'Boletas', type: 'bar', stack: 'total', data: {boletas3}, itemStyle: {{ color: '#FF9A00' }} }},
            {{ name: 'Comprobantes', type: 'bar', stack: 'total', data: {comp3}, itemStyle: {{ color: '#4CAF50' }} }},
            {{ name: 'Notas Déb.', type: 'bar', stack: 'total', data: {nd3}, itemStyle: {{ color: '#9C27B0' }} }}
        ]
    }});

    // HOJA 3 - Dona
    const cD3 = echarts.init(document.getElementById('chartDonaHoja3'), null, _echarts_opts);
    cD3.setOption({{
        title: {{ text: 'Mix Ingresos {ano}', left: 'center', textStyle: {{ fontSize: 11 }} }},
        tooltip: {{ trigger: 'item', textStyle: {{ fontSize: 10 }} }},
        legend: {{ bottom: 0, textStyle: {{ fontSize: 9 }} }},
        series: [{{ type: 'pie', radius: ['38%','62%'], center: ['50%','46%'],
            label: {{ show: true, fontSize: 10, fontWeight: 'bold', formatter: '{{d}}%', position: 'inside' }},
            labelLine: {{ show: false }},
            data: [
                {{ value: {fa3}, name: 'Facturas', itemStyle: {{ color: '#00C4CC' }} }},
                {{ value: {bo3}, name: 'Boletas', itemStyle: {{ color: '#FF9A00' }} }},
                {{ value: {co3}, name: 'Comprobantes', itemStyle: {{ color: '#4CAF50' }} }},
                {{ value: {nd3a}, name: 'Notas Déb.', itemStyle: {{ color: '#9C27B0' }} }}
            ] }}]
    }});

    // HOJA 4 - Barras
    const cB4 = echarts.init(document.getElementById('chartBarrasHoja4'), null, _echarts_opts);
    cB4.setOption({{
        title: {{ text: 'Gastos por Tipo', left: 'center', textStyle: {{ fontSize: 12 }} }},
        tooltip: {{ trigger: 'axis', axisPointer: {{ type: 'shadow' }},
            formatter: params => {{ let r=params[0].axisValue+'<br/>'; let t=0;
                params.forEach(p => {{ r+=p.marker+' '+p.seriesName+': '+fmtM(p.value)+'<br/>'; t+=p.value; }});
                return r+'<b>Total: '+fmtM(t)+'</b>'; }} }},
        legend: {{ bottom: 0, textStyle: {{ fontSize: 9 }} }},
        grid: {{ left: '4%', right: '4%', bottom: '14%', top: '14%', containLabel: true }},
        xAxis: {{ type: 'category', data: {meses}, axisLabel: {{ fontSize: 10 }} }},
        yAxis: {{ type: 'value', axisLabel: {{ formatter: v => '$'+(v/1000000).toFixed(1)+'M', fontSize: 9 }} }},
        series: [
            {{ name: 'Remuneraciones', type: 'bar', stack: 'total', data: {rem4}, itemStyle: {{ color: '#10B981' }}, barWidth:'60%' }},
            {{ name: 'Facturas', type: 'bar', stack: 'total', data: {fac4}, itemStyle: {{ color: '#00C4CC' }} }},
            {{ name: 'Honorarios', type: 'bar', stack: 'total', data: {hon4}, itemStyle: {{ color: '#FF9A00' }} }},
            {{ name: 'Otros', type: 'bar', stack: 'total', data: {otr4}, itemStyle: {{ color: '#8B5CF6' }} }}
        ]
    }});

    // HOJA 4 - Líneas
    const cL4 = echarts.init(document.getElementById('chartLineasHoja4'), null, _echarts_opts);
    cL4.setOption({{
        title: {{ text: 'Tendencias por Tipo de Gasto', left: 'center', textStyle: {{ fontSize: 12 }} }},
        tooltip: {{ trigger: 'axis', textStyle: {{ fontSize: 10 }} }},
        legend: {{ bottom: 0, textStyle: {{ fontSize: 9 }} }},
        grid: {{ left: '4%', right: '4%', bottom: '14%', top: '14%', containLabel: true }},
        xAxis: {{ type: 'category', data: {meses}, boundaryGap: false, axisLabel: {{ fontSize: 10 }} }},
        yAxis: {{ type: 'value', axisLabel: {{ formatter: v => '$'+(v/1000000).toFixed(1)+'M', fontSize: 9 }} }},
        series: [
            {{ name: 'Remuneraciones', type: 'line', data: {rem4}, smooth: true,
               lineStyle: {{ width: 2, color: '#10B981' }}, areaStyle: {{ color: '#10B981', opacity: 0.12 }}, symbolSize: 5 }},
            {{ name: 'Facturas', type: 'line', data: {fac4}, smooth: true,
               lineStyle: {{ width: 2, color: '#00C4CC' }}, areaStyle: {{ color: '#00C4CC', opacity: 0.12 }}, symbolSize: 5 }},
            {{ name: 'Honorarios', type: 'line', data: {hon4}, smooth: true,
               lineStyle: {{ width: 2, color: '#FF9A00' }}, areaStyle: {{ color: '#FF9A00', opacity: 0.12 }}, symbolSize: 5 }},
            {{ name: 'Otros', type: 'line', data: {otr4}, smooth: true,
               lineStyle: {{ width: 2, color: '#8B5CF6' }}, areaStyle: {{ color: '#8B5CF6', opacity: 0.12 }}, symbolSize: 5 }}
        ]
    }});

    // HOJA 4 - Dona
    const cD4 = echarts.init(document.getElementById('chartDonaHoja4'), null, _echarts_opts);
    cD4.setOption({{
        title: {{ text: 'Composición Gastos {ano}', left: 'center', textStyle: {{ fontSize: 11 }} }},
        tooltip: {{ trigger: 'item', textStyle: {{ fontSize: 10 }} }},
        legend: {{ bottom: 0, textStyle: {{ fontSize: 9 }} }},
        series: [{{ type: 'pie', radius: ['38%','62%'], center: ['50%','46%'],
            label: {{ show: true, fontSize: 10, fontWeight: 'bold', formatter: '{{d}}%', position: 'inside' }},
            labelLine: {{ show: false }},
            data: [
                {{ value: {ra4}, name: 'RRHH', itemStyle: {{ color: '#10B981' }} }},
                {{ value: {fa4}, name: 'Facturas', itemStyle: {{ color: '#00C4CC' }} }},
                {{ value: {ha4}, name: 'Honorarios', itemStyle: {{ color: '#FF9A00' }} }},
                {{ value: {oa4}, name: 'Otros', itemStyle: {{ color: '#8B5CF6' }} }}
            ] }}]
    }});
    """.format(
        meses=meses_json, ingresos=ingresos, gastos=gastos, utilidad=utilidad, cp=cp, cs=cs,
        facturas3=_jlist(cat.get('facturas')), boletas3=_jlist(cat.get('boletas')),
        comp3=_jlist(cat.get('comprobantes')), nd3=_jlist(cat.get('notas_debito')),
        fa3=float(a3.get('facturas') or 0), bo3=float(a3.get('boletas') or 0),
        co3=float(a3.get('comprobantes') or 0), nd3a=float(a3.get('notas_debito') or 0),
        rem4=_jlist(gas.get('remuneraciones')), fac4=_jlist(gas.get('facturas')),
        hon4=_jlist(gas.get('honorarios')), otr4=_jlist(gas.get('otros')),
        ra4=float(a4.get('remuneraciones') or 0), fa4=float(a4.get('facturas') or 0),
        ha4=float(a4.get('honorarios') or 0), oa4=float(a4.get('otros') or 0),
        ano=ano,
    )


# ──────────────────────────────────────────────────────────
# GENERACIÓN HTML COMPLETO
# ──────────────────────────────────────────────────────────

def generar_html(payload, config=None):
    if config is None:
        config = frappe.get_single('Configuracion App')

    cp = getattr(config, 'pdf_color_primario', None) or '#00C4CC'
    cs = getattr(config, 'pdf_color_secundario', None) or '#FF9A00'
    hoja6 = int(getattr(config, 'pdf_habilitar_hoja6', 1) or 1)
    texto_promo = getattr(config, 'pdf_texto_promocion', None) or ''
    logo_src = getattr(config, 'logo_empresa', None) or payload.get('logo_url', '')

    d = payload
    ofi = d.get('oficina') or {}
    mes = int(d.get('mes') or 1)
    ano = int(d.get('ano') or 2026)

    f = d.get('fechas') or {}
    if not f.get('f29'):
        f = _calcular_fechas(mes, ano)

    meses_nombres = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
                     'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
    meses = meses_nombres[:mes]

    css = _get_css(cp, cs)
    chart_js = _chart_script(d, meses, cp, cs)

    pages = [
        _hoja1(d, f, ofi, logo_src),
        _hoja2(d, meses, logo_src),
        _hoja3(d, meses, logo_src),
        _hoja4(d, meses, logo_src),
        _hoja5(d, logo_src),
    ]
    if hoja6:
        pages.append(_hoja6(d, ofi, logo_src, texto_promo))

    pages_html = ''.join(
        '<div class="page">{}</div>'.format(p) for p in pages
    )

    return """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Reporte - {cliente}</title>
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@700;800;900&family=Open+Sans:wght@400;600;700&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
<style>{css}</style>
</head>
<body>
{pages}
<script>{chart_js}</script>
</body>
</html>""".format(
        cliente=d.get('cliente', ''),
        css=css,
        pages=pages_html,
        chart_js=chart_js,
    )


# ──────────────────────────────────────────────────────────
# GOTENBERG
# ──────────────────────────────────────────────────────────

def convertir_a_pdf(html_content):
    config = frappe.get_single('Configuracion App')
    url = getattr(config, 'gotenberg_url', None)
    if not url:
        frappe.throw('URL de Gotenberg no configurada en Configuracion App → Integraciones')

    url = url.rstrip('/') + '/forms/chromium/convert/html'

    auth = None
    usuario = getattr(config, 'gotenberg_usuario', None)
    password = getattr(config, 'gotenberg_password', None)
    if usuario and password:
        auth = (usuario, password)

    files = {'index.html': ('index.html', html_content.encode('utf-8'), 'text/html')}
    data = {
        'waitDelay': '3s',
        'paperWidth': '8.27',
        'paperHeight': '11.69',
        'marginTop': '0',
        'marginBottom': '0',
        'marginLeft': '0',
        'marginRight': '0',
    }

    resp = requests.post(url, files=files, data=data, auth=auth, timeout=120)
    if resp.status_code != 200:
        frappe.throw('Error Gotenberg {}: {}'.format(resp.status_code, resp.text[:300]))

    return resp.content


# ──────────────────────────────────────────────────────────
# FUNCIÓN PRINCIPAL
# ──────────────────────────────────────────────────────────

@frappe.whitelist()
def generar_y_subir_pdf(declaracion_name):
    from evoluciona_pyme_v2.evoluciona_pyme_v2.api import preparar_datos_pdf_payload
    from evoluciona_pyme_v2.evoluciona_pyme_v2.drive import subir_pdf

    try:
        payload = preparar_datos_pdf_payload(declaracion_name)
        config = frappe.get_single('Configuracion App')

        html = generar_html(payload, config)
        pdf_bytes = convertir_a_pdf(html)

        decl = frappe.get_doc('Declaracion_Mensual', declaracion_name)
        cliente = frappe.get_doc('Ficha_Cliente', decl.cliente)
        carpeta_id = cliente.get('drive_declaraciones_id') or cliente.get('drive_folder_id')

        meses_nombres = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                         'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
        mes_nombre = meses_nombres[int(decl.mes) - 1]
        nombre_archivo = 'Declaracion_{}_{}_{}.pdf'.format(
            cliente.abreviatura_cliente or decl.cliente, mes_nombre, decl.ano)

        resultado = subir_pdf(pdf_bytes, nombre_archivo, carpeta_id, año=int(decl.ano))

        frappe.db.set_value('Declaracion_Mensual', declaracion_name, {
            'pdf_link_cliente': resultado.get('url'),
            'pdf_drive_file_id': resultado.get('id'),
        })
        frappe.db.commit()

        return {'status': 'success', 'pdf_url': resultado.get('url')}

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), 'PDF - generar_y_subir_pdf')
        return {'status': 'error', 'message': str(e)}
