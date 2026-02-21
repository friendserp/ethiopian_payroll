import frappe
from frappe import _
from frappe.utils import flt, getdate, formatdate

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

	# Fetch earnings and deductions separately
	ss_earning_map = get_salary_slip_details(salary_slips, "earnings")
	ss_ded_map = get_salary_slip_details(salary_slips, "deductions")

	# Salary Components (exact names)
	BASIC_COMPONENT = "Basic Salary"
	ESI_EMPLOYEE_COMPONENT = "ESI - Employee Contribution"
	ESI_EMPLOYER_COMPONENT = "ESI-Employer Contribution"

	columns = get_columns()

	data = []
	total_basic = 0.0
	total_esi_employee = 0.0
	total_esi_employer = 0.0
	total_all = 0.0

	for idx, ss in enumerate(salary_slips, start=1):

		# Basic Salary (from earnings, NOT part of total)
		basic_amount = flt(
			ss_earning_map.get(ss.name, {}).get(BASIC_COMPONENT, 0)
		)

		# ESI Employee Contribution (from deductions)
		esi_employee_amount = flt(
			ss_ded_map.get(ss.name, {}).get(ESI_EMPLOYEE_COMPONENT, 0)
		)

		# ESI Employer Contribution (from earnings)
		esi_employer_amount = flt(
			ss_earning_map.get(ss.name, {}).get(ESI_EMPLOYER_COMPONENT, 0)
		)

		# TOTAL = ESI Employee + ESI Employer (Basic excluded)
		total_amount = esi_employee_amount + esi_employer_amount

		row = frappe._dict({
			"idx": idx,
			"employee": ss.employee,
			"employee_name": ss.employee_name,
			"basic_salary": basic_amount,
			"esi_employee_contribution": esi_employee_amount,
			"esi_employer_contribution": esi_employer_amount,
			"total": total_amount,
		})

		data.append(row)

		# Accumulate totals
		total_basic += basic_amount
		total_esi_employee += esi_employee_amount
		total_esi_employer += esi_employer_amount
		total_all += total_amount

	# Summary metadata (for print format)
	if data:
		data[0]._meta = {
			"total_basic": total_basic,
			"total_esi_employee": total_esi_employee,
			"total_esi_employer": total_esi_employer,
			"total_all": total_all,
			"employee_count": len(data),
			"company": company,
			"month": filters.get("month") or "",
			"year": filters.get("year") or "",
		}

		if not data[0]._meta["month"] and filters.get("from_date"):
			from_date = getdate(filters["from_date"])
			data[0]._meta["month"] = formatdate(from_date, "MMMM")
			data[0]._meta["year"] = from_date.year

	return columns, data


def get_columns():
	return [
		{"label": _("Emp. ID"), "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 100},
		{"label": _("Emp. Name"), "fieldname": "employee_name", "fieldtype": "Data", "width": 200},
		{"label": _("BASIC"), "fieldname": "basic_salary", "fieldtype": "Currency", "width": 120},
		{"label": _("Employee Contribution"), "fieldname": "esi_employee_contribution", "fieldtype": "Currency", "width": 150},
		{"label": _("Employer Contribution"), "fieldname": "esi_employer_contribution", "fieldtype": "Currency", "width": 150},
		{"label": _("Total"), "fieldname": "total", "fieldtype": "Currency", "width": 120},
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



