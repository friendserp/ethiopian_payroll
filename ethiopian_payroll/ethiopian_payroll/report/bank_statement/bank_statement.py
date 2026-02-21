import frappe
from frappe.utils import getdate, nowdate


def execute(filters=None):
	filters = filters or {}

	company = filters.get("company")
	from_date = getdate(filters.get("from_date") or nowdate())
	to_date = getdate(filters.get("to_date") or nowdate())
	bank_name_filter = filters.get("bank_name")

	# Use both posting_date and pay-period dates to avoid slips outside the range.
	slip_filters = {
		"docstatus": 1,
		"posting_date": ["between", [from_date, to_date]],
		"start_date": [">=", from_date],
		"end_date": ["<=", to_date],
	}
	if company:
		slip_filters["company"] = company
	if bank_name_filter:
		slip_filters["bank_name"] = bank_name_filter

	slips = frappe.get_all(
		"Salary Slip",
		fields=[
			"name",
			"employee",
			"employee_name",
			"bank_name",
			"bank_account_no",
			"rounded_total",
			"net_pay",
			"posting_date",
		],
		filters=slip_filters,
		order_by="employee asc",
	)

	columns = [
		{"label": "SL", "fieldname": "idx", "fieldtype": "Int", "width": 60},
		{"label": "Pers No", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 100},
		{"label": "Employee", "fieldname": "employee_name", "fieldtype": "Data", "width": 200},
		{"label": "Bank Acc No", "fieldname": "bank_account_no", "fieldtype": "Data", "width": 140},
		{"label": "Amt Rs.", "fieldname": "amount", "fieldtype": "Currency", "width": 120},
	]

	data = []
	total = 0
	for idx, slip in enumerate(slips, start=1):
		amount = slip.rounded_total or slip.net_pay or 0
		total += amount
		data.append(
			{
				"idx": idx,
				"employee": slip.employee,
				"employee_name": slip.employee_name,
				"bank_account_no": slip.bank_account_no,
				"amount": amount,
			}
		)

	message = f"Total Amount: {frappe.utils.fmt_money(total, currency=None)}"
	return columns, data, message

