// Copyright (c) 2026, WildanYR and contributors
// For license information, please see license.txt

frappe.ui.form.on("Quick Purchase", {
	setup: function (frm) {
		// Set query filters for Company-dependent fields
		frm.set_query("payment_account", function () {
			return {
				filters: {
					is_group: 0,
					company: frm.doc.company || frappe.defaults.get_default("company"),
					account_type: ["in", ["Cash", "Bank", "Temporary"]],
				},
			};
		});

		frm.set_query("warehouse", function () {
			return {
				filters: {
					company: frm.doc.company || frappe.defaults.get_default("company"),
				},
			};
		});

		frm.set_query("warehouse", "items_bought", function () {
			return {
				filters: {
					company:
						frm.doc.company ||
						frm.doc.company ||
						frappe.defaults.get_default("company"),
				},
			};
		});
	},

	onload: function (frm) {
		if (frm.is_new() && !frm.doc.company) {
			frm.set_value("company", frappe.defaults.get_default("company"));
		}
	},

	material_request: function (frm) {
		if (frm.doc.material_request) {
			frappe.db.get_doc("Material Request", frm.doc.material_request).then((mr) => {
				if (mr.company) {
					frm.set_value("company", mr.company);
				}
				if (mr.set_warehouse) {
					frm.set_value("warehouse", mr.set_warehouse);
				}

				// Fetch pending items from MR
				frappe.call({
					method: "akgp_extensions.akgp_extensions.doctype.quick_purchase.quick_purchase.get_items_from_material_request",
					args: {
						material_request: frm.doc.material_request,
					},
					callback: function (r) {
						if (r.message) {
							frm.clear_table("items_bought");
							r.message.forEach((item) => {
								let row = frm.add_child("items_bought");
								row.item_code = item.item_code;
								row.qty = item.qty;
								row.rate = 0;
								row.amount = 0;
								row.warehouse =
									item.warehouse || frm.doc.warehouse || mr.set_warehouse;
								row.material_request_item = item.material_request_item;
							});
							frm.refresh_field("items_bought");
						}
					},
				});
			});
		}
	},

	warehouse: function (frm) {
		if (frm.doc.warehouse) {
			frm.doc.items_bought.forEach((row) => {
				if (!row.warehouse) {
					row.warehouse = frm.doc.warehouse;
				}
			});
			frm.refresh_field("items_bought");
		}
	},
});

frappe.ui.form.on("Quick Purchase Item", {
	qty: function (frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		frappe.model.set_value(cdt, cdn, "amount", flt(row.qty) * flt(row.rate));
	},
	rate: function (frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		frappe.model.set_value(cdt, cdn, "amount", flt(row.qty) * flt(row.rate));
	},
});
