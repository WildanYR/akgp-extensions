# Copyright (c) 2026, WildanYR and Contributors
# See license.txt

import sys
import frappe
from importlib import reload
from frappe.modules import load_doctype_module

# Increase recursion limit just in case
sys.setrecursionlimit(4000)

# Monkeypatch frappe.get_meta to gracefully handle the missing Payment Gateway DocType in testing
if not hasattr(frappe, "_orig_get_meta"):
    frappe._orig_get_meta = frappe.get_meta

def patched_get_meta(doctype):
    # Directly mock the deleted Payment Gateway DocType to avoid database queries during dependency traversal
    if doctype == "Payment Gateway":
        class MockMeta:
            def get_link_fields(self): return []
            def get_table_fields(self): return []
            def get(self, key, filters=None): return []
            issingle = 0
            is_virtual = 0
            istable = 0
            name = doctype
            autoname = ""
        return MockMeta()
    return frappe._orig_get_meta(doctype)

frappe.get_meta = patched_get_meta

# Replace get_modules and load_test_records_for in the test generator to bypass the missing Payment Gateway DocType cleanly
try:
    import frappe.tests.utils.generators as generators

    if not hasattr(generators, "_orig_get_modules"):
        generators._orig_get_modules = generators.get_modules

    def patched_get_modules(doctype):
        if doctype == "Payment Gateway":
            return None, None
        return generators._orig_get_modules(doctype)

    generators.get_modules = patched_get_modules

    if not hasattr(generators, "_orig_load_test_records_for"):
        generators._orig_load_test_records_for = generators.load_test_records_for

    def patched_load_test_records_for(index_doctype):
        if index_doctype == "Payment Gateway":
            return {}
        return generators._orig_load_test_records_for(index_doctype)

    generators.load_test_records_for = patched_load_test_records_for
except Exception:
    pass

# Clean up existing test Price Lists to prevent ERPNext's bootstrapping duplicate key error
if frappe.flags.in_test:
    try:
        frappe.db.delete("Price List", {"name": "Standard Buying"})
        frappe.db.delete("Price List", {"name": "Standard Selling"})
        frappe.db.commit()
    except Exception:
        pass

from frappe.tests.utils import FrappeTestCase

