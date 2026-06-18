# Copyright (c) 2026, WildanYR and contributors
# For license information, please see license.txt

import frappe
import json
import datetime
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, today, cint

def get_item_warehouse(item_code, company):
	warehouse = frappe.db.get_value("Item Default", {"parent": item_code, "company": company}, "default_warehouse")
	if not warehouse:
		warehouse = frappe.db.get_value("Item Reorder", {"parent": item_code}, "warehouse")
	if not warehouse:
		warehouse = frappe.db.get_value("Warehouse", {"company": company, "is_group": 0}, "name")
	return warehouse


class CateringOrder(Document):
	def validate(self):
		self.validate_dates()
		self.validate_categories()

	def validate_dates(self):
		if getdate(self.start_date) > getdate(self.end_date):
			frappe.throw(_("Start Date tidak boleh lebih besar dari End Date."))

	def validate_categories(self):
		if not self.categories:
			frappe.throw(_("Harap pilih setidaknya satu Meal Category."))

	def on_submit(self):
		# Ubah status menjadi Generating Sales Orders
		self.db_set("status", "Generating Sales Orders")
		
		# Jalankan background job untuk membuat Sales Orders
		frappe.enqueue(
			"akgp_extensions.akgp_extensions.doctype.catering_order.catering_order.create_sales_orders_job",
			catering_order_name=self.name,
			queue="default"
		)

	def on_update_after_submit(self):
		# Tangani perubahan menu harian secara otomatis
		self.handle_menu_changes()

	def handle_menu_changes(self):
		prev_doc = self.get_doc_before_save()
		if not prev_doc:
			return

		# Map previous items by (date, meal_category) -> item_code, sales_order_ref, delivery_status
		prev_map = {}
		for row in prev_doc.schedule_items:
			prev_map[(str(row.date), row.meal_category)] = (row.item_code, row.sales_order_ref, row.delivery_status)

		# Kelompokkan Sales Order yang harus di-amend berdasarkan ref lama
		so_to_recreate = set()

		for row in self.schedule_items:
			key = (str(row.date), row.meal_category)
			if key in prev_map:
				old_item_code, old_so, old_delivery_status = prev_map[key]
				if row.item_code != old_item_code:
					# Validasi: Jika sudah dikirim, tidak boleh diubah
					if old_delivery_status == "Dispatched" or row.delivery_status == "Dispatched":
						frappe.throw(
							_("Baris jadwal untuk tanggal {0} ({1}) tidak bisa diubah karena sudah dikirim (Dispatched).").format(
								row.date, row.meal_category
							)
						)
					if old_so:
						so_to_recreate.add(old_so)

		# Proses re-create / amend Sales Orders
		for old_so in so_to_recreate:
			# Dapatkan informasi tanggal dari SO lama
			so_doc = frappe.get_doc("Sales Order", old_so)
			delivery_date_str = str(so_doc.delivery_date)

			# Clear database reference to avoid LinkExistsError during cancel
			frappe.db.sql("""
				update `tabCatering Order Item`
				set sales_order_ref = NULL
				where parent = %s and sales_order_ref = %s
			""", (self.name, old_so))

			for item in self.schedule_items:
				if item.sales_order_ref == old_so:
					item.sales_order_ref = None

			# Batalkan SO lama
			if so_doc.docstatus == 1:
				so_doc.cancel()

			# Buat SO baru berisi semua item dari schedule_items saat ini untuk tanggal tersebut
			new_so = frappe.new_doc("Sales Order")
			new_so.customer = self.customer
			new_so.company = self.company
			new_so.delivery_date = so_doc.delivery_date
			new_so.transaction_date = today()
			new_so.custom_catering_order_ref = self.name
			new_so.amended_from = so_doc.name

			company_currency = frappe.db.get_value("Company", self.company, "default_currency") or "IDR"
			new_so.selling_price_list = "Standard Selling"
			new_so.price_list_currency = company_currency
			new_so.plc_conversion_rate = 1.0
			new_so.conversion_rate = 1.0
			new_so.currency = company_currency

			# Cari semua baris menu untuk tanggal ini di schedule_items saat ini
			items_for_date = [r for r in self.schedule_items if str(r.date) == delivery_date_str]
			for item in items_for_date:
				new_so.append("items", {
					"item_code": item.item_code,
					"qty": 1,
					"warehouse": get_item_warehouse(item.item_code, self.company)
				})

			new_so.set_missing_values()
			new_so.run_method("calculate_taxes_and_totals")
			new_so.insert(ignore_permissions=True)
			new_so.submit()

			# Perbarui referensi sales_order_ref pada baris schedule katering terkait
			for item in items_for_date:
				item.sales_order_ref = new_so.name
				item.db_set("sales_order_ref", new_so.name)


