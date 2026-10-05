"""
Student Attendance Analyzer Using Set Theory
---------------------------------------------
Backend: Python Flask Application (REST API + Static Page Server)

Modules Implemented:
1. Core Web Server & Static Page Routing (Index, Students, Attendance, Subjects, Analysis, Reports)
2. Subject Management (CRUD: GET, POST, PUT, DELETE)
3. Student Management (CRUD: GET, POST, PUT, DELETE)
4. Attendance Recording & Date-Based Retrieval (Linked with Subjects & Date Picker)
5. Set Theory Operations Engine (Dynamic Single-Subject and Two-Subject Comparison Venn Diagrams)
6. Academic Reports (Multi-filtered attendance reports, Individual Student Reports)
7. Excel Report Export (Real .xlsx file generation using openpyxl)
8. Dashboard Analytics & System Status
"""

import os
from datetime import date, datetime
from io import BytesIO
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory, send_file, Response
from flask_cors import CORS
from werkzeug.exceptions import HTTPException
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# Import database helper functions
from database import (
    init_db,
    fetch_all,
    fetch_one,
    execute_query,
    get_db_status
)

# Initialize Flask App
# Static folder points to frontend directory so all HTML/CSS/JS are served directly.
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="")
CORS(app)  # Enable Cross-Origin Resource Sharing for API requests


@app.errorhandler(Exception)
def handle_unexpected_error(error):
    """Keep API failures actionable and JSON-shaped without hiding server errors."""
    if isinstance(error, HTTPException):
        status_code = error.code or 500
        message = error.description
    else:
        app.logger.exception("Unhandled request error")
        status_code = 500
        message = "An unexpected server or database error occurred."

    if request.path.startswith("/api/"):
        return jsonify({"error": message}), status_code
    if isinstance(error, HTTPException):
        return error
    return "Internal server error", 500


# ============================================================================
# 1. FRONTEND PAGE ROUTES
# ============================================================================

@app.route("/")
def index_page():
    """Serves the portal login page."""
    return send_from_directory(FRONTEND_DIR, "login.html")

@app.route("/dashboard")
def dashboard_page():
    """Serves the Dashboard page after portal login."""
    return send_from_directory(FRONTEND_DIR, "index.html")

@app.route("/students")
def students_page():
    """Serves the Student Management page."""
    return send_from_directory(FRONTEND_DIR, "students.html")

@app.route("/attendance")
def attendance_page():
    """Serves the Daily Attendance Marking page."""
    return send_from_directory(FRONTEND_DIR, "attendance.html")

@app.route("/subjects")
def subjects_page():
    """Serves the Subject Management page."""
    return send_from_directory(FRONTEND_DIR, "subjects.html")

@app.route("/analysis")
def analysis_page():
    """Serves the Set Theory Analysis & Venn Diagram page."""
    return send_from_directory(FRONTEND_DIR, "analysis.html")

@app.route("/reports")
def reports_page():
    """Serves the Academic Attendance Reports page."""
    return send_from_directory(FRONTEND_DIR, "reports.html")


# ============================================================================
# 2. SYSTEM & DATABASE STATUS API
# ============================================================================

@app.route("/api/status", methods=["GET"])
def api_status():
    """Returns database connection status and high-level system metadata."""
    db_info = get_db_status()
    student_count_row = fetch_one("SELECT COUNT(*) AS total FROM students")
    subject_count_row = fetch_one("SELECT COUNT(*) AS total FROM subjects")
    dates_count_row = fetch_one("SELECT COUNT(DISTINCT attendance_date) AS total_dates FROM attendance")
    return jsonify({
        "status": "online",
        "database": db_info,
        "total_students": student_count_row["total"] if student_count_row else 0,
        "total_subjects": subject_count_row["total"] if subject_count_row else 0,
        "total_working_days": dates_count_row["total_dates"] if dates_count_row else 0
    })

@app.route("/api/classes", methods=["GET"])
def get_classes():
    """Returns a list of distinct class names and sections."""
    rows = fetch_all("""
        SELECT DISTINCT class_name, section FROM students
        UNION
        SELECT DISTINCT class_name, section FROM subjects
        ORDER BY class_name, section
    """)
    return jsonify({"classes": rows})


# ============================================================================
# 3. SUBJECT MANAGEMENT (CRUD) APIs
# ============================================================================

@app.route("/api/subjects", methods=["GET"])
def get_subjects():
    """
    Fetch all subjects with optional search and class filtering.
    Query parameters:
      - search: string matching subject_name, subject_code, or subject_id
      - class_name: filter by class
      - section: filter by section
    """
    search = request.args.get("search", "").strip()
    class_name = request.args.get("class_name", "").strip()
    section = request.args.get("section", "").strip()

    sql = "SELECT id, subject_id, subject_code, subject_name, class_name, section, created_at FROM subjects WHERE 1=1"
    params = []

    if search:
        sql += " AND (subject_name LIKE %s OR subject_code LIKE %s OR subject_id LIKE %s)"
        pat = f"%{search}%"
        params.extend([pat, pat, pat])

    if class_name:
        sql += " AND class_name = %s"
        params.append(class_name)

    if section:
        sql += " AND section = %s"
        params.append(section)

    sql += " ORDER BY subject_id ASC"
    subjects = fetch_all(sql, tuple(params))
    return jsonify({"subjects": subjects, "count": len(subjects)})


@app.route("/api/subjects/<subject_id>", methods=["GET"])
def get_subject(subject_id):
    """Fetch details of a single subject by subject_id."""
    subject = fetch_one("SELECT * FROM subjects WHERE subject_id = %s", (subject_id,))
    if not subject:
        return jsonify({"error": f"Subject with ID '{subject_id}' not found."}), 404
    return jsonify({"subject": subject})


@app.route("/api/subjects", methods=["POST"])
def add_subject():
    """
    Add a new subject to the database.
    Expected JSON payload:
      {
        "subject_id": "SUB005",
        "subject_code": "CS105",
        "subject_name": "Operating Systems",
        "class_name": "CSE-AI/ML",
        "section": "D"
      }
    """
    data = request.get_json() or {}
    subject_id = data.get("subject_id", "").strip().upper()
    subject_code = data.get("subject_code", "").strip().upper()
    subject_name = data.get("subject_name", "").strip()
    class_name = data.get("class_name", "").strip()
    section = data.get("section", "").strip().upper()

    # Validation
    if not subject_id or not subject_code or not subject_name or not class_name or not section:
        return jsonify({"error": "All fields (subject_id, subject_code, subject_name, class_name, section) are required."}), 400

    # Check for existing duplicate Subject ID
    existing = fetch_one("SELECT id FROM subjects WHERE subject_id = %s", (subject_id,))
    if existing:
        return jsonify({"error": f"Subject ID '{subject_id}' is already registered."}), 409

    # Check duplicate subject code in same class and section
    code_conflict = fetch_one(
        "SELECT id FROM subjects WHERE subject_code = %s AND class_name = %s AND section = %s",
        (subject_code, class_name, section)
    )
    if code_conflict:
        return jsonify({"error": f"Subject Code '{subject_code}' already exists for {class_name} ({section})."}), 409

    sql = """
        INSERT INTO subjects (subject_id, subject_code, subject_name, class_name, section)
        VALUES (%s, %s, %s, %s, %s)
    """
    execute_query(sql, (subject_id, subject_code, subject_name, class_name, section))
    return jsonify({
        "message": f"Subject '{subject_name}' ({subject_code}) added successfully.",
        "subject": {
            "subject_id": subject_id,
            "subject_code": subject_code,
            "subject_name": subject_name,
            "class_name": class_name,
            "section": section
        }
    }), 201


