frappe.ui.form.on('Notificacion_Push_Portal', {
    refresh(frm) {

        function _confirmar_y_enviar(esReenvio) {
            frappe.call({
                method: 'evoluciona_pyme_v2.evoluciona_pyme_v2.doctype.notificacion_push_portal.notificacion_push_portal.contar_dispositivos',
                args: { name: frm.doc.name },
                callback(r) {
                    const info = r.message || {};
                    const prefix = esReenvio ? 'Se reenviará' : 'Se enviará';
                    const msg = info.dispositivos > 0
                        ? `${prefix} a <b>${info.dispositivos} dispositivo(s)</b> de <b>${info.clientes} cliente(s)</b>.<br>¿Confirmas?`
                        : '<b>No hay dispositivos suscritos</b> que coincidan con la selección. ¿Igual continúas?';

                    frappe.confirm(msg, function() {
                        frappe.call({
                            method: 'evoluciona_pyme_v2.evoluciona_pyme_v2.doctype.notificacion_push_portal.notificacion_push_portal.enviar_notificacion',
                            args: { name: frm.doc.name },
                            freeze: true,
                            freeze_message: esReenvio ? 'Reenviando notificaciones...' : 'Enviando notificaciones...',
                            callback(r2) {
                                if (r2.message && r2.message.ok) {
                                    frappe.show_alert({
                                        message: `✅ ${esReenvio ? 'Reenviado' : 'Enviado'} a ${r2.message.total_enviados} dispositivo(s)`,
                                        indicator: 'green'
                                    }, 5);
                                    frm.reload_doc();
                                }
                            }
                        });
                    });
                }
            });
        }

        if (!frm.doc.enviado) {
            frm.add_custom_button(__('📣 Enviar Notificación'), function() {
                _confirmar_y_enviar(false);
            }, __('Acciones'));
        } else {
            frm.dashboard.set_headline_alert(
                `✅ Enviada el ${frappe.datetime.str_to_user(frm.doc.fecha_envio)} — ${frm.doc.total_enviados || 0} dispositivos`,
                'green'
            );
            frm.add_custom_button(__('🔄 Reenviar'), function() {
                _confirmar_y_enviar(true);
            }, __('Acciones'));
        }
    }
});
