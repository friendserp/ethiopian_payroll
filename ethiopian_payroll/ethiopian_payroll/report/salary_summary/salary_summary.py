import frappe
from frappe import _
from frappe.utils import flt

import erpnext


salary_slip = frappe.qb.DocType("Salary Slip")
salary_detail = frappe.qb.DocType("Salary Detail")


def execute(filters=None):
	if not filters:
		filters = {}

	company = filters.get("company")
	if not company:
		frappe.throw(_("Company is required"))

	currency = filters.get("currency")
	company_currency = erpnext.get_company_currency(company)

	salary_slips = get_salary_slips(filters, company_currency)
	if not salary_slips:
		return [], []

	earning_types, ded_types = get_earning_and_deduction_types(salary_slips)
	columns = get_columns(earning_types, ded_types)

	ss_earning_map = get_salary_slip_details(salary_slips, currency, company_currency, "earnings")
	ss_ded_map = get_salary_slip_details(salary_slips, currency, company_currency, "deductions")

	doj_map = get_employee_doj_map()

	data = []
	for ss in salary_slips:
		row = {
			"salary_slip_id": ss.name,
			"employee": ss.employee,
			"employee_name": ss.employee_name,
			"designation": ss.designation,
			"total_working_days": ss.get("total_working_days") or 0,
			"date_of_joining": doj_map.get(ss.employee),
			"branch": ss.branch,
			"department": ss.department,
			"company": ss.company,
			"start_date": ss.start_date,
			"end_date": ss.end_date,
			"leave_without_pay": ss.leave_without_pay,
			"absent_days": ss.absent_days,
			"payment_days": ss.payment_days,
			"currency": currency or company_currency,
			"total_loan_repayment": ss.total_loan_repayment,
		}

		update_column_width(ss, columns)

		for e in earning_types:
			row.update({frappe.scrub(e): ss_earning_map.get(ss.name, {}).get(e)})

		for d in ded_types:
			row.update({frappe.scrub(d): ss_ded_map.get(ss.name, {}).get(d)})

		if currency == company_currency:
			row.update(
				{
					"gross_pay": flt(ss.gross_pay) * flt(ss.exchange_rate),
					"total_deduction": (flt(ss.total_deduction) + flt(ss.total_loan_repayment))
					* flt(ss.exchange_rate),
					"net_pay": flt(ss.net_pay) * flt(ss.exchange_rate),
				}
			)
		else:
			row.update(
				{
					"gross_pay": ss.gross_pay,
					"total_deduction": flt(ss.total_deduction) + flt(ss.total_loan_repayment),
					"net_pay": ss.net_pay,
				}
			)

		data.append(row)

	return columns, data


def get_earning_and_deduction_types(salary_slips):
	salary_component_and_type = {_("Earning"): [], _("Deduction"): []}

	for salary_component in get_salary_components(salary_slips):
		component_type = get_salary_component_type(salary_component)
		salary_component_and_type[_(component_type)].append(salary_component)

	return sorted(salary_component_and_type[_("Earning")]), sorted(salary_component_and_type[_("Deduction")])


def update_column_width(ss, columns):
	# Column widths are now compact and mostly fixed in the HTML layout.
	# Keep this function for backwards compatibility but do not mutate
	# column definitions here.
	return


