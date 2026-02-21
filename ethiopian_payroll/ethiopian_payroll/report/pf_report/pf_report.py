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

	# Get salary slip details for earnings and deductions
	ss_earning_map = get_salary_slip_details(salary_slips, "earnings")
	ss_ded_map = get_salary_slip_details(salary_slips, "deductions")

	columns = get_columns()

	data = []

	for ss in salary_slips:
		# UAN (Employee ID)
		uan = ss.employee
		
		# Name
		name = ss.employee_name
		
		# Gross Salary
		gross_salary = flt(ss.gross_pay)
		
		# Get earnings map for this salary slip
		earnings_map = ss_earning_map.get(ss.name, {})
		
		# Get Basic Salary
		basic_amount = 0.0
		basic_components = ["Basic Salary", "Basic", "BASIC"]
		
		# First try exact matches
		for comp in basic_components:
			if comp in earnings_map:
				basic_amount = flt(earnings_map[comp])
				break
		
		# If not found, try case-insensitive match
		if basic_amount == 0:
			for key in earnings_map.keys():
				key_lower = key.lower().strip()
				if key_lower in [c.lower() for c in basic_components] or \
				   (key_lower.startswith("basic") and len(key_lower) < 20):
					basic_amount = flt(earnings_map[key])
					break
		
		# Get Dearness Allowances (DA) - search with case-insensitive and partial matching
		da_amount = 0.0
		da_components = ["Dearness Allowences", "Dearness Allowence", "DA", "D.A.", "Dearness"]
		
		# First try exact matches
		for comp in da_components:
			if comp in earnings_map:
				da_amount = flt(earnings_map[comp])
				break
		
		# If not found, try case-insensitive and partial matches
		if da_amount == 0:
			for key in earnings_map.keys():
				key_lower = key.lower().strip()
				# Check for "dearness" or "allowence" (with typo) or standalone "da"
				if ("dearness" in key_lower and "allowence" in key_lower) or \
				   (key_lower == "da" or key_lower == "d.a.") or \
				   ("dearness" in key_lower and len(key_lower) < 20):
					da_amount = flt(earnings_map[key])
					break
		
		# PF wages = Basic + DA (capped at 15000)
		pf_wages = flt(basic_amount + da_amount, 2)
		if pf_wages > 15000:
			pf_wages = 15000.0
		
		# EPS wages = Employee Pension Scheme
		eps_wages = 0.0
		eps_components = ["Employee Pension Scheme", "EPS", "Employee Pension"]
		for comp in eps_components:
			if comp in ss_earning_map.get(ss.name, {}):
				eps_wages = flt(ss_earning_map[ss.name][comp])
				break
		
		# EDLI wages = EDLI
		edli_wages = 0.0
		edli_components = ["EDLI", "Employee Deposit Linked Insurance"]
		for comp in edli_components:
			if comp in ss_earning_map.get(ss.name, {}):
				edli_wages = flt(ss_earning_map[ss.name][comp])
				break
		
		# Employee cont.12% + VPF = Provident Fund - Employee Contribution
		pf_employee_cont = 0.0
		pf_employee_components = [
			"Provident Fund - Employee Contribution",
			"PF - Employee Contribution",
			"PF Employee Contribution",
			"Provident Fund Employee",
		]
		for comp in pf_employee_components:
			if comp in ss_ded_map.get(ss.name, {}):
				pf_employee_cont = flt(ss_ded_map[ss.name][comp])
				break
		
		# Employer to EPS = 8.33% of PF wages (capped at 15000)
		employer_to_eps = flt(pf_wages * 0.0833, 2)
		
		# Employer to PF = 3.67% of PF wages (capped at 15000)
		employer_to_pf = flt(pf_wages * 0.0367, 2)

		row = {
			"uan": uan,
			"name": name,
			"gross_salary": gross_salary,
			"pf_wages": pf_wages,
			"eps_wages": eps_wages,
			"edli_wages": edli_wages,
			"employee_cont": pf_employee_cont,
			"employer_to_eps": employer_to_eps,
			"employer_to_pf": employer_to_pf,
		}

		data.append(row)

	return columns, data


def get_columns():
	return [
		{
			"label": _("UAN"),
			"fieldname": "uan",
			"fieldtype": "Link",
			"options": "Employee",
			"width": 120,
		},
		{
			"label": _("Name"),
			"fieldname": "name",
			"fieldtype": "Data",
			"width": 200,
		},
		{
			"label": _("Gross Salary"),
			"fieldname": "gross_salary",
			"fieldtype": "Currency",
			"width": 120,
		},
		{
			"label": _("PF Wages (Basic + DA)"),
			"fieldname": "pf_wages",
			"fieldtype": "Currency",
			"width": 150,
		},
		{
			"label": _("EPS Wages"),
			"fieldname": "eps_wages",
			"fieldtype": "Currency",
			"width": 120,
		},
		{
			"label": _("EDLI Wages"),
			"fieldname": "edli_wages",
			"fieldtype": "Currency",
			"width": 120,
		},
		{
			"label": _("Employee Cont.12% + VPF"),
			"fieldname": "employee_cont",
			"fieldtype": "Currency",
			"width": 180,
		},
		{
			"label": _("Employer to EPS (8.33%)"),
			"fieldname": "employer_to_eps",
			"fieldtype": "Currency",
			"width": 180,
		},
		{
			"label": _("Employer to PF (3.67%)"),
			"fieldname": "employer_to_pf",
			"fieldtype": "Currency",
			"width": 180,
		},
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

