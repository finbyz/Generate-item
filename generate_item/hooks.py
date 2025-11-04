app_name = "generate_item"
app_title = "Generate Item"
app_publisher = "Finbyz"
app_description = "Item"
app_email = "info@finbyz.tech"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "generate_item",
# 		"logo": "/assets/generate_item/logo.png",
# 		"title": "Generate Item",
# 		"route": "/generate_item",
# 		"has_permission": "generate_item.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# Export/import fixtures for this app
# fixtures = [
#     {"doctype": "Custom Field", "filters": [["module", "=", "Generate Item"]]},
#     {"doctype": "Property Setter", "filters": [["module", "=", "Generate Item"]]},
# ]

# include js, css files in header of desk.html
# app_include_css = "/assets/generate_item/css/generate_item.css"
# app_include_js = "/assets/generate_item/js/generate_item.js"

# include js, css files in header of web template
# web_include_css = "/assets/generate_item/css/generate_item.css"
# web_include_js = "/assets/generate_item/js/generate_item.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "generate_item/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {"Item" : "public/js/item.js",
              "Sales Order" : "public/js/sales_order.js",
              "BOM" : "public/js/bom.js",
              "BOM Creator" : "public/js/bom_creator.js",
              "Material Request" : "public/js/material_request.js",
              "Purchase Receipt" : "public/js/purchase_receipt.js",
              "Production Plan" : "public/js/production_plan.js",
              "Purchase Order" : "public/js/purchase_order.js",
              "Stock Entry" : "public/js/stock_entry.js",
              "Subcontracting Order" : "public/js/subcontracting_order.js",
              "Delivery Note" : "public/js/delivery_note.js",
              "Sales Invoice" : "public/js/sales_invoice.js",
              "Quality Inspection" : "public/js/quality_inspection.js",
              "Work Order" : "public/js/work_order.js",
              }

doctype_list_js = {"Item Generator" : "public/js/item_generator_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "generate_item/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "generate_item.utils.jinja_methods",
# 	"filters": "generate_item.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "generate_item.install.before_install"
# after_install = "generate_item.install.after_install"


# Uninstallation
# ------------

# before_uninstall = "generate_item.uninstall.before_uninstall"
# after_uninstall = "generate_item.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "generate_item.utils.before_app_install"
# after_app_install = "generate_item.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "generate_item.utils.before_app_uninstall"
# after_app_uninstall = "generate_item.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "generate_item.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }
override_doctype_class = {
    "BOM": "generate_item.overrides.custombom.CustomBOM",
    "Production Plan": "generate_item.overrides.production_plan.ProductionPlan",
    "BOM Creator": "generate_item.overrides.custom_bom_creator.BOMCreator",
    "Work Order": "generate_item.overrides.customWorkorder.WorkOrder",
    "Sales Order": "generate_item.overrides.custom_sales_order.CustomSalesOrder",
    # "Purchase Receipt": "generate_item.overrides.purchase_receipt.PurchaseReceipt",
}


# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
    "Purchase Order": {
        "before_insert": "generate_item.utils.purchase_order.before_insert",
        "validate": "generate_item.utils.purchase_order.validate",
        "before_save": "generate_item.utils.purchase_order.before_save"
    },
    "Batch":{
        "before_save":"generate_item.utils.batch.before_save",
    },
    "Purchase Receipt": {
        "before_save": "generate_item.utils.purchase_receipt.before_save",
        "validate": "generate_item.utils.purchase_receipt.validate",
    },  
    "Stock Entry": {
        "before_insert": "generate_item.utils.stock_entry.before_insert"
    },
    "Sales Order": {
        "before_save": "generate_item.utils.sales_order.before_save"
    },
    "Subcontracting Order": {
        "before_insert": "generate_item.utils.subcontracting_order.before_insert",
        "validate": "generate_item.utils.subcontracting_order.validate",
        "before_save": "generate_item.utils.subcontracting_order.before_save",
        "after_save": "generate_item.utils.subcontracting_order.after_save"
    },
    "Material Request":{
        "before_insert": "generate_item.utils.material_request.before_insert",
        "validate":"generate_item.utils.material_request.validate"
    },
    "Sales Invoice": {
        "after_insert": "generate_item.utils.sales_invoice.after_insert",
        "validate": "generate_item.utils.sales_invoice.validate",
    },
    "Production Plan":{
        "before_save": "generate_item.utils.production_plan.before_save"
    },
    "Work Order":{
        "before_insert": "generate_item.utils.work_order.before_insert",
    },
    "Delivery Note": {
        "after_insert": "generate_item.utils.delivery_note.after_insert",
    },
    "Purchase Invoice": {
        "validate": "generate_item.utils.purchase_invoice.validate",
    },
     "BOM":{
        "before_validate": "generate_item.utils.bom.before_validate",
        "before_insert": "generate_item.utils.bom.before_insert",
        "before_save": "generate_item.utils.bom.before_save",
        "on_cancel": "generate_item.utils.bom.clear_custom_fields_on_cancel",
        "on_submit": "generate_item.utils.bom.on_submit"
    },
    "Quality Inspection": {
        "before_save": "generate_item.utils.quality_inspection.before_save"
    },
    "Subcontracting Receipt": {
        "before_save": "generate_item.utils.subcontracting_receipt.before_save",
        "after_save": "generate_item.utils.subcontracting_receipt.after_save"
    },
   
}
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"generate_item.tasks.all"
# 	],
# 	"daily": [
# 		"generate_item.tasks.daily"
# 	],
# 	"hourly": [
# 		"generate_item.tasks.hourly"
# 	],
# 	"weekly": [
# 		"generate_item.tasks.weekly"
# 	],
# 	"monthly": [
# 		"generate_item.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "generate_item.install.before_tests"

# Overriding Methods
# ------------------------------
override_whitelisted_methods = {
    # Include Draft Purchase Orders in pending qty calculation when creating PO from MR
    "erpnext.stock.doctype.material_request.material_request.make_purchase_order": "generate_item.utils.material_request.make_purchase_order",
    # Map custom_batch_no from Purchase Order Item to Purchase Receipt Item.batch_no
    "erpnext.buying.doctype.purchase_order.purchase_order.make_purchase_receipt": "generate_item.utils.purchase_receipt.make_purchase_receipt",
    # Ensure Delivery Note mapping uses remaining qty excluding Draft DNs
    "erpnext.selling.doctype.sales_order.sales_order.make_delivery_note": "generate_item.utils.delivery_note.make_delivery_note",
    # Ensure Sales Invoice mapping from Delivery Note excludes Draft SI qty
    "erpnext.stock.doctype.delivery_note.delivery_note.make_sales_invoice": "generate_item.utils.sales_invoice.make_sales_invoice",
    # "erpnext.stock.get_item_details.get_item_details": "generate_item.utils.purchase_order.get_item_details",
    # Ensure Production Plan Get Items for MR returns BOM and drawing
    "erpnext.manufacturing.doctype.production_plan.production_plan.get_items_for_material_requests": "generate_item.overrides.production_plan.get_items_for_material_requests_patched"
}
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "generate_item.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["generate_item.utils.before_request"]
# after_request = ["generate_item.utils.after_request"]

# Job Events
# ----------
# before_job = ["generate_item.utils.before_job"]
# after_job = ["generate_item.utils.after_job"]

# User Data Protection
# --------------------
queries = {
    "Delivery Note.sales_order": "generate_item.utils.delivery_note.get_dispatchable_sales_orders",
}
# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"generate_item.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

