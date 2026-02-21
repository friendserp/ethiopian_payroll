// Copyright (c) 2025, Friends ERP and contributors
// For license information, please see license.txt

frappe.ui.form.on("Pay Matrix", {
	refresh(frm) {
		render_matrix(frm);
		
		// Add button to create Standard Pay Matrix
		if (!frm.doc.name || frm.doc.name !== "Standard") {
			frm.add_custom_button(__("Create Standard Matrix"), function() {
				frappe.confirm(
					__("This will create or recreate the 'Standard' Pay Matrix with all 18 grade levels and 22 scales. Continue?"),
					function() {
						// Yes
						frappe.call({
							method: "ethiopian_payroll.ethiopian_payroll.doctype.pay_matrix.pay_matrix.create_standard_pay_matrix",
							freeze: true,
							freeze_message: __("Creating Standard Pay Matrix..."),
							callback: function(r) {
								if (r && r.message && r.message.success) {
									frappe.msgprint({
										title: __("Success"),
										message: r.message.message,
										indicator: "green"
									});
									// Reload the form if Standard was created
									if (frappe.db.exists("Pay Matrix", "Standard")) {
										frappe.set_route("Form", "Pay Matrix", "Standard");
									}
								} else {
									frappe.msgprint({
										title: __("Error"),
										message: r.message?.message || __("Could not create Standard Pay Matrix"),
										indicator: "red"
									});
								}
							}
						});
					}
				);
			}, __("Actions"));
		}
	},
	add_level(frm) {
		create_pay_matrix_level(frm);
	},
});

async function render_matrix(frm) {
	if (!frm.doc.name) return;

	// Fetch all Pay Matrix Levels for this Pay Matrix
	const level_list = await frappe.db.get_list("Pay Matrix Level", {
		filters: { pay_matrix_link: frm.doc.name },
		fields: ["name", "grade"],
		order_by: "grade asc",
	});

	if (!level_list.length) {
		$(frm.fields_dict.matrix_html.wrapper).html("<p>No data found.</p>");
		return;
	}

	// Fetch full doc for each level to get the child table
	const levels = [];
	for (const lvl of level_list) {
		const full_doc = await frappe.db.get_doc("Pay Matrix Level", lvl.name);
		levels.push(full_doc);
	}

	// Sort levels by grade name numerically
	levels.sort((a, b) => {
		const gradeA = a.grade || "";
		const gradeB = b.grade || "";
		
		// Extract numeric part from grade name (handles both "1" and "Grade 1" formats)
		const numA = parseInt(gradeA.replace(/[^0-9]/g, '')) || 0;
		const numB = parseInt(gradeB.replace(/[^0-9]/g, '')) || 0;
		
		return numA - numB;
	});

	// Prepare matrix data
	let all_scales = new Set();
	const matrix_data = {};

	levels.forEach((lvl) => {
		matrix_data[lvl.grade] = {};
		if (lvl.scales && lvl.scales.length) {
			lvl.scales.forEach((s) => {
				matrix_data[lvl.grade][s.scale] = s.amount;
				all_scales.add(s.scale);
			});
		}
	});

	all_scales = Array.from(all_scales).sort((a, b) => a - b);

	// Build HTML table with styling
	let html = `
	<div class="pm-table-wrapper">
	<table class="pay-matrix-grid">
		<thead>
			<tr>
				<th class="pm-header pm-grade">Grade</th>`;
	all_scales.forEach((scale) => {
		html += `<th class="pm-header pm-scale">${scale}</th>`;
	});
	html += `</tr>
		</thead>
		<tbody>`;

	levels.forEach((lvl) => {
		html += `<tr>
					<td class="pm-header pm-row" data-level-name="${lvl.name}" style="cursor: pointer; text-decoration: underline;">${lvl.grade || ""}</td>`;
		all_scales.forEach((scale) => {
			let amount = matrix_data[lvl.grade][scale] || "";
			if (amount !== "") {
				amount = Number(amount).toLocaleString(); // add comma
			}
			html += `<td class="pm-cell">${amount}</td>`;
		});
		html += `</tr>`;
	});

	html += `</tbody></table>
	</div>
	<style>
		.pm-table-wrapper {
			width: 100%;
			overflow-x: auto;
		}
		.pay-matrix-grid {
			min-width: 960px;
			width: 100%;
			border-collapse: separate;
			border-spacing: 0;
			font-size: 0.7rem;
			text-align: center;
			border: 1px solid #d1d8dd;
			border-radius: 8px;
			overflow: hidden;
			box-shadow: 0 1px 2px rgba(0,0,0,0.05);
		}
		.pay-matrix-grid thead {
			background: #f8f9fa;
		}
		.pay-matrix-grid th,
		.pay-matrix-grid td {
			padding: 6px 8px;
			border-right: 1px solid #e1e6eb;
			border-bottom: 1px solid #e1e6eb;
		}
		.pay-matrix-grid tr:last-child td {
			border-bottom: none;
		}
		.pay-matrix-grid tr td:last-child,
		.pay-matrix-grid tr th:last-child {
			border-right: none;
		}
		.pay-matrix-grid .pm-header {
			font-weight: 600;
			background: #f8f9fa;
		}
		.pay-matrix-grid .pm-grade {
			cursor: pointer;
			text-decoration: underline;
		}
		.pay-matrix-grid .pm-row {
			text-align: left;
			padding-left: 10px;
		}
		.pay-matrix-grid .pm-cell {
			font-size: 0.68rem;
		}
		.pay-matrix-grid tr:hover td {
			background: #fbfcfd;
		}
	</style>`;

	const wrapper = $(frm.fields_dict.matrix_html.wrapper);
	wrapper.html(html);
	bind_grade_clicks(frm, levels);
}

