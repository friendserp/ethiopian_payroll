# Copyright (c) 2026, Sami and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {"label": _("NO"), "fieldname": "idx", "fieldtype": "Int", "width": 50},
        {"label": _("Employee Name"), "fieldname": "employee_name", "fieldtype": "Data", "width": 200},
        {"label": _("Job Title"), "fieldname": "designation", "fieldtype": "Data", "width": 180},
        {"label": _("Account / Phone No"), "fieldname": "bank_account_no", "fieldtype": "Data", "width": 180},
        {"label": _("Net Pay"), "fieldname": "net_pay", "fieldtype": "Currency", "width": 150}
    ]

def get_data(filters):
    data = []
    
    # First, get Payroll Entries based on status filter
    payroll_entry_filters = {}
    
    if filters.get("project"):
        payroll_entry_filters["project"] = filters.get("project")
    
    if filters.get("from_date"):
        payroll_entry_filters["start_date"] = [">=", filters.get("from_date")]
    if filters.get("to_date"):
        payroll_entry_filters["end_date"] = ["<=", filters.get("to_date")]
    
    # Handle Status Filter on Payroll Entry's custom_employee_type
    status = filters.get("status")
    if status:
        if status == "Active":
            # Get Payroll Entries where custom_employee_type is not "Left"
            payroll_entry_filters["custom_employee_type"] = ["!=", "Left"]
        elif status == "Left":
            # Get Payroll Entries where custom_employee_type is "Left"
            payroll_entry_filters["custom_employee_type"] = "Left"
    
    # Get filtered Payroll Entries
    payroll_entries = frappe.get_all("Payroll Entry", 
        filters=payroll_entry_filters,
        pluck="name"
    )
    
    if not payroll_entries:
        return []
    
    # Now filter Salary Slips by these Payroll Entries
    ss_filters = {
        "docstatus": 1,
        "company": filters.get("company"),
        "payroll_entry": ["in", payroll_entries]
    }
    
    # Apply date filters to salary slips as well
    if filters.get("from_date"):
        ss_filters["start_date"] = [">=", filters.get("from_date")]
    if filters.get("to_date"):
        ss_filters["end_date"] = ["<=", filters.get("to_date")]

    salary_slips = frappe.get_all("Salary Slip", 
        filters=ss_filters,
        fields=["employee", "employee_name", "designation", "net_pay"],
        order_by="employee_name"
    )

    if not salary_slips:
        return []

    # Fetch needed employee details in one go
    employees = [ss.employee for ss in salary_slips]
    employee_details = frappe.get_all("Employee",
        filters={"name": ["in", employees]},
        fields=["name", "bank_name", "bank_ac_no", "custom_mobile_no"]
    )
    emp_map = {e.name: e for e in employee_details}

    mode_of_payment = filters.get("mode_of_payment")
    total_net_pay = 0
    idx = 1
    for ss in salary_slips:
        emp = emp_map.get(ss.employee, {})
        bank_name = emp.get("bank_name")
        bank_ac_no = emp.get("bank_ac_no")
        mobile_no = emp.get("custom_mobile_no")

        # Determine if it is a phone-based payment (CBE Birr) - handle case variations
        is_cbe_birr = (bank_name and bank_name.lower() == "cbe birr")

        # Apply filtering
        if mode_of_payment == "Bank":
            # Show only those that are NOT CBE Birr
            if is_cbe_birr:
                continue
        elif mode_of_payment == "Phone No":
            # Show only those that ARE CBE Birr
            if not is_cbe_birr:
                continue
        
        # Determine account display: mobile for CBE Birr, bank_ac_no for others
        display_account = mobile_no if is_cbe_birr else bank_ac_no

        row = frappe._dict({
            "idx": idx,
            "employee_name": ss.employee_name,
            "designation": ss.designation,
            "bank_account_no": display_account,
            "net_pay": ss.net_pay
        })
        data.append(row)
        total_net_pay += flt(ss.net_pay)
        idx += 1
        
    if data:
        data.append({
            "idx": "",
            "employee_name": _("Total"),
            "designation": "",
            "bank_account_no": "",
            "net_pay": total_net_pay,
            "is_total_row": True
        })
        
    return data
