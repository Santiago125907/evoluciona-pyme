frappe.ui.form.on('Libro_de_Compras_Cliente', {
	refresh(frm) {
		frm.add_custom_button('Ver Ficha Cliente', () => {
			if (frm.doc.cliente) frappe.set_route('Form', 'Ficha_Cliente', frm.doc.cliente);
		}, 'Navegar');

		frm.add_custom_button('Ver Declaración', () => {
			if (frm.doc.cliente && frm.doc.mes_tributario && frm.doc.ano_tributario) {
				frappe.set_route('List', 'Declaracion_Mensual', {
					cliente: frm.doc.cliente,
					mes: frm.doc.mes_tributario,
					ano: frm.doc.ano_tributario
				});
			}
		}, 'Navegar');
	},

	neto(frm) { _calcular_total(frm); },
	iva_credito(frm) { _calcular_total(frm); },
	monto_exento(frm) { _calcular_total(frm); },
});

function _calcular_total(frm) {
	const neto = flt(frm.doc.neto);
	const iva  = flt(frm.doc.iva_credito);
	const exento = flt(frm.doc.monto_exento);
	frm.set_value('total_documento', neto + iva + exento);
	if (!frm.doc.costo_empresa) {
		frm.set_value('costo_empresa', neto + iva + exento);
	}
}