class TestQuickPurchase(FrappeTestCase):
    def setUp(self):
        # Setup basic data for testing locally
        self.company = "_Test Company QP"
        self.supplier = "_Test Supplier QP"
        self.item_code = "_Test Item Quick Purchase"
        self.warehouse = "_Test Warehouse QP - _TCQP"
        self.mode_of_payment = "Cash QP"
        self.payment_account = "Cash QP Account - _TCQP"
        
        # 1. Ensure Company exists
        if not frappe.db.exists("Company", self.company):
            comp = frappe.new_doc("Company")
            comp.company_name = self.company
            comp.default_currency = "IDR"
            comp.insert(ignore_permissions=True)
            
        # 2. Ensure Supplier Group and Supplier exist
        supplier_group = "_Test Supplier Group QP"
        if not frappe.db.exists("Supplier Group", supplier_group):
            sg = frappe.new_doc("Supplier Group")
            sg.supplier_group_name = supplier_group
            sg.insert(ignore_permissions=True)
            
        if not frappe.db.exists("Supplier", self.supplier):
            sup = frappe.new_doc("Supplier")
            sup.supplier_name = self.supplier
            sup.supplier_group = supplier_group
            sup.insert(ignore_permissions=True)
            
        # 3. Ensure Item Group and Item exist
        item_group = "_Test Item Group QP"
        if not frappe.db.exists("Item Group", item_group):
            ig = frappe.new_doc("Item Group")
            ig.item_group_name = item_group
            ig.parent_item_group = "All Item Groups"
            ig.insert(ignore_permissions=True)
            
        if not frappe.db.exists("Item", self.item_code):
            item = frappe.new_doc("Item")
            item.item_code = self.item_code
            item.item_name = self.item_code
            item.item_group = item_group
            item.stock_uom = "Nos"
            item.is_stock_item = 1
            item.insert(ignore_permissions=True)
            
        # 4. Ensure Warehouse exists
        wh_name = frappe.db.get_value("Warehouse", {"warehouse_name": "_Test Warehouse QP", "company": self.company})
        if not wh_name:
            wh = frappe.new_doc("Warehouse")
            wh.warehouse_name = "_Test Warehouse QP"
            wh.company = self.company
            wh.insert(ignore_permissions=True)
            self.warehouse = wh.name
        else:
            self.warehouse = wh_name
            
        # 5. Ensure Cash Account exists for Payment Account
        parent_account = frappe.db.get_value("Account", {"company": self.company, "is_group": 1}, "name")
        acc_name = frappe.db.get_value("Account", {"account_name": "Cash QP Account", "company": self.company})
        if not acc_name:
            acc = frappe.new_doc("Account")
            acc.account_name = "Cash QP Account"
            acc.parent_account = parent_account
            acc.company = self.company
            acc.account_type = "Cash"
            acc.insert(ignore_permissions=True)
            self.payment_account = acc.name
        else:
            self.payment_account = acc_name
            
        # 6. Ensure Mode of Payment exists
        if not frappe.db.exists("Mode of Payment", self.mode_of_payment):
            mop = frappe.new_doc("Mode of Payment")
            mop.mode_of_payment = self.mode_of_payment
            mop.type = "Cash"
            mop.append("accounts", {
                "company": self.company,
                "default_account": self.payment_account
            })
            mop.insert(ignore_permissions=True)
            
    def test_independent_quick_purchase(self):
        """Skenario 1: Pembelian Independen (tanpa MR) -> Pastikan PO, PR, dan PI terbuat & ter-submit, PI berstatus Paid."""
        qp = frappe.new_doc("Quick Purchase")
        qp.company = self.company
        qp.posting_date = frappe.utils.today()
        qp.warehouse = self.warehouse
        qp.payment_account = self.payment_account
        qp.mode_of_payment = self.mode_of_payment
        
        qp.append("items_bought", {
            "item_code": self.item_code,
            "qty": 5,
            "rate": 150,
            "warehouse": self.warehouse,
            "supplier": self.supplier
        })
        
        qp.insert()
        qp.submit()
        
        # Cek apakah references terisi
        self.assertEqual(len(qp.references), 3)
        
        ref_docs = {r.reference_doctype: r.reference_name for r in qp.references}
        self.assertIn("Purchase Order", ref_docs)
        self.assertIn("Purchase Receipt", ref_docs)
        self.assertIn("Purchase Invoice", ref_docs)
        
        # Cek status dokumen turunan
        po = frappe.get_doc("Purchase Order", ref_docs["Purchase Order"])
        pr = frappe.get_doc("Purchase Receipt", ref_docs["Purchase Receipt"])
        pi = frappe.get_doc("Purchase Invoice", ref_docs["Purchase Invoice"])
        
        self.assertEqual(po.docstatus, 1)
        self.assertEqual(pr.docstatus, 1)
        self.assertEqual(pi.docstatus, 1)
        self.assertEqual(pi.is_paid, 1)
        
        # Uji Skenario 3: Pembatalan -> Pastikan PI, PR, dan PO ikut dibatalkan (docstatus = 2)
        qp.cancel()
        
        po.reload()
        pr.reload()
        pi.reload()
        
        self.assertEqual(po.docstatus, 2)
        self.assertEqual(pr.docstatus, 2)
        self.assertEqual(pi.docstatus, 2)
        
    def test_quick_purchase_with_material_request(self):
        """Skenario 2: Pembelian Berdasarkan MR -> Pastikan status MR terupdate dan dokumen ter-link secara benar."""
        # Buat Material Request terlebih dahulu
        mr = frappe.new_doc("Material Request")
        mr.company = self.company
        mr.transaction_date = frappe.utils.today()
        mr.material_request_type = "Purchase"
        mr.append("items", {
            "item_code": self.item_code,
            "qty": 10,
            "uom": "Nos",
            "warehouse": self.warehouse,
            "schedule_date": frappe.utils.add_days(frappe.utils.today(), 1)
        })
        mr.insert()
        mr.submit()
        
        # Buat Quick Purchase terhubung ke MR
        qp = frappe.new_doc("Quick Purchase")
        qp.company = self.company
        qp.posting_date = frappe.utils.today()
        qp.warehouse = self.warehouse
        qp.payment_account = self.payment_account
        qp.mode_of_payment = self.mode_of_payment
        qp.material_request = mr.name
        
        # Tarik item dari MR (sama dengan logika JS di backend)
        from akgp_extensions.akgp_extensions.doctype.quick_purchase.quick_purchase import get_items_from_material_request
        items = get_items_from_material_request(mr.name)
        self.assertEqual(len(items), 1)
        
        qp.append("items_bought", {
            "item_code": items[0]["item_code"],
            "qty": items[0]["qty"] + 2, # Uji support over-ordering (MR = 10, QP = 12)
            "rate": 120,
            "warehouse": items[0]["warehouse"],
            "supplier": self.supplier,
            "material_request_item": items[0]["material_request_item"]
        })
        
        qp.insert()
        qp.submit()
        
        # Cek apakah MR ter-link
        ref_docs = {r.reference_doctype: r.reference_name for r in qp.references}
        po = frappe.get_doc("Purchase Order", ref_docs["Purchase Order"])
        self.assertEqual(po.items[0].material_request, mr.name)
        
        # Cek apakah status MR terupdate
        mr.reload()
        self.assertEqual(mr.per_ordered, 100) # Capped di 100% meskipun over-ordered
