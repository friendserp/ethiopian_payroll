# Copyright (c) 2025, Friends ERP and contributors
# For license information, please see license.txt

import frappe
import json
import os
from frappe.model.document import Document


class PayMatrix(Document):
	pass


@frappe.whitelist()
def update_pay_matrix_level(level_name, grade, pay_matrix_link, scales_data):
	"""Update Pay Matrix Level with custom scales data"""
	try:
		# Get the document
		doc = frappe.get_doc("Pay Matrix Level", level_name)
		
		# Update main fields
		doc.grade = grade or ""
		doc.pay_matrix_link = pay_matrix_link or ""
		
		# Clear existing scales
		doc.scales = []
		
		# Add new scales
		if scales_data:
			if isinstance(scales_data, str):
				scales_data = json.loads(scales_data)
			
			for scale_row in scales_data:
				if scale_row.get("scale") is not None and scale_row.get("amount") is not None:
					doc.append("scales", {
						"scale": scale_row["scale"],
						"amount": scale_row["amount"]
					})
		
		# Save the document
		doc.save()
		frappe.db.commit()
		
		return {"success": True, "message": "Pay Matrix Level updated successfully"}
	except Exception as e:
		frappe.log_error(f"Error updating Pay Matrix Level: {str(e)}")
		return {"success": False, "message": str(e)}


def load_matrix_data():
	"""Load matrix data from JSON file"""
	try:
		# Get the path to the JSON file
		file_path = os.path.join(
			os.path.dirname(__file__),
			"standard_matrix_data.json"
		)
		
		with open(file_path, "r") as f:
			data = json.load(f)
			return data.get("matrix_data", {})
	except Exception as e:
		frappe.log_error(f"Error loading matrix data: {str(e)}")
		# Fallback to hardcoded data (using numeric grade keys)
		return {
			"1": [4905, 5346, 5828, 6352, 6924, 7547, 8226, 8967, 9774, 10653, 11612, 12657, 13796, 15038, 16391, 17866, 19474, 21227, 23137, 25220, 27490, 29964],
			"2": [5690, 6202, 6760, 7368, 8032, 8754, 9542, 10401, 11337, 12358, 13470, 14682, 16004, 17444, 19014, 20725, 22590, 24623, 26839, 29255, 31888, 34758],
			"3": [6600, 7194, 7842, 8547, 9317, 10155, 11069, 12065, 13151, 14335, 15625, 17031, 18564, 20235, 22056, 24041, 26205, 28563, 31134, 33936, 36990, 40319],
			"4": [7656, 8345, 9096, 9915, 10807, 11780, 12840, 13996, 15255, 16628, 18125, 19756, 21534, 23472, 25585, 27888, 30397, 33133, 36115, 39366, 42908, 46770],
			"5": [8881, 9680, 10552, 11501, 12537, 13665, 14895, 16235, 17696, 19289, 21025, 22917, 24980, 27228, 29678, 32350, 35261, 38435, 41894, 45664, 49774, 54253],
			"6": [10208, 11024, 11906, 12859, 13887, 14998, 16198, 17494, 18894, 20405, 22038, 23801, 25705, 27761, 29982, 32380, 34971, 37769, 40790, 44053, 47577, 51384],
			"7": [11841, 12788, 13811, 14916, 16109, 17398, 18790, 20293, 21917, 23670, 25564, 27609, 29817, 32203, 34779, 37561, 40566, 43811, 47316, 51102, 55190, 59605],
			"8": [13735, 14834, 16021, 17303, 18687, 20182, 21796, 23540, 25423, 27457, 29654, 32026, 34588, 37355, 40344, 43571, 47057, 50821, 54887, 59278, 64020, 69142],
			"9": [15933, 17208, 18584, 20071, 21677, 23411, 25284, 27307, 29491, 31850, 34398, 37150, 40122, 43332, 46799, 50542, 54586, 58953, 63669, 68762, 74263, 80205],
			"10": [18311, 19593, 20965, 22432, 24002, 25682, 27480, 29404, 31462, 33665, 36021, 38542, 41240, 44127, 47216, 50521, 54058, 57842, 61891, 66223, 70859, 75819],
			"11": [21241, 22728, 24319, 26021, 27843, 29792, 31877, 34109, 36496, 39051, 41784, 44709, 47839, 51188, 54771, 58605, 62707, 67097, 71793, 76819, 82196, 87950],
			"12": [24640, 26364, 28210, 30185, 32298, 34558, 36977, 39566, 42335, 45299, 48470, 51863, 55493, 59378, 63534, 67982, 72740, 77832, 83280, 89110, 95348, 102022],
			"13": [28315, 30014, 31815, 33723, 35747, 37892, 40165, 42575, 45130, 47837, 50708, 53750, 56975, 60394, 64017, 67858, 71930, 76245, 80820, 85669, 90810, 96258],
			"14": [32845, 34816, 36905, 39119, 41466, 43954, 46592, 49387, 52350, 55491, 58821, 62350, 66091, 70057, 74260, 78715, 83438, 88445, 93751, 99376, 105339, 111659],
			"15": [38100, 40386, 42810, 45378, 48101, 50987, 54046, 57289, 60726, 64370, 68232, 72326, 76666, 81266, 86141, 91310, 96789, 102596, 108752, 115277, 122193, 129525],
			"16": [44197, 46848, 49659, 52639, 55797, 59145, 62694, 66455, 70443, 74669, 79149, 83898, 88932, 94268, 99924, 105920, 112275, 119011, 126152, 133721, 141744, 150249],
			"17": [51268, 54344, 57605, 61061, 64725, 68608, 72725, 77088, 81713, 86616, 91813, 97322, 103161, 109351, 115912, 122867, 130239, 138053, 146336, 155116, 164423, 174289],
			"18": [59471, 63039, 66821, 70831, 75081, 79585, 84361, 89422, 94788, 100475, 106503, 112893, 119667, 126847, 134458, 142525, 151077, 160142, 169750, 179935, 190731, 202175]
		}


