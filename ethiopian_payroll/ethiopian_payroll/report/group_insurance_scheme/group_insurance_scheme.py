import frappe
from frappe import _
from frappe.utils import flt, getdate, formatdate

salary_slip = frappe.qb.DocType("Salary Slip")
salary_detail = frappe.qb.DocType("Salary Detail")
salary_structure_assignment = frappe.qb.DocType("Salary Structure Assignment")


def execute(filters=None):
	if not filters:
		filters = {}

	company = filters.get("company")
	if not company:
		frappe.throw(_("Company is required"))

	salary_slips = get_salary_slips(filters)
	if not salary_slips:
		return [], []

	# Get salary slip details for deductions
	ss_ded_map = get_salary_slip_details(salary_slips, "deductions")

	# Component name
	group_insurance_component = "Group Insurance"

	columns = get_columns()

	data = []
	total_amount = 0.0

	idx = 0
	for ss in salary_slips:
		# Get Group Insurance amount from salary slip deductions
		group_insurance_amount = 0.0
		if group_insurance_component:
			group_insurance_amount = flt(ss_ded_map.get(ss.name, {}).get(group_insurance_component, 0))

		# Only include employees who have Group Insurance component
		if group_insurance_amount > 0:
			idx += 1
			# Get Policy amount from Salary Structure Assignment
			policy_amount = get_policy_amount(ss.employee, ss.start_date)

			row = frappe._dict({
				"idx": idx,
				"employee": ss.employee,
				"employee_name": ss.employee_name,
				"policy_amount": policy_amount,
				"amount": group_insurance_amount,
			})

			data.append(row)
			total_amount += group_insurance_amount

	# Store metadata in first row for print format
	if data:
		data[0]._meta = frappe._dict({
			"total_amount": total_amount,
			"employee_count": len(data),
			"company": company,
			"month": filters.get("month") or "",
			"year": filters.get("year") or "",
		})

		# Derive month and year from date range if not provided
		if not data[0]._meta["month"] and filters.get("from_date"):
			from_date = getdate(filters["from_date"])
			data[0]._meta["month"] = formatdate(from_date, "MMMM")
			data[0]._meta["year"] = from_date.year
		if not data[0]._meta["year"] and filters.get("from_date"):
			from_date = getdate(filters["from_date"])
			data[0]._meta["year"] = from_date.year

	return columns, data


def get_columns():
	return [
		{"label": _("SL"), "fieldname": "idx", "fieldtype": "Int", "width": 60},
		{"label": _("Pers No"), "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 100},
		{"label": _("Employee"), "fieldname": "employee_name", "fieldtype": "Data", "width": 200},
		{"label": _("Policy amount"), "fieldname": "policy_amount", "fieldtype": "Currency", "width": 120},
		{"label": _("Amt Rs."), "fieldname": "amount", "fieldtype": "Currency", "width": 120},
	]


def get_salary_slips(filters):
	doc_status = {"Draft": 0, "Submitted": 1, "Cancelled": 2}

	query = frappe.qb.from_(salary_slip).select(salary_slip.star)

	if filters.get("docstatus"):
		query = query.where(salary_slip.docstatus == doc_status[filters.get("docstatus")])
	else:
		query = query.where(salary_slip.docstatus == 1)

	if filters.get("from_date"):
		query = query.where(salary_slip.start_date >= filters.get("from_date"))

	if filters.get("to_date"):
		query = query.where(salary_slip.end_date <= filters.get("to_date"))

	if filters.get("company"):
		query = query.where(salary_slip.company == filters.get("company"))

	if filters.get("employee"):
		query = query.where(salary_slip.employee == filters.get("employee"))

	if filters.get("department"):
		query = query.where(salary_slip.department == filters["department"])

	if filters.get("designation"):
		query = query.where(salary_slip.designation == filters["designation"])

	if filters.get("branch"):
		query = query.where(salary_slip.branch == filters["branch"])

	return query.run(as_dict=1) or []


def get_salary_slip_details(salary_slips, component_type):
	salary_slips = [ss.name for ss in salary_slips]

	result = (
		frappe.qb.from_(salary_slip)
		.join(salary_detail)
		.on(salary_slip.name == salary_detail.parent)
		.where(
			(salary_detail.parent.isin(salary_slips))
			& (salary_detail.parentfield == component_type)
		)
		.select(
			salary_detail.parent,
			salary_detail.salary_component,
			salary_detail.amount,
		)
	).run(as_dict=1)

	ss_map = {}
	for d in result:
		ss_map.setdefault(d.parent, frappe._dict()).setdefault(d.salary_component, 0.0)
		ss_map[d.parent][d.salary_component] += flt(d.amount)

	return ss_map


def get_policy_amount(employee, on_date):
	"""Get custom_group_insurance_amount from Salary Structure Assignment for the employee on the given date"""
	if not employee or not on_date:
		return 0.0

	# Get the most recent Salary Structure Assignment for this employee on or before the given date
	assignment = (
		frappe.qb.from_(salary_structure_assignment)
		.select(salary_structure_assignment.custom_group_insurance_amount)
		.where(salary_structure_assignment.employee == employee)
		.where(salary_structure_assignment.docstatus == 1)
		.where(salary_structure_assignment.from_date <= on_date)
		.orderby(salary_structure_assignment.from_date, order=frappe.qb.desc)
		.limit(1)
	).run(as_dict=1)

	if assignment and assignment[0].get("custom_group_insurance_amount"):
		return flt(assignment[0].get("custom_group_insurance_amount"))

	return 0.0

