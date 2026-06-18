import frappe

def execute():
	# Seed data untuk Catering Meal Category
	for category in ["Breakfast", "Lunch"]:
		if not frappe.db.exists("Catering Meal Category", category):
			doc = frappe.get_doc({
				"doctype": "Catering Meal Category",
				"category_name": category,
				"description": f"Kategori Katering {category}"
			})
			doc.insert(ignore_permissions=True)
