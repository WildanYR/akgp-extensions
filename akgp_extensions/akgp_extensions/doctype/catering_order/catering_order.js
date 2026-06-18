// Copyright (c) 2026, WildanYR and contributors
// For license information, please see license.txt

frappe.ui.form.on("Catering Order", {
	setup: function (frm) {
		// Set filter agar Item yang bisa dipilih di schedule hanyalah sales item
		frm.set_query("item_code", "schedule_items", function () {
			return {
				filters: {
					is_sales_item: 1,
				},
			};
		});
		frm.set_query("meal_category", "categories", function () {
			return {
				filters: {},
			};
		});
	},
	refresh: function (frm) {
		if (frm.doc.docstatus === 1) {
			// Sembunyikan tombol Edit jika status sedang Generating SO
			if (frm.doc.status === "Generating Sales Orders") {
				frm.disable_save();
				frm.page.clear_primary_action();
				frm.page.clear_secondary_action();
			}

			// Tambahkan tombol aksi custom di grup Actions
			if (frm.doc.payment_status !== "Fully Paid" && frm.doc.status === "Active") {
				frm.add_custom_button(
					__("Buat Invoice Tagihan"),
					function () {
						frappe.call({
							method: "akgp_extensions.akgp_extensions.doctype.catering_order.catering_order.make_consolidated_invoice",
							args: {
								catering_order_name: frm.doc.name,
							},
							freeze: true,
							callback: function (r) {
								if (r.message) {
									let invoice_name = r.message;
									frappe.set_route("Form", "Sales Invoice", invoice_name);
								}
							},
						});
					},
					__("Actions"),
				);
			}

			if (frm.doc.status === "Active") {
				frm.add_custom_button(
					__("Proses Pengantaran Hari Ini"),
					function () {
						frappe.call({
							method: "akgp_extensions.akgp_extensions.doctype.catering_order.catering_order.process_today_delivery",
							args: {
								catering_order_name: frm.doc.name,
							},
							freeze: true,
							callback: function (r) {
								if (r.message && r.message.length > 0) {
									frappe.msgprint(
										__("Delivery Note Draft berhasil dibuat: ") +
											r.message.join(", "),
									);
									frm.reload_doc();
								} else {
									frappe.msgprint(
										__(
											"Tidak ada pengantaran terjadwal untuk hari ini yang belum dikirim.",
										),
									);
								}
							},
						});
					},
					__("Actions"),
				);
			}
		}
	},
	menu_template: function (frm) {
		frm.trigger("generate_schedule");
	},
	start_date: function (frm) {
		frm.trigger("generate_schedule");
	},
	end_date: function (frm) {
		frm.trigger("generate_schedule");
	},
	skip_sundays: function (frm) {
		frm.trigger("generate_schedule");
	},
	generate_schedule: function (frm) {
		if (frm.doc.docstatus !== 0) {
			return; // Jangan generate schedule jika dokumen sudah disubmit atau dibatalkan
		}
		if (!frm.doc.menu_template || !frm.doc.start_date || !frm.doc.end_date) {
			return;
		}

		if (frm.doc.start_date > frm.doc.end_date) {
			frappe.msgprint({
				title: __("Tanggal Tidak Valid"),
				indicator: "red",
				message: __(
					"Tanggal mulai (Start Date) tidak boleh setelah tanggal selesai (End Date).",
				),
			});
			return;
		}

		let categories = (frm.doc.categories || []).map((row) => row.meal_category);
		if (categories.length === 0) {
			return;
		}

		frappe.call({
			method: "akgp_extensions.akgp_extensions.doctype.catering_order.catering_order.get_schedule_items",
			args: {
				menu_template: frm.doc.menu_template,
				start_date: frm.doc.start_date,
				end_date: frm.doc.end_date,
				categories: categories,
				skip_sundays: frm.doc.skip_sundays,
			},
			freeze: true,
			callback: function (r) {
				if (r.message) {
					frm.clear_table("schedule_items");
					r.message.forEach((row) => {
						let child = frm.add_child("schedule_items");
						child.date = row.date;
						child.meal_category = row.meal_category;
						child.item_code = row.item_code;
						child.delivery_status = "Not Dispatched";
					});
					frm.refresh_field("schedule_items");
				}
			},
		});
	},
});

// Listener untuk Child Table Categories
frappe.ui.form.on("Catering Order Category", {
	meal_category: function (frm) {
		frm.trigger("generate_schedule");
	},
	categories_remove: function (frm) {
		frm.trigger("generate_schedule");
	},
});
