import frappe

def run():
    ss = frappe.get_doc('Salary Slip','Sal Slip/HR-EMP-00020/00003')
    print('\n=== Earnings')
    for d in ss.earnings:
        print(f"{d.salary_component}: {d.amount}")
    print('\n=== Deductions')
    for d in ss.deductions:
        print(f"{d.salary_component}: {d.amount}")
