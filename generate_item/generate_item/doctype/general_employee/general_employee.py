# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe import parse_json
from frappe.model.document import Document


class GeneralEmployee(Document):
	def autoname(self):
		if self.is_group:
			dep = (self.department or "").strip()
			branch = (self.branch or "").strip()
			if dep and branch:
				self.name = f"{dep}-{branch}"
			elif dep:
				self.name = dep
			elif branch:
				self.name = branch
			else:
				self.name = (self.employee_name or "").strip()
		else:
			self.name = (self.employee_name or "").strip()

	def validate(self):
		if self.is_group and self.department:
			self.employee_name = self.department


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

	conditions = ["ge.is_group = 1", "(ge.name LIKE %(txt)s OR ge.employee_name LIKE %(txt)s)"]
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
	department = (filters.get("department") or "").strip()

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
		child_conditions.append("LOWER(TRIM(gei.department)) = LOWER(TRIM(%(department)s))")
		values["department"] = department

	if branch:
		child_conditions.append("LOWER(TRIM(gei.branch)) = LOWER(TRIM(%(branch)s))")
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


