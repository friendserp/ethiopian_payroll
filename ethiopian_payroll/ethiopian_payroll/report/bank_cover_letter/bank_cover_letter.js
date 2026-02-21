frappe.query_reports["Bank Cover Letter"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
		},
		{
			fieldname: "company_address",
			label: __("Company Address"),
			fieldtype: "Data",
		},
		{
			fieldname: "bank_name",
			label: __("Bank Name"),
			fieldtype: "Data",
		},
		{
			fieldname: "bank_address",
			label: __("Bank Address"),
			fieldtype: "Data",
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.month_start(),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.month_end(),
			reqd: 1,
		},
		{
			fieldname: "period_title",
			label: __("Period Title"),
			fieldtype: "Data",
			default: __("Salary for the selected period"),
		},
		{
			fieldname: "month_label",
			label: __("Month Label"),
			fieldtype: "Data",
		},
		{
			fieldname: "cheque_no",
			label: __("Cheque No."),
			fieldtype: "Data",
		},
		{
			fieldname: "cheque_date",
			label: __("Cheque Date"),
			fieldtype: "Date",
		},
	],
};

