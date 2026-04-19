frappe.ui.form.on('Test_API', {
    refresh: function(frm) {
        frm.add_custom_button(__('Buscar Producto'), function() {
            
            console.log('Código a buscar:', frm.doc.codigo_producto);
            
            frappe.call({
                method: 'test_api.obtener_datos',
                args: {
                    'codigo_producto': frm.doc.codigo_producto
                },
                callback: function(r) {
                    if (r.message) {
                        frm.set_value('resultado', JSON.stringify(r.message, null, 2));
                        
                        frappe.show_alert({
                            message: r.message.mensaje,
                            indicator: r.message.producto_encontrado ? 'green' : 'orange'
                        }, 5);
                    }
                }
            });
        });
    }
});