import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
	custom_fields = {
		"Sales Order": [
			{
				"fieldname": "custom_catering_order_ref",
				"fieldtype": "Link",
				"label": "Catering Order Ref",
				"options": "Catering Order",
				"read_only": 1,
				"insert_after": "customer"
			}
		],
		"Sales Invoice": [
			{
				"fieldname": "custom_catering_order_ref",
				"fieldtype": "Link",
				"label": "Catering Order Ref",
				"options": "Catering Order",
				"read_only": 1,
				"insert_after": "customer"
			}
		],
		"Delivery Note": [
			{
				"fieldname": "custom_catering_order_ref",
				"fieldtype": "Link",
				"label": "Catering Order Ref",
				"options": "Catering Order",
				"read_only": 1,
				"insert_after": "customer"
			}
		]
	}
	create_custom_fields(custom_fields, update=True)
