# Copyright (c) 2026, WildanYR and contributors
# For license information, please see license.txt

from frappe import _

def get_data():
    return {
        "fieldname": "reference_name",
        "internal_links": {
            "Purchase Order": ["references", "reference_name"],
            "Purchase Receipt": ["references", "reference_name"],
            "Purchase Invoice": ["references", "reference_name"]
        },
        "transactions": [
            {
                "label": _("Buying Documents"),
                "items": ["Purchase Order", "Purchase Receipt", "Purchase Invoice"]
            }
        ]
    }