@app.route("/api/subjects/<subject_id>", methods=["PUT"])
def update_subject(subject_id):
    """Update subject details."""
    existing = fetch_one("SELECT * FROM subjects WHERE subject_id = %s", (subject_id,))
    if not existing:
        return jsonify({"error": f"Subject with ID '{subject_id}' not found."}), 404

    data = request.get_json() or {}
    subject_code = data.get("subject_code", existing["subject_code"]).strip().upper()
    subject_name = data.get("subject_name", existing["subject_name"]).strip()
    class_name = data.get("class_name", existing["class_name"]).strip()
    section = data.get("section", existing["section"]).strip().upper()

    if not subject_code or not subject_name or not class_name or not section:
        return jsonify({"error": "Fields cannot be blank."}), 400

    sql = """
        UPDATE subjects
        SET subject_code = %s, subject_name = %s, class_name = %s, section = %s
        WHERE subject_id = %s
    """
    execute_query(sql, (subject_code, subject_name, class_name, section, subject_id))
    return jsonify({"message": f"Subject '{subject_id}' updated successfully."})


@app.route("/api/subjects/<subject_id>", methods=["DELETE"])
def delete_subject(subject_id):
    """Delete subject and associated attendance records."""
    existing = fetch_one("SELECT * FROM subjects WHERE subject_id = %s", (subject_id,))
    if not existing:
        return jsonify({"error": f"Subject with ID '{subject_id}' not found."}), 404

    execute_query("DELETE FROM attendance WHERE subject_id = %s", (subject_id,))
    execute_query("DELETE FROM subjects WHERE subject_id = %s", (subject_id,))
    return jsonify({"message": f"Subject '{existing['subject_name']}' ({subject_id}) deleted successfully."})


# ============================================================================
# 4. STUDENT MANAGEMENT (CRUD) APIs
# ============================================================================

@app.route("/api/students", methods=["GET"])
def get_students():
    """
    Fetch all students with optional search and class filtering.
    Query parameters:
      - search: string to match name, roll number, or student ID
      - class_name: filter by class
      - section: filter by section
    """
    search = request.args.get("search", "").strip()
    class_name = request.args.get("class_name", "").strip()
    section = request.args.get("section", "").strip()

    sql = "SELECT id, student_id, name, roll_number, class_name, section, created_at FROM students WHERE 1=1"
    params = []

    if search:
        sql += " AND (name LIKE %s OR roll_number LIKE %s OR student_id LIKE %s)"
        pat = f"%{search}%"
        params.extend([pat, pat, pat])

    if class_name:
        sql += " AND class_name = %s"
        params.append(class_name)

    if section:
        sql += " AND section = %s"
        params.append(section)

    sql += " ORDER BY student_id ASC"
    students = fetch_all(sql, tuple(params))
    return jsonify({"students": students, "count": len(students)})


@app.route("/api/students/<student_id>", methods=["GET"])
def get_student(student_id):
    """Fetch details of a single student by student_id including per-subject attendance breakdown."""
    student = fetch_one("SELECT * FROM students WHERE student_id = %s", (student_id,))
    if not student:
        return jsonify({"error": f"Student with ID '{student_id}' not found."}), 404

    # Fetch subject-wise summary
    subjects = fetch_all(
        "SELECT * FROM subjects WHERE class_name = %s AND section = %s ORDER BY subject_id ASC",
        (student["class_name"], student["section"])
    )
    subject_summary = []
    total_conducted_all = 0
    total_present_all = 0

    for sub in subjects:
        sub_id = sub["subject_id"]
        # Total classes conducted for this subject
        tot_row = fetch_one(
            "SELECT COUNT(DISTINCT attendance_date) AS total FROM attendance WHERE subject_id = %s",
            (sub_id,)
        )
        total_classes = tot_row["total"] if tot_row else 0

        # Present classes for this student in this subject
        pres_row = fetch_one(
            "SELECT COUNT(*) AS pres FROM attendance WHERE student_id = %s AND subject_id = %s AND status = 'Present'",
            (student_id, sub_id)
        )
        present_count = pres_row["pres"] if pres_row else 0
        absent_count = max(0, total_classes - present_count)
        pct = round((present_count / total_classes * 100), 2) if total_classes > 0 else 0.0

        subject_summary.append({
            "subject_id": sub_id,
            "subject_code": sub["subject_code"],
            "subject_name": sub["subject_name"],
            "total_classes": total_classes,
            "present": present_count,
            "absent": absent_count,
            "percentage": pct
        })
        total_conducted_all += total_classes
        total_present_all += present_count

    overall_pct = round((total_present_all / total_conducted_all * 100), 2) if total_conducted_all > 0 else 0.0

    return jsonify({
        "student": student,
        "subject_summary": subject_summary,
        "overall_percentage": overall_pct,
        "total_classes": total_conducted_all,
        "total_present": total_present_all
    })


@app.route("/api/students", methods=["POST"])
def add_student():
    """
    Add a new student with comprehensive validation.
    Expected JSON payload:
      {
        "student_id": "S011",
        "name": "Karan Verma",
        "roll_number": "21CS11",
        "class_name": "CSE-A",
        "section": "A"
      }
    """
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "A JSON object is required."}), 400

    values = [data.get(key, "") for key in ("student_id", "name", "roll_number", "class_name", "section")]
    if any(not isinstance(value, str) for value in values):
        return jsonify({"error": "Student fields must be text values."}), 400
    student_id, name, roll_number, class_name, section = [value.strip() for value in values]
    student_id = student_id.upper()
    roll_number = roll_number.upper()
    section = section.upper()

    # Required field validation
    if not student_id or not name or not roll_number or not class_name or not section:
        return jsonify({"error": "All fields (Student ID, Name, Roll Number, Class, Section) are required."}), 400

    # Check for existing duplicate Student ID
    existing_id = fetch_one("SELECT id FROM students WHERE student_id = %s", (student_id,))
    if existing_id:
        return jsonify({"error": f"Student ID '{student_id}' is already registered in the system."}), 409

    # Check for existing duplicate Roll Number
    existing_roll = fetch_one("SELECT id FROM students WHERE roll_number = %s", (roll_number,))
    if existing_roll:
        return jsonify({"error": f"Roll Number '{roll_number}' is already registered to another student."}), 409

    sql = """
        INSERT INTO students (student_id, name, roll_number, class_name, section)
        VALUES (%s, %s, %s, %s, %s)
    """
    try:
        execute_query(sql, (student_id, name, roll_number, class_name, section))
    except Exception:
        duplicate = fetch_one(
            "SELECT student_id, roll_number FROM students WHERE student_id = %s OR roll_number = %s",
            (student_id, roll_number)
        )
        if duplicate:
            return jsonify({"error": "Student ID or Roll Number is already registered."}), 409
        raise
    return jsonify({
        "message": "Student added successfully.",
        "student": {
            "student_id": student_id,
            "name": name,
            "roll_number": roll_number,
            "class_name": class_name,
            "section": section
        }
    }), 201