function create_pay_matrix_level(frm) {
	if (!frm.doc.name) {
		frappe.msgprint(__("Please save the Pay Matrix first."));
		return;
	}

	let scales_data = [];

	const d = new frappe.ui.Dialog({
		title: __("Add Pay Matrix Level"),
		fields: [
			{
				fieldname: "grade",
				fieldtype: "Link",
				options: "Employee Grade",
				label: __("Grade"),
				reqd: 1,
			},
			{
				fieldname: "scales_html",
				fieldtype: "HTML",
				options: "",
			},
		],
		primary_action_label: __("Create"),
		primary_action: async (values) => {
			if (!values) return;
			try {
				// Get data from custom table
				const scales = get_scales_from_table();
				
				if (!scales || scales.length === 0) {
					frappe.msgprint({
						title: __("Validation Error"),
						message: __("Please add at least one scale entry"),
						indicator: "orange",
					});
					return;
				}

				// Format for insert
				const scales_formatted = scales.map((row) => ({
					doctype: "Pay Matrix Scale Items",
					scale: row.scale,
					amount: row.amount,
				}));

				await frappe.call({
					method: "frappe.client.insert",
					args: {
						doc: {
							doctype: "Pay Matrix Level",
							grade: values.grade,
							pay_matrix_link: frm.doc.name,
							scales: scales_formatted,
						},
					},
					freeze: true,
					freeze_message: __("Creating Level..."),
				});
				d.hide();
				frappe.msgprint(__("Pay Matrix Level created"));
				render_matrix(frm);
			} catch (e) {
				console.error(e);
				frappe.msgprint({
					title: __("Error"),
					message: e.message || __("Could not create Pay Matrix Level"),
					indicator: "red",
				});
			}
		},
	});

	// Function to get scales data from custom table
	function get_scales_from_table() {
		const rows = d.$wrapper.find(".custom-scales-table tbody tr");
		const scales = [];
		rows.each(function () {
			const $row = $(this);
			const scale = parseInt($row.find('input[name="scale"]').val());
			const amount = parseFloat($row.find('input[name="amount"]').val());
			if (scale && !isNaN(amount)) {
				scales.push({ scale: scale, amount: amount });
			}
		});
		return scales;
	}

	// Function to render custom table
	function render_custom_table() {
		const scales_html = `
			<div class="custom-scales-container">
				<label class="control-label">${__("Scales (Scale / Amount)")}</label>
				<table class="custom-scales-table table table-bordered" style="margin-top: 10px;">
					<thead>
						<tr>
							<th style="width: 40%;">${__("Scale")}</th>
							<th style="width: 50%;">${__("Amount")}</th>
							<th style="width: 10%;"></th>
						</tr>
					</thead>
					<tbody>
						${scales_data.map((row, idx) => `
							<tr data-index="${idx}">
								<td>
									<input type="number" name="scale" class="form-control" value="${row.scale || ""}" placeholder="${__("Scale")}" min="1" />
								</td>
								<td>
									<input type="number" name="amount" class="form-control" value="${row.amount || ""}" step="0.01" placeholder="${__("Amount")}" />
								</td>
								<td>
									<button type="button" class="btn btn-sm btn-secondary remove-row" style="width: 100%;">
										${__("Remove")}
									</button>
								</td>
							</tr>
						`).join("")}
					</tbody>
				</table>
				<button type="button" class="btn btn-sm btn-primary add-scale-row" style="margin-top: 10px;">
					${__("Add Row")}
				</button>
			</div>
			<style>
				.custom-scales-container {
					margin: 15px 0;
				}
				.custom-scales-table {
					font-size: 12px;
				}
				.custom-scales-table input {
					font-size: 12px;
					padding: 4px 8px;
				}
				.custom-scales-table th {
					background: #f8f9fa;
					font-weight: 600;
					padding: 8px;
				}
				.custom-scales-table td {
					padding: 4px;
					vertical-align: middle;
				}
			</style>
		`;
		
		d.fields_dict.scales_html.$wrapper.html(scales_html);
		
		// Bind add row button
		d.$wrapper.find(".add-scale-row").on("click", function () {
			const new_row = `
				<tr>
					<td>
						<input type="number" name="scale" class="form-control" value="" placeholder="${__("Scale")}" min="1" />
					</td>
					<td>
						<input type="number" name="amount" class="form-control" value="" step="0.01" placeholder="${__("Amount")}" />
					</td>
					<td>
						<button type="button" class="btn btn-sm btn-secondary remove-row" style="width: 100%;">
							${__("Remove")}
						</button>
					</td>
				</tr>
			`;
			d.$wrapper.find(".custom-scales-table tbody").append(new_row);
		});
		
		// Bind remove row buttons (using event delegation)
		d.$wrapper.on("click", ".remove-row", function () {
			$(this).closest("tr").remove();
		});
	}

	// Render table after dialog is shown
	d.show();
	setTimeout(() => {
		render_custom_table();
	}, 100);
}

