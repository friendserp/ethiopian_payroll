import frappe
from frappe import _
from frappe.utils import flt


salary_slip = frappe.qb.DocType("Salary Slip")
salary_detail = frappe.qb.DocType("Salary Detail")


def execute(filters=None):
	if not filters:
		filters = {}

	company = filters.get("company")
	if not company:
		frappe.throw(_("Company is required"))

	salary_slips = get_salary_slips(filters)
	if not salary_slips:
		return [], []

	ded_types = get_deduction_types(salary_slips)
	columns = get_columns(ded_types)

	ss_ded_map = get_salary_slip_details(salary_slips, "deductions")
	emp_pan_map = get_employee_pan_map()

	data = []
	for idx, ss in enumerate(salary_slips, start=1):
		row = {
			"idx": idx,
			"employee": ss.employee,
			"employee_name": ss.employee_name,
			"pan_number": emp_pan_map.get(ss.employee),
			"total_deduction": flt(ss.total_deduction) + flt(ss.total_loan_repayment),
		}

		for d in ded_types:
			row.update({frappe.scrub(d): ss_ded_map.get(ss.name, {}).get(d)})

		data.append(row)

	return columns, data


def get_deduction_types(salary_slips):
	salary_component_and_type = []
	for salary_component in get_salary_components(salary_slips):
		component_type = get_salary_component_type(salary_component)
		if _(component_type) == _("Deduction"):
			salary_component_and_type.append(salary_component)
	return sorted(salary_component_and_type)


def get_columns(ded_types):
	columns = [
		{
			"label": _("SL"),
			"fieldname": "idx",
			"fieldtype": "Int",
			"width": 60,
		},
		{
			"label": _("Pers No"),
			"fieldname": "employee",
			"fieldtype": "Link",
			"options": "Employee",
			"width": 100,
		},
		{
			"label": _("Employee"),
			"fieldname": "employee_name",
			"fieldtype": "Data",
			"width": 160,
		},
		{
			"label": _("PAN No."),
			"fieldname": "pan_number",
			"fieldtype": "Data",
			"width": 120,
		},
	]

	for deduction in ded_types:
		columns.append(
			{
				"label": deduction,
				"fieldname": frappe.scrub(deduction),
				"fieldtype": "Currency",
				"width": 120,
			}
		)

	columns.append(
		{
			"label": _("Total Deduction"),
			"fieldname": "total_deduction",
			"fieldtype": "Currency",
			"width": 120,
		}
	)

	return columns


def get_salary_components(salary_slips):
	return (
		frappe.qb.from_(salary_detail)
		.where(
			(salary_detail.amount != 0)
			& (salary_detail.parent.isin([d.name for d in salary_slips]))
			& (salary_detail.parentfield == "deductions")
		)
		.select(salary_detail.salary_component)
		.distinct()
	).run(pluck=True)


def get_salary_component_type(salary_component):
	return frappe.db.get_value("Salary Component", salary_component, "type", cache=True)


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


def get_employee_pan_map():
	employee = frappe.qb.DocType("Employee")
	result = (frappe.qb.from_(employee).select(employee.name, employee.pan_number)).run()
	return frappe._dict(result)


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

