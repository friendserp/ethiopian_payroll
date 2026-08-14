# Copyright (c) 2026, Sami and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, formatdate

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {"label": _("Project"), "fieldname": "project", "fieldtype": "Data", "width": 200},
        {"label": _("Name of Employees"), "fieldname": "employee_name", "fieldtype": "Data", "width": 180},
        {"label": _("Job Title"), "fieldname": "designation", "fieldtype": "Data", "width": 150},
        {"label": _("Basic Salary"), "fieldname": "basic", "fieldtype": "Currency", "width": 120},
        {"label": _("Working Days"), "fieldname": "working_days", "fieldtype": "Float", "width": 100},
        {"label": _("Basic Earning"), "fieldname": "basic_earning", "fieldtype": "Currency", "width": 120},
        {"label": _("Perdiem Days"), "fieldname": "perdiem_days", "fieldtype": "Float", "width": 100},
        {"label": _("Resp. Allow."), "fieldname": "resp_allow", "fieldtype": "Currency", "width": 120},
        {"label": _("Profe. Allow."), "fieldname": "profe_allow", "fieldtype": "Currency", "width": 120},
        {"label": _("Project Allow."), "fieldname": "project_allow", "fieldtype": "Currency", "width": 120},
        {"label": _("Transp Allow. (Taxable)"), "fieldname": "transp_taxable", "fieldtype": "Currency", "width": 120},
        {"label": _("House Allow."), "fieldname": "house_allow", "fieldtype": "Currency", "width": 120},
        {"label": _("Transp Allow. (Non Taxable)"), "fieldname": "transp_nontaxable", "fieldtype": "Currency", "width": 120},
        {"label": _("Perdiem Taxable Rate"), "fieldname": "perdiem_taxable_rate", "fieldtype": "Currency", "width": 120},
        {"label": _("Perdiem Taxable Payable"), "fieldname": "perdiem_taxable_payable", "fieldtype": "Currency", "width": 120},
        {"label": _("Perdiem Non Taxable Rate"), "fieldname": "perdiem_nontaxable_rate", "fieldtype": "Currency", "width": 120},
        {"label": _("Perdiem Non Taxable Payable"), "fieldname": "perdiem_nontaxable_payable", "fieldtype": "Currency", "width": 120},
        {"label": _("N.Hr 1.5"), "fieldname": "ot_normal_hr", "fieldtype": "Float", "width": 80},
        {"label": _("Ngt 1.75"), "fieldname": "ot_night_hr", "fieldtype": "Float", "width": 80},
        {"label": _("Sun 2"), "fieldname": "ot_sunday_hr", "fieldtype": "Float", "width": 80},
        {"label": _("H.D 2.5"), "fieldname": "ot_holiday_hr", "fieldtype": "Float", "width": 80},
        {"label": _("Overtime Cost"), "fieldname": "ot_cost", "fieldtype": "Currency", "width": 120},
        {"label": _("Gross Earned"), "fieldname": "gross_earned", "fieldtype": "Currency", "width": 120},
        {"label": _("Taxable Salary"), "fieldname": "taxable_salary", "fieldtype": "Currency", "width": 120},
        {"label": _("Income Tax"), "fieldname": "income_tax", "fieldtype": "Currency", "width": 120},
        {"label": _("Pension 7%"), "fieldname": "pension_7", "fieldtype": "Currency", "width": 100},
        {"label": _("Pension 11%"), "fieldname": "pension_11", "fieldtype": "Currency", "width": 100},
        {"label": _("Other Deductions"), "fieldname": "other_deductions", "fieldtype": "Currency", "width": 120},
        {"label": _("Total Deductions"), "fieldname": "total_deductions", "fieldtype": "Currency", "width": 120},
        {"label": _("Net Pay"), "fieldname": "net_pay", "fieldtype": "Currency", "width": 120}
    ]

