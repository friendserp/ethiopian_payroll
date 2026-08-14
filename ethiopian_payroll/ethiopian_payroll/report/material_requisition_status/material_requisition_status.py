# Copyright (c) 2026, Sami and contributors
# For license information, please see license.txt

import copy
import frappe
from frappe import _
from frappe.query_builder.functions import Coalesce, Sum
from frappe.utils import cint, date_diff, flt, getdate

def execute(filters=None):
	if not filters:
		return [], []

	validate_filters(filters)

	columns = get_columns(filters)
	data = get_data(filters)

	# prepare data for report and chart views
	data, chart_data = prepare_data(data, filters)

	return columns, data, None, chart_data

def validate_filters(filters):
	from_date, to_date = filters.get("from_date"), filters.get("to_date")

	if not from_date and to_date:
		frappe.throw(_("From and To Dates are required."))
	elif date_diff(to_date, from_date) < 0:
		frappe.throw(_("To Date cannot be before From Date."))

def get_data(filters):
	mr = frappe.qb.DocType("Material Request")
	mr_item = frappe.qb.DocType("Material Request Item")

	request_type = filters.get("request_type")
	
	if request_type == "Fuel Request":
		requisition_field = Coalesce(mr_item.custom_fuel_request, mr.custom_fuel_request)
	elif request_type == "Fixed Asset Request":
		requisition_field = Coalesce(mr_item.custom_far_no, mr.custom_fixed_asset_request)
	else: # Material Requisition
		requisition_field = Coalesce(mr_item.custom_mr_number, mr.custom_mr_no)

	query = (
		frappe.qb.from_(mr)
		.join(mr_item)
		.on(mr_item.parent == mr.name)
		.select(
			requisition_field.as_("material_requisition"),
			mr.name.as_("material_request"),
			mr.custom_project.as_("project"),
			mr.transaction_date.as_("date"),
			mr_item.schedule_date.as_("required_date"),
			mr_item.item_code.as_("item_code"),
			Sum(Coalesce(mr_item.qty, 0)).as_("qty"),
			Coalesce(mr_item.uom, "").as_("uom"),
			Sum(Coalesce(mr_item.ordered_qty, 0)).as_("ordered_qty"),
			Sum(Coalesce(mr_item.received_qty, 0)).as_("received_qty"),
			(Sum(Coalesce(mr_item.qty, 0)) - Sum(Coalesce(mr_item.received_qty, 0))).as_(
				"qty_to_receive"
			),
			(Sum(Coalesce(mr_item.qty, 0)) - Sum(Coalesce(mr_item.ordered_qty, 0))).as_("qty_to_order"),
			mr_item.item_name,
			mr_item.description,
			mr.company,
			mr_item.name.as_("mr_item"),
		)
		.where(
			(mr.material_request_type == "Purchase")
			& (mr.docstatus == 1)
			& (mr.status != "Stopped")
			& (mr.per_received < 100)
		)
	)

	query = get_conditions(filters, query, mr, mr_item)  # add conditional conditions

	query = query.groupby(mr.name, mr_item.item_code).orderby(mr.transaction_date, mr_item.schedule_date)
	data = query.run(as_dict=True)
	return data

def get_conditions(filters, query, mr, mr_item):
	if filters.get("from_date") and filters.get("to_date"):
		query = query.where(
			(mr.transaction_date >= filters.get("from_date"))
			& (mr.transaction_date <= filters.get("to_date"))
		)
	if filters.get("company"):
		query = query.where(mr.company == filters.get("company"))

	if filters.get("project"):
		query = query.where(mr.custom_project == filters.get("project"))

	if filters.get("material_request"):
		query = query.where(mr.name == filters.get("material_request"))

	if filters.get("item_code"):
		query = query.where(mr_item.item_code == filters.get("item_code"))

	request_type = filters.get("request_type")
	if request_type == "Fuel Request":
		query = query.where(
			(mr.custom_fuel_request.isnotnull()) | (mr_item.custom_fuel_request.isnotnull())
		)
	elif request_type == "Fixed Asset Request":
		query = query.where(
			(mr.custom_fixed_asset_request.isnotnull()) | (mr_item.custom_far_no.isnotnull())
		)
	else: # Material Requisition
		query = query.where(
			(mr.custom_mr_no.isnotnull()) | (mr_item.custom_mr_number.isnotnull())
		)

	if filters.get("material_requisition"):
		mr_no = filters.get("material_requisition")
		if request_type == "Fuel Request":
			query = query.where(
				(mr.custom_fuel_request == mr_no) | (mr_item.custom_fuel_request == mr_no)
			)
		elif request_type == "Fixed Asset Request":
			query = query.where(
				(mr.custom_fixed_asset_request == mr_no) | (mr_item.custom_far_no == mr_no)
			)
		else: # Material Requisition
			query = query.where(
				(mr.custom_mr_no == mr_no) | (mr_item.custom_mr_number == mr_no)
			)

	return query