function bind_grade_clicks(frm, levels) {
	const wrapper = $(frm.fields_dict.matrix_html.wrapper);
	wrapper.find("td[data-level-name]").on("click", async function (e) {
		e.preventDefault();
		const level_name = $(this).data("level-name");
		// Fetch fresh document with child tables
		const level_doc = await frappe.db.get_doc("Pay Matrix Level", level_name);
		if (level_doc) {
			edit_pay_matrix_level(frm, level_doc);
		}
	});
}

function edit_pay_matrix_level(frm, level_doc) {
	// Prepare initial scales data
	let scales_data = (level_doc.scales || []).map((row) => ({
		scale: row.scale,
		amount: row.amount,
	}));

	const d = new frappe.ui.Dialog({
		title: __("Edit Pay Matrix Level"),
		fields: [
			{
				fieldname: "grade",
				fieldtype: "Link",
				options: "Employee Grade",
				label: __("Grade"),
				reqd: 1,
				default: level_doc.grade || "",
			},
			{
				fieldname: "scales_html",
				fieldtype: "HTML",
				options: "",
			},
		],
		primary_action_label: __("Update"),
		primary_action: async (values) => {
			if (!values) return;
			try {
				// Get data from custom table
				const scales = get_scales_from_table();
				
				if (!scales || scales.length === 0) {
					frappe.msgprint({
						title: __("Validation Error"),
						message: __("Please add at least one scale entry"),
						indicator: "orange",
					});
					return;
				}

				// Call Python method to update
				const result = await frappe.call({
					method: "ethiopian_payroll.ethiopian_payroll.doctype.pay_matrix.pay_matrix.update_pay_matrix_level",
					args: {
						level_name: level_doc.name,
						grade: values.grade,
						pay_matrix_link: level_doc.pay_matrix_link || frm.doc.name,
						scales_data: scales,
					},
					freeze: true,
					freeze_message: __("Updating Level..."),
				});
				
				if (result && result.message && result.message.success) {
					d.hide();
					frappe.msgprint(__("Pay Matrix Level updated"));
					render_matrix(frm);
				} else {
					throw new Error(result?.message?.message || __("Could not update Pay Matrix Level"));
				}
			} catch (e) {
				console.error(e);
				frappe.msgprint({
					title: __("Error"),
					message: e.message || __("Could not update Pay Matrix Level"),
					indicator: "red",
				});
			}
		},
	});

	// Function to get scales data from custom table
	function get_scales_from_table() {
		const rows = d.$wrapper.find(".custom-scales-table tbody tr");
		const scales = [];
		rows.each(function () {
			const $row = $(this);
			const scale = parseInt($row.find('input[name="scale"]').val());
			const amount = parseFloat($row.find('input[name="amount"]').val());
			if (scale && !isNaN(amount)) {
				scales.push({ scale: scale, amount: amount });
			}
		});
		return scales;
	}

	// Function to render custom table
	function render_custom_table() {
		const scales_html = `
			<div class="custom-scales-container">
				<label class="control-label">${__("Scales (Scale / Amount)")}</label>
				<table class="custom-scales-table table table-bordered" style="margin-top: 10px;">
					<thead>
						<tr>
							<th style="width: 40%;">${__("Scale")}</th>
							<th style="width: 50%;">${__("Amount")}</th>
							<th style="width: 10%;"></th>
						</tr>
					</thead>
					<tbody>
						${scales_data.map((row, idx) => `
							<tr data-index="${idx}">
								<td>
									<input type="number" name="scale" class="form-control" value="${row.scale || ""}" placeholder="${__("Scale")}" min="1" />
								</td>
								<td>
									<input type="number" name="amount" class="form-control" value="${row.amount || ""}" step="0.01" placeholder="${__("Amount")}" />
								</td>
								<td>
									<button type="button" class="btn btn-sm btn-secondary remove-row" style="width: 100%;">
										${__("Remove")}
									</button>
								</td>
							</tr>
						`).join("")}
					</tbody>
				</table>
				<button type="button" class="btn btn-sm btn-primary add-scale-row" style="margin-top: 10px;">
					${__("Add Row")}
				</button>
			</div>
			<style>
				.custom-scales-container {
					margin: 15px 0;
				}
				.custom-scales-table {
					font-size: 12px;
				}
				.custom-scales-table input {
					font-size: 12px;
					padding: 4px 8px;
				}
				.custom-scales-table th {
					background: #f8f9fa;
					font-weight: 600;
					padding: 8px;
				}
				.custom-scales-table td {
					padding: 4px;
					vertical-align: middle;
				}
			</style>
		`;
		
		d.fields_dict.scales_html.$wrapper.html(scales_html);
		
		// Bind add row button
		d.$wrapper.find(".add-scale-row").on("click", function () {
			const new_row = `
				<tr>
					<td>
						<input type="number" name="scale" class="form-control" value="" placeholder="${__("Scale")}" min="1" />
					</td>
					<td>
						<input type="number" name="amount" class="form-control" value="" step="0.01" placeholder="${__("Amount")}" />
					</td>
					<td>
						<button type="button" class="btn btn-sm btn-secondary remove-row" style="width: 100%;">
							${__("Remove")}
						</button>
					</td>
				</tr>
			`;
			d.$wrapper.find(".custom-scales-table tbody").append(new_row);
		});
		
		// Bind remove row buttons (using event delegation)
		d.$wrapper.on("click", ".remove-row", function () {
			$(this).closest("tr").remove();
		});
	}

	// Render table after dialog is shown
	d.show();
	setTimeout(() => {
		render_custom_table();
	}, 100);

	d.set_secondary_action_label(__("Delete"));
	d.set_secondary_action(async () => {
		frappe.confirm(
			__("Delete this Pay Matrix Level and its rows?"),
			async () => {
				try {
					await frappe.call({
						method: "frappe.client.delete",
						args: {
							doctype: "Pay Matrix Level",
							name: level_doc.name,
						},
						freeze: true,
						freeze_message: __("Deleting Level..."),
					});
					d.hide();
					frappe.msgprint(__("Pay Matrix Level deleted"));
					render_matrix(frm);
				} catch (e) {
					console.error(e);
					frappe.msgprint({
						title: __("Error"),
						message: e.message || __("Could not delete Pay Matrix Level"),
						indicator: "red",
					});
				}
			}
		);
	});

	d.show();
}
