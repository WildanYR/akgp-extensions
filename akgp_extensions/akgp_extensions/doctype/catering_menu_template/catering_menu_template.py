# Copyright (c) 2026, WildanYR and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

class CateringMenuTemplate(Document):
	def validate(self):
		self.validate_duplicate_entries()

	def validate_duplicate_entries(self):
		"""
		Memastikan tidak ada duplikasi kombinasi Day of Month + Meal Category
		di tabel template_items.
		"""
		seen = set()
		for item in self.get("template_items"):
			key = (item.day_of_month, item.meal_category)
			if key in seen:
				frappe.throw(
					_("Duplikasi entri terdeteksi untuk Hari ke-{0} dengan Kategori Meal '{1}'.").format(
						item.day_of_month, item.meal_category
					)
				)
			seen.add(key)
