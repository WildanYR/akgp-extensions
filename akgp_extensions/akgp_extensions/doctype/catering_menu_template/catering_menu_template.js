// Copyright (c) 2026, WildanYR and contributors
// For license information, please see license.txt

frappe.ui.form.on("Catering Menu Template", {
	validate: function(frm) {
		let seen = new Set();
		let has_duplicate = false;
		
		(frm.doc.template_items || []).forEach(row => {
			if (row.day_of_month && row.meal_category) {
				let key = `${row.day_of_month}-${row.meal_category}`;
				if (seen.has(key)) {
					frappe.msgprint({
						title: __("Duplikasi Entri"),
						indicator: "red",
						message: __("Hari ke-{0} dengan Kategori Meal '{1}' dimasukkan lebih dari sekali.", [row.day_of_month, row.meal_category])
					});
					has_duplicate = true;
				}
				seen.add(key);
			}
		});

		if (has_duplicate) {
			frappe.validated = false;
		}
	}
});
