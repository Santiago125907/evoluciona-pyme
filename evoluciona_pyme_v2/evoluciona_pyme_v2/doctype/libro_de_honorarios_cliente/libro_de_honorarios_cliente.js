frappe.ui.form.on("Libro_de_Honorarios_Cliente", {
	refresh(frm) {
		frm.add_custom_button("Ver Ficha Cliente", () => {
			if (frm.doc.cliente) frappe.set_route("Form", "Ficha_Cliente", frm.doc.cliente);
		}, "Navegar");
	},

	_recalcular(frm) {
		const bruto = flt(frm.doc.monto_bruto);
		const retencion = flt(frm.doc.retencion_honorarios);
		frm.set_value("monto_liquido", Math.round(bruto - retencion));
		frm.set_value("total_documento", Math.round(bruto));
		frm.set_value("costo_empresa", Math.round(bruto));
	},

	monto_bruto(frm) { frm.trigger("_recalcular"); },
	retencion_honorarios(frm) { frm.trigger("_recalcular"); },
});
