// Copyright (c) 2026, Sami and contributors
// For license information, please see license.txt

frappe.query_reports["Material Requisition Status"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			width: "100",
			options: "Company",
			reqd: 1,
			default: frappe.defaults.get_default("company"),
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			width: "100",
			reqd: 1,
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			width: "100",
			reqd: 1,
			default: frappe.datetime.get_today(),
		},
		{
			fieldname: "project",
			label: __("Project"),
			fieldtype: "Link",
			options: "Project",
			width: "100px",
		},
		{
			fieldname: "request_type",
			label: __("Request Type"),
			fieldtype: "Select",
			options: ["Material Requisition", "Fuel Request", "Fixed Asset Request"],
			default: "Material Requisition",
			width: "100px",
			on_change: function () {
				const request_type = frappe.query_report.get_filter_value("request_type");
				const mr_filter = frappe.query_report.get_filter("material_requisition");

				let label = __("Material Requisition");
				if (request_type === "Material Requisition") {
					mr_filter.df.options = "Material Request";
					label = __("Material Requisition");
				} else if (request_type === "Fuel Request") {
					mr_filter.df.options = "Fuel Request";
					label = __("Fuel Request");
				} else if (request_type === "Fixed Asset Request") {
					mr_filter.df.options = "Fixed Asset Request";
					label = __("Fixed Asset Request");
				}

				mr_filter.df.label = label;
				frappe.query_report.set_filter_value("material_requisition", "");
				mr_filter.refresh();
				
				// Force update label in DOM
				if (mr_filter.$wrapper) {
					mr_filter.$wrapper.find("label").text(label);
				}
			},
		},
		{
			fieldname: "material_requisition",
			label: __("Material Requisition"),
			fieldtype: "Link",
			options: "Material Request",
			width: "100px",
			get_query: () => {
				const request_type = frappe.query_report.get_filter_value("request_type");
				if (request_type === "Material Requisition") {
					return {
						filters: {
							material_request_type: "Material Issue",
						},
					};
				}
				return {};
			},
		},
		{
			fieldname: "material_request",
			label: __("Purchase Request"),
			fieldtype: "Link",
			width: "80",
			options: "Material Request",
			get_query: () => {
				return {
					filters: {
						docstatus: 1,
						material_request_type: "Purchase",
						per_received: ["<", 100],
					},
				};
			},
		},
		{
			fieldname: "item_code",
			label: __("Item Code"),
			fieldtype: "Link",
			width: "80",
			options: "Item",
			get_query: () => {
				return {
					query: "erpnext.controllers.queries.item_query",
				};
			},
			on_change: function () {
				const item_code = frappe.query_report.get_filter_value("item_code");
				if (item_code) {
					frappe.db.get_value("Item", item_code, "item_name", (r) => {
						if (r && r.item_name) {
							frappe.query_report.set_filter_value("item_name", r.item_name);
						}
					});
				} else {
					frappe.query_report.set_filter_value("item_name", "");
				}
			},
		},
		{
			fieldname: "item_name",
			label: __("Item Name"),
			fieldtype: "Data",
			width: "100",
			read_only: 1,
		},
		{
			fieldname: "group_by_mr",
			label: __("Group by Purchase Request"),
			fieldtype: "Check",
			default: 0,
		},
	],

	formatter: function (value, row, column, data, default_formatter) {
		if (["purchase_orders", "purchase_receipts"].includes(column.fieldname) && value) {
			return value; 
		}

		value = default_formatter(value, row, column, data);

		if (column.fieldname == "ordered_qty" && data && data.ordered_qty > 0) {
			value = "<span style='color:green'>" + value + "</span>";
		}
		
		return value;
	},
};