@app.route("/api/students/<student_id>", methods=["PUT"])
def update_student(student_id):
    """Update student details by student_id."""
    existing = fetch_one("SELECT * FROM students WHERE student_id = %s", (student_id,))
    if not existing:
        return jsonify({"error": f"Student '{student_id}' not found."}), 404

    data = request.get_json() or {}
    name = data.get("name", existing["name"]).strip()
    roll_number = data.get("roll_number", existing["roll_number"]).strip().upper()
    class_name = data.get("class_name", existing["class_name"]).strip()
    section = data.get("section", existing["section"]).strip().upper()

    if not name or not roll_number or not class_name or not section:
        return jsonify({"error": "All fields are required."}), 400

    # Check if roll number conflicts with another student
    if roll_number != existing["roll_number"]:
        conflict = fetch_one(
            "SELECT id FROM students WHERE roll_number = %s AND student_id != %s",
            (roll_number, student_id)
        )
        if conflict:
            return jsonify({"error": f"Roll Number '{roll_number}' is already assigned to another student."}), 409

    sql = """
        UPDATE students
        SET name = %s, roll_number = %s, class_name = %s, section = %s
        WHERE student_id = %s
    """
    execute_query(sql, (name, roll_number, class_name, section, student_id))
    return jsonify({"message": f"Student '{student_id}' updated successfully."})


@app.route("/api/students/<student_id>", methods=["DELETE"])
def delete_student(student_id):
    """Delete student and all corresponding attendance records."""
    existing = fetch_one("SELECT * FROM students WHERE student_id = %s", (student_id,))
    if not existing:
        return jsonify({"error": f"Student '{student_id}' not found."}), 404

    execute_query("DELETE FROM attendance WHERE student_id = %s", (student_id,))
    execute_query("DELETE FROM students WHERE student_id = %s", (student_id,))
    return jsonify({"message": f"Student '{student_id}' and all attendance records deleted successfully."})


@app.route("/api/students/sample-data", methods=["POST"])
def load_sample_students_data():
    """Seeds standard student cohort and sample attendance across subjects for testing/demo."""
    sample_students = [
        ('S001', 'Aarav Sharma',  '21CS01', 'CSE-AI/ML', 'D'),
        ('S002', 'Bhavna Patel',  '21CS02', 'CSE-AI/ML', 'D'),
        ('S003', 'Chirag Reddy',  '21CS03', 'CSE-AI/ML', 'D'),
        ('S004', 'Divya Nair',    '21CS04', 'CSE-AI/ML', 'D'),
        ('S005', 'Eshaan Khan',   '21CS05', 'CSE-AI/ML', 'D'),
        ('S006', 'Farhan Ali',    '21CS06', 'CSE-AI/ML', 'D'),
        ('S007', 'Gayatri Joshi', '21CS07', 'CSE-AI/ML', 'D'),
        ('S008', 'Harshitha V',   '21CS08', 'CSE-AI/ML', 'D'),
        ('S009', 'Ishan Gupta',   '21CS09', 'CSE-AI/ML', 'D'),
        ('S010', 'Juhi Mehta',    '21CS10', 'CSE-AI/ML', 'D')
    ]
    added = 0
    for s_id, name, roll, cls, sec in sample_students:
        exists = fetch_one("SELECT id FROM students WHERE student_id = %s OR roll_number = %s", (s_id, roll))
        if not exists:
            execute_query(
                "INSERT INTO students (student_id, name, roll_number, class_name, section) VALUES (%s, %s, %s, %s, %s)",
                (s_id, name, roll, cls, sec)
            )
            added += 1

    # Multi-subject sample attendance
    sample_att = [
        # Mathematics (SUB001) - 2026-09-22
        ('S001', 'SUB001', '2026-09-22', 'Present'), ('S002', 'SUB001', '2026-09-22', 'Present'),
        ('S003', 'SUB001', '2026-09-22', 'Present'), ('S004', 'SUB001', '2026-09-22', 'Present'),
        ('S005', 'SUB001', '2026-09-22', 'Absent'),  ('S006', 'SUB001', '2026-09-22', 'Present'),
        ('S007', 'SUB001', '2026-09-22', 'Present'), ('S008', 'SUB001', '2026-09-22', 'Absent'),
        ('S009', 'SUB001', '2026-09-22', 'Present'), ('S010', 'SUB001', '2026-09-22', 'Present'),
        # Physics (SUB002) - 2026-09-22
        ('S001', 'SUB002', '2026-09-22', 'Present'), ('S002', 'SUB002', '2026-09-22', 'Present'),
        ('S003', 'SUB002', '2026-09-22', 'Present'), ('S004', 'SUB002', '2026-09-22', 'Absent'),
        ('S005', 'SUB002', '2026-09-22', 'Present'), ('S006', 'SUB002', '2026-09-22', 'Present'),
        ('S007', 'SUB002', '2026-09-22', 'Absent'),  ('S008', 'SUB002', '2026-09-22', 'Absent'),
        ('S009', 'SUB002', '2026-09-22', 'Present'), ('S010', 'SUB002', '2026-09-22', 'Present'),
        # Mathematics (SUB001) - 2026-09-25
        ('S001', 'SUB001', '2026-09-25', 'Present'), ('S002', 'SUB001', '2026-09-25', 'Absent'),
        ('S003', 'SUB001', '2026-09-25', 'Present'), ('S004', 'SUB001', '2026-09-25', 'Present'),
        ('S005', 'SUB001', '2026-09-25', 'Absent'),  ('S006', 'SUB001', '2026-09-25', 'Absent'),
        ('S007', 'SUB001', '2026-09-25', 'Present'), ('S008', 'SUB001', '2026-09-25', 'Absent'),
        ('S009', 'SUB001', '2026-09-25', 'Absent'),  ('S010', 'SUB001', '2026-09-25', 'Present'),
        # Physics (SUB002) - 2026-09-25
        ('S001', 'SUB002', '2026-09-25', 'Present'), ('S002', 'SUB002', '2026-09-25', 'Present'),
        ('S003', 'SUB002', '2026-09-25', 'Absent'),  ('S004', 'SUB002', '2026-09-25', 'Present'),
        ('S005', 'SUB002', '2026-09-25', 'Present'), ('S006', 'SUB002', '2026-09-25', 'Present'),
        ('S007', 'SUB002', '2026-09-25', 'Present'), ('S008', 'SUB002', '2026-09-25', 'Absent'),
        ('S009', 'SUB002', '2026-09-25', 'Present'), ('S010', 'SUB002', '2026-09-25', 'Present'),
        # Mathematics (SUB001) - 2026-09-29
        ('S001', 'SUB001', '2026-09-29', 'Present'), ('S002', 'SUB001', '2026-09-29', 'Present'),
        ('S003', 'SUB001', '2026-09-29', 'Absent'),  ('S004', 'SUB001', '2026-09-29', 'Present'),
        ('S005', 'SUB001', '2026-09-29', 'Present'), ('S006', 'SUB001', '2026-09-29', 'Present'),
        ('S007', 'SUB001', '2026-09-29', 'Present'), ('S008', 'SUB001', '2026-09-29', 'Absent'),
        ('S009', 'SUB001', '2026-09-29', 'Absent'),  ('S010', 'SUB001', '2026-09-29', 'Present'),
    ]
    for s_id, sub_id, d, st in sample_att:
        att_exists = fetch_one(
            "SELECT id FROM attendance WHERE student_id = %s AND subject_id = %s AND attendance_date = %s",
            (s_id, sub_id, d)
        )
        if not att_exists:
            execute_query(
                "INSERT INTO attendance (student_id, subject_id, attendance_date, status) VALUES (%s, %s, %s, %s)",
                (s_id, sub_id, d, st)
            )

    return jsonify({"message": f"Sample student cohort loaded ({added} new students added).", "added_count": added})


