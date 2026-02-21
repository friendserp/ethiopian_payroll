# Copyright (c) 2025, Friends ERP and contributors
# For license information, please see license.txt

"""
Script to create the Project and Head Office Pay Matrices
Run this via: bench --site [site-name] execute ethiopian_payroll.config.ethiopian_payroll.create_matrices.create
"""

import frappe
import json
import os


def create():
	"""Create Project and Head Office Pay Matrices from JSON data"""
	try:
		# Load JSON data from the data folder
		json_path = os.path.join(frappe.get_app_path("ethiopian_payroll.ethiopian_payroll"), "data", "pay_matrix.json")
		
		if not os.path.exists(json_path):
			frappe.msgprint(f"JSON file not found at {json_path}")
			return {"success": False, "message": "JSON file not found"}
		
		with open(json_path, 'r') as f:
			data = json.load(f)
		
		matrices_data = data.get("matrices", {})
		results = []
		
		# Create each matrix
		for matrix_key, matrix_info in matrices_data.items():
			result = create_pay_matrix(
				matrix_name=matrix_info["name"],
				matrix_data=matrix_info["data"]
			)
			results.append(result)
		
		# Summary
		success_count = sum(1 for r in results if r.get("success"))
		print(f"\n{'='*50}")
		print(f"✅ Created {success_count} out of {len(results)} Pay Matrices successfully!")
		print(f"{'='*50}")
		
		return {"success": True, "results": results}
	
	except Exception as e:
		frappe.log_error(f"Error creating Pay Matrices: {str(e)}")
		print(f"❌ Error: {str(e)}")
		import traceback
		traceback.print_exc()
		return {"success": False, "message": str(e)}


def create_pay_matrix(matrix_name, matrix_data):
	"""Create a single pay matrix with the given data"""
	try:
		# Check if matrix already exists
		if frappe.db.exists("Pay Matrix", matrix_name):
			print(f"Pay Matrix '{matrix_name}' already exists. Deleting and recreating...")
			# Delete all related Pay Matrix Levels first
			levels = frappe.get_all("Pay Matrix Level", filters={"pay_matrix_link": matrix_name}, pluck="name")
			for level_name in levels:
				frappe.delete_doc("Pay Matrix Level", level_name, force=1, ignore_permissions=True)
			frappe.delete_doc("Pay Matrix", matrix_name, force=1, ignore_permissions=True)
			frappe.db.commit()
		
		# Create Pay Matrix (without CPC field)
		pay_matrix = frappe.get_doc({
			"doctype": "Pay Matrix",
			"pm": matrix_name
		})
		pay_matrix.insert(ignore_permissions=True)
		frappe.db.commit()
		
		print(f"Created Pay Matrix: {pay_matrix.name}")
		
		# Create Pay Matrix Levels for each grade
		grades_created = 0
		scales_count = 0
		
		for grade_level, scale_amounts in matrix_data.items():
			# Get or create Employee Grade
			grade_name = grade_level
			if not frappe.db.exists("Employee Grade", grade_name):
				grade_doc = frappe.get_doc({
					"doctype": "Employee Grade",
					"grade_name": grade_name  # Adjust field name as per your doctype
				})
				grade_doc.insert(ignore_permissions=True)
				frappe.db.commit()
				print(f"Created Employee Grade: {grade_name}")
			
			# Create Pay Matrix Level
			level_doc = frappe.get_doc({
				"doctype": "Pay Matrix Level",
				"grade": grade_name,
				"pay_matrix_link": pay_matrix.name
			})
			
			# Add scales (1-22)
			for scale_num, amount in enumerate(scale_amounts, start=1):
				level_doc.append("scales", {
					"scale": scale_num,
					"amount": amount
				})
				scales_count += 1
			
			level_doc.insert(ignore_permissions=True)
			frappe.db.commit()
			grades_created += 1
			print(f"Created Pay Matrix Level for {grade_name} with {len(scale_amounts)} scales")
		
		print(f"\n✅ Pay Matrix '{matrix_name}' created successfully!")
		print(f"   - Grades: {grades_created}")
		print(f"   - Total Scales: {scales_count}")
		
		return {
			"success": True,
			"matrix_name": matrix_name,
			"grades": grades_created,
			"scales": scales_count
		}
	
	except Exception as e:
		frappe.log_error(f"Error creating Pay Matrix '{matrix_name}': {str(e)}")
		print(f"❌ Error creating '{matrix_name}': {str(e)}")
		return {
			"success": False,
			"matrix_name": matrix_name,
			"message": str(e)
		}


def delete_all_matrices():
	"""Delete all pay matrices (utility function)"""
	try:
		matrices = frappe.get_all("Pay Matrix", pluck="name")
		for matrix_name in matrices:
			levels = frappe.get_all("Pay Matrix Level", filters={"pay_matrix_link": matrix_name}, pluck="name")
			for level_name in levels:
				frappe.delete_doc("Pay Matrix Level", level_name, force=1, ignore_permissions=True)
			frappe.delete_doc("Pay Matrix", matrix_name, force=1, ignore_permissions=True)
			frappe.db.commit()
			print(f"Deleted matrix: {matrix_name}")
		print(f"✅ Deleted {len(matrices)} matrices")
	except Exception as e:
		print(f"❌ Error: {str(e)}")


# Hook functions
def after_install():
	"""Run after app installation"""
	try:
		print("\n" + "="*50)
		print("Creating Pay Matrices after app installation...")
		print("="*50)
		
		result = create()
		
		if result.get("success"):
			print("\n✅ Pay Matrices created successfully during installation!")
		else:
			print(f"\n❌ Failed to create pay matrices: {result.get('message')}")
	
	except Exception as e:
		print(f"Error in after_install hook: {str(e)}")
		frappe.log_error(f"after_install hook error: {str(e)}")


def after_migrate():
	"""Run after migrate to ensure matrices exist"""
	try:
		# Check if matrices exist, create if they don't
		if not frappe.db.exists("Pay Matrix", "Project") or not frappe.db.exists("Pay Matrix", "Head Office"):
			print("\n" + "="*50)
			print("Creating missing Pay Matrices after migrate...")
			print("="*50)
			
			result = create()
			
			if result.get("success"):
				print("\n✅ Missing pay matrices created successfully!")
			else:
				print(f"\n❌ Failed to create pay matrices: {result.get('message')}")
	
	except Exception as e:
		print(f"Error in after_migrate hook: {str(e)}")
		frappe.log_error(f"after_migrate hook error: {str(e)}")