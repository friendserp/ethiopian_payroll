// Copyright (c) 2026, Friends ERP and contributors
// For license information, please see license.txt

frappe.query_reports["MR Supplier Quotation Comparison"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			reqd: 1,
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "material_request",
			label: __("Material Request"),
			fieldtype: "Link",
			options: "Material Request",
			reqd: 1,
			get_query: () => {
				return {
					filters: {
						material_request_type: "Purchase",
						docstatus: ["<", 2],
					},
				};
			},
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			width: "80",
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			width: "80",
		},
	],

	formatter: (value, row, column, data, default_formatter) => {
		value = default_formatter(value, row, column, data);

		// Highlight winners
		if (column.fieldname === "price_per_unit" && data && data.is_winner) {
			value = `<b style="color:green">${value}</b>`;
		}

		if (column.fieldname === "rank" && data && data.rank === 1) {
			value = `<b style="color:green">${value}</b>`;
		}

		return value;
	},
};

