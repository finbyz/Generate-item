__version__ = "0.0.1"


from erpnext.stock.report.stock_balance import stock_balance
from generate_item.override_report.stock_balance import custom_execute as custom_stock_balance_execute

stock_balance.execute = custom_stock_balance_execute