def get_data(filters):
    data = []
    
    # Get Salary Slips based on filters
    ss_filters = {
        "docstatus": 1,
        "company": filters.get("company")
    }
    
    if filters.get("from_date"):
        ss_filters["start_date"] = [">=", filters.get("from_date")]
    if filters.get("to_date"):
        ss_filters["end_date"] = ["<=", filters.get("to_date")]
        
    if filters.get("project"):
        # Since project is on Payroll Entry, we might need to filter by it
        payroll_entries = frappe.get_all("Payroll Entry", filters={"project": filters.get("project")}, pluck="name")
        if payroll_entries:
            ss_filters["payroll_entry"] = ["in", payroll_entries]
        else:
            return []

    salary_slips = frappe.get_all("Salary Slip", 
        filters=ss_filters,
        fields=["name", "employee", "employee_name", "designation", "payment_days", "total_deduction", "net_pay", "payroll_entry", "start_date", "end_date"],
        order_by="employee_name"
    )

    site_projects = ["Lot-2 Fitesha Sululta Town Road", "Seada", "Lege Tafo Building"]

    for idx, ss in enumerate(salary_slips, start=1):
        payroll = None
        if ss.payroll_entry:
            payroll = frappe.get_cached_doc("Payroll Entry", ss.payroll_entry)
        
        project_name = (payroll.project if payroll else None) or (payroll.payroll_name if payroll else None) or "Head Office"
        is_site_project = project_name in site_projects
        project_prefix = "Projects" if is_site_project else "Head Office"
        
        row = frappe._dict({
            "project": project_name,
            "employee_name": ss.employee_name,
            "designation": ss.designation,
            "basic": 0,
            "working_days": ss.payment_days,
            "basic_earning": 0,
            "perdiem_days": 0,
            "resp_allow": 0,
            "profe_allow": 0,
            "project_allow": 0,
            "transp_taxable": 0,
            "house_allow": 0,
            "transp_nontaxable": 0,
            "perdiem_taxable_rate": 0,
            "perdiem_taxable_payable": 0,
            "perdiem_nontaxable_rate": 0,
            "perdiem_nontaxable_payable": 0,
            "ot_normal_hr": 0,
            "ot_night_hr": 0,
            "ot_sunday_hr": 0,
            "ot_holiday_hr": 0,
            "ot_cost": 0,
            "gross_earned": 0,
            "taxable_salary": 0,
            "income_tax": 0,
            "pension_7": 0,
            "pension_11": 0,
            "other_deductions": 0,
            "total_deductions": ss.total_deduction,
            "net_pay": ss.net_pay
        })

        # Get Earnings and Deductions
        details = frappe.get_all("Salary Detail", 
            filters={"parent": ss.name}, 
            fields=["salary_component", "amount", "parentfield"]
        )
        
        resp_prefix = project_prefix + " Responsibility Allowance"
        profe_prefix = project_prefix + " Professional Allowance"
        project_prefix_comp = project_prefix + " Project Allowance"
        transp_tax_prefix = project_prefix + " Taxable Transport Allowance"
        transp_nontax_prefix = project_prefix + " Non Taxable Transport Allowance"
        
        # Component identification logic as per print format
        for d in details:
            comp = d.salary_component
            amt = flt(d.amount)
            
            if d.parentfield == "earnings":
                if comp == "Basic":
                    row.basic = amt
                elif comp in [resp_prefix, "Head Office Responsibility Allowance", "Projects Responsibility Allowance", "Responsibility Allowance"]:
                    row.resp_allow = amt
                elif comp in [profe_prefix, "Head Office Professional Allowance", "Projects Professional Allowance", "Professional Allowance"]:
                    row.profe_allow = amt
                elif comp in [project_prefix_comp, "Head Office Project Allowance", "Projects Project Allowance", "Project Allowance"]:
                    row.project_allow = amt
                elif comp in [transp_tax_prefix, "Head Office Taxable Transport Allowance", "Projects Taxable Transport Allowance", "Taxable Transport Allowance"]:
                    row.transp_taxable = amt
                elif comp in ["Head Office House Allowance", "Projects House Allowance", "House Allowance"]:
                    row.house_allow = amt
                elif comp in [transp_nontax_prefix, "Head Office Non Taxable Transport Allowance", "Projects Non Taxable Transport Allowance", "Non Taxable Transport Allowance"]:
                    row.transp_nontaxable = amt
            else:
                # Deductions
                # Income Tax
                income_tax_comps = []
                if is_site_project:
                    if project_name == "Lot-2 Fitesha Sululta Town Road":
                        income_tax_comps = ["Sululta Income Tax", "Income Tax"]
                    elif project_name == "Seada":
                        income_tax_comps = ["Seada Income Tax", "Income Tax"]
                    elif project_name == "Lege Tafo Building":
                        income_tax_comps = ["Lefetafo Income Tax", "Income Tax"]
                    else:
                        income_tax_comps = ["Head Office Income Tax", "Income Tax"]
                else:
                    income_tax_comps = ["Head Office Income Tax", "Income Tax"]
                
                if comp in income_tax_comps:
                    row.income_tax = amt
                
                # Pension 7%
                pension_7_comps = []
                if is_site_project:
                    if project_name == "Lot-2 Fitesha Sululta Town Road":
                        pension_7_comps = ["Sululta Pension 7%", "Pension 7%"]
                    elif project_name == "Seada":
                        pension_7_comps = ["Seada Pension 7%", "Pension 7%"]
                    elif project_name == "Lege Tafo Building":
                        pension_7_comps = ["Legetafo Pension 7%", "Pension 7%"]
                    else:
                        pension_7_comps = ["Head Office Pension 7%", "Pension 7%"]
                else:
                    pension_7_comps = ["Head Office Pension 7%", "Pension 7%"]
                
                if comp in pension_7_comps:
                    row.pension_7 = amt
                
                # Pension 11%
                pension_11_prefix = project_prefix + " Pension 11%"
                if comp in [pension_11_prefix, "Head Office Pension 11%", "Projects Pension 11%", "Pension 11%"]:
                    row.pension_11 = amt
                
                # Other Deductions
                if comp == "Other Deduction":
                    row.other_deductions += amt

        # Fetch Bulk Additional Salary
        additional_salaries = frappe.get_all("Additional Salary",
            filters={
                "employee": ss.employee,
                "payroll_date": ["between", [ss.start_date, ss.end_date]],
                "docstatus": 1
            },
            fields=["name", "custom_bulk_additional_salary"]
        )

        # Process each additional salary record
        for add_salary in additional_salaries:
            if add_salary.custom_bulk_additional_salary:
                bulk_salary = frappe.get_doc("Bulk Additional Salary", add_salary.custom_bulk_additional_salary)
                for item in bulk_salary.items:
                    if item.employee == ss.employee:
                        if hasattr(item, "payment_days") and item.payment_days:
                            row.perdiem_days = flt(item.payment_days)
                        
                        if hasattr(item, "perdium_type"):
                            if item.perdium_type == "Taxable":
                                row.perdiem_taxable_rate = flt(item.perdium_rate)
                                row.perdiem_taxable_payable = flt(item.perdium_amount)
                            elif item.perdium_type == "Non Taxable":
                                row.perdiem_nontaxable_rate = flt(item.perdium_rate)
                                row.perdiem_nontaxable_payable = flt(item.perdium_amount)
                        
                        if hasattr(item, "ot_normal_hr"):
                            row.ot_normal_hr = flt(item.ot_normal_hr)
                            row.ot_night_hr = flt(item.ot_night_hr)
                            row.ot_sunday_hr = flt(item.ot_sunday_hr)
                            row.ot_holiday_hr = flt(item.ot_holiday_hr)
                            row.ot_cost = flt(item.total_ot_amount)
                        
                        # FIXED: Correctly fetch other_deduction_amount
                        if hasattr(item, "other_deduction_amount") and item.other_deduction_amount:
                            row.other_deductions = flt(item.other_deduction_amount)  # Use = instead of +=

        # Calculate Gross Earned
        row.gross_earned = (row.basic + row.resp_allow + row.profe_allow + row.project_allow + 
                           row.transp_taxable + row.house_allow + row.transp_nontaxable + 
                           row.perdiem_taxable_payable + row.perdiem_nontaxable_payable + row.ot_cost)
        
        # Calculate Basic Earning: basic salary * working day / 30
        employee_salary = frappe.db.get_value("Employee", ss.employee, "custom_salary") or 0
        row.basic_earning = flt(employee_salary) * flt(ss.payment_days) / 30
        
        # Calculate Taxable Salary: Gross Earned - Non Taxable Components
        row.taxable_salary = row.gross_earned - row.transp_nontaxable - row.perdiem_nontaxable_payable
        
        data.append(row)
        
    if data:
        total_row = frappe._dict({
            "project": _("Total"),
            "employee_name": "",
            "designation": "",
            "basic": 0,
            "working_days": 0,
            "basic_earning": 0,
            "perdiem_days": 0,
            "resp_allow": 0,
            "profe_allow": 0,
            "project_allow": 0,
            "transp_taxable": 0,
            "house_allow": 0,
            "transp_nontaxable": 0,
            "perdiem_taxable_rate": 0,
            "perdiem_taxable_payable": 0,
            "perdiem_nontaxable_rate": 0,
            "perdiem_nontaxable_payable": 0,
            "ot_normal_hr": 0,
            "ot_night_hr": 0,
            "ot_sunday_hr": 0,
            "ot_holiday_hr": 0,
            "ot_cost": 0,
            "gross_earned": 0,
            "taxable_salary": 0,
            "income_tax": 0,
            "pension_7": 0,
            "pension_11": 0,
            "other_deductions": 0,
            "total_deductions": 0,
            "net_pay": 0,
            "is_total_row": True
        })
        
        for row in data:
            total_row.basic += row.basic
            total_row.working_days += row.working_days
            total_row.basic_earning += row.basic_earning
            total_row.perdiem_days += row.perdiem_days
            total_row.resp_allow += row.resp_allow
            total_row.profe_allow += row.profe_allow
            total_row.project_allow += row.project_allow
            total_row.transp_taxable += row.transp_taxable
            total_row.house_allow += row.house_allow
            total_row.transp_nontaxable += row.transp_nontaxable
            total_row.perdiem_taxable_payable += row.perdiem_taxable_payable
            total_row.perdiem_nontaxable_payable += row.perdiem_nontaxable_payable
            total_row.ot_normal_hr += row.ot_normal_hr
            total_row.ot_night_hr += row.ot_night_hr
            total_row.ot_sunday_hr += row.ot_sunday_hr
            total_row.ot_holiday_hr += row.ot_holiday_hr
            total_row.ot_cost += row.ot_cost
            total_row.gross_earned += row.gross_earned
            total_row.taxable_salary += row.taxable_salary
            total_row.income_tax += row.income_tax
            total_row.pension_7 += row.pension_7
            total_row.pension_11 += row.pension_11
            total_row.other_deductions += row.other_deductions
            total_row.total_deductions += row.total_deductions
            total_row.net_pay += row.net_pay
            
        data.append(total_row)
        
    return data
