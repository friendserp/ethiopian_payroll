import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate

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

	earning_types, ded_types = get_earning_and_deduction_types(salary_slips)
	columns = get_columns(earning_types, ded_types)

	ss_earning_map = get_salary_slip_details(salary_slips, "earnings")
	ss_ded_map = get_salary_slip_details(salary_slips, "deductions")

	data = []
	for idx, ss in enumerate(salary_slips, start=1):
		row = {
			"idx": idx,
			"employee": ss.employee,
			"employee_name": ss.employee_name,
			"bank_account_no": ss.bank_account_no,
			"pan_number": ss.pan_number,
			"gross_pay": flt(ss.gross_pay),
			"total_deduction": flt(ss.total_deduction) + flt(ss.total_loan_repayment),
			"net_pay": flt(ss.net_pay),
			"earnings": [],
			"deductions": [],
		}

		for e in earning_types:
			amt = ss_earning_map.get(ss.name, {}).get(e)
			if amt:
				row["earnings"].append({"label": e, "amount": flt(amt)})
			row[frappe.scrub(e)] = amt

		for d in ded_types:
			amt = ss_ded_map.get(ss.name, {}).get(d)
			if amt:
				row["deductions"].append({"label": d, "amount": flt(amt)})
			row[frappe.scrub(d)] = amt

		data.append(row)

	return columns, data


def get_earning_and_deduction_types(salary_slips):
	salary_component_and_type = {_("Earning"): [], _("Deduction"): []}

	for salary_component in get_salary_components(salary_slips):
		component_type = get_salary_component_type(salary_component)
		salary_component_and_type[_(component_type)].append(salary_component)

	return sorted(salary_component_and_type[_("Earning")]), sorted(salary_component_and_type[_("Deduction")])


def get_columns(earning_types, ded_types):
	columns = [
		{"label": _("SL"), "fieldname": "idx", "fieldtype": "Int", "width": 50},
		{"label": _("Pers No"), "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 90},
		{"label": _("Employee"), "fieldname": "employee_name", "fieldtype": "Data", "width": 160},
		{"label": _("Bank A/c No"), "fieldname": "bank_account_no", "fieldtype": "Data", "width": 140},
		{"label": _("PAN No"), "fieldname": "pan_number", "fieldtype": "Data", "width": 120},
	]

	for earning in earning_types:
		columns.append(
			{
				"label": earning,
				"fieldname": frappe.scrub(earning),
				"fieldtype": "Currency",
				"width": 120,
			}
		)

	for deduction in ded_types:
		columns.append(
			{
				"label": deduction,
				"fieldname": frappe.scrub(deduction),
				"fieldtype": "Currency",
				"width": 120,
			}
		)

	columns.extend(
		[
			{"label": _("Gross Earning"), "fieldname": "gross_pay", "fieldtype": "Currency", "width": 120},
			{"label": _("Total Deduction"), "fieldname": "total_deduction", "fieldtype": "Currency", "width": 120},
			{"label": _("Net Salary"), "fieldname": "net_pay", "fieldtype": "Currency", "width": 120},
		]
	)

	return columns


def get_salary_components(salary_slips):
	return (
		frappe.qb.from_(salary_detail)
		.where((salary_detail.amount != 0) & (salary_detail.parent.isin([d.name for d in salary_slips])))
		.select(salary_detail.salary_component)
		.distinct()
	).run(pluck=True)


def get_salary_component_type(salary_component):
	return frappe.db.get_value("Salary Component", salary_component, "type", cache=True)


def get_salary_slips(filters):
	doc_status = {"Draft": 0, "Submitted": 1, "Cancelled": 2}

	query = frappe.qb.from_(salary_slip).select(
		salary_slip.star
	)

	if filters.get("docstatus"):
		query = query.where(salary_slip.docstatus == doc_status[filters.get("docstatus")])
	else:
		query = query.where(salary_slip.docstatus == 1)

	from_date = getdate(filters.get("from_date") or nowdate())
	to_date = getdate(filters.get("to_date") or nowdate())

	query = query.where(salary_slip.start_date >= from_date).where(salary_slip.end_date <= to_date)

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
		.where((salary_detail.parent.isin(salary_slips)) & (salary_detail.parentfield == component_type))
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

