# Copyright (c) 2026, WildanYR and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt
from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt, make_purchase_invoice

@frappe.whitelist()
def get_items_from_material_request(material_request):
    """
    Mengambil daftar item dari Material Request yang bertipe 'Purchase' 
    dan masih memiliki kuantitas tersisa yang belum dipesan.
    """
    items = frappe.db.get_all(
        "Material Request Item",
        filters={
            "parent": material_request,
            "docstatus": 1
        },
        fields=["name", "item_code", "qty", "ordered_qty", "warehouse"]
    )
    
    pending_items = []
    for d in items:
        pending_qty = flt(d.qty) - flt(d.ordered_qty)
        if pending_qty > 0:
            pending_items.append({
                "item_code": d.item_code,
                "qty": pending_qty,
                "warehouse": d.warehouse,
                "material_request_item": d.name
            })
            
    return pending_items


class QuickPurchase(Document):
    def validate(self):
        self.validate_items()
        
    def validate_items(self):
        if not self.items_bought:
            frappe.throw(_("Tabel Items Bought tidak boleh kosong."))
            
        for row in self.items_bought:
            if not row.item_code:
                frappe.throw(_("Item Code wajib diisi pada setiap baris."))
            if flt(row.qty) <= 0:
                frappe.throw(_("Kuantitas (Qty) untuk item {0} harus lebih dari 0.").format(row.item_code))
            if flt(row.rate) < 0:
                frappe.throw(_("Harga satuan (Rate) untuk item {0} tidak boleh negatif.").format(row.item_code))
                
    def on_submit(self):
        # 1. Kelompokkan item berdasarkan Supplier
        grouped_items = {}
        for row in self.items_bought:
            grouped_items.setdefault(row.supplier, []).append(row)
            
        # 2. Iterasi untuk setiap Supplier dan buat dokumen terkait
        for supplier, rows in grouped_items.items():
            # A. Buat Purchase Order (PO)
            po = frappe.new_doc("Purchase Order")
            po.supplier = supplier
            po.company = self.company
            po.transaction_date = self.posting_date
            po.schedule_date = self.posting_date
            
            for row in rows:
                po.append("items", {
                    "item_code": row.item_code,
                    "qty": row.qty,
                    "rate": row.rate,
                    "warehouse": row.warehouse or self.warehouse,
                    "schedule_date": self.posting_date,
                    "material_request": self.material_request,
                    "material_request_item": row.material_request_item
                })
                
            # Set values default & currencies dari supplier/company
            po.set_missing_values()
            
            # BYPASS: Matikan validasi kuantitas berlebih terhadap Material Request
            for updater in po.status_updater:
                if updater.get("target_dt") == "Material Request Item":
                    updater["validate_qty"] = False
                    
            po.insert()
            po.submit()
            
            # Catat referensi PO
            ref_po = self.append("references", {
                "reference_doctype": "Purchase Order",
                "reference_name": po.name
            })
            ref_po.db_insert()
            
            # B. Buat Purchase Receipt (PR) - Auto-Receipt
            pr = make_purchase_receipt(po.name)
            pr.posting_date = self.posting_date
            # Sinkronkan posting date/time
            pr.set_missing_values()
            pr.insert()
            pr.submit()
            
            # Catat referensi PR
            ref_pr = self.append("references", {
                "reference_doctype": "Purchase Receipt",
                "reference_name": pr.name
            })
            ref_pr.db_insert()
            
            # C. Buat Purchase Invoice (PI) - Auto-Payment
            pi = make_purchase_invoice(po.name)
            pi.posting_date = self.posting_date
            pi.is_paid = 1
            pi.mode_of_payment = self.mode_of_payment
            pi.cash_bank_account = self.payment_account
            
            pi.set_missing_values()
            pi.insert()
            pi.submit()
            
            # Catat referensi PI
            ref_pi = self.append("references", {
                "reference_doctype": "Purchase Invoice",
                "reference_name": pi.name
            })
            ref_pi.db_insert()
            
    def on_cancel(self):
        # Ambil referensi dokumen yang terhubung
        invoices = []
        receipts = []
        orders = []
        
        for ref in self.references:
            if ref.reference_doctype == "Purchase Invoice":
                invoices.append(ref.reference_name)
            elif ref.reference_doctype == "Purchase Receipt":
                receipts.append(ref.reference_name)
            elif ref.reference_doctype == "Purchase Order":
                orders.append(ref.reference_name)
                
        # Batalkan secara berurutan terbalik (PI -> PR -> PO)
        # 1. Batalkan Purchase Invoices
        for inv in invoices:
            if frappe.db.exists("Purchase Invoice", inv):
                doc = frappe.get_doc("Purchase Invoice", inv)
                if doc.docstatus == 1:
                    doc.cancel()
                    
        # 2. Batalkan Purchase Receipts
        for rec in receipts:
            if frappe.db.exists("Purchase Receipt", rec):
                doc = frappe.get_doc("Purchase Receipt", rec)
                if doc.docstatus == 1:
                    doc.cancel()
                    
        # 3. Batalkan Purchase Orders
        for ord in orders:
            if frappe.db.exists("Purchase Order", ord):
                doc = frappe.get_doc("Purchase Order", ord)
                if doc.docstatus == 1:
                    doc.cancel()
                    
        # Bersihkan tabel referensi
        self.set("references", [])
        frappe.db.delete("Quick Purchase Reference", {"parent": self.name})
