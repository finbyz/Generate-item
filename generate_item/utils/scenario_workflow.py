import frappe
from frappe import _
from frappe.utils import cint


SETTINGS_DOCTYPE = "Scenario Workflow Settings"

SCENARIO_PP_MR_MATERIAL_TRANSFER = "Production Plan Material Request - Material Transfer"
SCENARIO_WO_MATERIAL_TRANSFER_FOR_MANUFACTURE = "Work Order - Material Transfer for Manufacture"
SCENARIO_WO_MANUFACTURE = "Work Order - Manufacture"
SCENARIO_ANY_STOCK_ENTRY = "Any Stock Entry"


def validate_stock_entry_submit(doc, method=None):
	settings = _get_settings()
	if not settings or not cint(settings.get("enable_stock_entry_submit_control")):
		return

	if _system_manager_can_bypass(settings):
		return

	user_roles = _get_user_roles()
	unrestricted_roles = _get_stock_entry_scenario_roles(settings, SCENARIO_ANY_STOCK_ENTRY)
	if _has_allowed_role(user_roles, unrestricted_roles):
		return

	scenario = _get_stock_entry_scenario(doc)
	if not scenario:
		return

	allowed_roles = _get_stock_entry_scenario_roles(settings, scenario)
	if _has_allowed_role(user_roles, allowed_roles):
		return

	_throw_permission_error(
		_("Only selected roles can submit Stock Entry for scenario {0}.").format(
			frappe.bold(_(scenario))
		),
		allowed_roles,
	)


def validate_material_request_create(doc, method=None):
    # frappe.log_error("validate_material_request_create")
    settings = _get_settings()
    if not settings or not cint(settings.get("enable_manual_purchase_mr_approval")):
        return

    if _system_manager_can_bypass(settings):
        return

    if not _is_manual_purchase_material_request(doc):
        return

    creator_roles = _get_manual_purchase_mr_creator_roles(settings)
    if _has_allowed_role(_get_user_roles(), creator_roles):
        return

    _throw_permission_error(
        _("Only selected creator roles can create manual Purchase Material Requests."),
        creator_roles,
    )


def validate_material_request_submit(doc, method=None):
	settings = _get_settings()
	if not settings or not cint(settings.get("enable_manual_purchase_mr_approval")):
		return

	if _system_manager_can_bypass(settings):
		return

	if not _is_manual_purchase_material_request(doc):
		return

	approver_roles = _get_manual_purchase_mr_approver_roles(settings, doc.get("owner"))
	if _has_allowed_role(_get_user_roles(), approver_roles):
		return

	_throw_permission_error(
		_("Only approver roles mapped to the creator role can submit this manual Purchase Material Request."),
		approver_roles,
	)


def set_submit_control_onload(doc, method=None):
	doc.set_onload("scenario_submit_control", _get_submit_control_response(doc))


@frappe.whitelist()
def get_submit_control(doc):
	doc = frappe.get_doc(frappe.parse_json(doc))
	return _get_submit_control_response(doc)


def _get_submit_control_response(doc):
	settings = _get_settings()

	if doc.doctype == "Stock Entry":
		return _get_stock_entry_submit_control(doc, settings)

	if doc.doctype == "Material Request":
		return _get_material_request_submit_control(doc, settings)

	return {"hide_submit": False}


def _get_stock_entry_submit_control(doc, settings):
	if not settings or not cint(settings.get("enable_stock_entry_submit_control")):
		return {"hide_submit": False}

	if _system_manager_can_bypass(settings):
		return {"hide_submit": False}

	user_roles = _get_user_roles()
	unrestricted_roles = _get_stock_entry_scenario_roles(settings, SCENARIO_ANY_STOCK_ENTRY)
	if _has_allowed_role(user_roles, unrestricted_roles):
		return {"hide_submit": False}

	scenario = _get_stock_entry_scenario(doc)
	if not scenario:
		return {"hide_submit": False}

	allowed_roles = _get_stock_entry_scenario_roles(settings, scenario)
	return {
		"hide_submit": not _has_allowed_role(user_roles, allowed_roles),
		"scenario": scenario,
		"allowed_roles": sorted(allowed_roles),
	}


