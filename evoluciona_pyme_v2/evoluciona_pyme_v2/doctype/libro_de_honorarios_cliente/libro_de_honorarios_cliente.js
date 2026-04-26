frappe.ui.form.on('Libro_de_Honorarios_Cliente', {
	refresh(frm) {
		frm.add_custom_button('Ver Ficha Cliente', () => {
			if (frm.doc.cliente) frappe.set_route('Form', 'Ficha_Cliente', frm.doc.cliente);
		}, 'Navegar');
	},

	monto_bruto(frm) {
		const bruto = flt(frm.doc.monto_bruto);
		const retencion = Math.round(bruto * 0.1075);
		const liquido   = bruto - retencion;
		frm.set_value('retencion_honorarios', retencion);
		frm.set_value('monto_liquido', liquido);
		frm.set_value('total_documento', bruto);
		if (!frm.doc.costo_empresa) {
			frm.set_value('costo_empresa', bruto);
		}
	},
});
