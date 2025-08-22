import csv

# ======================
# 1. Generate subjects.txt
# ======================
subjects = ["Telugu", "Hindi", "English", "Maths", "Science", "Social"]

with open("subjects.txt", "w") as f:
    for subject in subjects:
        f.write(subject + "\n")

print("✅ subjects.txt created with subjects:", subjects)

# ======================
# 2. Generate marks_sample.csv
# ======================
sample_marks = [
    ["student_id", "subject", "marks", "class", "section", "submitted_by"],
    ["S001", "Telugu", 85, "6", "A", "teacher1@school.com"],
    ["S001", "Maths", 92, "6", "A", "teacher1@school.com"],
    ["S002", "English", 78, "6", "A", "teacher2@school.com"],
    ["S003", "Science", 88, "7", "B", "teacher1@school.com"],
    ["S004", "Social", 67, "7", "B", "teacher2@school.com"]
]

with open("marks_sample.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerows(sample_marks)

print("✅ marks_sample.csv created with sample marks.")
