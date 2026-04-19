frappe.ui.form.on('Test_Calculadora', {
    refresh: function(frm) {
        if (frm.is_new()) return;
        
        frm.add_custom_button(__('Calcular Suma'), function() {
            frappe.call({
                method: 'test_calcular_suma',
                args: { doc_name: frm.doc.name },
                freeze: true,
                freeze_message: __('Calculando...'),
                callback: function(r) {
                    if (r.message && r.message.status === 'ok') {
                        frappe.show_alert({
                            message: 'Suma: $' + r.message.suma,
                            indicator: 'green'
                        }, 3);
                        frm.reload_doc();
                    }
                },
                error: function(r) {
                    console.error('Error:', r);
                    frappe.msgprint('Error al calcular');
                }
            });
        }).addClass('btn-primary');
    }
});