def update_qty_columns(row_to_update, data_row):
	fields = ["qty", "ordered_qty", "received_qty", "qty_to_receive", "qty_to_order"]
	for field in fields:
		row_to_update[field] += flt(data_row[field])

def prepare_data(data, filters):
	"""Prepare consolidated Report data and Chart data"""
	material_request_map, item_qty_map = {}, {}
	precision = cint(frappe.db.get_default("float_precision")) or 2

	# Pre-fetch linked POs and PRs to avoid multiple queries in loop
	mr_item_names = [row["mr_item"] for row in data]
	
	po_links = {}
	if mr_item_names:
		pos = frappe.get_all("Purchase Order Item", 
			filters={"material_request_item": ["in", mr_item_names], "docstatus": ["<", 2]},
			fields=["material_request_item", "parent"]
		)
		for po in pos:
			if po.material_request_item not in po_links:
				po_links[po.material_request_item] = set()
			po_links[po.material_request_item].add(po.parent)

	pr_links = {}
	if mr_item_names:
		prs = frappe.get_all("Purchase Receipt Item", 
			filters={"material_request_item": ["in", mr_item_names], "docstatus": ["<", 2]},
			fields=["material_request_item", "parent"]
		)
		for pr in prs:
			if pr.material_request_item not in pr_links:
				pr_links[pr.material_request_item] = set()
			pr_links[pr.material_request_item].add(pr.parent)

	for row in data:
		# Add links to row
		po_list = sorted(list(po_links.get(row["mr_item"], [])))
		row["purchase_orders"] = ", ".join([f'<a href="/app/purchase-order/{po}">{po}</a>' for po in po_list])
		
		pr_list = sorted(list(pr_links.get(row["mr_item"], [])))
		row["purchase_receipts"] = ", ".join([f'<a href="/app/purchase-receipt/{pr}">{pr}</a>' for pr in pr_list])

		# item wise map for charts
		item_key = row["item_code"]
		if row.get("item_name"):
			item_key = f"{row['item_code']}: {row['item_name']}"

		if item_key not in item_qty_map:
			item_qty_map[item_key] = {
				"qty": flt(row["qty"], precision),
				"ordered_qty": flt(row["ordered_qty"], precision),
				"received_qty": flt(row["received_qty"], precision),
				"qty_to_receive": flt(row["qty_to_receive"], precision),
				"qty_to_order": flt(row["qty_to_order"], precision),
			}
		else:
			item_entry = item_qty_map[item_key]
			update_qty_columns(item_entry, row)

		if filters.get("group_by_mr"):
			# consolidated material request map for group by filter
			if row["material_request"] not in material_request_map:
				# create an entry with mr as key
				row_copy = copy.deepcopy(row)
				material_request_map[row["material_request"]] = row_copy
				# Initialize sets for links when grouping
				row_copy["po_set"] = po_links.get(row["mr_item"], set()).copy()
				row_copy["pr_set"] = pr_links.get(row["mr_item"], set()).copy()
			else:
				mr_row = material_request_map[row["material_request"]]
				mr_row["required_date"] = min(getdate(mr_row["required_date"]), getdate(row["required_date"]))

				# sum numeric columns
				update_qty_columns(mr_row, row)
				# Update sets for links
				mr_row["po_set"].update(po_links.get(row["mr_item"], set()))
				mr_row["pr_set"].update(pr_links.get(row["mr_item"], set()))

	chart_data = prepare_chart_data(item_qty_map)

	if filters.get("group_by_mr"):
		data = []
		for mr in material_request_map:
			mr_row = material_request_map[mr]
			po_list = sorted(list(mr_row.get("po_set", [])))
			mr_row["purchase_orders"] = ", ".join([f'<a href="/app/purchase-order/{po}">{po}</a>' for po in po_list])
			
			pr_list = sorted(list(mr_row.get("pr_set", [])))
			mr_row["purchase_receipts"] = ", ".join([f'<a href="/app/purchase-receipt/{pr}">{pr}</a>' for pr in pr_list])
			data.append(mr_row)
		return data, chart_data

	return data, chart_data

