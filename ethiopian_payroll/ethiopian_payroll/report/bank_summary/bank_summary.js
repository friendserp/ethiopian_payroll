// Copyright (c) 2026, Sami and contributors
// For license information, please see license.txt

frappe.query_reports["Bank Summary"] = {
	"filters": [
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"),
			"reqd": 1
		},
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.month_start(),
			"reqd": 1
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.month_end(),
			"reqd": 1
		},
		{
			"fieldname": "project",
			"label": __("Project"),
			"fieldtype": "Link",
			"options": "Project"
		},
		{
			"fieldname": "status",
			"label": __("Status"),
			"fieldtype": "Select",
			"options": "\nActive\nLeft",
			"default": ""
		},
		{
			"fieldname": "mode_of_payment",
			"label": __("Mode of Payment"),
			"fieldtype": "Select",
			"options": "\nBank\nPhone No",
			"default": ""
		}
	]
};

