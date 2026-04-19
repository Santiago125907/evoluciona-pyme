# ================================================================
# SERVER SCRIPT: Borrador F29 - Generador HTML
# ================================================================
# Tipo: DocType Event
# Reference Document Type: Borrador_F29
# Event: Before Save
# ================================================================

def generar_html_f29(doc):
    """
    Genera el HTML completo del Formulario 29 con diseño moderno
    """
    
    # =====================================================
    # VALIDACIÓN: Solo generar HTML si hay líneas
    # =====================================================
    if not doc.tabla_debitos and not doc.tabla_creditos and not doc.tabla_impuestos:
        # Si no hay líneas, retornar un mensaje temporal
        return """
        <div style="padding: 40px; text-align: center; background: #f8f9fa; border-radius: 8px;">
            <h3 style="color: #6c757d;">📋 Borrador vacío</h3>
            <p style="color: #adb5bd;">Las líneas del F29 se agregarán automáticamente al guardar el documento.</p>
        </div>
        """
    
    # =====================================================
    # FUNCIÓN PARA OBTENER CONFIGURACIÓN DE CÓDIGOS
    # =====================================================
    def obtener_config_codigo(codigo_f29):
        """Obtiene la configuración de un código F29"""
        config = frappe.db.get_value(
            "Configuracion_Codigo_F29",
            {"codigo_f29": codigo_f29, "es_calculado": 1},
            ["fuente_doctype", "filtro_tipo"],
            as_dict=True
        )
        return config
    
    def generar_link_documentos(codigo_f29, cliente, ano, mes):
        """Genera el link para ver los documentos que componen un código"""
        config = obtener_config_codigo(codigo_f29)
        
        if not config or not config.fuente_doctype:
            return ""
        
        # Determinar qué report usar
        report_name = ""
        filtro_adicional = ""
        
        if config.fuente_doctype == "Libro_de_Ingresos_Cliente":
            report_name = "Detalle Ingresos F29"
            if config.filtro_tipo:
                try:
                    import urllib.parse
                    filtro_encoded = urllib.parse.quote(config.filtro_tipo)
                    filtro_adicional = f"&tipo_documento={filtro_encoded}"
                except:
                    pass
        elif config.fuente_doctype == "Libro_de_Egresos_Cliente":
            report_name = "Detalle Egresos F29"
            if config.filtro_tipo:
                try:
                    import urllib.parse
                    filtro_encoded = urllib.parse.quote(config.filtro_tipo)
                    filtro_adicional = f"&tipo_egreso={filtro_encoded}"
                except:
                    pass
        elif config.fuente_doctype == "Registro_Remuneraciones":
            report_name = "Detalle RRHH F29"
        
        if not report_name:
            return ""
        
        # Construir URL del report
        url = f"/app/query-report/{report_name}?cliente={cliente}&ano_tributario={ano}&mes_tributario={mes}{filtro_adicional}"
        
        # HTML del link
        return f'''
        <a href="{url}" 
           target="_blank" 
           class="link-documentos"
           title="Ver documentos que componen este monto">
            Ver docs
        </a>
        '''
    
    # =====================================================
    # CSS INLINE (Diseño moderno tipo SII)
    # =====================================================
    css = """
    <style>
        .f29-container {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f7fa;
        }
        
        .seccion {
            background: white;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            border: 1px solid #e1e8ed;
        }
        
        .seccion-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 16px;
            border-bottom: 3px solid #0066cc;
        }
        
        .seccion-title {
            font-size: 20px;
            font-weight: 700;
            color: #1a1a1a;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .subtotal {
            font-size: 18px;
            font-weight: 700;
            color: #28a745;
            background: #e8f5e9;
            padding: 8px 16px;
            border-radius: 6px;
        }
        
        .tabla-f29 {
            width: 100%;
            border-collapse: collapse;
            margin-top: 16px;
        }
        
        .tabla-f29 thead {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        
        .tabla-f29 th {
            padding: 8px 10px;
            text-align: left;
            font-weight: 600;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .tabla-f29 tbody tr {
            border-bottom: 1px solid #e1e8ed;
            transition: all 0.2s ease;
            height: 36px;
        }
        
        .tabla-f29 tbody tr:hover {
            background: #f8f9fa;
        }
        
        .tabla-f29 td {
            padding: 6px 10px;
            font-size: 13px;
            color: #2c3e50;
            line-height: 1.2;
        }
        
        /* Campos calculados */
        .campo-calculado {
            background: #ecf0f1 !important;
        }
        
        .campo-calculado input {
            background: #ecf0f1 !important;
            color: #7f8c8d !important;
            cursor: not-allowed;
            border: 1px solid #bdc3c7;
            width: 100%;
            padding: 6px 10px;
            border-radius: 4px;
            font-size: 13px;
            font-weight: 600;
            text-align: right;
        }
        
        /* Campos manuales */
        .campo-manual input {
            width: 100%;
            padding: 6px 10px;
            border: 2px solid #e1e8ed;
            border-radius: 4px;
            font-size: 13px;
            font-weight: 600;
            color: #2c3e50;
            transition: all 0.2s ease;
            text-align: right;
        }
        
        .campo-manual input:focus {
            outline: none;
            border-color: #0066cc;
            box-shadow: 0 0 0 3px rgba(0,102,204,0.1);
            background: #f0f8ff;
        }
        
        .campo-manual input:hover {
            border-color: #0066cc;
        }
        
        /* Link a documentos */
        .link-documentos {
            display: inline-block;
            margin-left: 8px;
            padding: 4px 10px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-decoration: none;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            transition: all 0.2s ease;
        }
        
        .link-documentos:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(102,126,234,0.3);
            text-decoration: none;
            color: white;
        }
        
        /* Badges */
        .badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .badge-calculado {
            background: linear-gradient(135deg, #6c757d 0%, #495057 100%);
            color: white;
        }
        
        .badge-manual {
            background: linear-gradient(135deg, #ffc107 0%, #ff9800 100%);
            color: #000;
        }
        
        /* Resumen final */
        .resumen-final {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            border-radius: 12px;
            margin-top: 32px;
            box-shadow: 0 8px 24px rgba(102,126,234,0.4);
        }
        
        .resumen-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 24px;
            margin-bottom: 32px;
        }
        
        .resumen-item {
            text-align: center;
        }
        
        .resumen-label {
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 1px;
            opacity: 0.9;
            margin-bottom: 8px;
        }
        
        .resumen-valor {
            font-size: 24px;
            font-weight: 700;
        }
        
        .total-pagar {
            text-align: center;
            padding-top: 32px;
            border-top: 2px solid rgba(255,255,255,0.3);
        }
        
        .total-pagar-label {
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 2px;
            margin-bottom: 12px;
            opacity: 0.9;
        }
        
        .total-pagar-valor {
            font-size: 48px;
            font-weight: 900;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }
    </style>
    """
    
    # =====================================================
    # CALCULAR SUBTOTALES
    # =====================================================
    CODIGO_POSTERGACION_IVA = '771'
    
    subtotal_debitos = 0
    subtotal_creditos = 0
    subtotal_postergacion = 0
    subtotal_impuestos = 0
    
    # Calcular débitos
    if doc.tabla_debitos:
        for linea in doc.tabla_debitos:
            monto = float(linea.monto or 0)
            if linea.tipo_operacion_subtotal == 'Resta':
                subtotal_debitos -= monto
            elif linea.tipo_operacion_subtotal != 'Informativo':
                subtotal_debitos += monto
    
    # Calcular créditos y postergación
    if doc.tabla_creditos:
        for linea in doc.tabla_creditos:
            monto = float(linea.monto or 0)
            if linea.codigo_f29 == CODIGO_POSTERGACION_IVA:
                subtotal_postergacion += monto
            else:
                if linea.tipo_operacion_subtotal == 'Resta':
                    subtotal_creditos -= monto
                elif linea.tipo_operacion_subtotal != 'Informativo':
                    subtotal_creditos += monto
    
    # Calcular otros impuestos
    if doc.tabla_impuestos:
        for linea in doc.tabla_impuestos:
            monto = float(linea.monto or 0)
            if linea.tipo_operacion_subtotal == 'Resta':
                subtotal_impuestos -= monto
            elif linea.tipo_operacion_subtotal != 'Informativo':
                subtotal_impuestos += monto
    
    # Calcular IVA determinado y remanente
    iva_resultante = subtotal_debitos - subtotal_creditos
    if iva_resultante > 0:
        iva_determinado = iva_resultante
        remanente = 0
    else:
        iva_determinado = 0
        remanente = abs(iva_resultante)
    
    # Calcular total a pagar
    postergacion_periodo = float(doc.postergacion_del_periodo or 0)
    total_pagar = max(0, iva_determinado - postergacion_periodo + subtotal_impuestos)    
    
    # Actualizar campos del documento
    doc.subtotal_debitos = subtotal_debitos
    doc.subtotal_creditos = subtotal_creditos
    doc.subtotal_postergacion_iva = subtotal_postergacion
    doc.subtotal_otros_impuestos = subtotal_impuestos
    doc.impuesto_determinado = iva_determinado
    doc.remanente_mes_siguiente = remanente
    doc.total_a_pagar_f29 = total_pagar
    
    # =====================================================
    # FUNCIONES DE FORMATO
    # =====================================================
    
    def formatear_moneda(valor):
        """Formatea un número como moneda chilena para MOSTRAR"""
        return f"${valor:,.0f}".replace(",", ".")
    
    def formatear_input(valor):
        """Formatea un número para el VALUE del input (con puntos)"""
        if valor == 0:
            return "0"
        return f"{valor:,.0f}".replace(",", ".")
    
    # =====================================================
    # GENERAR HTML
    # =====================================================
    
    html = f"""
    {css}
    <div class="f29-container">
        
        <!-- SECCIÓN: DÉBITOS FISCALES -->
        <div class="seccion">
            <div class="seccion-header">
                <span class="seccion-title">
                    <span>📊</span>
                    DÉBITOS FISCALES
                </span>
                <span class="subtotal" id="subtotal-debitos">
                    {formatear_moneda(subtotal_debitos)}
                </span>
            </div>
            
            <table class="tabla-f29">
                <thead>
                    <tr>
                        <th style="width: 8%;">Código</th>
                        <th style="width: 38%;">Descripción</th>
                        <th style="width: 18%;">Monto</th>
                        <th style="width: 15%;">Operación</th>
                        <th style="width: 21%;">Origen</th>
                    </tr>
                </thead>
                <tbody id="tbody-debitos">
    """
    
    # Generar filas de débitos
    if doc.tabla_debitos:
        for linea in doc.tabla_debitos:
            es_calculado = linea.tipo_origen == 'Calculado'
            clase_campo = 'campo-calculado' if es_calculado else 'campo-manual'
            readonly = 'readonly disabled' if es_calculado else ''
            badge_clase = 'badge-calculado' if es_calculado else 'badge-manual'
            icono = '🤖' if es_calculado else '✏️'
            
            # Generar link si es calculado
            link_docs = ""
            if es_calculado:
                link_docs = generar_link_documentos(linea.codigo_f29, doc.cliente, doc.ano, doc.mes)
            
            html += f"""
                    <tr data-tabla="tabla_debitos" data-idx="{linea.idx}">
                        <td><strong>{linea.codigo_f29}</strong></td>
                        <td>{linea.descripcion}</td>
                        <td class="{clase_campo}">
                            <input type="text" 
                                   class="monto-field"
                                   value="{formatear_input(linea.monto or 0)}" 
                                   {readonly}
                                   data-tabla="tabla_debitos"
                                   data-idx="{linea.idx}"
                                   data-monto-real="{linea.monto or 0}">
                        </td>
                        <td>{linea.tipo_operacion_subtotal or 'Suma'}</td>
                        <td>
                            <span class="badge {badge_clase}">
                                {icono} {linea.tipo_origen}
                            </span>
                            {link_docs}
                        </td>
                    </tr>
            """
    
    html += f"""
                </tbody>
            </table>
        </div>
        
        <!-- SECCIÓN: CRÉDITOS FISCALES -->
        <div class="seccion">
            <div class="seccion-header">
                <span class="seccion-title">
                    <span>📊</span>
                    CRÉDITOS FISCALES
                </span>
                <span class="subtotal" id="subtotal-creditos">
                    {formatear_moneda(subtotal_creditos)}
                </span>
            </div>
            
            <table class="tabla-f29">
                <thead>
                    <tr>
                        <th style="width: 8%;">Código</th>
                        <th style="width: 38%;">Descripción</th>
                        <th style="width: 18%;">Monto</th>
                        <th style="width: 15%;">Operación</th>
                        <th style="width: 21%;">Origen</th>
                    </tr>
                </thead>
                <tbody id="tbody-creditos">
    """
    
    # Generar filas de créditos
    if doc.tabla_creditos:
        for linea in doc.tabla_creditos:
            es_calculado = linea.tipo_origen == 'Calculado'
            clase_campo = 'campo-calculado' if es_calculado else 'campo-manual'
            readonly = 'readonly disabled' if es_calculado else ''
            badge_clase = 'badge-calculado' if es_calculado else 'badge-manual'
            icono = '🤖' if es_calculado else '✏️'
            
            # Generar link si es calculado
            link_docs = ""
            if es_calculado:
                link_docs = generar_link_documentos(linea.codigo_f29, doc.cliente, doc.ano, doc.mes)
            
            html += f"""
                    <tr data-tabla="tabla_creditos" data-idx="{linea.idx}">
                        <td><strong>{linea.codigo_f29}</strong></td>
                        <td>{linea.descripcion}</td>
                        <td class="{clase_campo}">
                            <input type="text" 
                                   class="monto-field"
                                   value="{formatear_input(linea.monto or 0)}" 
                                   {readonly}
                                   data-tabla="tabla_creditos"
                                   data-idx="{linea.idx}"
                                   data-monto-real="{linea.monto or 0}">
                        </td>
                        <td>{linea.tipo_operacion_subtotal or 'Suma'}</td>
                        <td>
                            <span class="badge {badge_clase}">
                                {icono} {linea.tipo_origen}
                            </span>
                            {link_docs}
                        </td>
                    </tr>
            """
    
    html += f"""
                </tbody>
            </table>
        </div>
        
        <!-- SECCIÓN: OTROS IMPUESTOS -->
        <div class="seccion">
            <div class="seccion-header">
                <span class="seccion-title">
                    <span>📊</span>
                    OTROS IMPUESTOS Y RETENCIONES
                </span>
                <span class="subtotal" id="subtotal-impuestos">
                    {formatear_moneda(subtotal_impuestos)}
                </span>
            </div>
            
            <table class="tabla-f29">
                <thead>
                    <tr>
                        <th style="width: 8%;">Código</th>
                        <th style="width: 38%;">Descripción</th>
                        <th style="width: 18%;">Monto</th>
                        <th style="width: 15%;">Operación</th>
                        <th style="width: 21%;">Origen</th>
                    </tr>
                </thead>
                <tbody id="tbody-impuestos">
    """
    
    # Generar filas de impuestos
    if doc.tabla_impuestos:
        for linea in doc.tabla_impuestos:
            es_calculado = linea.tipo_origen == 'Calculado'
            clase_campo = 'campo-calculado' if es_calculado else 'campo-manual'
            readonly = 'readonly disabled' if es_calculado else ''
            badge_clase = 'badge-calculado' if es_calculado else 'badge-manual'
            icono = '🤖' if es_calculado else '✏️'
            
            # Generar link si es calculado
            link_docs = ""
            if es_calculado:
                link_docs = generar_link_documentos(linea.codigo_f29, doc.cliente, doc.ano, doc.mes)
            
            html += f"""
                    <tr data-tabla="tabla_impuestos" data-idx="{linea.idx}">
                        <td><strong>{linea.codigo_f29}</strong></td>
                        <td>{linea.descripcion}</td>
                        <td class="{clase_campo}">
                            <input type="text" 
                                   class="monto-field"
                                   value="{formatear_input(linea.monto or 0)}" 
                                   {readonly}
                                   data-tabla="tabla_impuestos"
                                   data-idx="{linea.idx}"
                                   data-monto-real="{linea.monto or 0}">
                        </td>
                        <td>{linea.tipo_operacion_subtotal or 'Suma'}</td>
                        <td>
                            <span class="badge {badge_clase}">
                                {icono} {linea.tipo_origen}
                            </span>
                            {link_docs}
                        </td>
                    </tr>
            """
    
    html += f"""
                </tbody>
            </table>
        </div>
        
        <!-- RESUMEN FINAL -->
        <div class="resumen-final">
            <div class="resumen-grid">
                <div class="resumen-item">
                    <div class="resumen-label">Débitos Fiscales</div>
                    <div class="resumen-valor" id="resumen-debitos">{formatear_moneda(subtotal_debitos)}</div>
                </div>
                <div class="resumen-item">
                    <div class="resumen-label">Créditos Fiscales</div>
                    <div class="resumen-valor" id="resumen-creditos">{formatear_moneda(subtotal_creditos)}</div>
                </div>
                <div class="resumen-item">
                    <div class="resumen-label">IVA Determinado</div>
                    <div class="resumen-valor" id="resumen-iva-determinado">{formatear_moneda(iva_determinado)}</div>
                </div>
                <div class="resumen-item">
                    <div class="resumen-label">Remanente Mes Siguiente</div>
                    <div class="resumen-valor" id="resumen-remanente" style="color: {'#28a745' if remanente > 0 else '#ffffff80'}">
                        {formatear_moneda(remanente) if remanente > 0 else '$0'}
                    </div>
                </div>
                <div class="resumen-item">
                    <div class="resumen-label">Postergación IVA</div>
                    <div class="resumen-valor" id="resumen-postergacion">{formatear_moneda(subtotal_postergacion)}</div>
                </div>
                <div class="resumen-item">
                    <div class="resumen-label">Otros Impuestos</div>
                    <div class="resumen-valor" id="resumen-impuestos">{formatear_moneda(subtotal_impuestos)}</div>
                </div>
            </div>
            
            <div class="total-pagar">
                <div class="total-pagar-label">💰 TOTAL A PAGAR</div>
                <div class="total-pagar-valor" id="total-pagar">
                    {formatear_moneda(total_pagar)}
                </div>
            </div>
        </div>
        
    </div>
    """
    
    return html


# =====================================================
# EVENTO BEFORE_SAVE
# =====================================================

# Solo generar HTML, NO modificar nada más del documento
doc.html_renderizado = generar_html_f29(doc)