@frappe.whitelist()
def create_standard_pay_matrix():
	"""Create Standard Pay Matrix with the provided data from JSON"""
	try:
		# Check if Standard already exists - delete and recreate if it does
		if frappe.db.exists("Pay Matrix", "Standard"):
			# Delete all related Pay Matrix Levels first
			levels = frappe.get_all("Pay Matrix Level", filters={"pay_matrix_link": "Standard"}, pluck="name")
			for level_name in levels:
				frappe.delete_doc("Pay Matrix Level", level_name, force=1, ignore_permissions=True)
			frappe.delete_doc("Pay Matrix", "Standard", force=1, ignore_permissions=True)
			frappe.db.commit()
		
		# Create Pay Matrix (without CPC field)
		pay_matrix = frappe.get_doc({
			"doctype": "Pay Matrix",
			"pm": "Standard"
		})
		pay_matrix.insert(ignore_permissions=True)
		frappe.db.commit()
		
		# Load matrix data from JSON
		matrix_data = load_matrix_data()
		
		# First, fetch all existing Employee Grades
		existing_grades = frappe.get_all("Employee Grade", fields=["name"], order_by="name asc")
		existing_grade_names = {grade.name for grade in existing_grades}
		
		# Create a mapping of grade numbers to grade names
		# Grades might be named as "1", "2", "3" or "Grade 1", "Grade 2", etc.
		grade_map = {}
		for grade in existing_grades:
			grade_name = grade.name
			# Try to extract number from grade name
			# Handle both "1" and "Grade 1" formats
			if grade_name.isdigit():
				grade_map[grade_name] = grade_name
			elif grade_name.startswith("Grade "):
				grade_num = grade_name.replace("Grade ", "").strip()
				if grade_num.isdigit():
					grade_map[grade_num] = grade_name
		
		# Create Pay Matrix Levels only for grades that exist and match JSON
		created_levels = 0
		skipped_grades = []
		matched_grades = []
		
		for grade_num_str, scale_amounts in matrix_data.items():
			# Check if this grade exists in the system
			if grade_num_str in grade_map:
				grade_name = grade_map[grade_num_str]
				matched_grades.append(grade_name)
				
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
						"amount": float(amount)
					})
				
				level_doc.insert(ignore_permissions=True)
				frappe.db.commit()
				created_levels += 1
			else:
				skipped_grades.append(grade_num_str)
		
		# Build message
		message = f"Standard Pay Matrix created successfully! Created {created_levels} grade levels with 22 scales each."
		
		if matched_grades:
			message += f"\n\nMatched grades: {', '.join(sorted(matched_grades, key=lambda x: int(x) if x.isdigit() else int(x.replace('Grade ', '').strip()) if x.startswith('Grade ') else 999))}"
		
		if skipped_grades:
			message += f"\n\nSkipped grades (not found in system): {', '.join(sorted(skipped_grades, key=int))}"
			message += f"\nPlease create Employee Grades with names: {', '.join(sorted(skipped_grades, key=int))}"
		
		frappe.msgprint(message, indicator="green")
		return {"success": True, "message": message, "created": created_levels, "skipped": len(skipped_grades)}
	except Exception as e:
		frappe.log_error(f"Error creating Standard Pay Matrix: {str(e)}")
		frappe.msgprint(f"Error: {str(e)}", indicator="red")
		return {"success": False, "message": str(e)}