# ============================================================================
# 5. ATTENDANCE MANAGEMENT APIs
# ============================================================================

@app.route("/api/dates", methods=["GET"])
def get_recorded_dates():
    """Returns list of distinct dates on which attendance has been recorded."""
    subject_id = request.args.get("subject_id", "").strip()
    if subject_id:
        rows = fetch_all(
            "SELECT DISTINCT attendance_date FROM attendance WHERE subject_id = %s ORDER BY attendance_date DESC",
            (subject_id,)
        )
    else:
        rows = fetch_all("SELECT DISTINCT attendance_date FROM attendance ORDER BY attendance_date DESC")
    dates_list = [r["attendance_date"] for r in rows]
    return jsonify({"dates": dates_list})


@app.route("/api/attendance", methods=["GET"])
def get_attendance_sheet():
    """
    Returns student list merged with attendance status for a given date and subject.
    Query parameters:
      - date: YYYY-MM-DD
      - subject_id: specific subject (defaults to first subject in DB)
      - class_name: optional filter by class
      - section: optional filter by section
    """
    attendance_date = request.args.get("date", "").strip()
    subject_id = request.args.get("subject_id", "").strip()
    class_name = request.args.get("class_name", "").strip()
    section = request.args.get("section", "").strip()

    # Determine default subject if none provided
    if not subject_id:
        first_sub = fetch_one("SELECT subject_id FROM subjects ORDER BY subject_id ASC LIMIT 1")
        if first_sub:
            subject_id = first_sub["subject_id"]

    # Subject details
    subject = fetch_one("SELECT * FROM subjects WHERE subject_id = %s", (subject_id,))
    if subject_id and not subject:
        return jsonify({"error": f"Subject '{subject_id}' was not found."}), 404

    if subject:
        class_name = class_name or subject["class_name"]
        section = section or subject["section"]

    # If date is not provided, pick latest recorded date for this subject, or today
    if not attendance_date:
        latest = fetch_one(
            "SELECT MAX(attendance_date) as max_date FROM attendance WHERE subject_id = %s",
            (subject_id,) if subject_id else ()
        )
        if latest and latest["max_date"]:
            attendance_date = str(latest["max_date"])
        else:
            attendance_date = str(date.today())

    # Build student query with LEFT JOIN on attendance for this date & subject
    sql = """
        SELECT 
            s.id,
            s.student_id,
            s.name,
            s.roll_number,
            s.class_name,
            s.section,
            a.status AS status,
            a.attendance_date,
            a.subject_id
        FROM students s
        LEFT JOIN attendance a 
            ON s.student_id = a.student_id 
            AND a.attendance_date = %s
            AND a.subject_id = %s
        WHERE 1=1
    """
    params = [attendance_date, subject_id or ""]

    if class_name:
        sql += " AND s.class_name = %s"
        params.append(class_name)

    if section:
        sql += " AND s.section = %s"
        params.append(section)

    sql += " ORDER BY s.student_id ASC"
    records = fetch_all(sql, tuple(params))

    present_count = sum(1 for r in records if r["status"] == "Present")
    absent_count = sum(1 for r in records if r["status"] == "Absent")
    unmarked_count = sum(1 for r in records if not r["status"])

    return jsonify({
        "date": attendance_date,
        "subject_id": subject_id,
        "subject_name": subject["subject_name"] if subject else "General Attendance",
        "subject_code": subject["subject_code"] if subject else "",
        "class_name": class_name or "All Classes",
        "total_students": len(records),
        "present_count": present_count,
        "absent_count": absent_count,
        "unmarked_count": unmarked_count,
        "records": records
    })


