# generate_item/utils/supplier_scorecard.py
import importlib

def import_file(doc, method=None):
    """
    Forces generate_item.api.supplier_scorecard into sys.modules
    before Frappe's import_string_path (called from validate_path_exists)
    tries to resolve the Path field on this Supplier Scorecard Variable.
    Works around erpnext#46852.
    """
    importlib.import_module("generate_item.api.supplier_scorecard")