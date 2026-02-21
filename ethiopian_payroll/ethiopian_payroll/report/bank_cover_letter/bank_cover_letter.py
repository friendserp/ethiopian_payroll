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

	columns = get_columns()

	data = []
	for idx, ss in enumerate(salary_slips, start=1):
		# Prefer rounded_total if present, else net_pay
		amount = flt(ss.rounded_total) or flt(ss.net_pay)
		data.append(
			{
				"idx": idx,
				"employee": ss.employee,
				"employee_name": ss.employee_name,
				"amount": amount,
			}
		)

	# Optional message
	message = _("Total Salary: {0}").format(
		frappe.utils.fmt_money(sum(d.get("amount", 0) for d in data), currency=None)
	)

	return columns, data, message


def get_columns():
	return [
		{"label": _("SL"), "fieldname": "idx", "fieldtype": "Int", "width": 60},
		{"label": _("Employee"), "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 120},
		{"label": _("Employee Name"), "fieldname": "employee_name", "fieldtype": "Data", "width": 200},
		{"label": _("Amount"), "fieldname": "amount", "fieldtype": "Currency", "width": 120},
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