@app.route("/api/attendance", methods=["POST"])
def save_attendance():
    """
    Save or update attendance for students for a specific date and subject.
    Expected JSON payload:
      {
        "date": "2026-09-29",
        "subject_id": "SUB001",
        "records": [
          {"student_id": "S001", "status": "Present"},
          {"student_id": "S002", "status": "Absent"}
        ]
      }
    """
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "A JSON object is required."}), 400

    attendance_date = data.get("date", "")
    subject_id = data.get("subject_id", "")
    records = data.get("records", [])

    if not isinstance(attendance_date, str) or not isinstance(subject_id, str):
        return jsonify({"error": "Date and subject ID must be text values."}), 400
    attendance_date = attendance_date.strip()
    subject_id = subject_id.strip()

    if not attendance_date:
        return jsonify({"error": "Field 'date' (YYYY-MM-DD) is required."}), 400
    try:
        date.fromisoformat(attendance_date)
    except ValueError:
        return jsonify({"error": "Date must be a valid YYYY-MM-DD calendar date."}), 400

    if not subject_id:
        # Fallback to first available subject
        first_sub = fetch_one("SELECT subject_id FROM subjects ORDER BY subject_id ASC LIMIT 1")
        if first_sub:
            subject_id = first_sub["subject_id"]
        else:
            return jsonify({"error": "No subjects found in database. Please create a subject first."}), 400

    if not isinstance(records, list) or len(records) == 0:
        return jsonify({"error": "Field 'records' must be a non-empty list of students."}), 400

    subject = fetch_one("SELECT class_name, section FROM subjects WHERE subject_id = %s", (subject_id,))
    if not subject:
        return jsonify({"error": f"Subject '{subject_id}' was not found."}), 404

    normalized_records = []
    seen_student_ids = set()
    for item in records:
        if not isinstance(item, dict):
            return jsonify({"error": "Every attendance record must be an object."}), 400
        student_id = item.get("student_id", "")
        status = item.get("status", "")
        if not isinstance(student_id, str) or status not in ("Present", "Absent"):
            return jsonify({"error": "Each record needs a student ID and a Present or Absent status."}), 400
        student_id = student_id.strip()
        if not student_id or student_id in seen_student_ids:
            return jsonify({"error": "Student IDs must be non-empty and unique in the attendance batch."}), 400
        student = fetch_one(
            "SELECT student_id FROM students WHERE student_id = %s AND class_name = %s AND section = %s",
            (student_id, subject["class_name"], subject["section"])
        )
        if not student:
            return jsonify({"error": f"Student '{student_id}' is not enrolled in this subject's class and section."}), 400
        seen_student_ids.add(student_id)
        normalized_records.append((student_id, status))

    saved_count = 0
    for student_id, status in normalized_records:
        # Prevent duplicate attendance: Check if record exists for this student + subject + date
        existing = fetch_one(
            "SELECT id FROM attendance WHERE student_id = %s AND subject_id = %s AND attendance_date = %s",
            (student_id, subject_id, attendance_date)
        )

        if existing:
            # Update existing status
            execute_query(
                "UPDATE attendance SET status = %s WHERE id = %s",
                (status, existing["id"])
            )
        else:
            # Insert new attendance record
            execute_query(
                "INSERT INTO attendance (student_id, subject_id, attendance_date, status) VALUES (%s, %s, %s, %s)",
                (student_id, subject_id, attendance_date, status)
            )
        saved_count += 1

    subject_name = fetch_one("SELECT subject_name FROM subjects WHERE subject_id = %s", (subject_id,))["subject_name"]

    return jsonify({
        "message": f"Attendance saved successfully for {saved_count} student(s) in {subject_name} on {attendance_date}.",
        "date": attendance_date,
        "subject_id": subject_id,
        "saved_count": saved_count
    })


# ============================================================================
# 6. SET THEORY ENGINE & VENN DIAGRAM API
# ============================================================================

