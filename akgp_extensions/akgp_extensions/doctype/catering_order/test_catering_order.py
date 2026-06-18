# Copyright (c) 2026, WildanYR and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate, today, add_days

from akgp_extensions.akgp_extensions.doctype.catering_order.catering_order import (
	get_schedule_items,
	create_sales_orders_job,
	make_consolidated_invoice,
	process_today_delivery
)

class TestCateringOrder(FrappeTestCase):
	def setUp(self):
		self.company = "_Test Company Catering"
		self.customer = "_Test Customer Catering"
		self.item_code_1 = "_Test Item Catering 1"
		self.item_code_2 = "_Test Item Catering 2"
		
		# 1. Ensure Company exists
		if not frappe.db.exists("Company", self.company):
			comp = frappe.new_doc("Company")
			comp.company_name = self.company
			comp.default_currency = "IDR"
			comp.insert(ignore_permissions=True)
			
		# Ensure Standard Selling Price List exists
		if not frappe.db.exists("Price List", "Standard Selling"):
			pl = frappe.new_doc("Price List")
			pl.price_list_name = "Standard Selling"
			pl.enabled = 1
			pl.selling = 1
			pl.currency = "IDR"
			pl.insert(ignore_permissions=True)
			
		# 2. Ensure Customer exists
		if not frappe.db.exists("Customer", self.customer):
			cust = frappe.new_doc("Customer")
			cust.customer_name = self.customer
			cust.insert(ignore_permissions=True)
			
		# 3. Ensure Items exist
		for item_code in [self.item_code_1, self.item_code_2]:
			if not frappe.db.exists("Item", item_code):
				item = frappe.new_doc("Item")
				item.item_code = item_code
				item.item_name = item_code
				item.item_group = "All Item Groups"
				item.stock_uom = "Nos"
				item.is_sales_item = 1
				item.is_stock_item = 1
				item.insert(ignore_permissions=True)
				
		# 4. Ensure Catering Meal Categories exist
		for cat in ["Breakfast", "Lunch"]:
			if not frappe.db.exists("Catering Meal Category", cat):
				doc = frappe.new_doc("Catering Meal Category")
				doc.category_name = cat
				doc.description = f"Kategori Katering {cat}"
				doc.insert(ignore_permissions=True)
				
		# 5. Ensure Catering Menu Template exists
		self.template_name = "Test June Template"
		existing_template = frappe.db.get_value("Catering Menu Template", {"template_name": self.template_name})
		if not existing_template:
			template = frappe.new_doc("Catering Menu Template")
			template.template_name = self.template_name
			template.month = "Juni"
			template.year = 2026
			
			# Setup menu for day 1 to 31
			for day in range(1, 32):
				template.append("template_items", {
					"day_of_month": str(day),
					"meal_category": "Breakfast",
					"item_code": self.item_code_1
				})
				template.append("template_items", {
					"day_of_month": str(day),
					"meal_category": "Lunch",
					"item_code": self.item_code_2
				})
			template.insert(ignore_permissions=True)
			self.template_name = template.name
		else:
			self.template_name = existing_template

	def test_schedule_generation(self):
		"""Uji logika auto-fill jadwal katering (get_schedule_items)"""
		start_date = "2026-06-01"
		end_date = "2026-06-03" # 1 Juni (Senin), 2 Juni (Selasa), 3 Juni (Rabu)
		categories = ["Breakfast", "Lunch"]
		
		# 1 Juni 2026 adalah Senin. Tidak ada Minggu di range ini.
		schedule = get_schedule_items(
			menu_template=self.template_name,
			start_date=start_date,
			end_date=end_date,
			categories=categories,
			skip_sundays=1
		)
		
		# Harusnya ada 3 hari * 2 kategori = 6 baris
		self.assertEqual(len(schedule), 6)
		self.assertEqual(schedule[0]["date"], "2026-06-01")
		self.assertEqual(schedule[0]["meal_category"], "Breakfast")
		self.assertEqual(schedule[0]["item_code"], self.item_code_1)
		
		# Uji skip hari Minggu. 7 Juni 2026 adalah hari Minggu.
		schedule_with_sunday = get_schedule_items(
			menu_template=self.template_name,
			start_date="2026-06-07",
			end_date="2026-06-07",
			categories=categories,
			skip_sundays=1
		)
		# Harus kosong karena 7 Juni adalah Minggu dan skip_sundays=1
		self.assertEqual(len(schedule_with_sunday), 0)

	def test_catering_order_workflow(self):
		"""Uji alur lengkap dari pembuatan Catering Order, background job SO, edit menu (auto amend), konsolidasi invoice, & DN."""
		# 1. Buat Catering Order Baru
		co = frappe.new_doc("Catering Order")
		co.customer = self.customer
		co.company = self.company
		co.start_date = today()
		co.end_date = add_days(today(), 2) # 3 hari pesanan
		co.menu_template = self.template_name
		co.skip_sundays = 0 # aktifkan semua hari untuk testing
		
		co.append("categories", {"meal_category": "Breakfast"})
		co.append("categories", {"meal_category": "Lunch"})
		
		# Generate schedule secara programmatic
		schedule = get_schedule_items(
			menu_template=co.menu_template,
			start_date=co.start_date,
			end_date=co.end_date,
			categories=["Breakfast", "Lunch"],
			skip_sundays=co.skip_sundays
		)
		
		for row in schedule:
			co.append("schedule_items", {
				"date": row["date"],
				"meal_category": row["meal_category"],
				"item_code": row["item_code"]
			})
			
		co.insert(ignore_permissions=True)
		co.submit()
		
		# Cek status berubah ke "Generating Sales Orders"
		self.assertEqual(co.status, "Generating Sales Orders")
		
		# 2. Simulasikan Background Job Pembuatan SO
		create_sales_orders_job(co.name)
		
		co.reload()
		# Cek status berubah ke "Active" setelah job selesai
		self.assertEqual(co.status, "Active")
		
		# Cek Sales Orders yang terbuat
		for row in co.schedule_items:
			self.assertTrue(row.sales_order_ref)
			so_status = frappe.db.get_value("Sales Order", row.sales_order_ref, "docstatus")
			self.assertEqual(so_status, 1)
			
		# Pastikan 2 item pada hari yang sama digabungkan ke 1 SO
		so_date_1 = co.schedule_items[0].sales_order_ref
		so_date_2 = co.schedule_items[1].sales_order_ref
		# Item 0 (date 1, Breakfast) & Item 1 (date 1, Lunch) harus menunjuk ke SO yang sama
		self.assertEqual(so_date_1, so_date_2)
		
		# 3. Uji Edit Menu (Auto Cancel & Amend SO)
		# Kita ganti menu untuk baris pertama (date 1, Breakfast) dari item_code_1 menjadi item_code_2
		old_so_ref = co.schedule_items[0].sales_order_ref
		co.schedule_items[0].item_code = self.item_code_2
		co.save(ignore_permissions=True)
		
		co.reload()
		new_so_ref = co.schedule_items[0].sales_order_ref
		
		# SO ref baru harus terbentuk (tidak sama dengan yang lama)
		self.assertNotEqual(old_so_ref, new_so_ref)
		
		# SO lama harus berstatus Cancelled (docstatus = 2)
		self.assertEqual(frappe.db.get_value("Sales Order", old_so_ref, "docstatus"), 2)
		# SO baru harus berstatus Submitted (docstatus = 1)
		self.assertEqual(frappe.db.get_value("Sales Order", new_so_ref, "docstatus"), 1)
		
		# 4. Uji Pembuatan Consolidated Invoice
		invoice_name = make_consolidated_invoice(co.name)
		self.assertTrue(invoice_name)
		
		invoice_doc = frappe.get_doc("Sales Invoice", invoice_name)
		self.assertEqual(invoice_doc.docstatus, 0) # Berstatus draft
		self.assertEqual(invoice_doc.custom_catering_order_ref, co.name)
		
		# 5. Uji Today's Delivery Note
		# Kita paksa salah satu tanggal baris katering menjadi hari ini agar terdeteksi
		co.schedule_items[0].date = today()
		co.schedule_items[1].date = today()
		co.save(ignore_permissions=True)
		
		# Jalankan proses pengiriman hari ini
		dns = process_today_delivery(co.name)
		self.assertTrue(len(dns) > 0)
		
		dn_doc = frappe.get_doc("Delivery Note", dns[0])
		self.assertEqual(dn_doc.docstatus, 0) # Berstatus draft
		self.assertEqual(dn_doc.custom_catering_order_ref, co.name)
		
		# Bersihkan dokumen-dokumen yang dibuat dalam test secara aman
		frappe.db.sql("delete from `tabSales Invoice Item` where parent in (select name from `tabSales Invoice` where custom_catering_order_ref = %s)", co.name)
		frappe.db.sql("delete from `tabSales Invoice` where custom_catering_order_ref = %s", co.name)
		
		frappe.db.sql("delete from `tabDelivery Note Item` where parent in (select name from `tabDelivery Note` where custom_catering_order_ref = %s)", co.name)
		frappe.db.sql("delete from `tabDelivery Note` where custom_catering_order_ref = %s", co.name)
		
		frappe.db.sql("delete from `tabSales Order Item` where parent in (select name from `tabSales Order` where custom_catering_order_ref = %s)", co.name)
		frappe.db.sql("delete from `tabSales Order` where custom_catering_order_ref = %s", co.name)
		
		co.cancel()
		co.delete()