def prepare_chart_data(item_data):
	labels, qty_to_order, ordered_qty, received_qty, qty_to_receive = [], [], [], [], []

	if len(item_data) > 30:
		item_data = dict(list(item_data.items())[:30])

	for row in item_data:
		mr_row = item_data[row]
		labels.append(row)
		qty_to_order.append(mr_row["qty_to_order"])
		ordered_qty.append(mr_row["ordered_qty"])
		received_qty.append(mr_row["received_qty"])
		qty_to_receive.append(mr_row["qty_to_receive"])

	chart_data = {
		"data": {
			"labels": labels,
			"datasets": [
				{"name": _("Qty to Order"), "values": qty_to_order},
				{"name": _("Ordered Qty"), "values": ordered_qty},
				{"name": _("Received Qty"), "values": received_qty},
				{"name": _("Qty to Receive"), "values": qty_to_receive},
			],
		},
		"type": "bar",
		"barOptions": {"stacked": 1},
	}

	return chart_data

def get_columns(filters):
	request_type = filters.get("request_type") or "Material Requisition"
	
	columns = [
		{
			"label": _(request_type),
			"fieldname": "material_requisition",
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"label": _("Purchase Request"),
			"fieldname": "material_request",
			"fieldtype": "Link",
			"options": "Material Request",
			"width": 150,
		},
		{
			"label": _("Project"),
			"fieldname": "project",
			"fieldtype": "Link",
			"options": "Project",
			"width": 120,
		},
		{"label": _("Date"), "fieldname": "date", "fieldtype": "Date", "width": 90},
		{"label": _("Required By"), "fieldname": "required_date", "fieldtype": "Date", "width": 100},
	]

	if not filters.get("group_by_mr"):
		columns.extend(
			[
				{
					"label": _("Item Code"),
					"fieldname": "item_code",
					"fieldtype": "Link",
					"options": "Item",
					"width": 100,
				},
				{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 100},
				{"label": _("Description"), "fieldname": "description", "fieldtype": "Data", "width": 200},
				{
					"label": _("UOM"),
					"fieldname": "uom",
					"fieldtype": "Data",
					"width": 100,
				}
			]
		)

	columns.extend(
		[
			{
				"label": _("Qty"),
				"fieldname": "qty",
				"fieldtype": "Float",
				"width": 100,
				"convertible": "qty",
			},
			{
				"label": _("Ordered Qty"),
				"fieldname": "ordered_qty",
				"fieldtype": "Float",
				"width": 100,
				"convertible": "qty",
			},
			{
				"label": _("Purchase Orders"),
				"fieldname": "purchase_orders",
				"fieldtype": "Data",
				"width": 150,
			},
			{
				"label": _("Received Qty"),
				"fieldname": "received_qty",
				"fieldtype": "Float",
				"width": 100,
				"convertible": "qty",
			},
			{
				"label": _("Purchase Receipts"),
				"fieldname": "purchase_receipts",
				"fieldtype": "Data",
				"width": 150,
			},
			{
				"label": _("Qty to Receive"),
				"fieldname": "qty_to_receive",
				"fieldtype": "Float",
				"width": 100,
				"convertible": "qty",
			},
			{
				"label": _("Qty to Order"),
				"fieldname": "qty_to_order",
				"fieldtype": "Float",
				"width": 100,
				"convertible": "qty",
			},
			{
				"label": _("Company"),
				"fieldname": "company",
				"fieldtype": "Link",
				"options": "Company",
				"width": 100,
			},
		]
	)

	return columns