@app.route("/api/analysis", methods=["GET"])
def set_theory_analysis():
    """
    Set Theory & Venn Diagram Analytics Engine
    -------------------------------------------
    Supports two operating modes:
    1. Single Subject Mode (mode='single' or default):
       - U = Universal Set (all students in cohort)
       - A = Present Students for the selected subject on evaluated date
       - B = Absent Students for the selected subject on evaluated date
       - A ∪ B = U
       - A ∩ B = ∅
       - Attendance % = (A / U) * 100

    2. Two-Subject Comparison Mode (mode='comparison'):
       - A = Students Present in Subject 1
       - B = Students Present in Subject 2
       - A ∩ B = Present in BOTH subjects
       - A - B = Present ONLY in Subject 1
       - B - A = Present ONLY in Subject 2
       - A ∪ B = Present in EITHER subject
       - Outside = Absent in BOTH subjects
    """
    subject_id = request.args.get("subject_id", "").strip()
    subject2_id = request.args.get("subject2_id", "").strip()
    mode = request.args.get("mode", "single").strip().lower()
    analysis_date = request.args.get("date", "").strip()
    class_name = request.args.get("class_name", "").strip()
    section = request.args.get("section", "").strip()

    # Default to first subject if not specified
    if not subject_id:
        first_sub = fetch_one("SELECT subject_id FROM subjects ORDER BY subject_id ASC LIMIT 1")
        if first_sub:
            subject_id = first_sub["subject_id"]

    sub1 = fetch_one("SELECT * FROM subjects WHERE subject_id = %s", (subject_id,)) if subject_id else None
    if subject_id and not sub1:
        return jsonify({"error": f"Subject '{subject_id}' was not found."}), 404

    if sub1:
        class_name = class_name or sub1["class_name"]
        section = section or sub1["section"]

    # Fetch cohort students (Universal Set U)
    sql_cohort = "SELECT id, student_id, name, roll_number, class_name, section FROM students WHERE 1=1"
    cohort_params = []
    if class_name:
        sql_cohort += " AND class_name = %s"
        cohort_params.append(class_name)
    if section:
        sql_cohort += " AND section = %s"
        cohort_params.append(section)
    sql_cohort += " ORDER BY student_id ASC"
    cohort_students = fetch_all(sql_cohort, tuple(cohort_params))
    students_by_id = {s["student_id"]: s for s in cohort_students}
    universal_set_ids = set(students_by_id.keys())

    # Pick date if not specified
    if not analysis_date:
        latest = fetch_one(
            "SELECT MAX(attendance_date) as max_date FROM attendance WHERE subject_id = %s",
            (subject_id,) if subject_id else ()
        )
        if latest and latest["max_date"]:
            analysis_date = str(latest["max_date"])
        else:
            analysis_date = str(date.today())

    def enrich(id_set):
        sorted_ids = sorted(list(id_set))
        return [students_by_id[s_id] for s_id in sorted_ids if s_id in students_by_id]

    # MODE 1: SINGLE SUBJECT (Present A vs Absent B)
    if mode != "comparison" or not subject2_id:
        # Get Present students for this subject & date
        present_rows = fetch_all("""
            SELECT student_id FROM attendance 
            WHERE subject_id = %s AND attendance_date = %s AND status = 'Present'
        """, (subject_id, analysis_date))
        set_a_ids = {r["student_id"] for r in present_rows} & universal_set_ids

        # Get Absent students (or cohort members not marked present)
        absent_rows = fetch_all("""
            SELECT student_id FROM attendance 
            WHERE subject_id = %s AND attendance_date = %s AND status = 'Absent'
        """, (subject_id, analysis_date))
        set_b_explicit_ids = {r["student_id"] for r in absent_rows} & universal_set_ids

        # In set theory: B is Absent students = U - A
        set_b_ids = (universal_set_ids - set_a_ids)

        u_count = len(universal_set_ids)
        a_count = len(set_a_ids)
        b_count = len(set_b_ids)
        pct = round((a_count / u_count * 100), 2) if u_count > 0 else 0.0

        return jsonify({
            "mode": "single",
            "subject": sub1,
            "selected_date": analysis_date,
            "class_name": class_name or "All Classes",
            "universal_count": u_count,
            "present_count": a_count,
            "absent_count": b_count,
            "attendance_percentage": pct,
            "sets": {
                "U": {
                    "label": "Universal Set (U)",
                    "description": "All enrolled students belonging to selected class/section",
                    "count": u_count,
                    "students": enrich(universal_set_ids)
                },
                "A": {
                    "label": "Present Set (A)",
                    "description": f"Students marked Present in {sub1['subject_name'] if sub1 else subject_id} on {analysis_date}",
                    "count": a_count,
                    "students": enrich(set_a_ids)
                },
                "B": {
                    "label": "Absent Set (B)",
                    "description": f"Students marked Absent in {sub1['subject_name'] if sub1 else subject_id} on {analysis_date}",
                    "count": b_count,
                    "students": enrich(set_b_ids)
                },
                "union": {
                    "notation": "A ∪ B",
                    "label": "Union (A ∪ B)",
                    "description": "All evaluated students (A ∪ B = U)",
                    "count": len(set_a_ids | set_b_ids),
                    "students": enrich(set_a_ids | set_b_ids)
                },
                "intersection": {
                    "notation": "A ∩ B",
                    "label": "Intersection (A ∩ B)",
                    "description": "Disjoint sets: A ∩ B = ∅ (No student can be simultaneously Present and Absent)",
                    "count": 0,
                    "students": []
                },
                "diff_A_minus_B": {
                    "notation": "A - B",
                    "label": "Present only (A - B)",
                    "description": "Students present and not absent on the selected date",
                    "count": a_count,
                    "students": enrich(set_a_ids)
                },
                "diff_B_minus_A": {
                    "notation": "B - A",
                    "label": "Absent only (B - A)",
                    "description": "Students absent and not present on the selected date",
                    "count": b_count,
                    "students": enrich(set_b_ids)
                },
                "complement_A": {
                    "notation": "A'",
                    "label": "Complement of A (Absent)",
                    "description": "Students in U who are not in the present set",
                    "count": b_count,
                    "students": enrich(set_b_ids)
                },
                "complement_B": {
                    "notation": "B'",
                    "label": "Complement of B (Present)",
                    "description": "Students in U who are not in the absent set",
                    "count": a_count,
                    "students": enrich(set_a_ids)
                }
            },
            "venn_diagram": {
                "only_A": {
                    "count": a_count,
                    "label": "Present (A)",
                    "students": enrich(set_a_ids)
                },
                "intersection": {
                    "count": 0,
                    "label": "A ∩ B (Disjoint ∅)",
                    "students": []
                },
                "only_B": {
                    "count": b_count,
                    "label": "Absent (B)",
                    "students": enrich(set_b_ids)
                },
                "neither": {
                    "count": 0,
                    "label": "Outside",
                    "students": []
                }
            }
        })

    # MODE 2: TWO-SUBJECT COMPARISON (Subject 1 vs Subject 2)
    sub2 = fetch_one("SELECT * FROM subjects WHERE subject_id = %s", (subject2_id,))
    if not sub2:
        return jsonify({"error": f"Subject '{subject2_id}' was not found."}), 404
    s1_name = sub1["subject_name"] if sub1 else subject_id
    s2_name = sub2["subject_name"] if sub2 else subject2_id

    # Students present in Subject 1 on selected date
    p1_rows = fetch_all("""
        SELECT student_id FROM attendance 
        WHERE subject_id = %s AND attendance_date = %s AND status = 'Present'
    """, (subject_id, analysis_date))
    set_a_ids = {r["student_id"] for r in p1_rows} & universal_set_ids

    # Students present in Subject 2 on selected date
    p2_rows = fetch_all("""
        SELECT student_id FROM attendance 
        WHERE subject_id = %s AND attendance_date = %s AND status = 'Present'
    """, (subject2_id, analysis_date))
    set_b_ids = {r["student_id"] for r in p2_rows} & universal_set_ids

    # Set operations
    intersection_ids = set_a_ids & set_b_ids
    union_ids = set_a_ids | set_b_ids
    only_a_ids = set_a_ids - set_b_ids
    only_b_ids = set_b_ids - set_a_ids
    neither_ids = universal_set_ids - union_ids

    return jsonify({
        "mode": "comparison",
        "subject1": sub1,
        "subject2": sub2,
        "selected_date": analysis_date,
        "class_name": class_name or "All Classes",
        "universal_count": len(universal_set_ids),
        "subject1_present": len(set_a_ids),
        "subject2_present": len(set_b_ids),
        "both_present": len(intersection_ids),
        "only_sub1_present": len(only_a_ids),
        "only_sub2_present": len(only_b_ids),
        "either_present": len(union_ids),
        "neither_present": len(neither_ids),
        "sets": {
            "U": {
                "label": "Universal Set (U)",
                "description": "All registered students in the cohort",
                "count": len(universal_set_ids),
                "students": enrich(universal_set_ids)
            },
            "A": {
                "label": f"Set A ({s1_name})",
                "description": f"Students present in {s1_name}",
                "count": len(set_a_ids),
                "students": enrich(set_a_ids)
            },
            "B": {
                "label": f"Set B ({s2_name})",
                "description": f"Students present in {s2_name}",
                "count": len(set_b_ids),
                "students": enrich(set_b_ids)
            },
            "union": {
                "notation": "A ∪ B",
                "label": "Union (A ∪ B)",
                "description": f"Students present in either {s1_name} OR {s2_name}",
                "count": len(union_ids),
                "students": enrich(union_ids)
            },
            "intersection": {
                "notation": "A ∩ B",
                "label": "Intersection (A ∩ B)",
                "description": f"Students present in BOTH {s1_name} AND {s2_name}",
                "count": len(intersection_ids),
                "students": enrich(intersection_ids)
            },
            "diff_A_minus_B": {
                "notation": "A - B",
                "label": f"Only {s1_name} (A - B)",
                "description": f"Students present only in {s1_name}, absent in {s2_name}",
                "count": len(only_a_ids),
                "students": enrich(only_a_ids)
            },
            "diff_B_minus_A": {
                "notation": "B - A",
                "label": f"Only {s2_name} (B - A)",
                "description": f"Students present only in {s2_name}, absent in {s1_name}",
                "count": len(only_b_ids),
                "students": enrich(only_b_ids)
            },
            "complement_A": {
                "notation": "A'",
                "label": f"Complement of A ({s1_name})",
                "description": f"Students in U not present in {s1_name}",
                "count": len(universal_set_ids - set_a_ids),
                "students": enrich(universal_set_ids - set_a_ids)
            },
            "complement_B": {
                "notation": "B'",
                "label": f"Complement of B ({s2_name})",
                "description": f"Students in U not present in {s2_name}",
                "count": len(universal_set_ids - set_b_ids),
                "students": enrich(universal_set_ids - set_b_ids)
            }
        },
        "venn_diagram": {
            "only_A": {
                "count": len(only_a_ids),
                "label": f"Only {s1_name} (A - B)",
                "students": enrich(only_a_ids)
            },
            "intersection": {
                "count": len(intersection_ids),
                "label": f"A ∩ B (Both)",
                "students": enrich(intersection_ids)
            },
            "only_B": {
                "count": len(only_b_ids),
                "label": f"Only {s2_name} (B - A)",
                "students": enrich(only_b_ids)
            },
            "neither": {
                "count": len(neither_ids),
                "label": "Outside (Absent in Both)",
                "students": enrich(neither_ids)
            }
        }
    })


# ============================================================================
# 7. ACADEMIC REPORTS & EXCEL EXPORT APIs
# ============================================================================

