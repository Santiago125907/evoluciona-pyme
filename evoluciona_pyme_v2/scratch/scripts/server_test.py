resultado = {
    'status': 'success',
    'mensaje': 'Búsqueda iniciada',
    'timestamp': frappe.utils.now()
}

codigo_producto = frappe.form_dict.get('codigo_producto')

if codigo_producto:
    # Buscar el producto - NOTA: usa 'Producto_Simple' con guión bajo
    productos = frappe.get_all('Producto_Simple', 
        filters={'codigo': codigo_producto},
        fields=['nombre_producto', 'precio', 'stock', 'codigo']
    )
    
    if productos:
        resultado['producto_encontrado'] = productos[0]
        resultado['mensaje'] = 'Producto encontrado!'
    else:
        resultado['mensaje'] = 'Producto no encontrado'
else:
    resultado['mensaje'] = 'No se proporcionó código de producto'

frappe.response['message'] = resultado