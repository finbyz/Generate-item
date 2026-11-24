__version__ = "0.0.1"


from erpnext.stock.report.stock_balance import stock_balance
from generate_item.override_report.stock_balance import custom_execute as custom_stock_balance_execute

stock_balance.execute = custom_stock_balance_execute

# ERPNext restricts pricing rule calls to an allow-list of doctypes. Proforma Invoice uses the
# selling controller and calls the pricing engine, so it must be on that list.
from erpnext.accounts.doctype.pricing_rule import pricing_rule as _pricing_rule

if hasattr(_pricing_rule, "PRICING_TRANSACTION_DOCTYPES"):
	_pricing_rule.PRICING_TRANSACTION_DOCTYPES = frozenset(
		set(_pricing_rule.PRICING_TRANSACTION_DOCTYPES) | {"Proforma Invoice"}
	)
