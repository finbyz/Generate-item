import frappe

PATTERN_SET_TRANSFER_SE_TYPE = "Pattern Set Transfer"


def execute():
	if frappe.db.exists("Stock Entry Type", PATTERN_SET_TRANSFER_SE_TYPE):
		return

	frappe.get_doc(
		{
			"doctype": "Stock Entry Type",
			"name": PATTERN_SET_TRANSFER_SE_TYPE,
			"purpose": "Material Transfer",
			"is_standard": 0,
			"add_to_transit": 0,
		}
	).insert(ignore_permissions=True)
