import frappe

from frappe.query_builder import Case
from frappe.query_builder.functions import Sum

# @frappe.whitelist()
# def get_on_time_received_qty(scorecard):
#     return 1



def get_on_time_received_qty(scorecard):
	"""Returns the total received qty where posting_date <= schedule_date (on-time)"""

	pr = frappe.qb.DocType("Purchase Receipt")
	pri = frappe.qb.DocType("Purchase Receipt Item")

	on_time_case = Case().when(pr.posting_date <= pri.schedule_date, pri.received_qty).else_(0)

	return (
		frappe.qb.from_(pr)
		.inner_join(pri)
		.on(pri.parent == pr.name)
		.select(Sum(on_time_case))
		.where(
			(pr.supplier == scorecard.supplier)
			& (pr.docstatus == 1)
			& (pr.posting_date >= scorecard.get("start_date"))
			& (pr.posting_date <= scorecard.get("end_date"))
		)
	).run(as_list=True)[0][0] or 0