@frappe.whitelist()
def get_schedule_items(menu_template, start_date, end_date, categories, skip_sundays):
	start = getdate(start_date)
	end = getdate(end_date)

	if isinstance(categories, str):
		categories = json.loads(categories)

	skip_sundays = cint(skip_sundays)

	# Ambil semua data menu harian dari template
	template_items = frappe.get_all(
		"Catering Menu Template Item",
		filters={"parent": menu_template},
		fields=["day_of_month", "meal_category", "item_code"]
	)

	# Group template items by (day_of_month, meal_category)
	template_map = {}
	for item in template_items:
		template_map[(int(item.day_of_month), item.meal_category)] = item.item_code

	schedule = []
	current_date = start
	while current_date <= end:
		# Lewati Hari Minggu jika dikonfigurasi
		if skip_sundays and current_date.weekday() == 6:  # 6 = Sunday
			current_date += datetime.timedelta(days=1)
			continue

		day_num = current_date.day

		# Ambil menu untuk masing-masing kategori meal
		for cat in categories:
			item_code = template_map.get((day_num, cat))
			if item_code:
				schedule.append({
					"date": current_date.strftime("%Y-%m-%d"),
					"meal_category": cat,
					"item_code": item_code
				})

		current_date += datetime.timedelta(days=1)

	return schedule


def create_sales_orders_job(catering_order_name):
	"""
	Background Job untuk menggenerasi Sales Orders massal berdasarkan tanggal.
	Menggabungkan semua menu di hari yang sama ke dalam 1 Sales Order.
	"""
	try:
		doc = frappe.get_doc("Catering Order", catering_order_name)
		
		# Kelompokkan baris jadwal berdasarkan Tanggal
		grouped_by_date = {}
		for row in doc.schedule_items:
			if not row.sales_order_ref:
				grouped_by_date.setdefault(str(row.date), []).append(row)

		# Buat Sales Order untuk setiap tanggal
		for date_str, rows in grouped_by_date.items():
			so = frappe.new_doc("Sales Order")
			so.customer = doc.customer
			so.company = doc.company
			so.delivery_date = getdate(date_str)
			so.transaction_date = today()
			so.custom_catering_order_ref = doc.name

			company_currency = frappe.db.get_value("Company", doc.company, "default_currency") or "IDR"
			so.selling_price_list = "Standard Selling"
			so.price_list_currency = company_currency
			so.plc_conversion_rate = 1.0
			so.conversion_rate = 1.0
			so.currency = company_currency

			for row in rows:
				so.append("items", {
					"item_code": row.item_code,
					"qty": 1,
					"warehouse": get_item_warehouse(row.item_code, doc.company)
				})

			so.set_missing_values()
			so.run_method("calculate_taxes_and_totals")
			so.insert(ignore_permissions=True)
			so.submit()

			# Tulis balik nomor SO ke baris schedule terkait
			for row in rows:
				row.sales_order_ref = so.name
				row.db_set("sales_order_ref", so.name)

		# Setelah selesai, set status Catering Order menjadi Active
		doc.db_set("status", "Active")
		
		# Catat log sukses di timeline dokumen
		doc.add_comment("Comment", _("Generasi Sales Orders massal di background selesai dengan sukses."))
		
	except Exception as e:
		# Jika gagal, kembalikan status ke Draft agar user bisa men-submit ulang atau memeriksa kendala
		frappe.db.set_value("Catering Order", catering_order_name, "status", "Draft")
		log_msg = _("Gagal menggenerasi Sales Orders di background: {0}").format(str(e))
		frappe.log_error(log_msg, "Catering Order Background Job Error")
		
		# Catat warning di timeline dokumen
		try:
			doc = frappe.get_doc("Catering Order", catering_order_name)
			doc.add_comment("Comment", f"⚠️ {log_msg}")
		except Exception:
			pass


@frappe.whitelist()
def make_consolidated_invoice(catering_order_name):
	"""
	Menggabungkan seluruh Sales Order katering yang belum ditagih ke dalam 1 Sales Invoice baru.
	"""
	doc = frappe.get_doc("Catering Order", catering_order_name)
	sales_orders = list(set([item.sales_order_ref for item in doc.schedule_items if item.sales_order_ref]))

	if not sales_orders:
		frappe.throw(_("Tidak ada Sales Order yang terhubung untuk dibuatkan invoice."))

	from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice

	invoice = None
	for so_name in sales_orders:
		so_status, billing_status = frappe.db.get_value("Sales Order", so_name, ["docstatus", "billing_status"])
		
		# Pastikan SO sudah disubmit dan belum ditagih penuh
		if so_status == 1 and billing_status != "Fully Billed":
			invoice = make_sales_invoice(so_name, invoice, ignore_permissions=True)

	if not invoice:
		frappe.throw(_("Seluruh pesanan sudah ditagih penuh (Fully Billed) atau tidak ada SO aktif."))

	invoice.custom_catering_order_ref = catering_order_name
	invoice.set_missing_values()
	invoice.run_method("calculate_taxes_and_totals")
	invoice.insert(ignore_permissions=True)

	return invoice.name


