import frappe
from frappe import _
from frappe.utils import flt, getdate, formatdate
from datetime import datetime
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

	salary_slips = get_salary_slips(filters)
	if not salary_slips:
		return [], []

	# Aggregate earnings and deductions by component
	earnings = aggregate_components(salary_slips, "earnings", currency, company_currency)
	deductions = aggregate_components(salary_slips, "deductions", currency, company_currency)

	# Sort components alphabetically
	earnings_sorted = dict(sorted(earnings.items()))
	deductions_sorted = dict(sorted(deductions.items()))

	# Calculate totals
	total_earnings = sum(earnings.values())
	total_deductions = sum(deductions.values())
	net_pay = total_earnings - total_deductions

	# Derive month and year from date range if not provided
	month = filters.get("month")
	year = filters.get("year")
	
	if not month and filters.get("from_date"):
		from_date = getdate(filters["from_date"])
		month = formatdate(from_date, "MMMM")
		year = from_date.year
	
	if not year and filters.get("from_date"):
		from_date = getdate(filters["from_date"])
		year = from_date.year

	# Prepare data for table view - create rows with earnings and deductions side by side
	earnings_list = list(earnings_sorted.items())
	deductions_list = list(deductions_sorted.items())
	max_rows = max(len(earnings_list), len(deductions_list))

	rows = []
	for i in range(max_rows):
		row = {
			"earning_head": earnings_list[i][0] if i < len(earnings_list) else "",
			"earning_amount": earnings_list[i][1] if i < len(earnings_list) else 0,
			"deduction_head": deductions_list[i][0] if i < len(deductions_list) else "",
			"deduction_amount": deductions_list[i][1] if i < len(deductions_list) else 0,
		}
		rows.append(row)

	# Add totals row
	rows.append({
		"earning_head": "Total Earnings:",
		"earning_amount": total_earnings,
		"deduction_head": "Total Deductions:",
		"deduction_amount": total_deductions,
	})

	# Add net pay row
	rows.append({
		"earning_head": "",
		"earning_amount": 0,
		"deduction_head": "Net Pay:",
		"deduction_amount": net_pay,
	})

	# Store metadata for print format
	for row in rows:
		row["_meta"] = {
			"company": company,
			"month": month or "",
			"year": year or "",
			"currency": currency or company_currency,
			"total_earnings": total_earnings,
			"total_deductions": total_deductions,
			"net_pay": net_pay,
			"earnings": [{"name": k, "amount": v} for k, v in earnings_sorted.items()],
			"deductions": [{"name": k, "amount": v} for k, v in deductions_sorted.items()],
		}

	columns = get_columns()
	return columns, rows


@frappe.whitelist()
def get_print_format_html(report_name, filters=None, data=None):
	"""Server-side method to render Jinja print format for reports"""
	from frappe.utils.jinja import render_template
	
	# Get the Print Format
	print_format = frappe.get_doc("Print Format", "Consolidated Salary Report")
	
	if print_format.print_format_type != "Jinja":
		frappe.throw(_("Print Format must be of type Jinja"))
	
	# Parse filters if string
	if isinstance(filters, str):
		import json
		filters = json.loads(filters)
	
	# Parse data if string
	if isinstance(data, str):
		import json
		data = json.loads(data)
	
	# Prepare context
	context = {
		"data": data or [],
		"filters": filters or {},
		"frappe": frappe,
	}
	
	# Render the template
	html = render_template(print_format.html, context)
	css = print_format.css or ""
	
	return f"<style>{css}</style>{html}"


def get_salary_slips(filters):
	query = (
		frappe.qb.from_(salary_slip)
		.select(salary_slip.name, salary_slip.company, salary_slip.start_date, salary_slip.end_date)
		.where(salary_slip.docstatus == 1)
	)

	if filters.get("company"):
		query = query.where(salary_slip.company == filters["company"])

	if filters.get("from_date") and filters.get("to_date"):
		from_date = getdate(filters["from_date"])
		to_date = getdate(filters["to_date"])
		query = query.where(
			(salary_slip.posting_date >= from_date) & (salary_slip.posting_date <= to_date)
		)
		query = query.where(
			(salary_slip.start_date <= to_date) & (salary_slip.end_date >= from_date)
		)

	if filters.get("employee"):
		query = query.where(salary_slip.employee == filters["employee"])

	if filters.get("department"):
		query = query.where(salary_slip.department == filters["department"])

	if filters.get("designation"):
		query = query.where(salary_slip.designation == filters["designation"])

	if filters.get("branch"):
		query = query.where(salary_slip.branch == filters["branch"])

	return query.run(as_dict=1) or []


def aggregate_components(salary_slips, component_type, currency, company_currency):
	"""Aggregate salary components across all salary slips"""
	salary_slip_names = [ss.name for ss in salary_slips]

	result = (
		frappe.qb.from_(salary_slip)
		.join(salary_detail)
		.on(salary_slip.name == salary_detail.parent)
		.where(
			(salary_detail.parent.isin(salary_slip_names))
			& (salary_detail.parentfield == component_type)
		)
		.select(
			salary_detail.salary_component,
			salary_detail.amount,
			salary_slip.exchange_rate,
		)
	).run(as_dict=1)

	component_map = {}
	for d in result:
		component_name = d.salary_component
		amount = flt(d.amount)
		
		# Handle currency conversion
		if currency == company_currency:
			amount = amount * flt(d.exchange_rate if d.exchange_rate else 1)
		
		component_map.setdefault(component_name, 0.0)
		component_map[component_name] += amount

	return component_map


def get_columns():
	return [
		{
			"fieldname": "earning_head",
			"label": _("Earning Head"),
			"fieldtype": "Data",
			"width": 200,
		},
		{
			"fieldname": "earning_amount",
			"label": _("Amount Rs."),
			"fieldtype": "Currency",
			"width": 120,
			"options": "currency",
		},
		{
			"fieldname": "deduction_head",
			"label": _("Deduction Head"),
			"fieldtype": "Data",
			"width": 200,
		},
		{
			"fieldname": "deduction_amount",
			"label": _("Amount Rs."),
			"fieldtype": "Currency",
			"width": 120,
			"options": "currency",
		},
	]