def get_columns(earning_types, ded_types):
	def _short_label(component):
		"""Return a compact abbreviation for a salary component label.

		- Single word: first 4 letters (lowercase)
		- Multiple words: first 3 letters of first word + '.' + first 2 of next word
		- Special handling for ESI employer / employee contribution to keep them distinct
		"""
		if not component:
			return ""

		raw = (component or "").strip()

		# Normalised string for matching special cases
		normalised = raw.replace("-", " ").replace("_", " ")
		normalised = " ".join(normalised.split()).lower()

		# Special cases requested
		if "esi" in normalised and "employer" in normalised:
			return "Esi. Er"
		if "esi" in normalised and "employee" in normalised:
			return "Esi. Ee"

		words = normalised.split(" ")

		if len(words) == 1:
			w = words[0][:4]
			return w.capitalize()

		first = words[0][:3]
		second = words[1][:2] if len(words) > 1 else ""
		first_cap = first.capitalize()
		second_cap = second.capitalize() if second else ""
		abbr = f"{first_cap}. {second_cap}" if second_cap else first_cap
		return abbr

	# Base columns: only Employee and Employee Name before components
	columns = [
		{
			"label": _("Employee"),
			"fieldname": "employee",
			"fieldtype": "Link",
			"options": "Employee",
			"width": 120,
		},
		{
			"label": _("Employee Name"),
			"fieldname": "employee_name",
			"fieldtype": "Data",
			"width": 140,
		},
	]

	# Ensure "Basic" (or similar) appears as the first component column
	# right after Employee and Employee Name.
	basic_labels = {"Basic", "Basic Pay", "BASIC"}
	basic_component = None
	for lbl in earning_types:
		if lbl in basic_labels:
			basic_component = lbl
			break

	if basic_component:
		earning_types.remove(basic_component)
		columns.append(
			{
				"label": _("Basic"),
				"fieldname": frappe.scrub(basic_component),
				"fieldtype": "Currency",
				"options": "currency",
				"width": 90,
			}
		)

	for earning in earning_types:
		columns.append(
			{
				"label": _(_short_label(earning)),
				"fieldname": frappe.scrub(earning),
				"fieldtype": "Currency",
				"options": "currency",
				"width": 90,
			}
		)

	columns.append(
		{
			"label": _("Gross Pay"),
			"fieldname": "gross_pay",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120,
		}
	)

	for deduction in ded_types:
		columns.append(
			{
				"label": _(_short_label(deduction)),
				"fieldname": frappe.scrub(deduction),
				"fieldtype": "Currency",
				"options": "currency",
				"width": 90,
			}
		)

	columns.extend(
		[
			{
				"label": _("Loan Repayment"),
				"fieldname": "total_loan_repayment",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 120,
			},
			{
				"label": _("Total Deduction"),
				"fieldname": "total_deduction",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 120,
			},
			{
				"label": _("Net Pay"),
				"fieldname": "net_pay",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 120,
			},
			{
				"label": _("Currency"),
				"fieldtype": "Data",
				"fieldname": "currency",
				"options": "Currency",
				"hidden": 1,
			},
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


def get_salary_slips(filters, company_currency):
	doc_status = {"Draft": 0, "Submitted": 1, "Cancelled": 2}

	query = frappe.qb.from_(salary_slip).select(salary_slip.star)

	if filters.get("docstatus"):
		query = query.where(salary_slip.docstatus == doc_status[filters.get("docstatus")])

	if filters.get("from_date"):
		query = query.where(salary_slip.start_date >= filters.get("from_date"))

	if filters.get("to_date"):
		query = query.where(salary_slip.end_date <= filters.get("to_date"))

	if filters.get("company"):
		query = query.where(salary_slip.company == filters.get("company"))

	if filters.get("employee"):
		query = query.where(salary_slip.employee == filters.get("employee"))

	if filters.get("currency") and filters.get("currency") != company_currency:
		query = query.where(salary_slip.currency == filters.get("currency"))

	if filters.get("department"):
		query = query.where(salary_slip.department == filters["department"])

	if filters.get("designation"):
		query = query.where(salary_slip.designation == filters["designation"])

	if filters.get("branch"):
		query = query.where(salary_slip.branch == filters["branch"])

	return query.run(as_dict=1) or []


def get_employee_doj_map():
	employee = frappe.qb.DocType("Employee")

	result = (frappe.qb.from_(employee).select(employee.name, employee.date_of_joining)).run()

	return frappe._dict(result)


def get_salary_slip_details(salary_slips, currency, company_currency, component_type):
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
			salary_slip.exchange_rate,
		)
	).run(as_dict=1)

	ss_map = {}

	for d in result:
		ss_map.setdefault(d.parent, frappe._dict()).setdefault(d.salary_component, 0.0)
		if currency == company_currency:
			ss_map[d.parent][d.salary_component] += flt(d.amount) * flt(
				d.exchange_rate if d.exchange_rate else 1
			)
		else:
			ss_map[d.parent][d.salary_component] += flt(d.amount)

	return ss_map

