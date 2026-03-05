# Copyright (c) 2026, Friends ERP and contributors
# For license information, please see license.txt

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import cint, flt


def execute(filters=None):
	if not filters:
		filters = {}

	filters = frappe._dict(filters)

	if not filters.get("company"):
		frappe.throw(_("Company is required"))

	if not filters.get("material_request"):
		frappe.throw(_("Material Request is required"))

	columns = get_columns()
	data, chart = get_data(filters)

	message = None
	if not data:
		message = _("No Supplier Quotations found for Material Request {0}").format(filters.material_request)

	return columns, data, message, chart


def get_data(filters):
	sq = frappe.qb.DocType("Supplier Quotation")
	sqi = frappe.qb.DocType("Supplier Quotation Item")

	query = (
		frappe.qb.from_(sqi)
		.from_(sq)
		.select(
			sqi.parent.as_("supplier_quotation"),
			sq.supplier.as_("supplier"),
			sqi.item_code,
			sqi.description,
			sqi.qty,
			sqi.uom,
			sqi.stock_qty,
			sqi.stock_uom,
			sq.currency,
			sq.price_list_currency,
			sqi.rate,
			sqi.amount,
			sqi.base_rate,
			sqi.base_amount,
		)
		.where(
			(sqi.parent == sq.name)
			& (sqi.docstatus < 2)
			& (sq.company == filters.company)
			& (sqi.material_request == filters.material_request)
		)
		.orderby(sqi.item_code, sq.supplier)
	)

	if filters.get("from_date") and filters.get("to_date"):
		query = query.where(
			sq.transaction_date.between(filters.get("from_date"), filters.get("to_date"))
		)

	rows = query.run(as_dict=True)

	if not rows:
		return [], None

	# Group by item for per-item ranking, and accumulate supplier totals
	items_map: dict[str, list[dict]] = defaultdict(list)
	supplier_totals = defaultdict(float)

	float_precision = cint(frappe.db.get_default("float_precision")) or 2

	for r in rows:
		price_per_unit = flt(r.base_rate) or flt(r.amount) / (flt(r.stock_qty) or 1)

		row = {
			"item_code": r.item_code,
			"description": r.description,
			"qty": r.qty,
			"uom": r.uom,
			"stock_uom": r.stock_uom,
			"supplier": r.supplier,
			"supplier_quotation": r.supplier_quotation,
			"currency": r.currency,
			"price_list_currency": r.price_list_currency,
			"rate": flt(r.rate, float_precision),
			"amount": flt(r.amount, float_precision),
			"base_rate": flt(r.base_rate, float_precision),
			"base_amount": flt(r.base_amount, float_precision),
			"price_per_unit": flt(price_per_unit, float_precision),
		}

		items_map[r.item_code].append(row)
		supplier_totals[r.supplier] += flt(r.base_amount or 0)

	# Build final data with per-item ranking
	data = []

	for item_code, item_rows in sorted(items_map.items(), key=lambda d: d[0]):
		# Rank suppliers for this item by price per unit (lowest wins)
		sorted_rows = sorted(item_rows, key=lambda x: x["price_per_unit"])
		rank = 0
		last_price = None

		for idx, row in enumerate(sorted_rows):
			price = row["price_per_unit"]
			if last_price is None or price != last_price:
				rank += 1
				last_price = price

			row["rank"] = rank
			row["is_winner"] = 1 if rank == 1 else 0

			# For nicer grouping: show item details only on first row of each item
			if idx > 0:
				row["item_code"] = ""
				row["description"] = ""

			data.append(row)

	# Prepare supplier summary chart (total base amount per supplier)
	labels = list(supplier_totals.keys())
	values = [supplier_totals[s] for s in labels]

	chart = {
		"data": {
			"labels": labels,
			"datasets": [
				{
					"name": _("Total Base Amount"),
					"values": values,
				}
			],
		},
		"type": "bar",
	}

	return data, chart


def get_columns():
	company_currency = frappe.db.get_default("currency") or "ETB"

	return [
		{
			"fieldname": "item_code",
			"label": _("Item"),
			"fieldtype": "Link",
			"options": "Item",
			"width": 140,
		},
		{
			"fieldname": "description",
			"label": _("Description"),
			"fieldtype": "Data",
			"width": 220,
		},
		{
			"fieldname": "qty",
			"label": _("Qty"),
			"fieldtype": "Float",
			"width": 70,
		},
		{
			"fieldname": "uom",
			"label": _("UOM"),
			"fieldtype": "Link",
			"options": "UOM",
			"width": 70,
		},
		{
			"fieldname": "supplier",
			"label": _("Supplier"),
			"fieldtype": "Link",
			"options": "Supplier",
			"width": 160,
		},
		{
			"fieldname": "supplier_quotation",
			"label": _("Supplier Quotation"),
			"fieldtype": "Link",
			"options": "Supplier Quotation",
			"width": 160,
		},
		{
			"fieldname": "currency",
			"label": _("Currency"),
			"fieldtype": "Link",
			"options": "Currency",
			"width": 80,
		},
		{
			"fieldname": "rate",
			"label": _("Rate"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 100,
		},
		{
			"fieldname": "amount",
			"label": _("Amount"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 110,
		},
		{
			"fieldname": "base_rate",
			"label": _("Rate ({0})").format(company_currency),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 110,
		},
		{
			"fieldname": "base_amount",
			"label": _("Amount ({0})").format(company_currency),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 130,
		},
		{
			"fieldname": "price_per_unit",
			"label": _("Price / Unit ({0})").format(company_currency),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 130,
		},
		{
			"fieldname": "rank",
			"label": _("Rank"),
			"fieldtype": "Int",
			"width": 60,
		},
		{
			"fieldname": "is_winner",
			"label": _("Winner"),
			"fieldtype": "Check",
			"width": 70,
		},
	]

