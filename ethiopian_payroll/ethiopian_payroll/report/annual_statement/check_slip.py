import frappe


def run():
    ss_name = "Sal Slip/HR-EMP-00020/00003"
    ss = frappe.get_doc("Salary Slip", ss_name)

    print(f"\n=== Salary Slip: {ss_name} ===")
    print(f"Employee: {ss.employee} - {ss.employee_name}")
    print(f"Start Date: {ss.start_date}, End Date: {ss.end_date}")

    print(f"\n=== EARNINGS ===")
    for d in ss.earnings:
        print(f"  {d.salary_component}: {d.amount}")

    print(f"\n=== DEDUCTIONS ===")
    for d in ss.deductions:
        print(f"  {d.salary_component}: {d.amount}")

    print(f"\n=== HOUSE RENT RELATED COMPONENTS ===")
    related = []
    for d in ss.earnings:
        key = d.salary_component.lower()
        if any(k in key for k in ["house", "rent", "water", "garbage", "servant", "parking"]):
            related.append(f"EARNING: {d.salary_component} = {d.amount}")
    for d in ss.deductions:
        key = d.salary_component.lower()
        if any(k in key for k in ["house", "rent", "water", "garbage", "servant", "parking"]):
            related.append(f"DEDUCTION: {d.salary_component} = {d.amount}")

    if related:
        for line in related:
            print(f"  {line}")
    else:
        print("  None")