def generate_report_data(student_id=None, class_name=None, section=None, subject_id=None, date_from=None, date_to=None):
    """
    Core report generator that fetches and calculates attendance statistics
    from the database based on filters.
    """
    # 1. Fetch Students
    sql_s = "SELECT student_id, name, roll_number, class_name, section FROM students WHERE 1=1"
    params_s = []
    if student_id:
        sql_s += " AND student_id = %s"
        params_s.append(student_id)
    if class_name:
        sql_s += " AND class_name = %s"
        params_s.append(class_name)
    if section:
        sql_s += " AND section = %s"
        params_s.append(section)
    sql_s += " ORDER BY student_id ASC"
    students = fetch_all(sql_s, tuple(params_s))

    # 2. Fetch Subjects
    sql_sub = "SELECT subject_id, subject_code, subject_name, class_name, section FROM subjects WHERE 1=1"
    params_sub = []
    if subject_id:
        sql_sub += " AND subject_id = %s"
        params_sub.append(subject_id)
    sql_sub += " ORDER BY subject_id ASC"
    subjects = fetch_all(sql_sub, tuple(params_sub))

    report_rows = []

    for s in students:
        s_id = s["student_id"]
        for sub in subjects:
            if sub["class_name"] != s["class_name"] or sub["section"] != s["section"]:
                continue
            sub_id = sub["subject_id"]

            # Query total classes conducted for this subject within date range
            sql_tot = "SELECT COUNT(DISTINCT attendance_date) AS total FROM attendance WHERE subject_id = %s"
            params_tot = [sub_id]
            if date_from:
                sql_tot += " AND attendance_date >= %s"
                params_tot.append(date_from)
            if date_to:
                sql_tot += " AND attendance_date <= %s"
                params_tot.append(date_to)
            tot_row = fetch_one(sql_tot, tuple(params_tot))
            total_classes = tot_row["total"] if tot_row else 0

            # Query classes attended (Present) by this student for this subject
            sql_pres = "SELECT COUNT(*) AS pres FROM attendance WHERE student_id = %s AND subject_id = %s AND status = 'Present'"
            params_pres = [s_id, sub_id]
            if date_from:
                sql_pres += " AND attendance_date >= %s"
                params_pres.append(date_from)
            if date_to:
                sql_pres += " AND attendance_date <= %s"
                params_pres.append(date_to)
            pres_row = fetch_one(sql_pres, tuple(params_pres))
            present_count = pres_row["pres"] if pres_row else 0
            absent_count = max(0, total_classes - present_count)

            pct = round((present_count / total_classes * 100), 2) if total_classes > 0 else 0.0

            report_rows.append({
                "student_id": s["student_id"],
                "roll_number": s["roll_number"],
                "student_name": s["name"],
                "class_name": s["class_name"],
                "section": s["section"],
                "subject_id": sub_id,
                "subject_code": sub["subject_code"],
                "subject_name": sub["subject_name"],
                "total_classes": total_classes,
                "present": present_count,
                "absent": absent_count,
                "percentage": pct,
                "is_eligible": pct >= 75.0
            })

    return report_rows


@app.route("/api/reports/academic", methods=["GET"])
def get_academic_report():
    """Returns calculated student attendance report rows based on selected filters."""
    student_id = request.args.get("student_id", "").strip()
    class_name = request.args.get("class_name", "").strip()
    section = request.args.get("section", "").strip()
    subject_id = request.args.get("subject_id", "").strip()
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()

    try:
        if date_from:
            date.fromisoformat(date_from)
        if date_to:
            date.fromisoformat(date_to)
    except ValueError:
        return jsonify({"error": "Report dates must be valid YYYY-MM-DD calendar dates."}), 400
    if date_from and date_to and date_from > date_to:
        return jsonify({"error": "Date From must be on or before Date To."}), 400

    rows = generate_report_data(
        student_id=student_id or None,
        class_name=class_name or None,
        section=section or None,
        subject_id=subject_id or None,
        date_from=date_from or None,
        date_to=date_to or None
    )
    return jsonify({"report": rows, "count": len(rows)})


