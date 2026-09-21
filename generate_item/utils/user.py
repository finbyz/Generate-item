import frappe


def _resolve_employee_name(user_doc):
	"""Derive the Employee Name to use for a General Employee record from a User doc."""
	employee_name = (user_doc.full_name or "").strip()
	if not employee_name:
		first_name = (user_doc.first_name or "").strip()
		last_name = (user_doc.last_name or "").strip()
		employee_name = " ".join(filter(None, [first_name, last_name])).strip()
	if not employee_name:
		employee_name = (user_doc.email or user_doc.name or "").strip()
	return employee_name




@frappe.whitelist()
def check_general_employee_exists(user):
	"""
	Checks whether a corresponding General Employee already exists for a User,
	and fetches existing branch and permissions if any.
	"""
	user_doc = frappe.get_cached_doc("User", user)
	employee_name = _resolve_employee_name(user_doc)

	existing_ge = None
	if frappe.db.exists("General Employee", employee_name):
		existing_ge = frappe.db.get_value(
			"General Employee", employee_name, ["name", "branch", "enabled"], as_dict=True
		)
	if not existing_ge:
		existing_ge = frappe.db.get_value(
			"General Employee", {"employee_name": employee_name}, ["name", "branch", "enabled"], as_dict=True
		)

	branch_perm = frappe.db.get_value("User Permission", {"user": user, "allow": "Branch"}, "for_value")
	wh_perm = frappe.db.get_value("User Permission", {"user": user, "allow": "Warehouse"}, "for_value")

	current_branch = ""
	if existing_ge and existing_ge.branch:
		current_branch = existing_ge.branch
	elif branch_perm:
		current_branch = branch_perm

	return {
		"exists": bool(existing_ge),
		"employee_name": employee_name,
		"branch": current_branch,
		"has_branch_permission": bool(branch_perm),
		"has_warehouse_permission": bool(wh_perm),
		"warehouse": wh_perm or "",
	}


@frappe.whitelist()
def create_general_employee_and_permissions(
	user,
	branch,
	create_permission_branch=False,
	create_permission_warehouse=False,
	warehouse=None,
):
	"""
	Creates or updates a General Employee with branch, and creates optional Branch/Warehouse User Permissions.
	"""
	create_permission_branch = frappe.parse_json(create_permission_branch)
	create_permission_warehouse = frappe.parse_json(create_permission_warehouse)

	if not branch:
		frappe.throw("Branch is mandatory to create/configure General Employee.")

	user_doc = frappe.get_doc("User", user)
	employee_name = _resolve_employee_name(user_doc)

	if not employee_name:
		frappe.throw("Could not determine a valid Employee Name for this User.")

	# Step 1 - General Employee
	existing_name = frappe.db.exists("General Employee", employee_name) or frappe.db.get_value(
		"General Employee", {"employee_name": employee_name}, "name"
	)

	if not existing_name:
		ge = frappe.get_doc(
			{
				"doctype": "General Employee",
				"employee_name": employee_name,
				"branch": branch,
				"enabled": 1,
				"is_group": 0,
			}
		)
		ge.flags.ignore_permissions = True
		ge.insert(ignore_permissions=True)
		ge_name = ge.name
	else:
		existing_ge = frappe.get_doc("General Employee", existing_name)
		if existing_ge.branch != branch:
			existing_ge.db_set("branch", branch)
		ge_name = existing_ge.name

	# Step 2 - Branch User Permission
	if create_permission_branch:
		if not frappe.db.exists(
			"User Permission",
			{"user": user, "allow": "Branch", "for_value": branch},
		):
			perm_branch = frappe.get_doc(
				{
					"doctype": "User Permission",
					"user": user,
					"allow": "Branch",
					"for_value": branch,
				}
			)
			perm_branch.flags.ignore_permissions = True
			perm_branch.insert(ignore_permissions=True)

	# Step 3 - Warehouse User Permission
	if create_permission_warehouse and warehouse:
		wh_branch = frappe.db.get_value("Warehouse", warehouse, "branch")
		if wh_branch and wh_branch != branch:
			frappe.throw(
				f"Warehouse <b>{warehouse}</b> does not belong to Branch <b>{branch}</b>."
			)

		if not frappe.db.exists(
			"User Permission",
			{"user": user, "allow": "Warehouse", "for_value": warehouse},
		):
			perm_wh = frappe.get_doc(
				{
					"doctype": "User Permission",
					"user": user,
					"allow": "Warehouse",
					"for_value": warehouse,
				}
			)
			perm_wh.flags.ignore_permissions = True
			perm_wh.insert(ignore_permissions=True)

	return {
		"general_employee": ge_name,
		"branch": branch,
		"branch_permission_created": bool(create_permission_branch),
		"warehouse_permission_created": bool(create_permission_warehouse and warehouse),
	}