@frappe.whitelist()
def process_today_delivery(catering_order_name):
	"""
	Mencari jadwal pengantaran katering hari ini yang belum dikirim,
	lalu menggenerasi draft Delivery Note secara otomatis.
	"""
	doc = frappe.get_doc("Catering Order", catering_order_name)
	today_date_str = today()

	# Filter baris schedule untuk hari ini yang belum dikirim
	today_items = [
		item for item in doc.schedule_items
		if str(item.date) == today_date_str and item.delivery_status == "Not Dispatched"
	]

	if not today_items:
		return []

	from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note

	delivery_notes = []
	sales_orders = list(set([item.sales_order_ref for item in today_items if item.sales_order_ref]))

	for so_name in sales_orders:
		# Cek apakah sudah ada Delivery Note Draft untuk Sales Order ini yang terikat ke Catering Order ini
		existing_dn = frappe.db.get_value(
			"Delivery Note Item",
			{
				"against_sales_order": so_name,
				"docstatus": 0
			},
			"parent"
		)
		
		if existing_dn:
			# Jika ada, pastikan custom_catering_order_ref cocok
			ref = frappe.db.get_value("Delivery Note", existing_dn, "custom_catering_order_ref")
			if ref == catering_order_name:
				if existing_dn not in delivery_notes:
					delivery_notes.append(existing_dn)
				continue

		# Buat Delivery Note baru dalam status Draft
		frappe.flags.ignore_permissions = True
		try:
			dn = make_delivery_note(so_name)
		finally:
			frappe.flags.ignore_permissions = False
		dn.custom_catering_order_ref = catering_order_name
		dn.insert(ignore_permissions=True)
		delivery_notes.append(dn.name)

	return delivery_notes


def on_invoice_update(doc, method=None):
	"""Dipicu saat Sales Invoice di-submit, di-cancel, atau di-update."""
	if doc.custom_catering_order_ref:
		sync_catering_order_finance(doc.custom_catering_order_ref)


def on_payment_update(doc, method=None):
	"""Dipicu saat Payment Entry di-submit atau di-cancel."""
	for reference in doc.get("references", []):
		if reference.reference_doctype == "Sales Invoice":
			catering_ref = frappe.db.get_value("Sales Invoice", reference.reference_name, "custom_catering_order_ref")
			if catering_ref:
				sync_catering_order_finance(catering_ref)


def on_delivery_note_submit(doc, method=None):
	"""Dipicu saat Delivery Note di-submit."""
	if doc.custom_catering_order_ref:
		for item in doc.get("items", []):
			if item.against_sales_order:
				frappe.db.sql("""
					update `tabCatering Order Item`
					set delivery_status = 'Dispatched'
					where parent = %s and sales_order_ref = %s and item_code = %s
				""", (doc.custom_catering_order_ref, item.against_sales_order, item.item_code))
		
		check_and_update_catering_order_completion(doc.custom_catering_order_ref)


def on_delivery_note_cancel(doc, method=None):
	"""Dipicu saat Delivery Note di-cancel."""
	if doc.custom_catering_order_ref:
		for item in doc.get("items", []):
			if item.against_sales_order:
				frappe.db.sql("""
					update `tabCatering Order Item`
					set delivery_status = 'Not Dispatched'
					where parent = %s and sales_order_ref = %s and item_code = %s
				""", (doc.custom_catering_order_ref, item.against_sales_order, item.item_code))
		
		check_and_update_catering_order_completion(doc.custom_catering_order_ref)


def sync_catering_order_finance(catering_order_name):
	"""Menghitung ulang total tagihan, total bayar, dan status pembayaran di Catering Order."""
	if not catering_order_name:
		return

	# Ambil semua sales invoice tersubmit yang terikat ke katering order
	invoices = frappe.get_all(
		"Sales Invoice",
		filters={
			"custom_catering_order_ref": catering_order_name,
			"docstatus": 1
		},
		fields=["grand_total", "outstanding_amount"]
	)

	total_billed = sum([inv.grand_total for inv in invoices])
	total_paid = sum([inv.grand_total - inv.outstanding_amount for inv in invoices])

	if total_billed == 0:
		payment_status = "Unpaid"
	elif total_paid >= total_billed:
		payment_status = "Fully Paid"
	elif total_paid > 0:
		payment_status = "Partially Paid"
	else:
		payment_status = "Unpaid"

	frappe.db.set_value(
		"Catering Order",
		catering_order_name,
		{
			"total_billed": total_billed,
			"total_paid": total_paid,
			"payment_status": payment_status
		},
		update_modified=False
	)


def check_and_update_catering_order_completion(catering_order_name):
	"""Memeriksa status katering order, jika semua makanan sudah dikirim maka diselesaikan."""
	if not catering_order_name:
		return

	items = frappe.get_all(
		"Catering Order Item",
		filters={"parent": catering_order_name},
		fields=["delivery_status"]
	)

	if items and all([item.delivery_status == "Dispatched" for item in items]):
		frappe.db.set_value("Catering Order", catering_order_name, "status", "Completed")
	else:
		current_status = frappe.db.get_value("Catering Order", catering_order_name, "status")
		if current_status == "Completed":
			frappe.db.set_value("Catering Order", catering_order_name, "status", "Active")