@app.route("/api/reports/export-excel", methods=["GET"])
def export_excel_report():
    """
    Generates and downloads a genuine Microsoft Excel (.xlsx) workbook containing
    the filtered student attendance report using openpyxl.
    """
    student_id = request.args.get("student_id", "").strip()
    class_name = request.args.get("class_name", "").strip()
    section = request.args.get("section", "").strip()
    subject_id = request.args.get("subject_id", "").strip()
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()

    rows = generate_report_data(
        student_id=student_id or None,
        class_name=class_name or None,
        section=section or None,
        subject_id=subject_id or None,
        date_from=date_from or None,
        date_to=date_to or None
    )

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Attendance Report"
    ws.views.sheetView[0].showGridLines = True

    # Styling definitions
    font_title = Font(name="Segoe UI", size=16, bold=True, color="1E3A8A")
    font_subtitle = Font(name="Segoe UI", size=10, italic=True, color="475569")
    font_header = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
    font_data = Font(name="Segoe UI", size=10, color="0F172A")
    font_bold = Font(name="Segoe UI", size=10, bold=True, color="0F172A")

    fill_header = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    fill_alt = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    fill_eligible = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
    fill_defaulter = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")

    thin_border = Side(border_style="thin", color="CBD5E1")
    cell_border = Border(top=thin_border, left=thin_border, right=thin_border, bottom=thin_border)

    # 1. Title Banner
    ws.merge_cells("A1:K1")
    title_cell = ws["A1"]
    title_cell.value = "SANDIP UNIVERSITY - STUDENT ATTENDANCE REPORT"
    title_cell.font = font_title
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 35

    # 2. Subtitle with Filter Details
    ws.merge_cells("A2:K2")
    sub_cell = ws["A2"]
    filter_desc = []
    if class_name: filter_desc.append(f"Class: {class_name}")
    if section: filter_desc.append(f"Sec: {section}")
    if subject_id:
        sub_obj = fetch_one("SELECT subject_name FROM subjects WHERE subject_id = %s", (subject_id,))
        filter_desc.append(f"Subject: {sub_obj['subject_name'] if sub_obj else subject_id}")
    if date_from: filter_desc.append(f"From: {date_from}")
    if date_to: filter_desc.append(f"To: {date_to}")
    filter_str = " | ".join(filter_desc) if filter_desc else "All Records"
    sub_cell.value = f"Attendance Filter: {filter_str}  •  Generated on: {datetime.now().strftime('%d-%m-%Y %H:%M')}"
    sub_cell.font = font_subtitle
    sub_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[2].height = 20

    ws.row_dimensions[3].height = 8

    # 3. Table Column Headers
    headers = [
        "S.No",
        "Student ID",
        "Roll Number",
        "Student Name",
        "Class",
        "Section",
        "Subject",
        "Total Classes",
        "Present",
        "Absent",
        "Attendance %"
    ]
    ws.row_dimensions[4].height = 28
    for col_idx, h in enumerate(headers, 1):
        cell = ws.cell(row=4, column=col_idx, value=h)
        cell.font = font_header
        cell.fill = fill_header
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = cell_border

    # 4. Populate Data Rows
    current_row = 5
    for idx, r in enumerate(rows, 1):
        ws.row_dimensions[current_row].height = 22
        vals = [
            idx,
            r["student_id"],
            r["roll_number"],
            r["student_name"],
            r["class_name"],
            r["section"],
            r["subject_name"],
            r["total_classes"],
            r["present"],
            r["absent"],
            f"{r['percentage']}%"
        ]
        for col_idx, val in enumerate(vals, 1):
            cell = ws.cell(row=current_row, column=col_idx, value=val)
            cell.font = font_data
            cell.border = cell_border

            # Alignment
            if col_idx in (1, 8, 9, 10, 11):
                cell.alignment = Alignment(horizontal="center", vertical="center")
            elif col_idx in (2, 3, 5, 6):
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

            # Alternating background
            if idx % 2 == 0:
                cell.fill = fill_alt

        # Highlight attendance percentage cell based on eligibility (>=75%)
        pct_cell = ws.cell(row=current_row, column=11)
        pct_cell.fill = fill_eligible if r["is_eligible"] else fill_defaulter
        pct_cell.font = font_bold

        current_row += 1

    # 5. Summary Row
    if rows:
        ws.row_dimensions[current_row].height = 24
        ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=7)
        sum_label = ws.cell(row=current_row, column=1, value=f"Total Records: {len(rows)} student attendance entry(ies)")
        sum_label.font = font_bold
        sum_label.alignment = Alignment(horizontal="left", vertical="center")

        avg_pct = round(sum(r["percentage"] for r in rows) / len(rows), 2)
        avg_cell = ws.cell(row=current_row, column=11, value=f"Avg: {avg_pct}%")
        avg_cell.font = font_bold
        avg_cell.alignment = Alignment(horizontal="center", vertical="center")

        for c in range(1, 12):
            ws.cell(row=current_row, column=c).border = cell_border

    # Auto-adjust column widths
    for col in ws.columns:
        col_letter = get_column_letter(col[0].column)
        max_len = 0
        for cell in col:
            if cell.row > 2 and cell.value:
                max_len = max(max_len, len(str(cell.value)))
        ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    # Save to memory buffer
    output = BytesIO()
    wb.save(output)
    output.seek(0)

    filename = "Student_Attendance_Report.xlsx"
    return Response(
        output.getvalue(),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# Backwards compatibility endpoints for existing daily and defaulter tabs
@app.route("/api/reports/daily", methods=["GET"])
def report_daily():
    """Daily attendance summary log for all dates."""
    rows = fetch_all("""
        SELECT 
            attendance_date,
            COUNT(DISTINCT student_id) AS total_marked,
            SUM(CASE WHEN status = 'Present' THEN 1 ELSE 0 END) AS present_count,
            SUM(CASE WHEN status = 'Absent' THEN 1 ELSE 0 END) AS absent_count,
            ROUND(SUM(CASE WHEN status = 'Present' THEN 1.0 ELSE 0.0 END) * 100.0 / COUNT(*), 2) AS daily_percentage
        FROM attendance
        GROUP BY attendance_date
        ORDER BY attendance_date DESC
    """)
    return jsonify({"daily_reports": rows})


@app.route("/api/reports/student-wise", methods=["GET"])
def report_student_wise():
    """Student-wise cumulative attendance report."""
    class_name = request.args.get("class_name", "").strip()
    rows = generate_report_data(class_name=class_name or None)
    return jsonify({
        "total_records": len(rows),
        "students": rows
    })


@app.route("/api/reports/defaulters", methods=["GET"])
def report_defaulters():
    """List of students with attendance below 75%."""
    class_name = request.args.get("class_name", "").strip()
    subject_id = request.args.get("subject_id", "").strip()
    rows = generate_report_data(class_name=class_name or None, subject_id=subject_id or None)
    defaulters = [r for r in rows if not r["is_eligible"]]
    return jsonify({
        "threshold": 75.0,
        "total_defaulters": len(defaulters),
        "defaulters": defaulters
    })


# ============================================================================
# 8. DASHBOARD METRICS API
# ============================================================================

@app.route("/api/dashboard", methods=["GET"])
def get_dashboard_data():
    """Returns analytics for the main dashboard."""
    total_students_row = fetch_one("SELECT COUNT(*) AS total FROM students")
    total_students = total_students_row["total"] if total_students_row else 0

    total_subjects_row = fetch_one("SELECT COUNT(*) AS total FROM subjects")
    total_subjects = total_subjects_row["total"] if total_subjects_row else 0

    latest_row = fetch_one("SELECT MAX(attendance_date) AS max_date FROM attendance")
    latest_date = str(latest_row["max_date"]) if latest_row and latest_row["max_date"] else str(date.today())

    daily_stats = fetch_all(
        "SELECT status, COUNT(*) AS count FROM attendance WHERE attendance_date = %s GROUP BY status",
        (latest_date,)
    )
    present_today = 0
    absent_today = 0
    for r in daily_stats:
        if r["status"] == "Present":
            present_today = r["count"]
        elif r["status"] == "Absent":
            absent_today = r["count"]

    report_rows = generate_report_data()
    eligible_students_count = sum(1 for r in report_rows if r["is_eligible"])
    defaulters_count = len(report_rows) - eligible_students_count
    overall_avg_percentage = round(sum(r["percentage"] for r in report_rows) / len(report_rows), 2) if report_rows else 0.0

    trend_rows = fetch_all("""
        SELECT 
            attendance_date,
            SUM(CASE WHEN status = 'Present' THEN 1 ELSE 0 END) AS present_count,
            SUM(CASE WHEN status = 'Absent' THEN 1 ELSE 0 END) AS absent_count,
            COUNT(*) AS total_marked
        FROM attendance
        GROUP BY attendance_date
        ORDER BY attendance_date DESC
        LIMIT 7
    """)
    trend_rows.reverse()

    return jsonify({
        "metrics": {
            "total_students": total_students,
            "total_subjects": total_subjects,
            "latest_date": latest_date,
            "present_today": present_today,
            "absent_today": absent_today,
            "students_above_75": eligible_students_count,
            "defaulters_below_75": defaulters_count,
            "overall_avg_percentage": overall_avg_percentage,
            "total_working_days": len(trend_rows)
        },
        "trends": trend_rows
    })


# ============================================================================
# MAIN APPLICATION RUNNER
# ============================================================================

if __name__ == "__main__":
    print("=" * 65)
    print("  Student Attendance Analyzer Using Set Theory - Flask Server")
    print("=" * 65)
    success, msg = init_db()
    print(f"[*] Database Status: {msg}")
    print("[*] Server starting at: http://127.0.0.1:5000")
    print("[*] Open your browser and navigate to: http://127.0.0.1:5000")
    print("=" * 65)
    app.run(host="127.0.0.1", port=5000, debug=True)
