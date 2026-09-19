# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe import parse_json
from frappe.model.document import Document


class GeneralEmployee(Document):
	pass


@frappe.whitelist()
def general_employee_group_query(doctype, txt, searchfield, start, page_len, filters):
	"""
	Custom link query for the 'general_employee' Link field inside the
	General Employee Item child table.
	Returns General Employee records where:
	  - is_group = 1  (only group records, not individual employees)
	  - branch matches the parent's branch (case-insensitive, skipped when blank)
	"""
	filters = parse_json(filters) if isinstance(filters, str) else (filters or {})
	branch = filters.get("branch", "")

	conditions = ["ge.is_group = 1", "ge.name LIKE %(txt)s"]
	values = {"txt": f"%{txt}%", "start": int(start or 0), "page_len": int(page_len or 20)}

	if branch:
		conditions.append("LOWER(ge.branch) = LOWER(%(branch)s)")
		values["branch"] = branch

	where_clause = " AND ".join(conditions)

	return frappe.db.sql(
		f"""
		SELECT DISTINCT ge.name, ge.employee_name
		FROM `tabGeneral Employee` ge
		WHERE {where_clause}
		ORDER BY ge.name
		LIMIT %(start)s, %(page_len)s
		""",
		values,
	)


@frappe.whitelist()
def general_employee_by_department_query(doctype, txt, searchfield, start, page_len, filters):
	"""
	Custom link query for assembled_by / tested_by fields that link to General Employee.
	Returns parent General Employee records where:
	  - parent enabled = 1
	  - child row has matching department (case-insensitive)
	  - child row has matching branch (case-insensitive, skipped when blank)
	"""
	filters = parse_json(filters) if isinstance(filters, str) else (filters or {})
	branch = filters.get("branch", "")
	department = filters.get("department", "")

	conditions = [
		"ge.enabled = 1",
		"(ge.name LIKE %(txt)s OR ge.employee_name LIKE %(txt)s)",
	]
	values = {
		"txt": f"%{txt}%",
		"start": int(start or 0),
		"page_len": int(page_len or 20),
	}

	child_conditions = ["gei.parent = ge.name"]

	if department:
		child_conditions.append("LOWER(gei.department) = LOWER(%(department)s)")
		values["department"] = department

	if branch:
		child_conditions.append("LOWER(gei.branch) = LOWER(%(branch)s)")
		values["branch"] = branch

	child_where = " AND ".join(child_conditions)
	dept_join = f"INNER JOIN `tabGeneral Employee Item` gei ON {child_where}"
	where_clause = " AND ".join(conditions)

	return frappe.db.sql(
		f"""
		SELECT DISTINCT ge.name, ge.employee_name
		FROM `tabGeneral Employee` ge
		{dept_join}
		WHERE {where_clause}
		ORDER BY ge.name
		LIMIT %(start)s, %(page_len)s
		""",
		values,
	)

