frappe.ui.form.on('Libro_de_Gastos_Cliente', {
	refresh(frm) {
		frm.add_custom_button('Ver Ficha Cliente', () => {
			if (frm.doc.cliente) frappe.set_route('Form', 'Ficha_Cliente', frm.doc.cliente);
		}, 'Navegar');
	},

	neto(frm) { _calcular_total(frm); },
	iva(frm)  { _calcular_total(frm); },
});

function _calcular_total(frm) {
	const total = flt(frm.doc.neto) + flt(frm.doc.iva);
	frm.set_value('total_documento', total);
	if (!frm.doc.costo_empresa) {
		frm.set_value('costo_empresa', total);
	}
}