def _get_material_request_submit_control(doc, settings):
	if not settings or not cint(settings.get("enable_manual_purchase_mr_approval")):
		return {"hide_submit": False}

	if _system_manager_can_bypass(settings):
		return {"hide_submit": False}

	if not _is_manual_purchase_material_request(doc):
		return {"hide_submit": False}

	approver_roles = _get_manual_purchase_mr_approver_roles(settings, doc.get("owner"))
	return {
		"hide_submit": not _has_allowed_role(_get_user_roles(), approver_roles),
		"allowed_roles": sorted(approver_roles),
	}


def _get_settings():
	if not frappe.db.exists("DocType", SETTINGS_DOCTYPE):
		return None

	return frappe.get_single(SETTINGS_DOCTYPE)


def _system_manager_can_bypass(settings):
	return cint(settings.get("allow_system_manager_bypass")) and "System Manager" in _get_user_roles()


def _get_user_roles(user=None):
	return set(frappe.get_roles(user or frappe.session.user))


def _get_stock_entry_scenario_roles(settings, scenario):
	return {
		row.role
		for row in settings.get("stock_entry_scenario_roles") or []
		if row.get("role") and row.get("scenario") == scenario and not cint(row.get("disabled"))
	}


def _get_manual_purchase_mr_rules(settings):
	return [
		row
		for row in settings.get("manual_purchase_mr_approval_rules") or []
		if row.get("creator_role") and row.get("approver_role") and not cint(row.get("disabled"))
	]


def _get_manual_purchase_mr_creator_roles(settings):
	return {row.creator_role for row in _get_manual_purchase_mr_rules(settings)}


def _get_manual_purchase_mr_approver_roles(settings, creator_user):
	creator_roles = _get_user_roles(creator_user) if creator_user else set()
	return {
		row.approver_role
		for row in _get_manual_purchase_mr_rules(settings)
		if row.creator_role in creator_roles
	}


def _has_allowed_role(user_roles, allowed_roles):
	return bool(set(user_roles).intersection(set(allowed_roles)))


def _throw_permission_error(message, allowed_roles):
	if allowed_roles:
		role_list = ", ".join(sorted(allowed_roles))
	else:
		role_list = _("No roles configured")

	frappe.throw(
		_("{0}<br><br>Allowed Roles: {1}").format(message, frappe.bold(role_list)),
		frappe.PermissionError,
	)


def _get_stock_entry_scenario(doc):
	if _is_stock_entry_material_transfer_from_production_plan_mr(doc):
		return SCENARIO_PP_MR_MATERIAL_TRANSFER

	if doc.get("work_order") and _stock_entry_matches_purpose(doc, "Material Transfer for Manufacture"):
		return SCENARIO_WO_MATERIAL_TRANSFER_FOR_MANUFACTURE

	if doc.get("work_order") and _stock_entry_matches_purpose(doc, "Manufacture"):
		return SCENARIO_WO_MANUFACTURE

	return None


def _stock_entry_matches_purpose(doc, purpose):
	return doc.get("purpose") == purpose or doc.get("stock_entry_type") == purpose


def _is_stock_entry_material_transfer_from_production_plan_mr(doc):
	if not _stock_entry_matches_purpose(doc, "Material Transfer"):
		return False

	for material_request in _get_stock_entry_material_requests(doc):
		if _material_request_has_production_plan(material_request):
			return True

	return False


def _get_stock_entry_material_requests(doc):
	material_requests = set()
	for row in doc.get("items") or []:
		if row.get("material_request"):
			material_requests.add(row.material_request)

	return material_requests


def _is_manual_purchase_material_request(doc):
	if doc.get("material_request_type") != "Purchase":
		return False

	return not _doc_has_production_plan_items(doc)


def _doc_has_production_plan_items(doc):
	for row in doc.get("items") or []:
		if row.get("production_plan") or row.get("material_request_plan_item"):
			return True

	return False


def _material_request_has_production_plan(material_request):
	if not material_request:
		return False

	return bool(
		frappe.db.exists(
			"Material Request Item",
			{
				"parent": material_request,
				"parenttype": "Material Request",
				"production_plan": ["is", "set"],
			},
		)
		or frappe.db.exists(
			"Material Request Item",
			{
				"parent": material_request,
				"parenttype": "Material Request",
				"material_request_plan_item": ["is", "set"],
			},
		)
	)
